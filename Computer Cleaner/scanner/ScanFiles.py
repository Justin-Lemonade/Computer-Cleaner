from __future__ import annotations

from pathlib import Path
from typing import Iterable

from database.Db import upsert_file
from preview.PreviewManager import build_preview
from scanner.Metadata import get_basic_metadata, is_probably_hidden


def iter_files(folder: Path, *, include_hidden: bool = False) -> Iterable[Path]:
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if not include_hidden and is_probably_hidden(path):
            continue
        yield path


def scan_and_store(folder: Path, *, include_hidden: bool = False) -> int:
    count = 0
    for path in iter_files(folder, include_hidden=include_hidden):
        meta = get_basic_metadata(path)
        preview_path = build_preview(path, mime_type=meta.mime_type, filetype=meta.filetype)
        upsert_file(
            {
                "path": str(meta.path),
                "filename": meta.filename,
                "filetype": meta.filetype,
                "mime_type": meta.mime_type,
                "size": meta.size,
                "created_date": meta.created_date,
                "modified_date": meta.modified_date,
                "preview_path": str(preview_path) if preview_path else None,
            }
        )
        count += 1
    return count


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Scan a folder and store file metadata into SQLite.")
    parser.add_argument("folder", type=str, help="Folder to scan")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
    if not folder.exists():
        raise SystemExit(f"Folder does not exist: {folder}")
    n = scan_and_store(folder, include_hidden=args.include_hidden)
    print(f"Scanned {n} files from {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
