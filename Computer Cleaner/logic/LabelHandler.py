from __future__ import annotations

from database.Db import insert_label

LABEL_KEEP = "keep"
LABEL_ARCHIVE = "archive"
LABEL_NOT_NEEDED = "not_needed"

_VALID_LABELS = {LABEL_KEEP, LABEL_ARCHIVE, LABEL_NOT_NEEDED}


def save_label(file_id: int, label: str, *, confidence: float | None = None, notes: str | None = None) -> int:
    normalized = (label or "").strip().lower()
    if normalized not in _VALID_LABELS:
        raise ValueError(f"Unsupported label '{label}'. Expected one of: {sorted(_VALID_LABELS)}")

    return insert_label(file_id=file_id, label=normalized, confidence=confidence, notes=notes)
