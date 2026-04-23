from __future__ import annotations

from pathlib import Path


def build_pdf_thumbnail(path: Path, *, out_dir: Path, zoom: float = 1.5) -> Path | None:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.pdf.thumb.png"

    try:
        doc = fitz.open(str(path))
        try:
            page = doc.load_page(0)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(str(out_path))
        finally:
            doc.close()
        return out_path
    except Exception:
        return None

