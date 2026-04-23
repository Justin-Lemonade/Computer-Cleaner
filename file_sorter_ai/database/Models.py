from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileRecord:
    id: int
    path: str
    filename: str
    filetype: str | None
    mime_type: str | None
    size: int | None
    created_date: datetime | None
    modified_date: datetime | None
    preview_path: str | None


@dataclass(frozen=True)
class LabelRecord:
    id: int
    file_id: int
    label: str
    timestamp: datetime
    confidence: float | None
    notes: str | None

