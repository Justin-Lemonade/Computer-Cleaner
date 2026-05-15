from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: Path, *, chunk_size: int = 1024 * 1024, max_bytes: int | None = None) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    blake = _new_blake3()
    digest = blake if blake is not None else hashlib.sha256()
    consumed = 0
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(chunk_size)
                if not block:
                    break
                if max_bytes is not None and consumed >= max_bytes:
                    break
                if max_bytes is not None and consumed + len(block) > max_bytes:
                    block = block[: max_bytes - consumed]
                digest.update(block)
                consumed += len(block)
                if max_bytes is not None and consumed >= max_bytes:
                    break
    except Exception:
        return None
    return digest.hexdigest()


def _new_blake3():
    try:
        import blake3  # type: ignore

        return blake3.blake3()
    except Exception:
        return None
