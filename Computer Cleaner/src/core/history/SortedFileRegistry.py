from __future__ import annotations

import os
from pathlib import Path

from database.Db import get_connection


class SortedFileRegistry:
    """Single-source sorted-history checker backed by swipe history."""

    def normalize_path(self, path: str | Path) -> str:
        return os.path.normcase(os.path.abspath(str(path).strip()))

    def is_sorted(self, path: str | Path) -> bool:
        normalized = self.normalize_path(path)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM swipes WHERE file_path = ? AND is_active = 1 LIMIT 1;",
                (normalized,),
            ).fetchone()
        return row is not None

    def is_sorted_hash(self, file_hash: str | None) -> bool:
        if not file_hash:
            return False
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM swipes WHERE file_hash = ? AND is_active = 1 LIMIT 1;",
                (file_hash,),
            ).fetchone()
        return row is not None

    def bulk_sorted_check(self, paths: list[str | Path]) -> set[str]:
        normalized = [self.normalize_path(path) for path in paths]
        if not normalized:
            return set()
        placeholders = ",".join("?" for _ in normalized)
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT file_path FROM swipes WHERE is_active = 1 AND file_path IN ({placeholders});",
                normalized,
            ).fetchall()
        return {self.normalize_path(row["file_path"]) for row in rows}
