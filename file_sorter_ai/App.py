from __future__ import annotations

import sys

from database.Db import init_db
from utils.LoggingUtils import setup_logging


def main() -> int:
    setup_logging()
    init_db()

    try:
        from PySide6.QtWidgets import QApplication
    except Exception as exc:  # pragma: no cover
        print("PySide6 is required to run the desktop UI.")
        print(f"Import error: {exc}")
        return 1

    from ui.MainWindow import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
