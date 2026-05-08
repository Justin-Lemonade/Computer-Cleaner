from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from preview.PdfPreview import build_pdf_thumbnail


def find_soffice() -> Path | None:
    candidates = [
        os.environ.get("LIBREOFFICE_PATH"),
        os.environ.get("SOFFICE_PATH"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists() and path.is_file():
            return path
    return None


def build_libreoffice_thumbnail(path: Path, *, out_dir: Path, timeout_seconds: int = 45) -> Path | None:
    soffice = find_soffice()
    if soffice is None:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="file_sorter_lo_") as tmp:
            tmp_dir = Path(tmp)
            result = subprocess.run(
                [
                    str(soffice),
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_dir),
                    str(path),
                ],
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                return None

            pdf_path = tmp_dir / f"{path.stem}.pdf"
            if not pdf_path.exists():
                matches = list(tmp_dir.glob("*.pdf"))
                if not matches:
                    return None
                pdf_path = matches[0]
            return build_pdf_thumbnail(pdf_path, out_dir=out_dir)
    except Exception:
        return None
