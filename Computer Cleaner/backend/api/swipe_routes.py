from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.swipe_model import (
    SwipeCreate,
    SwipeDecision,
    SwipeFilters,
    SwipePagination,
    SwipeSort,
    SwipeSortField,
    SwipeSortOrder,
    SwipeSource,
    SwipeUpdate,
)
from backend.services.swipe_service import SwipeService


class SwipeCreateRequest(BaseModel):
    file_path: str
    file_name: str
    file_type: str
    file_size: int = Field(ge=0)
    decision: SwipeDecision
    source: SwipeSource
    folder_path: str | None = None
    file_hash: str | None = None
    ai_suggestion: SwipeDecision | None = None
    user_override: bool = False
    timestamp: str | None = None
    reason: str | None = None


class SwipeUpdateRequest(BaseModel):
    decision: SwipeDecision | None = None
    ai_suggestion: SwipeDecision | None = None
    reviewed: bool | None = None
    user_override: bool | None = None
    reason: str | None = None


class SwipeResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    folder_path: str
    decision: SwipeDecision
    timestamp: str
    file_hash: str | None
    ai_suggestion: SwipeDecision | None
    source: SwipeSource
    user_override: bool
    is_active: bool
    reviewed: bool
    reason: str | None


class SwipeListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SwipeResponse]


def build_router(db_path: str | Path) -> APIRouter:
    router = APIRouter(prefix="", tags=["swipes"])
    service = SwipeService(db_path=db_path)

    @router.post("/swipe", response_model=SwipeResponse)
    def create_swipe(payload: SwipeCreateRequest) -> SwipeResponse:
        record = service.save_swipe(SwipeCreate(**payload.model_dump()))
        return SwipeResponse(**record.__dict__)

    @router.get("/swipes", response_model=SwipeListResponse)
    def list_swipes(
        decision: SwipeDecision | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        file_type: str | None = None,
        folder_path: str | None = None,
        sort_field: SwipeSortField = Query(default=SwipeSortField.TIMESTAMP),
        sort_order: SwipeSortOrder = Query(default=SwipeSortOrder.DESC),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        include_inactive: bool = False,
    ) -> SwipeListResponse:
        filters = SwipeFilters(
            decision=decision,
            date_from=date_from,
            date_to=date_to,
            file_type=file_type,
            folder_path=folder_path,
            include_inactive=include_inactive,
        )
        items, total = service.get_swipes(
            filters=filters,
            pagination=SwipePagination(limit=limit, offset=offset),
            sort=SwipeSort(field=sort_field, order=sort_order),
        )
        return SwipeListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[SwipeResponse(**item.__dict__) for item in items],
        )

    @router.get("/swipe/{swipe_id}", response_model=SwipeResponse)
    def get_swipe(swipe_id: str) -> SwipeResponse:
        record = service.get_swipe_by_id(swipe_id)
        if not record:
            raise HTTPException(status_code=404, detail="Swipe not found")
        return SwipeResponse(**record.__dict__)

    @router.put("/swipe/{swipe_id}", response_model=SwipeResponse)
    def update_swipe(swipe_id: str, payload: SwipeUpdateRequest) -> SwipeResponse:
        record = service.update_swipe(swipe_id=swipe_id, update=SwipeUpdate(**payload.model_dump()))
        if not record:
            raise HTTPException(status_code=404, detail="Swipe not found")
        return SwipeResponse(**record.__dict__)

    @router.delete("/swipe/{swipe_id}")
    def delete_swipe(swipe_id: str) -> dict[str, str]:
        removed = service.delete_swipe(swipe_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Swipe not found")
        return {"status": "soft_deleted", "id": swipe_id}

    return router
