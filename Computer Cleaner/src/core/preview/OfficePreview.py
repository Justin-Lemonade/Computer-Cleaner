from __future__ import annotations

import re
from pathlib import Path

from preview.DocxPreview import build_docx_preview
from preview.LibreOfficePreview import build_libreoffice_thumbnail


def build_office_preview(path: Path, *, preview_dir: Path, thumbnail_dir: Path, max_chars: int = 4000) -> Path | None:
    thumbnail = build_libreoffice_thumbnail(path, out_dir=thumbnail_dir)
    if thumbnail is not None:
        return thumbnail

    suffix = path.suffix.lower()
    if suffix == ".docx":
        return build_docx_preview(path, out_dir=preview_dir, max_chars=max_chars)
    if suffix == ".odt":
        return _build_odt_text_preview(path, out_dir=preview_dir, max_chars=max_chars)
    if suffix == ".rtf":
        return _build_rtf_text_preview(path, out_dir=preview_dir, max_chars=max_chars)
    return None


def _build_odt_text_preview(path: Path, *, out_dir: Path, max_chars: int) -> Path | None:
    try:
        from odf import text  # type: ignore
        from odf.opendocument import load  # type: ignore
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.odt.preview.txt"
    try:
        document = load(str(path))
        paragraphs = [_node_text(node).strip() for node in document.getElementsByType(text.P)]
        content = "\n".join(item for item in paragraphs if item).strip()
        if not content:
            return None
        out_path.write_text(content[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _build_rtf_text_preview(path: Path, *, out_dir: Path, max_chars: int) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.rtf.preview.txt"
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
        text = re.sub(r"\\[a-zA-Z]+-?\\d* ?", " ", text)
        text = text.replace("{", " ").replace("}", " ")
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None
        out_path.write_text(text[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _node_text(node) -> str:
    parts: list[str] = []
    for child in getattr(node, "childNodes", []):
        data = getattr(child, "data", None)
        if data:
            parts.append(str(data))
        else:
            nested = _node_text(child)
            if nested:
                parts.append(nested)
    return "".join(parts)
