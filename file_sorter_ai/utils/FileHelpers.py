from __future__ import annotations

import shutil
from pathlib import Path

from Config import CONFIG


def ensure_sort_dirs(root: Path) -> dict[str, Path]:
    archive = root / CONFIG.archive_dir_name
    trash = root / CONFIG.trash_queue_dir_name
    review = root / CONFIG.review_later_dir_name
    for p in (archive, trash, review):
        p.mkdir(parents=True, exist_ok=True)
    return {"ARCHIVE": archive, "NOT_NEEDED": trash, "UNSURE": review}


def move_file(path: Path, destination_dir: Path, *, dry_run: bool = True) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / path.name
    if dry_run:
        return target
    return Path(shutil.move(str(path), str(target)))
