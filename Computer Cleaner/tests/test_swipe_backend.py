from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from backend.models.swipe_model import (
    SwipeCreate,
    SwipeDecision,
    SwipeFilters,
    SwipePagination,
    SwipeSort,
    SwipeSortField,
    SwipeSortOrder,
    SwipeSource,
    SwipeUpdate,
)
from backend.services.swipe_service import SwipeService


class SwipeBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "swipe_test.db"
        self.service = SwipeService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_insert_100_plus_swipes_and_retrieve_performance(self) -> None:
        total_records = 150
        for idx in range(total_records):
            self.service.save_swipe(
                SwipeCreate(
                    file_path=f"/tmp/files/file_{idx}.pdf",
                    file_name=f"file_{idx}.pdf",
                    file_type="pdf",
                    file_size=1024 + idx,
                    decision=SwipeDecision.KEEP if idx % 2 == 0 else SwipeDecision.DELETE,
                    source=SwipeSource.HUMAN,
                    user_override=bool(idx % 3 == 0),
                    reason="Used recently" if idx % 2 == 0 else "Not using",
                )
            )

        start = time.perf_counter()
        results, total = self.service.get_swipes(
            filters=SwipeFilters(),
            pagination=SwipePagination(limit=200, offset=0),
            sort=SwipeSort(field=SwipeSortField.TIMESTAMP, order=SwipeSortOrder.DESC),
        )
        duration = time.perf_counter() - start

        self.assertEqual(total, total_records)
        self.assertEqual(len(results), total_records)
        self.assertEqual(results[0].reason, "Not using")
        self.assertLess(duration, 1.0, msg=f"Retrieval took too long: {duration:.3f}s")

    def test_filtering_accuracy(self) -> None:
        self.service.save_swipe(
            SwipeCreate(
                file_path="/tmp/a/report.pdf",
                file_name="report.pdf",
                file_type="pdf",
                file_size=5000,
                decision=SwipeDecision.ARCHIVE,
                source=SwipeSource.AI,
                folder_path="/tmp/a",
                reason="Sentimental value",
            )
        )
        self.service.save_swipe(
            SwipeCreate(
                file_path="/tmp/b/photo.jpg",
                file_name="photo.jpg",
                file_type="jpg",
                file_size=2000,
                decision=SwipeDecision.DELETE,
                source=SwipeSource.HUMAN,
                folder_path="/tmp/b",
            )
        )

        filtered, total = self.service.get_swipes(
            filters=SwipeFilters(decision=SwipeDecision.ARCHIVE, file_type="pdf", folder_path="/tmp/a"),
            pagination=SwipePagination(limit=10, offset=0),
            sort=SwipeSort(),
        )
        self.assertEqual(total, 1)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].file_name, "report.pdf")
        self.assertEqual(filtered[0].reason, "Sentimental value")

    def test_update_and_soft_delete_consistency(self) -> None:
        created = self.service.save_swipe(
            SwipeCreate(
                file_path="/tmp/c/notes.txt",
                file_name="notes.txt",
                file_type="txt",
                file_size=300,
                decision=SwipeDecision.UNSURE,
                source=SwipeSource.RULE_ENGINE,
                reason="Need second opinion",
            )
        )

        updated = self.service.update_swipe(
            created.id,
            SwipeUpdate(
                decision=SwipeDecision.KEEP,
                ai_suggestion=SwipeDecision.ARCHIVE,
                reviewed=True,
                reason="Important",
            ),
        )
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.decision, SwipeDecision.KEEP)
        self.assertEqual(updated.ai_suggestion, SwipeDecision.ARCHIVE)
        self.assertTrue(updated.reviewed)
        self.assertEqual(updated.reason, "Important")

        deleted = self.service.delete_swipe(created.id)
        self.assertTrue(deleted)

        active_list, active_total = self.service.get_swipes(
            filters=SwipeFilters(include_inactive=False),
            pagination=SwipePagination(limit=20, offset=0),
            sort=SwipeSort(),
        )
        self.assertEqual(active_total, 0)
        self.assertEqual(len(active_list), 0)

        all_list, all_total = self.service.get_swipes(
            filters=SwipeFilters(include_inactive=True),
            pagination=SwipePagination(limit=20, offset=0),
            sort=SwipeSort(),
        )
        self.assertEqual(all_total, 1)
        self.assertEqual(len(all_list), 1)
        self.assertFalse(all_list[0].is_active)


if __name__ == "__main__":
    unittest.main()
