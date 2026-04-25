from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class InfoPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("InfoPanel")
        self.setMinimumWidth(290)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._header = QLabel("File Information")
        self._header.setObjectName("InfoHeader")

        self._index = self._info_row("Queue Position")
        self._type = self._info_row("Type")
        self._size = self._info_row("Size")
        self._created = self._info_row("Created")
        self._modified = self._info_row("Last Edited")

        self._detail = QLabel("")
        self._detail.setObjectName("InfoDetail")
        self._detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._detail.setWordWrap(True)
        self._detail.hide()

        self._shortcuts = QLabel("Shortcuts: A/Left=Not Needed  D/Right=Keep  W/Up=Archive")
        self._shortcuts.setObjectName("InfoShortcuts")
        self._shortcuts.setWordWrap(True)

        layout.addWidget(self._header)
        layout.addWidget(self._index)
        layout.addWidget(self._type)
        layout.addWidget(self._size)
        layout.addWidget(self._created)
        layout.addWidget(self._modified)
        layout.addWidget(self._detail)
        layout.addStretch(1)
        layout.addWidget(self._shortcuts)

        self.setStyleSheet(
            """
            QFrame#InfoPanel {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 14px;
            }
            QLabel#InfoHeader {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel[role="row"] {
                background: #212121;
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                color: #b3b3b3;
                font-size: 12px;
                padding: 10px;
            }
            QLabel#InfoDetail {
                background: #212121;
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                color: #b3b3b3;
                font-size: 12px;
                padding: 10px;
            }
            QLabel#InfoShortcuts {
                color: #6b6b6b;
                font-size: 11px;
            }
            """
        )

    def set_file(self, file_data: Mapping[str, Any], *, index: int, total: int) -> None:
        path = str(file_data.get("path") or "-")
        filetype = str(file_data.get("filetype") or "Unknown")
        size = self._format_size(file_data.get("size"))
        created = self._format_date(file_data.get("created_date"))
        modified = self._format_date(file_data.get("modified_date"))

        self._index.setText(f"Queue Position\n{index}/{total}")
        self._type.setText(f"Type\n{filetype}")
        self._size.setText(f"Size\n{size}")
        self._created.setText(f"Created\n{created}")
        self._modified.setText(f"Last Edited\n{modified}")
        self._detail.setText(f"Path\n{path}")

    def toggle_details(self) -> bool:
        self._detail.setVisible(not self._detail.isVisible())
        return self._detail.isVisible()

    def _info_row(self, title: str) -> QLabel:
        label = QLabel(f"{title}\n-")
        label.setProperty("role", "row")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _format_date(raw: Any) -> str:
        if not raw:
            return "-"
        if isinstance(raw, datetime):
            return raw.strftime("%Y-%m-%d %H:%M")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M")
            except Exception:
                return raw
        return str(raw)

    @staticmethod
    def _format_size(raw: Any) -> str:
        if raw is None:
            return "-"
        try:
            size = float(raw)
        except (TypeError, ValueError):
            return str(raw)
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1
        return f"{size:.1f} {units[idx]}"
