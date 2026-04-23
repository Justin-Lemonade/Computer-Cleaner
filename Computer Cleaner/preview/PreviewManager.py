from __future__ import annotations

from pathlib import Path

from Config import CONFIG

from preview.DocxPreview import build_docx_preview
from preview.ImagePreview import build_image_thumbnail
from preview.PdfPreview import build_pdf_thumbnail
from preview.TextPreview import build_text_preview


def build_preview(path: Path, *, mime_type: str | None, filetype: str | None) -> Path | None:
    """
    Returns a preview/thumbnail path for the given file, or None if unsupported.
    """
    suffix = (filetype or path.suffix.lower().lstrip(".") or "").lower()
    mt = (mime_type or "").lower()

    if mt.startswith("image/") or suffix in {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"}:
        return build_image_thumbnail(path, out_dir=CONFIG.thumbnails_dir)

    if mt == "application/pdf" or suffix == "pdf":
        return build_pdf_thumbnail(path, out_dir=CONFIG.thumbnails_dir)

    if suffix in {"docx"} or mt in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }:
        return build_docx_preview(path, out_dir=CONFIG.previews_dir)

    if mt.startswith("text/") or suffix in {"txt", "md", "log", "py", "json", "yaml", "yml", "csv"}:
        return build_text_preview(path, out_dir=CONFIG.previews_dir)

    return None
