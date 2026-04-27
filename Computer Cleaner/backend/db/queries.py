from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.db.connection import connection_context
from backend.models.swipe_model import SwipeFilters, SwipePagination, SwipeRecord, SwipeSort
from backend.utils.helpers import utc_now_iso


class SwipeRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = db_path

    def insert(self, payload: dict[str, Any]) -> SwipeRecord:
        with connection_context(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO swipes (
                    id, file_path, file_name, file_type, file_size, folder_path,
                    decision, timestamp, file_hash, ai_suggestion, source,
                    user_override, reviewed, is_active, updated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    payload["id"],
                    payload["file_path"],
                    payload["file_name"],
                    payload["file_type"],
                    payload["file_size"],
                    payload["folder_path"],
                    payload["decision"],
                    payload["timestamp"],
                    payload.get("file_hash"),
                    payload.get("ai_suggestion"),
                    payload["source"],
                    int(payload.get("user_override", False)),
                    int(payload.get("reviewed", False)),
                    int(payload.get("is_active", True)),
                    payload.get("updated_at"),
                    payload.get("created_at", utc_now_iso()),
                ),
            )
        return self.get_by_id(payload["id"])

    def get_by_id(self, swipe_id: str) -> SwipeRecord | None:
        with connection_context(self.db_path) as conn:
            row = conn.execute("SELECT * FROM swipes WHERE id = ?;", (swipe_id,)).fetchone()
        return SwipeRecord.from_row(row) if row else None

    def get_by_file(self, file_path: str, include_inactive: bool = False) -> list[SwipeRecord]:
        base = "SELECT * FROM swipes WHERE file_path = ?"
        params: list[Any] = [file_path]
        if not include_inactive:
            base += " AND is_active = 1"
        base += " ORDER BY timestamp DESC"

        with connection_context(self.db_path) as conn:
            rows = conn.execute(base, params).fetchall()
        return [SwipeRecord.from_row(row) for row in rows]

    def list_swipes(
        self,
        filters: SwipeFilters,
        pagination: SwipePagination,
        sort: SwipeSort,
    ) -> tuple[list[SwipeRecord], int]:
        where_clauses: list[str] = ["1=1"]
        params: list[Any] = []

        if filters.decision:
            where_clauses.append("decision = ?")
            params.append(filters.decision.value)
        if filters.file_type:
            where_clauses.append("file_type = ?")
            params.append(filters.file_type)
        if filters.folder_path:
            where_clauses.append("folder_path = ?")
            params.append(filters.folder_path)
        if filters.date_from:
            where_clauses.append("timestamp >= ?")
            params.append(filters.date_from)
        if filters.date_to:
            where_clauses.append("timestamp <= ?")
            params.append(filters.date_to)
        if not filters.include_inactive:
            where_clauses.append("is_active = 1")

        where_sql = " AND ".join(where_clauses)
        order_sql = f"{sort.field.value} {sort.order.value.upper()}"

        with connection_context(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT * FROM swipes WHERE {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?;",
                (*params, pagination.limit, pagination.offset),
            ).fetchall()
            count_row = conn.execute(
                f"SELECT COUNT(*) AS total FROM swipes WHERE {where_sql};",
                params,
            ).fetchone()

        results = [SwipeRecord.from_row(row) for row in rows]
        total = int(count_row["total"]) if count_row else 0
        return results, total

    def update(self, swipe_id: str, updates: dict[str, Any]) -> SwipeRecord | None:
        if not updates:
            return self.get_by_id(swipe_id)

        set_parts: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            set_parts.append(f"{key} = ?")
            params.append(value)
        set_parts.append("updated_at = ?")
        params.append(utc_now_iso())
        params.append(swipe_id)

        with connection_context(self.db_path) as conn:
            conn.execute(
                f"UPDATE swipes SET {', '.join(set_parts)} WHERE id = ?;",
                params,
            )
        return self.get_by_id(swipe_id)

    def soft_delete(self, swipe_id: str) -> bool:
        with connection_context(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE swipes SET is_active = 0, updated_at = ? WHERE id = ?;",
                (utc_now_iso(), swipe_id),
            )
        return cur.rowcount > 0
