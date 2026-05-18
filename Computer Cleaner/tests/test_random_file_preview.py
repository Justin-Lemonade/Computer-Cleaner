from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_path in (PROJECT_ROOT / "src" / "data", PROJECT_ROOT / "src" / "core", PROJECT_ROOT / "src"):
    sys.path.insert(0, str(import_path))

from Config import CONFIG
from database.Db import init_db, mark_file_seen, mark_file_sorted, upsert_file
from random_file_preview import gather_candidate_files
from utils.Hashing import compute_file_hash


class RandomFilePreviewTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        object.__setattr__(CONFIG, "db_path", self.old_db_path)
        object.__setattr__(CONFIG, "data_dir", self.old_data_dir)
        object.__setattr__(CONFIG, "previews_dir", self.old_previews_dir)
        object.__setattr__(CONFIG, "thumbnails_dir", self.old_thumbnails_dir)
        object.__setattr__(CONFIG, "logs_dir", self.old_logs_dir)
        self.temp_dir.cleanup()

    def test_gather_candidate_files_skips_already_sorted_files(self) -> None:
        source = self.root / "source"
        source.mkdir()
        sorted_file = source / "sorted.txt"
        unsorted_file = source / "unsorted.txt"
        sorted_file.write_text("sorted", encoding="utf-8")
        unsorted_file.write_text("unsorted", encoding="utf-8")

        modified = datetime.fromtimestamp(sorted_file.stat().st_mtime)
        file_id = upsert_file(
            {
                "path": str(sorted_file),
                "filename": sorted_file.name,
                "filetype": "txt",
                "mime_type": "text/plain",
                "size": sorted_file.stat().st_size,
                "created_date": modified,
                "modified_date": modified,
                "preview_path": None,
            }
        )
        mark_file_seen(file_id=file_id, path=str(sorted_file), modified_date=modified, preview_path=None, file_hash=compute_file_hash(sorted_file))
        mark_file_sorted(file_id)

        candidates = gather_candidate_files([source])

        self.assertNotIn(sorted_file, candidates)
        self.assertIn(unsorted_file, candidates)


if __name__ == "__main__":
    unittest.main()
