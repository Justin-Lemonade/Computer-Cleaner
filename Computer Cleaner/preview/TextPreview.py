from __future__ import annotations

from pathlib import Path


def build_text_preview(path: Path, *, out_dir: Path, max_chars: int = 4000) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.txt.preview.txt"
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        out_path.write_text(content[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None

