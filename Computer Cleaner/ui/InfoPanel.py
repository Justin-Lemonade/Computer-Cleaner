from __future__ import annotations

from PySide6.QtWidgets import QLabel, QFormLayout, QWidget


class InfoPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QFormLayout(self)
        self._path = QLabel("-")
        self._size = QLabel("-")
        self._created = QLabel("-")
        self._modified = QLabel("-")
        self._type = QLabel("-")

        for lbl in (self._path, self._size, self._created, self._modified, self._type):
            lbl.setTextInteractionFlags(lbl.textInteractionFlags() | lbl.textInteractionFlags().TextSelectableByMouse)

        layout.addRow("Path:", self._path)
        layout.addRow("Size:", self._size)
        layout.addRow("Created:", self._created)
        layout.addRow("Modified:", self._modified)
        layout.addRow("Type:", self._type)

    def set_info(
        self,
        *,
        path: str | None = None,
        size: int | None = None,
        created: str | None = None,
        modified: str | None = None,
        filetype: str | None = None,
    ) -> None:
        self._path.setText(path or "-")
        self._size.setText(f"{size} bytes" if size is not None else "-")
        self._created.setText(created or "-")
        self._modified.setText(modified or "-")
        self._type.setText(filetype or "-")

