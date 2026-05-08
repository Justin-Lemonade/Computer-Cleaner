from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path


def build_email_preview(path: Path, *, out_dir: Path, max_chars: int = 4000) -> Path | None:
    suffix = path.suffix.lower()
    if suffix == ".eml":
        return _build_eml_preview(path, out_dir=out_dir, max_chars=max_chars)
    if suffix == ".msg":
        return _build_msg_preview(path, out_dir=out_dir, max_chars=max_chars)
    return None


def _build_eml_preview(path: Path, *, out_dir: Path, max_chars: int) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.eml.preview.txt"
    try:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=("plain", "html"))
        body_text = body.get_content() if body is not None else ""
        content = "\n".join(
            [
                f"From: {message.get('from', '')}",
                f"To: {message.get('to', '')}",
                f"Subject: {message.get('subject', '')}",
                f"Date: {message.get('date', '')}",
                "",
                str(body_text),
            ]
        ).strip()
        if not content:
            return None
        out_path.write_text(content[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None


def _build_msg_preview(path: Path, *, out_dir: Path, max_chars: int) -> Path | None:
    try:
        import extract_msg  # type: ignore
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.msg.preview.txt"
    try:
        message = extract_msg.Message(str(path))
        try:
            content = "\n".join(
                [
                    f"From: {getattr(message, 'sender', '') or ''}",
                    f"To: {getattr(message, 'to', '') or ''}",
                    f"Subject: {getattr(message, 'subject', '') or ''}",
                    f"Date: {getattr(message, 'date', '') or ''}",
                    "",
                    getattr(message, "body", "") or "",
                ]
            ).strip()
        finally:
            message.close()
        if not content:
            return None
        out_path.write_text(content[:max_chars], encoding="utf-8", errors="replace")
        return out_path
    except Exception:
        return None
