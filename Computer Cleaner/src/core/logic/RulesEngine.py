from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RuleSuggestion:
    label: str
    reason: str


def suggest_from_rules(
    *,
    size_bytes: int | None,
    modified_date: datetime | None,
    now: datetime | None = None,
) -> RuleSuggestion | None:
    now = now or datetime.now()

    if size_bytes is not None and size_bytes > 500 * 1024 * 1024:
        return RuleSuggestion(label="ARCHIVE", reason="File is larger than 500MB")

    if modified_date is not None:
        age_days = (now - modified_date).days
        if age_days >= 365 * 3:
            return RuleSuggestion(label="UNSURE", reason="File is older than 3 years")

    return None

