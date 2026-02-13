from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from db.connection import Database


@dataclass(slots=True)
class User:
    user_id: int
    username: str
    office: str | None
    is_active: bool


@dataclass(slots=True)
class RoundRecord:
    id: int
    week_id: str
    draw_at: datetime
    status: str
    reminders_sent_at: datetime | None


def utc_now() -> datetime:
    return datetime.utcnow()


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


class Repository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_user(self, user_id: int, username: str, office: str | None, is_active: bool = True) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO users(user_id, username, office, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    office=COALESCE(excluded.office, users.office),
                    is_active=excluded.is_active,
                    updated_at=excluded.updated_at
                """,
                (user_id, username, office, int(is_active), now, now),
            )

    def get_user(self, user_id: int) -> User | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT user_id, username, office, is_active FROM users WHERE user_id=?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return User(
            user_id=row["user_id"],
            username=row["username"],
            office=row["office"],
            is_active=bool(row["is_active"]),
        )

    def set_user_office(self, user_id: int, office: str) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET office=?, updated_at=? WHERE user_id=?",
                (office, now, user_id),
            )

    def set_user_active(self, user_id: int, is_active: bool) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET is_active=?, updated_at=? WHERE user_id=?",
                (int(is_active), now, user_id),
            )

    def list_active_users(self) -> list[User]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT user_id, username, office, is_active FROM users WHERE is_active=1"
            ).fetchall()
        return [
            User(
                user_id=r["user_id"],
                username=r["username"],
                office=r["office"],
                is_active=bool(r["is_active"]),
            )
            for r in rows
        ]

    def get_or_create_round(self, week_id: str, draw_at: datetime) -> RoundRecord:
        now = iso(utc_now())
        draw_at_s = iso(draw_at)
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO rounds(week_id, draw_at, status, created_at, updated_at)
                VALUES (?, ?, 'planned', ?, ?)
                ON CONFLICT(week_id) DO NOTHING
                """,
                (week_id, draw_at_s, now, now),
            )
            row = conn.execute(
                "SELECT id, week_id, draw_at, status, reminders_sent_at FROM rounds WHERE week_id=?",
                (week_id,),
            ).fetchone()
        assert row is not None
        return RoundRecord(
            id=row["id"],
            week_id=row["week_id"],
            draw_at=datetime.fromisoformat(row["draw_at"]),
            status=row["status"],
            reminders_sent_at=parse_dt(row["reminders_sent_at"]),
        )

    def get_round_by_week(self, week_id: str) -> RoundRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT id, week_id, draw_at, status, reminders_sent_at FROM rounds WHERE week_id=?",
                (week_id,),
            ).fetchone()
        if not row:
            return None
        return RoundRecord(
            id=row["id"],
            week_id=row["week_id"],
            draw_at=datetime.fromisoformat(row["draw_at"]),
            status=row["status"],
            reminders_sent_at=parse_dt(row["reminders_sent_at"]),
        )

    def mark_round_running(self, round_id: int) -> bool:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            row = conn.execute("SELECT status FROM rounds WHERE id=?", (round_id,)).fetchone()
            if not row:
                return False
            status = row["status"]
            if status == "done":
                return False
            conn.execute(
                "UPDATE rounds SET status='running', updated_at=? WHERE id=?",
                (now, round_id),
            )
        return True

    def mark_round_done(self, round_id: int) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute("UPDATE rounds SET status='done', updated_at=? WHERE id=?", (now, round_id))

    def mark_reminders_sent(self, round_id: int) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE rounds SET reminders_sent_at=?, updated_at=? WHERE id=?",
                (now, now, round_id),
            )

    def set_ready(self, user_id: int, round_id: int, is_ready: bool) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO readiness(user_id, round_id, is_ready, set_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, round_id) DO UPDATE SET
                    is_ready=excluded.is_ready,
                    set_at=excluded.set_at
                """,
                (user_id, round_id, int(is_ready), now),
            )

    def is_ready(self, user_id: int, round_id: int) -> bool:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT is_ready FROM readiness WHERE user_id=? AND round_id=?",
                (user_id, round_id),
            ).fetchone()
        return bool(row and row["is_ready"])

    def reset_readiness(self, round_id: int) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute("UPDATE readiness SET is_ready=0, set_at=? WHERE round_id=?", (now, round_id))

    def get_ready_users_by_office(self, round_id: int) -> dict[str, list[User]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT u.user_id, u.username, u.office, u.is_active
                FROM users u
                JOIN readiness r ON r.user_id = u.user_id
                WHERE u.is_active=1
                  AND u.office IS NOT NULL
                  AND r.round_id=?
                  AND r.is_ready=1
                ORDER BY u.office, u.user_id
                """,
                (round_id,),
            ).fetchall()

        grouped: dict[str, list[User]] = {}
        for row in rows:
            office = row["office"]
            grouped.setdefault(office, []).append(
                User(
                    user_id=row["user_id"],
                    username=row["username"],
                    office=office,
                    is_active=bool(row["is_active"]),
                )
            )
        return grouped

    def get_recent_pairs(self, office: str, from_dt: datetime) -> dict[frozenset[int], float]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT ph.user_a, ph.user_b, r.draw_at
                FROM pair_history ph
                JOIN rounds r ON r.id = ph.round_id
                WHERE ph.office = ? AND r.draw_at >= ?
                """,
                (office, iso(from_dt)),
            ).fetchall()

        weights: dict[frozenset[int], float] = {}
        for row in rows:
            pair = frozenset((row["user_a"], row["user_b"]))
            draw_at = datetime.fromisoformat(row["draw_at"])
            weight = draw_at.timestamp()
            prev = weights.get(pair)
            if prev is None or weight > prev:
                weights[pair] = weight
        return weights

    def get_skip_counts(self, office: str) -> dict[int, int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT user_id, COUNT(*) AS c FROM skipped_history WHERE office=? GROUP BY user_id",
                (office,),
            ).fetchall()
        return {row["user_id"]: row["c"] for row in rows}

    def store_pairs(self, round_id: int, office: str, pairs: Iterable[tuple[int, int]], repeats: set[frozenset[int]]) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            for a, b in pairs:
                pair_key = frozenset((a, b))
                conn.execute(
                    """
                    INSERT INTO pair_history(round_id, user_a, user_b, office, is_repeat, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (round_id, a, b, office, int(pair_key in repeats), now),
                )

    def store_skipped(self, round_id: int, office: str, user_ids: Iterable[int]) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            for user_id in user_ids:
                conn.execute(
                    "INSERT INTO skipped_history(round_id, user_id, office, created_at) VALUES (?, ?, ?, ?)",
                    (round_id, user_id, office, now),
                )

    def log_message(self, user_id: int, round_id: int | None, msg_type: str, status: str, error: str | None = None) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO message_log(round_id, user_id, msg_type, status, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (round_id, user_id, msg_type, status, error, iso(utc_now())),
            )

    def get_setting(self, key: str) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        now = iso(utc_now())
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, now),
            )

    def stats(self, next_round_id: int | None, last_done_round_id: int | None) -> dict[str, int]:
        with self.db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            active = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_active=1").fetchone()["c"]
            ready = 0
            if next_round_id is not None:
                ready = conn.execute(
                    "SELECT COUNT(*) AS c FROM readiness WHERE round_id=? AND is_ready=1",
                    (next_round_id,),
                ).fetchone()["c"]
            last_pairs = 0
            skipped = 0
            if last_done_round_id is not None:
                last_pairs = conn.execute(
                    "SELECT COUNT(*) AS c FROM pair_history WHERE round_id=?",
                    (last_done_round_id,),
                ).fetchone()["c"]
                skipped = conn.execute(
                    "SELECT COUNT(*) AS c FROM skipped_history WHERE round_id=?",
                    (last_done_round_id,),
                ).fetchone()["c"]
        return {
            "total": total,
            "active": active,
            "ready_next": ready,
            "last_pairs": last_pairs,
            "last_skipped": skipped,
        }

    def count_by_office(self) -> dict[str, int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT office, COUNT(*) AS c FROM users WHERE office IS NOT NULL GROUP BY office"
            ).fetchall()
        return {row["office"]: row["c"] for row in rows}

    def get_last_done_round(self) -> RoundRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, week_id, draw_at, status, reminders_sent_at
                FROM rounds
                WHERE status='done'
                ORDER BY draw_at DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        return RoundRecord(
            id=row["id"],
            week_id=row["week_id"],
            draw_at=datetime.fromisoformat(row["draw_at"]),
            status=row["status"],
            reminders_sent_at=parse_dt(row["reminders_sent_at"]),
        )

    def cleanup_old_backups_marker(self) -> None:
        # Резерв для будущих расширений; БД-метки бэкапа не требуются.
        return
