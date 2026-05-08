from __future__ import annotations

import logging
import time
from pathlib import Path

from Config import CONFIG

from preview.ArchivePreview import build_archive_preview
from preview.EmailPreview import build_email_preview
from preview.HtmlPreview import build_html_preview
from preview.ImagePreview import build_image_thumbnail
from preview.OfficePreview import build_office_preview
from preview.PdfPreview import build_pdf_thumbnail
from preview.PresentationPreview import build_presentation_preview
from preview.SpreadsheetPreview import build_spreadsheet_preview
from preview.TextPreview import build_text_preview

LOGGER = logging.getLogger(__name__)


def build_preview(path: Path, *, mime_type: str | None, filetype: str | None) -> Path | None:
    """
    Returns a preview/thumbnail path for the given file, or None if unsupported.
    """
    suffix = (filetype or path.suffix.lower().lstrip(".") or "").lower()
    mt = (mime_type or "").lower()

    started = time.perf_counter()
    result: Path | None = None
    try:
        if mt.startswith("image/") or suffix in {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"}:
            result = build_image_thumbnail(path, out_dir=CONFIG.thumbnails_dir)
        elif mt == "application/pdf" or suffix == "pdf":
            result = build_pdf_thumbnail(path, out_dir=CONFIG.thumbnails_dir)
        elif suffix in {"ppt", "pptx", "odp"} or mt in {
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.presentation",
        }:
            result = build_presentation_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)
        elif suffix in {"xls", "xlsx", "ods"} or mt in {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
        }:
            result = build_spreadsheet_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)
        elif suffix in {"doc", "docx", "odt", "rtf"} or mt in {
            "application/msword",
            "application/rtf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text",
        }:
            result = build_office_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)
        elif suffix in {"html", "htm", "xml"} or mt in {"text/html", "application/xhtml+xml", "application/xml", "text/xml"}:
            result = build_html_preview(path, out_dir=CONFIG.previews_dir)
        elif suffix in {"zip", "rar", "7z", "tar", "gz", "tgz"}:
            result = build_archive_preview(path, out_dir=CONFIG.previews_dir)
        elif suffix in {"eml", "msg"}:
            result = build_email_preview(path, out_dir=CONFIG.previews_dir)
        elif mt.startswith("text/") or suffix in {"txt", "md", "log", "py", "json", "yaml", "yml", "csv", "js", "ts", "tsx", "css"}:
            result = build_text_preview(path, out_dir=CONFIG.previews_dir)
    finally:
        elapsed = time.perf_counter() - started
        LOGGER.info("Preview build: path=%s type=%s mime=%s elapsed=%.2fs success=%s", path, suffix, mt, elapsed, bool(result))
    return result
