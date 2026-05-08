from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_MAGIC_SCAN_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class FileMetadata:
    path: Path
    filename: str
    filetype: str | None
    mime_type: str | None
    size: int | None
    created_date: datetime | None
    modified_date: datetime | None


def _safe_dt_from_ts(ts: float | int | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts))
    except Exception:
        return None


def detect_mime_type(path: Path) -> str | None:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed

    try:
        file_size = path.stat().st_size
        if file_size > MAX_MAGIC_SCAN_BYTES:
            return None
    except Exception:
        pass

    try:
        import magic  # type: ignore

        return magic.from_file(str(path), mime=True)
    except Exception:
        return None


def get_basic_metadata(path: Path) -> FileMetadata:
    stat = path.stat()
    mime_type = detect_mime_type(path)

    suffix = path.suffix.lower().lstrip(".")
    filetype = suffix or None

    created_ts = getattr(stat, "st_ctime", None)
    modified_ts = getattr(stat, "st_mtime", None)

    return FileMetadata(
        path=path,
        filename=path.name,
        filetype=filetype,
        mime_type=mime_type,
        size=int(getattr(stat, "st_size", 0)) if stat is not None else None,
        created_date=_safe_dt_from_ts(created_ts),
        modified_date=_safe_dt_from_ts(modified_ts),
    )


def is_probably_hidden(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if os.name != "nt":
        return False
    try:
        import stat as statmod

        attrs = os.stat(str(path)).st_file_attributes  # type: ignore[attr-defined]
        return bool(attrs & statmod.FILE_ATTRIBUTE_HIDDEN)  # type: ignore[attr-defined]
    except Exception:
        return False
