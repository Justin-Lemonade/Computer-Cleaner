from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from Config import CONFIG


def get_connection() -> sqlite3.Connection:
    CONFIG.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CONFIG.db_path), timeout=3.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


def init_db() -> None:
    CONFIG.previews_dir.mkdir(parents=True, exist_ok=True)
    CONFIG.thumbnails_dir.mkdir(parents=True, exist_ok=True)
    CONFIG.logs_dir.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                filetype TEXT,
                mime_type TEXT,
                size INTEGER,
                created_date TEXT,
                modified_date TEXT,
                preview_path TEXT,
                file_hash TEXT,
                already_sorted INTEGER NOT NULL DEFAULT 0,
                preview_generated INTEGER NOT NULL DEFAULT 0,
                last_seen_path TEXT,
                last_modified TEXT,
                times_seen INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(files);").fetchall()}
        if "file_hash" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN file_hash TEXT;")
        if "already_sorted" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN already_sorted INTEGER NOT NULL DEFAULT 0;")
        if "preview_generated" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN preview_generated INTEGER NOT NULL DEFAULT 0;")
        if "last_seen_path" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN last_seen_path TEXT;")
        if "last_modified" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN last_modified TEXT;")
        if "times_seen" not in existing_cols:
            conn.execute("ALTER TABLE files ADD COLUMN times_seen INTEGER NOT NULL DEFAULT 0;")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_already_sorted ON files(already_sorted);")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL,
                notes TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS features (
                file_id INTEGER PRIMARY KEY,
                feature_vector BLOB,
                FOREIGN KEY(file_id) REFERENCES files(id)
            );
            """
        )


def upsert_file(metadata: dict[str, Any]) -> int:
    created = metadata.get("created_date")
    modified = metadata.get("modified_date")
    created_str = created.isoformat() if isinstance(created, datetime) else None
    modified_str = modified.isoformat() if isinstance(modified, datetime) else None

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO files (path, filename, filetype, mime_type, size, created_date, modified_date, preview_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename=excluded.filename,
                filetype=excluded.filetype,
                mime_type=excluded.mime_type,
                size=excluded.size,
                created_date=excluded.created_date,
                modified_date=excluded.modified_date,
                preview_path=excluded.preview_path
            ;
            """,
            (
                str(metadata["path"]),
                metadata.get("filename") or Path(metadata["path"]).name,
                metadata.get("filetype"),
                metadata.get("mime_type"),
                metadata.get("size"),
                created_str,
                modified_str,
                metadata.get("preview_path"),
            ),
        )
        row = conn.execute("SELECT id FROM files WHERE path = ?;", (str(metadata["path"]),)).fetchone()
        return int(row["id"])


def find_file_by_hash(file_hash: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM files WHERE file_hash = ? ORDER BY already_sorted DESC, id DESC LIMIT 1;",
            (file_hash,),
        ).fetchone()


def mark_file_seen(*, file_id: int, path: str, modified_date: datetime | None, preview_path: str | None, file_hash: str | None) -> None:
    modified_str = modified_date.isoformat() if isinstance(modified_date, datetime) else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE files
            SET file_hash = COALESCE(?, file_hash),
                last_seen_path = ?,
                last_modified = ?,
                preview_path = COALESCE(?, preview_path),
                preview_generated = CASE WHEN COALESCE(?, preview_path) IS NOT NULL THEN 1 ELSE preview_generated END,
                times_seen = CASE WHEN times_seen IS NULL OR times_seen < 1 THEN 1 ELSE times_seen + 1 END
            WHERE id = ?;
            """,
            (file_hash, path, modified_str, preview_path, preview_path, file_id),
        )


def mark_file_sorted(file_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE files SET already_sorted = 1, preview_generated = 1 WHERE id = ?;", (file_id,))


def list_files(limit: int = 100) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM files ORDER BY modified_date DESC NULLS LAST, id DESC LIMIT ?;",
            (limit,),
        ).fetchall()
    return list(rows)


def insert_label(file_id: int, label: str, confidence: float | None = None, notes: str | None = None) -> int:
    timestamp = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO labels (file_id, label, timestamp, confidence, notes)
            VALUES (?, ?, ?, ?, ?);
            """,
            (file_id, label, timestamp, confidence, notes),
        )
        return int(cur.lastrowid)
