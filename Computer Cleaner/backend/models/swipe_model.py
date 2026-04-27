from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SwipeDecision(str, Enum):
    KEEP = "KEEP"
    DELETE = "DELETE"
    ARCHIVE = "ARCHIVE"
    UNSURE = "UNSURE"


class SwipeSource(str, Enum):
    HUMAN = "human"
    AI = "AI"
    RULE_ENGINE = "rule engine"


class SwipeSortField(str, Enum):
    TIMESTAMP = "timestamp"
    FILE_SIZE = "file_size"
    DECISION = "decision"


class SwipeSortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class SwipeRecord:
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

    @classmethod
    def from_row(cls, row: Any) -> "SwipeRecord":
        ai_value = row["ai_suggestion"]
        return cls(
            id=row["id"],
            file_path=row["file_path"],
            file_name=row["file_name"],
            file_type=row["file_type"],
            file_size=row["file_size"],
            folder_path=row["folder_path"],
            decision=SwipeDecision(row["decision"]),
            timestamp=row["timestamp"],
            file_hash=row["file_hash"],
            ai_suggestion=SwipeDecision(ai_value) if ai_value else None,
            source=SwipeSource(row["source"]),
            user_override=bool(row["user_override"]),
            is_active=bool(row["is_active"]),
            reviewed=bool(row["reviewed"]),
        )


@dataclass(frozen=True)
class SwipeCreate:
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    decision: SwipeDecision
    source: SwipeSource
    folder_path: str | None = None
    file_hash: str | None = None
    ai_suggestion: SwipeDecision | None = None
    user_override: bool = False
    timestamp: str | None = None


@dataclass(frozen=True)
class SwipeUpdate:
    decision: SwipeDecision | None = None
    ai_suggestion: SwipeDecision | None = None
    reviewed: bool | None = None
    user_override: bool | None = None


@dataclass(frozen=True)
class SwipeFilters:
    decision: SwipeDecision | None = None
    file_type: str | None = None
    folder_path: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    include_inactive: bool = False


@dataclass(frozen=True)
class SwipePagination:
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SwipeSort:
    field: SwipeSortField = SwipeSortField.TIMESTAMP
    order: SwipeSortOrder = SwipeSortOrder.DESC
