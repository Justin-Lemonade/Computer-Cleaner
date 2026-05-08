from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "File Sorter AI"
    base_dir: Path = Path(__file__).resolve().parent.parent

    data_dir: Path = base_dir / "data"
    previews_dir: Path = data_dir / "previews"
    thumbnails_dir: Path = data_dir / "thumbnails"
    logs_dir: Path = data_dir / "logs"

    db_path: Path = base_dir / "files.db"

    archive_dir_name: str = "Archive"
    trash_queue_dir_name: str = "Trash_Queue"
    review_later_dir_name: str = "Review_Later"


CONFIG = AppConfig()
