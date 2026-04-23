from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FileCard(QWidget):
    def __init__(self, filename: str, path: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(filename))
        layout.addWidget(QLabel(path))

