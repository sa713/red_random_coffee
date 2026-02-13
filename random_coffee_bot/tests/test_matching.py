from matching.algorithm import make_pairs


def test_strict_no_repeats() -> None:
    users = [1, 2, 3, 4]
    recent = {frozenset((1, 2)): 100.0}
    result = make_pairs(users, recent, skip_counts={})
    assert len(result.pairs) == 2
    assert frozenset((1, 2)) not in {frozenset(p) for p in result.pairs}
    assert result.skipped == []


def test_odd_rotates_skip() -> None:
    users = [1, 2, 3]
    result = make_pairs(users, recent_pairs={}, skip_counts={1: 3, 2: 0, 3: 2})
    assert result.skipped == [2]


def test_relaxed_when_strict_impossible() -> None:
    users = [1, 2, 3, 4]
    recent = {
        frozenset((1, 2)): 10.0,
        frozenset((1, 3)): 11.0,
        frozenset((1, 4)): 12.0,
    }
    result = make_pairs(users, recent, skip_counts={})
    assert len(result.pairs) == 2
    assert any(1 in p for p in result.pairs)
