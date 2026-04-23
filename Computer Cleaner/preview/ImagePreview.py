from __future__ import annotations

from pathlib import Path


def build_image_thumbnail(path: Path, *, out_dir: Path, max_size: tuple[int, int] = (512, 512)) -> Path | None:
    try:
        from PIL import Image
    except Exception:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.thumb.png"
    try:
        with Image.open(path) as img:
            img.thumbnail(max_size)
            img.convert("RGBA").save(out_path, format="PNG")
        return out_path
    except Exception:
        return None

