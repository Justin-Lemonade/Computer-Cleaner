from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_path in (PROJECT_ROOT / "src", PROJECT_ROOT / "src" / "data", PROJECT_ROOT / "src" / "core"):
    sys.path.insert(0, str(import_path))

from Config import CONFIG
from core.history.SortedFileRegistry import SortedFileRegistry
from backend.db.schema import init_swipe_schema
from database.Db import get_connection, init_db
from utils.Hashing import compute_file_hash


class SortedFileRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.old_db_path = CONFIG.db_path
        self.old_data_dir = CONFIG.data_dir
        self.old_previews_dir = CONFIG.previews_dir
        self.old_thumbnails_dir = CONFIG.thumbnails_dir
        self.old_logs_dir = CONFIG.logs_dir
        object.__setattr__(CONFIG, "data_dir", self.root / "data")
        object.__setattr__(CONFIG, "previews_dir", self.root / "data" / "previews")
        object.__setattr__(CONFIG, "thumbnails_dir", self.root / "data" / "thumbnails")
        object.__setattr__(CONFIG, "logs_dir", self.root / "data" / "logs")
        object.__setattr__(CONFIG, "db_path", self.root / "files.db")
        init_db()
        init_swipe_schema(CONFIG.db_path)

    def tearDown(self) -> None:
        object.__setattr__(CONFIG, "db_path", self.old_db_path)
        object.__setattr__(CONFIG, "data_dir", self.old_data_dir)
        object.__setattr__(CONFIG, "previews_dir", self.old_previews_dir)
        object.__setattr__(CONFIG, "thumbnails_dir", self.old_thumbnails_dir)
        object.__setattr__(CONFIG, "logs_dir", self.old_logs_dir)
        self.temp_dir.cleanup()

    def test_sorted_registry_survives_files_cache_clear(self) -> None:
        path = self.root / "a.txt"
        path.write_text("abc", encoding="utf-8")
        reg = SortedFileRegistry()
        normalized = reg.normalize_path(path)
        file_hash = compute_file_hash(path)
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO swipes (id,file_path,file_name,file_type,file_size,folder_path,decision,timestamp,file_hash,source,user_override,reviewed,is_active,created_at)
                VALUES ('1', ?, 'a.txt', 'txt', 3, ?, 'KEEP', ?, ?, 'human', 0, 0, 1, ?);""",
                (normalized, str(path.parent), now, file_hash, now),
            )
            conn.execute("DELETE FROM files;")
        self.assertTrue(reg.is_sorted(path))
        self.assertTrue(reg.is_sorted_hash(file_hash))

