from __future__ import annotations

import logging
from datetime import datetime

from Config import CONFIG


def setup_logging() -> None:
    CONFIG.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = CONFIG.logs_dir / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
