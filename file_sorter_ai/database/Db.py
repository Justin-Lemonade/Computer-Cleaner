from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from Config import CONFIG


def get_connection() -> sqlite3.Connection:
    CONFIG.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CONFIG.db_path))
    conn.row_factory = sqlite3.Row
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
                preview_path TEXT
            );
            """
        )
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
