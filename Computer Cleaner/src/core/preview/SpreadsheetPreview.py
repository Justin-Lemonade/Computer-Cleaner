from __future__ import annotations

from pathlib import Path
from typing import Iterable

from preview.LibreOfficePreview import build_libreoffice_thumbnail


def build_spreadsheet_preview(
    path: Path,
    *,
    preview_dir: Path,
    thumbnail_dir: Path,
    max_sheets: int = 3,
    max_rows: int = 20,
    max_cols: int = 10,
) -> Path | None:
    thumbnail = build_libreoffice_thumbnail(path, out_dir=thumbnail_dir)
    if thumbnail is not None:
        return thumbnail

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _build_xlsx_text_preview(path, out_dir=preview_dir, max_sheets=max_sheets, max_rows=max_rows, max_cols=max_cols)
    if suffix == ".ods":
        return _build_ods_text_preview(path, out_dir=preview_dir, max_sheets=max_sheets, max_rows=max_rows, max_cols=max_cols)
    return None


def _build_xlsx_text_preview(path: Path, *, out_dir: Path, max_sheets: int, max_rows: int, max_cols: int) -> Path | None:
    try:
        import openpyxl  # type: ignore
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.xlsx.preview.txt"
    try:
        workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        try:
            sections: list[str] = []
            for sheet in workbook.worksheets[:max_sheets]:
                rows = _format_rows(sheet.iter_rows(max_row=max_rows, max_col=max_cols, values_only=True))
                if rows:
                    sections.append(f"Sheet: {sheet.title}\n" + "\n".join(rows))
            content = "\n\n".join(sections).strip()
        finally:
            workbook.close()
        if not content:
            return None
        out_path.write_text(content, encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _build_ods_text_preview(path: Path, *, out_dir: Path, max_sheets: int, max_rows: int, max_cols: int) -> Path | None:
    try:
        from odf import table, text  # type: ignore
        from odf.opendocument import load  # type: ignore
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.ods.preview.txt"
    try:
        document = load(str(path))
        sections: list[str] = []
        for sheet in document.spreadsheet.getElementsByType(table.Table)[:max_sheets]:
            sheet_name = sheet.getAttribute("name") or "Sheet"
            rendered_rows: list[str] = []
            for row in sheet.getElementsByType(table.TableRow)[:max_rows]:
                cells: list[str] = []
                for cell in row.getElementsByType(table.TableCell)[:max_cols]:
                    paragraphs = cell.getElementsByType(text.P)
                    value = " ".join(_node_text(paragraph) for paragraph in paragraphs).strip()
                    cells.append(value)
                if any(cells):
                    rendered_rows.append(" | ".join(cells))
            if rendered_rows:
                sections.append(f"Sheet: {sheet_name}\n" + "\n".join(rendered_rows))
        content = "\n\n".join(sections).strip()
        if not content:
            return None
        out_path.write_text(content, encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _format_rows(rows: Iterable[tuple[object, ...]]) -> list[str]:
    rendered: list[str] = []
    for row in rows:
        values = ["" if value is None else str(value) for value in row]
        if any(values):
            rendered.append(" | ".join(values))
    return rendered


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
