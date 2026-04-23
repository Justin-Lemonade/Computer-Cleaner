from __future__ import annotations

from pathlib import Path


def build_docx_preview(path: Path, *, out_dir: Path, max_chars: int = 4000) -> Path | None:
    try:
        import docx  # python-docx
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.docx.txt"

    try:
        document = docx.Document(str(path))
        text = "\n".join(p.text for p in document.paragraphs if p.text).strip()
        text = text[:max_chars]
        out_path.write_text(text, encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None

