from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from Config import CONFIG
from core.history.SortedFileRegistry import SortedFileRegistry
from preview.FilePreviewEngine import (
    FilePreviewEngine,
    ProcessingStats,
    build_processing_report,
    is_hidden_file,
    is_system_or_executable,
)


def scan_folder_recursively(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if is_hidden_file(path) or is_system_or_executable(path):
            continue
        files.append(path)
    return files


def process_folder_to_queue(engine: FilePreviewEngine, folder: Path) -> dict[str, Any]:
    sorted_registry = SortedFileRegistry()
    queue: list[dict[str, Any]] = []
    stats = ProcessingStats()

    for file_path in scan_folder_recursively(folder):
        normalized_path = sorted_registry.normalize_path(file_path)
        if sorted_registry.is_sorted(normalized_path):
            continue
        try:
            result = engine.process_file(file_path)
            queue.append(result)
            stats.processed_count += 1
            stats.file_types[result["file_type"]] += 1

            preview = result.get("preview", {})
            if preview.get("thumbnail") or preview.get("text_preview"):
                stats.preview_success_count += 1
            if result.get("extracted_content"):
                stats.extraction_success_count += 1
        except Exception as exc:
            stats.failures.append({"file_path": str(file_path), "reason": str(exc)})

    report = build_processing_report(stats)
    report["queue_summary"] = {
        "selected_folder": str(folder),
        "queued_items": len(queue),
    }
    return {
        "queue": queue,
        "report": report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Folder selector preview pipeline.")
    parser.add_argument("folder", type=str, help="Folder path to recursively scan and process")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print only report summary instead of full queue payload",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    folder = Path(args.folder).expanduser()
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Invalid folder path: {folder}")

    engine = FilePreviewEngine(
        thumbnail_dir=CONFIG.thumbnails_dir,
        preview_dir=CONFIG.previews_dir,
    )
    result = process_folder_to_queue(engine, folder)

    if args.report_only:
        print(json.dumps(result["report"], indent=2))
    else:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
