from __future__ import annotations

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


def build_preview(path: Path, *, mime_type: str | None, filetype: str | None) -> Path | None:
    """
    Returns a preview/thumbnail path for the given file, or None if unsupported.
    """
    suffix = (filetype or path.suffix.lower().lstrip(".") or "").lower()
    mt = (mime_type or "").lower()

    if mt.startswith("image/") or suffix in {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"}:
        return build_image_thumbnail(path, out_dir=CONFIG.thumbnails_dir)

    if mt == "application/pdf" or suffix == "pdf":
        return build_pdf_thumbnail(path, out_dir=CONFIG.thumbnails_dir)

    if suffix in {"ppt", "pptx", "odp"} or mt in {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.oasis.opendocument.presentation",
    }:
        return build_presentation_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)

    if suffix in {"xls", "xlsx", "ods"} or mt in {
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.oasis.opendocument.spreadsheet",
    }:
        return build_spreadsheet_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)

    if suffix in {"doc", "docx", "odt", "rtf"} or mt in {
        "application/msword",
        "application/rtf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.oasis.opendocument.text",
    }:
        return build_office_preview(path, preview_dir=CONFIG.previews_dir, thumbnail_dir=CONFIG.thumbnails_dir)

    if suffix in {"html", "htm", "xml"} or mt in {"text/html", "application/xhtml+xml", "application/xml", "text/xml"}:
        return build_html_preview(path, out_dir=CONFIG.previews_dir)

    if suffix in {"zip", "rar", "7z", "tar", "gz", "tgz"}:
        return build_archive_preview(path, out_dir=CONFIG.previews_dir)

    if suffix in {"eml", "msg"}:
        return build_email_preview(path, out_dir=CONFIG.previews_dir)

    if mt.startswith("text/") or suffix in {"txt", "md", "log", "py", "json", "yaml", "yml", "csv", "js", "ts", "tsx", "css"}:
        return build_text_preview(path, out_dir=CONFIG.previews_dir)

    return None
