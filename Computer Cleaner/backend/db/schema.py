from __future__ import annotations

from pathlib import Path

from backend.db.connection import connection_context


def init_swipe_schema(db_path: str | Path) -> None:
    with connection_context(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swipes (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL CHECK(file_size >= 0),
                folder_path TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('KEEP','DELETE','ARCHIVE','UNSURE')),
                timestamp TEXT NOT NULL,
                file_hash TEXT,
                ai_suggestion TEXT CHECK(ai_suggestion IN ('KEEP','DELETE','ARCHIVE','UNSURE') OR ai_suggestion IS NULL),
                source TEXT NOT NULL CHECK(source IN ('human','AI','rule engine')),
                user_override INTEGER NOT NULL DEFAULT 0 CHECK(user_override IN (0, 1)),
                reviewed INTEGER NOT NULL DEFAULT 0 CHECK(reviewed IN (0, 1)),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
                updated_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_swipes_decision_timestamp
            ON swipes(decision, timestamp DESC);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_swipes_file_path
            ON swipes(file_path);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_swipes_file_type
            ON swipes(file_type);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_swipes_folder_path
            ON swipes(folder_path);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_swipes_is_active_timestamp
            ON swipes(is_active, timestamp DESC);
            """
        )
