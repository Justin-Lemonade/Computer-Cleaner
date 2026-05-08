from __future__ import annotations

from pathlib import Path


def build_html_preview(path: Path, *, out_dir: Path, max_chars: int = 4000) -> Path | None:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.html.preview.txt"
    try:
        raw = path.read_bytes()
        encoding = _detect_encoding(raw)
        soup = BeautifulSoup(raw.decode(encoding, errors="replace"), "html.parser")
        for item in soup(["script", "style"]):
            item.decompose()
        content = soup.get_text("\n")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        text = "\n".join(lines).strip()
        if not text:
            return None
        out_path.write_text(text[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _detect_encoding(raw: bytes) -> str:
    try:
        import chardet  # type: ignore

        detected = chardet.detect(raw)
        encoding = detected.get("encoding")
        if encoding:
            return str(encoding)
    except Exception:
        pass
    return "utf-8"
