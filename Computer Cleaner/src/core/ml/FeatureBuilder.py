from __future__ import annotations

from datetime import datetime


def build_feature_dict(
    *,
    size_bytes: int | None,
    modified_date: datetime | None,
    filetype: str | None,
    parent_folder: str | None,
) -> dict[str, float]:
    now = datetime.now()
    age_days = float((now - modified_date).days) if modified_date is not None else 0.0
    size_mb = float(size_bytes) / (1024.0 * 1024.0) if size_bytes is not None else 0.0
    filetype_code = float(abs(hash((filetype or "").lower())) % 10_000)
    folder_code = float(abs(hash((parent_folder or "").lower())) % 10_000)

    return {
        "file_age_days": age_days,
        "file_size_mb": size_mb,
        "file_type_code": filetype_code,
        "folder_code": folder_code,
    }

