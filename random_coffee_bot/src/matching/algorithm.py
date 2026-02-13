from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MatchResult:
    pairs: list[tuple[int, int]]
    skipped: list[int]
    repeated_pairs: set[frozenset[int]]


def _sort_pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _select_skip(users: list[int], skip_counts: dict[int, int]) -> int:
    # Меньше пропусков в прошлом -> выше шанс пропустить сейчас (ротация).
    ranked = sorted(users, key=lambda u: (skip_counts.get(u, 0), u))
    return ranked[0]


def _greedy_pair(
    users: list[int],
    allowed_fn,
) -> tuple[list[tuple[int, int]], list[int]]:
    remaining = users[:]
    pairs: list[tuple[int, int]] = []

    while len(remaining) > 1:
        options_count: dict[int, int] = {}
        for u in remaining:
            options_count[u] = sum(1 for v in remaining if v != u and allowed_fn(u, v))

        remaining.sort(key=lambda u: (options_count[u], u))
        u = remaining[0]
        candidates = [v for v in remaining[1:] if allowed_fn(u, v)]
        if not candidates:
            return pairs, remaining

        # Выбираем партнера, у которого меньше вариантов дальше.
        def candidate_score(v: int) -> tuple[int, int]:
            left = [x for x in remaining if x not in {u, v}]
            count = sum(1 for x in left if allowed_fn(v, x))
            return (count, v)

        v = sorted(candidates, key=candidate_score)[0]
        pairs.append(_sort_pair(u, v))
        remaining = [x for x in remaining if x not in {u, v}]

    return pairs, remaining


def make_pairs(
    user_ids: list[int],
    recent_pairs: dict[frozenset[int], float],
    skip_counts: dict[int, int],
) -> MatchResult:
    users = sorted(set(user_ids))
    if len(users) < 2:
        return MatchResult(pairs=[], skipped=users, repeated_pairs=set())

    skipped: list[int] = []
    strict_users = users[:]
    if len(strict_users) % 2 == 1:
        skip_user = _select_skip(strict_users, skip_counts)
        strict_users.remove(skip_user)
        skipped = [skip_user]

    def strict_allowed(u: int, v: int) -> bool:
        return frozenset((u, v)) not in recent_pairs

    strict_pairs, unpaired = _greedy_pair(strict_users, strict_allowed)
    if not unpaired:
        return MatchResult(pairs=strict_pairs, skipped=skipped, repeated_pairs=set())

    # Ослабление: для оставшихся выбираем пары с минимальным весом повтора.
    pool = unpaired[:]
    repeated: set[frozenset[int]] = set()
    relaxed_pairs = strict_pairs[:]

    while len(pool) > 1:
        u = pool[0]
        candidates = pool[1:]

        def weight(v: int) -> tuple[float, int]:
            pair_key = frozenset((u, v))
            # Чем меньше timestamp, тем старее повтор и тем лучше.
            return (recent_pairs.get(pair_key, -1.0), v)

        v = sorted(candidates, key=weight)[0]
        pair_key = frozenset((u, v))
        if pair_key in recent_pairs:
            repeated.add(pair_key)
        relaxed_pairs.append(_sort_pair(u, v))
        pool = [x for x in pool if x not in {u, v}]

    skipped.extend(pool)
    return MatchResult(pairs=relaxed_pairs, skipped=skipped, repeated_pairs=repeated)
