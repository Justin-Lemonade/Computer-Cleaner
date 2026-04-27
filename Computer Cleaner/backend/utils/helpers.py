from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    """Return timezone-aware UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def normalize_path(file_path: str) -> str:
    """Normalize a path to a consistent, absolute string format."""
    return str(Path(file_path).expanduser().resolve())


def normalize_folder_path(file_path: str, folder_path: str | None = None) -> str:
    if folder_path:
        return str(Path(folder_path).expanduser().resolve())
    return str(Path(file_path).expanduser().resolve().parent)


def parse_iso8601(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromisoformat(timestamp)
