from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from Config import CONFIG
from database.Db import find_file_by_hash, find_file_by_path_signature
from preview.FilePreviewEngine import (
    FilePreviewEngine,
    ProcessingStats,
    build_processing_report,
    is_hidden_file,
    is_system_or_executable,
)
from utils.Hashing import compute_file_hash

DEFAULT_ALLOWED_FOLDERS = ["~/Documents", "~/Downloads", "~/Desktop"]


def resolve_allowed_folders(user_selected: list[str] | None = None) -> list[Path]:
    allowed = [Path(p).expanduser() for p in DEFAULT_ALLOWED_FOLDERS]
    for folder in user_selected or []:
        allowed.append(Path(folder).expanduser())
    return [folder for folder in allowed if folder.exists() and folder.is_dir()]


def _modified_datetime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return None


def is_sorted_file(path: Path) -> bool:
    """Return True when the local queue DB says this path or content was sorted."""
    try:
        stat = path.stat()
        path_row = find_file_by_path_signature(
            path=str(path),
            modified_date=_modified_datetime(path),
            size=int(stat.st_size),
        )
        if path_row is not None and int(path_row["already_sorted"] or 0) == 1:
            return True

        file_hash = compute_file_hash(path)
        hash_row = find_file_by_hash(file_hash) if file_hash else None
        return hash_row is not None and int(hash_row["already_sorted"] or 0) == 1
    except Exception:
        return False


def gather_candidate_files(allowed_folders: list[Path], *, include_sorted: bool = False) -> list[Path]:
    candidates: list[Path] = []
    for root in allowed_folders:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if is_hidden_file(path) or is_system_or_executable(path):
                continue
            if not include_sorted and is_sorted_file(path):
                continue
            candidates.append(path)
    return candidates


def process_single_random_file(
    engine: FilePreviewEngine,
    *,
    user_selected_folders: list[str] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    allowed_folders = resolve_allowed_folders(user_selected_folders)
    if not allowed_folders:
        raise RuntimeError("No valid allowed folders were found. Add folders with --folder.")

    candidates = gather_candidate_files(allowed_folders)
    if not candidates:
        raise RuntimeError("No valid files found in allowed folders after filtering.")

    picker = rng or random
    selected = picker.choice(candidates)
    return engine.process_file(selected)


def process_user_selected_file(engine: FilePreviewEngine, file_path_raw: str) -> dict[str, Any]:
    file_path = Path(file_path_raw).expanduser()
    if not file_path.exists() or not file_path.is_file():
        raise RuntimeError(f"Invalid file path selected: {file_path}")
    if is_hidden_file(file_path) or is_system_or_executable(file_path):
        raise RuntimeError("Selected file is hidden/system/executable and cannot be processed.")
    return engine.process_file(file_path)


def process_user_selected_folder(
    engine: FilePreviewEngine,
    folder_path_raw: str,
    *,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    folder_path = Path(folder_path_raw).expanduser()
    if not folder_path.exists() or not folder_path.is_dir():
        raise RuntimeError(f"Invalid folder path selected: {folder_path}")

    candidates = gather_candidate_files([folder_path])
    if not candidates:
        raise RuntimeError("No valid files found in selected folder after filtering.")

    picker = rng or random
    return engine.process_file(picker.choice(candidates))


def prompt_selection_mode() -> str:
    prompt = (
        "Choose preview source mode (press Enter for default random):\n"
        "  1) Random file (default)\n"
        "  2) Choose a specific file\n"
        "  3) Choose a folder (then random file from that folder)\n"
        "Selection [1/2/3]: "
    )
    raw = input(prompt).strip()
    if raw in {"", "1"}:
        return "random"
    if raw == "2":
        return "file"
    if raw == "3":
        return "folder"
    print("Invalid selection. Falling back to default random mode.")
    return "random"


def process_with_user_choice(
    engine: FilePreviewEngine,
    *,
    user_selected_folders: list[str] | None = None,
) -> dict[str, Any]:
    mode = prompt_selection_mode()

    if mode == "file":
        file_path = input("Enter file path to preview: ").strip()
        return process_user_selected_file(engine, file_path)

    if mode == "folder":
        folder_path = input("Enter folder path to use for random selection: ").strip()
        return process_user_selected_folder(engine, folder_path)

    return process_single_random_file(engine, user_selected_folders=user_selected_folders)


def run_test_mode(
    engine: FilePreviewEngine,
    *,
    iterations: int = 10,
    user_selected_folders: list[str] | None = None,
) -> dict[str, Any]:
    stats = ProcessingStats()
    distribution = Counter()

    for run_idx in range(iterations):
        try:
            result = process_single_random_file(
                engine,
                user_selected_folders=user_selected_folders,
                rng=random.Random(run_idx + 100),
            )
            stats.processed_count += 1
            distribution[result["file_type"]] += 1
            stats.file_types[result["file_type"]] += 1

            preview = result.get("preview", {})
            if preview.get("thumbnail") or preview.get("text_preview"):
                stats.preview_success_count += 1
            if result.get("extracted_content"):
                stats.extraction_success_count += 1
        except Exception as exc:  # defensive logging for test mode
            stats.failures.append({"run": str(run_idx + 1), "reason": str(exc)})

    report = build_processing_report(stats)
    report["test_mode"] = {
        "iterations": iterations,
        "file_type_distribution": dict(distribution),
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Random file preview and extraction runner.")
    parser.add_argument(
        "--folder",
        action="append",
        help="Additional folder to include in random file selection. Can be supplied multiple times.",
    )
    parser.add_argument("--test-mode", action="store_true", help="Run 10 random previews and print analytics.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    engine = FilePreviewEngine(
        thumbnail_dir=CONFIG.thumbnails_dir,
        preview_dir=CONFIG.previews_dir,
    )

    if args.test_mode:
        report = run_test_mode(engine, iterations=10, user_selected_folders=args.folder)
        print(json.dumps(report, indent=2))
        return 0

    result = process_with_user_choice(engine, user_selected_folders=args.folder)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
