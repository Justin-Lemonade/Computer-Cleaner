from __future__ import annotations

import gzip
import tarfile
import zipfile
from pathlib import Path


def build_archive_preview(path: Path, *, out_dir: Path, max_entries: int = 100) -> Path | None:
    suffixes = [item.lower() for item in path.suffixes]
    suffix = path.suffix.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.archive.preview.txt"

    try:
        if suffix == ".zip":
            entries = _zip_entries(path, max_entries=max_entries)
        elif suffix in {".tar", ".tgz"} or suffixes[-2:] in [[".tar", ".gz"], [".tar", ".bz2"], [".tar", ".xz"]]:
            entries = _tar_entries(path, max_entries=max_entries)
        elif suffix == ".gz":
            entries = _gzip_entries(path)
        elif suffix == ".7z":
            entries = _seven_zip_entries(path, max_entries=max_entries)
        elif suffix == ".rar":
            entries = _rar_entries(path, max_entries=max_entries)
        else:
            return None

        if not entries:
            return None
        content = f"Archive: {path.name}\n\n" + "\n".join(entries)
        out_path.write_text(content, encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _zip_entries(path: Path, *, max_entries: int) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        return [f"{index + 1}. {name}" for index, name in enumerate(names[:max_entries])]


def _tar_entries(path: Path, *, max_entries: int) -> list[str]:
    with tarfile.open(path) as archive:
        members = archive.getmembers()[:max_entries]
        return [f"{index + 1}. {member.name}" for index, member in enumerate(members)]


def _gzip_entries(path: Path) -> list[str]:
    try:
        with gzip.open(path, "rb") as handle:
            sample = handle.read(1)
        return [f"1. {path.stem}", f"Readable gzip stream: {'yes' if sample or path.stat().st_size >= 0 else 'unknown'}"]
    except Exception:
        return [f"1. {path.stem}"]


def _seven_zip_entries(path: Path, *, max_entries: int) -> list[str]:
    try:
        import py7zr  # type: ignore
    except Exception:
        return []
    with py7zr.SevenZipFile(path, mode="r") as archive:
        names = archive.getnames()
        return [f"{index + 1}. {name}" for index, name in enumerate(names[:max_entries])]


def _rar_entries(path: Path, *, max_entries: int) -> list[str]:
    try:
        import rarfile  # type: ignore
    except Exception:
        return []
    with rarfile.RarFile(path) as archive:
        names = archive.namelist()
        return [f"{index + 1}. {name}" for index, name in enumerate(names[:max_entries])]
