from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class FileCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PreviewCard")
        self.setMinimumSize(520, 340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        self._preview_label = QLabel("Preview")
        self._preview_label.setObjectName("PreviewLabel")

        self._surface = QFrame()
        self._surface.setObjectName("PreviewSurface")
        surface_layout = QVBoxLayout(self._surface)
        surface_layout.setContentsMargins(36, 36, 36, 36)
        surface_layout.setSpacing(14)
        surface_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("No file selected")
        self._title.setObjectName("PreviewTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)

        self._asset = QLabel("")
        self._asset.setObjectName("PreviewAsset")
        self._asset.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._asset.setWordWrap(True)

        self._hint = QLabel("Use KEEP, ARCHIVE, or NOT NEEDED to classify this file.")
        self._hint.setObjectName("PreviewHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)

        surface_layout.addWidget(self._title)
        surface_layout.addWidget(self._asset, 1)
        surface_layout.addWidget(self._hint)

        layout.addWidget(self._preview_label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._surface, 1)

        self.setStyleSheet(
            """
            QFrame#PreviewCard {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 16px;
            }
            QLabel#PreviewLabel {
                color: #b3b3b3;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QFrame#PreviewSurface {
                background: #0f0f0f;
                border: 1px solid #2f2f2f;
                border-radius: 14px;
            }
            QLabel#PreviewTitle {
                color: #ffffff;
                font-size: 20px;
                font-weight: 600;
            }
            QLabel#PreviewAsset {
                color: #c8c8c8;
                font-size: 13px;
                border: 1px solid #2f2f2f;
                border-radius: 8px;
                background: #141414;
                padding: 10px;
            }
            QLabel#PreviewHint {
                color: #6b6b6b;
                font-size: 12px;
            }
            """
        )

    def set_file(self, file_data: Mapping[str, Any]) -> None:
        filename = str(file_data.get("filename") or "Unnamed file")
        self._title.setText(filename)
        preview_path_raw = file_data.get("preview_path")
        preview_path = str(preview_path_raw) if preview_path_raw else ""
        self._asset.clear()

        if preview_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    480,
                    280,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._asset.setPixmap(scaled)
                return

        if preview_path.lower().endswith(".txt"):
            try:
                snippet = Path(preview_path).read_text(encoding="utf-8", errors="replace")[:500].strip()
                if snippet:
                    self._asset.setText(snippet)
                    return
            except Exception:
                pass

        self._asset.setText("No generated preview asset available yet.")
