from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: Path, *, chunk_size: int = 1024 * 1024) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(chunk_size)
                if not block:
                    break
                digest.update(block)
    except Exception:
        return None
    return digest.hexdigest()
