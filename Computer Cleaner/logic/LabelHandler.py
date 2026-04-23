from __future__ import annotations

from database.Db import insert_label


LABEL_KEEP = "KEEP"
LABEL_ARCHIVE = "ARCHIVE"
LABEL_NOT_NEEDED = "NOT_NEEDED"
LABEL_UNSURE = "UNSURE"

ALL_LABELS = {LABEL_KEEP, LABEL_ARCHIVE, LABEL_NOT_NEEDED, LABEL_UNSURE}


def save_label(file_id: int, label: str, *, confidence: float | None = None, notes: str | None = None) -> int:
    if label not in ALL_LABELS:
        raise ValueError(f"Unknown label: {label}")
    return insert_label(file_id, label, confidence=confidence, notes=notes)
