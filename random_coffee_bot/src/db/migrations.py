from __future__ import annotations

from db.connection import Database


MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );
    """,
    """
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        office TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id TEXT NOT NULL UNIQUE,
        draw_at TEXT NOT NULL,
        status TEXT NOT NULL,
        reminders_sent_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE readiness (
        user_id INTEGER NOT NULL,
        round_id INTEGER NOT NULL,
        is_ready INTEGER NOT NULL,
        set_at TEXT NOT NULL,
        PRIMARY KEY (user_id, round_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );

    CREATE TABLE pair_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER NOT NULL,
        user_a INTEGER NOT NULL,
        user_b INTEGER NOT NULL,
        office TEXT NOT NULL,
        is_repeat INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );

    CREATE TABLE skipped_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        office TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );

    CREATE TABLE message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER,
        user_id INTEGER NOT NULL,
        msg_type TEXT NOT NULL,
        status TEXT NOT NULL,
        error TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX idx_users_active_office ON users (is_active, office);
    CREATE INDEX idx_readiness_round_ready ON readiness (round_id, is_ready);
    CREATE INDEX idx_pair_history_users ON pair_history (user_a, user_b);
    CREATE INDEX idx_skipped_user ON skipped_history (user_id);
    """,
]


def migrate(db: Database) -> None:
    with db.transaction() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
        row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        current = int(row["v"] or 0)

        while current < len(MIGRATIONS):
            sql = MIGRATIONS[current]
            conn.executescript(sql)
            current += 1
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (current,))
