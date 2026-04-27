from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.db.queries import SwipeRepository
from backend.db.schema import init_swipe_schema
from backend.models.swipe_model import (
    SwipeCreate,
    SwipeFilters,
    SwipePagination,
    SwipeRecord,
    SwipeSort,
    SwipeUpdate,
)
from backend.utils.helpers import normalize_folder_path, normalize_path, utc_now_iso


class SwipeService:
    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        init_swipe_schema(self.db_path)
        self.repository = SwipeRepository(db_path=self.db_path)

    def save_swipe(self, swipe: SwipeCreate) -> SwipeRecord:
        timestamp = swipe.timestamp or utc_now_iso()
        normalized_file_path = normalize_path(swipe.file_path)
        payload = {
            "id": str(uuid4()),
            "file_path": normalized_file_path,
            "file_name": swipe.file_name,
            "file_type": swipe.file_type.lower(),
            "file_size": swipe.file_size,
            "folder_path": normalize_folder_path(swipe.file_path, swipe.folder_path),
            "decision": swipe.decision.value,
            "timestamp": timestamp,
            "file_hash": swipe.file_hash,
            "ai_suggestion": swipe.ai_suggestion.value if swipe.ai_suggestion else None,
            "source": swipe.source.value,
            "user_override": swipe.user_override,
            "reviewed": False,
            "reason": swipe.reason,
            "is_active": True,
            "created_at": timestamp,
        }
        return self.repository.insert(payload)

    def get_swipe_by_id(self, swipe_id: str) -> SwipeRecord | None:
        return self.repository.get_by_id(swipe_id)

    def get_swipe_by_file(self, file_path: str, include_inactive: bool = False) -> list[SwipeRecord]:
        return self.repository.get_by_file(file_path=normalize_path(file_path), include_inactive=include_inactive)

    def get_swipes(
        self,
        filters: SwipeFilters,
        pagination: SwipePagination,
        sort: SwipeSort,
    ) -> tuple[list[SwipeRecord], int]:
        return self.repository.list_swipes(filters=filters, pagination=pagination, sort=sort)

    def update_swipe(self, swipe_id: str, update: SwipeUpdate) -> SwipeRecord | None:
        updates: dict[str, object] = {}
        if update.decision:
            updates["decision"] = update.decision.value
        if update.ai_suggestion:
            updates["ai_suggestion"] = update.ai_suggestion.value
        if update.reviewed is not None:
            updates["reviewed"] = int(update.reviewed)
        if update.user_override is not None:
            updates["user_override"] = int(update.user_override)
        if update.reason is not None:
            updates["reason"] = update.reason
        return self.repository.update(swipe_id=swipe_id, updates=updates)

    def delete_swipe(self, swipe_id: str) -> bool:
        return self.repository.soft_delete(swipe_id)
