from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class FileCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PreviewCard")
        self.setMinimumSize(520, 340)
        self._focus_mode = False
        self._last_preview_path = ""
        self._last_file_data: Mapping[str, Any] | None = None
        self._loading_frames = ("Loading", "Loading.", "Loading..", "Loading...")
        self._loading_index = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        label_row = QWidget()
        label_row_layout = QHBoxLayout(label_row)
        label_row_layout.setContentsMargins(0, 0, 0, 0)
        label_row_layout.setSpacing(10)

        self._preview_label = QLabel("File Preview")
        self._preview_label.setObjectName("PreviewLabel")
        self._loading_label = QLabel("Loading")
        self._loading_label.setObjectName("PreviewLoading")
        self._loading_label.setVisible(False)

        label_row_layout.addWidget(self._preview_label, 0, Qt.AlignmentFlag.AlignLeft)
        label_row_layout.addStretch(1)
        label_row_layout.addWidget(self._loading_label, 0, Qt.AlignmentFlag.AlignRight)

        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(130)
        self._loading_timer.timeout.connect(self._advance_loading_text)

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

        layout.addWidget(label_row, 0)
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
            QLabel#PreviewLoading {
                color: #19c37d;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.3px;
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
        self._last_file_data = file_data
        filename = str(file_data.get("filename") or "Unnamed file")
        self._title.setText(filename)
        self._preview_label.setText(self._friendly_preview_label(file_data))
        preview_path_raw = file_data.get("preview_path")
        self._last_preview_path = str(preview_path_raw) if preview_path_raw else ""
        self._asset.clear()
        self._render_asset()

    def set_focus_mode(self, enabled: bool) -> None:
        self._focus_mode = enabled
        if self._last_file_data is None:
            return
        self._render_asset()

    def _render_asset(self) -> None:
        preview_path = self._last_preview_path

        if preview_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                max_w = 760 if self._focus_mode else 480
                max_h = 500 if self._focus_mode else 280
                scaled = pixmap.scaled(
                    max_w,
                    max_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._asset.setPixmap(scaled)
                return

        if preview_path.lower().endswith(".txt"):
            try:
                max_chars = 1400 if self._focus_mode else 500
                snippet = Path(preview_path).read_text(encoding="utf-8", errors="replace")[:max_chars].strip()
                if snippet:
                    self._asset.setText(snippet)
                    return
            except Exception:
                pass

        self._asset.setText("No generated preview asset available yet.")

    def set_loading_state(self, is_loading: bool) -> None:
        if is_loading:
            self._loading_index = 0
            self._loading_label.setText(self._loading_frames[self._loading_index])
            self._loading_label.setVisible(True)
            self._loading_timer.start()
            return

        self._loading_timer.stop()
        self._loading_label.setVisible(False)

    def _advance_loading_text(self) -> None:
        self._loading_index = (self._loading_index + 1) % len(self._loading_frames)
        self._loading_label.setText(self._loading_frames[self._loading_index])

    def _friendly_preview_label(self, file_data: Mapping[str, Any]) -> str:
        extension = self._resolve_file_extension(file_data)
        if not extension:
            return "File Preview"

        named_types = {
            "pdf": "PDF",
            "doc": "Word Document",
            "docx": "Word Document",
            "odt": "Word Document",
            "rtf": "Word Document",
            "xls": "Spreadsheet",
            "xlsx": "Spreadsheet",
            "ods": "Spreadsheet",
            "csv": "Spreadsheet",
            "ppt": "Presentation",
            "pptx": "Presentation",
            "odp": "Presentation",
            "zip": "Archive",
            "rar": "Archive",
            "7z": "Archive",
            "tar": "Archive",
            "gz": "Archive",
            "tgz": "Archive",
            "eml": "Email",
            "msg": "Email",
            "html": "Web Document",
            "htm": "Web Document",
            "xml": "Web Document",
            "txt": "Text",
            "md": "Text",
            "jpg": "Image",
            "jpeg": "Image",
            "png": "Image",
            "webp": "Image",
            "bmp": "Image",
            "gif": "Image",
            "svg": "Image",
        }
        label = named_types.get(extension) or extension.upper()
        return f"{label} Preview"

    def _resolve_file_extension(self, file_data: Mapping[str, Any]) -> str:
        filetype = str(file_data.get("filetype") or "").strip().lower().lstrip(".")
        if filetype:
            return filetype

        filename = str(file_data.get("filename") or "").strip()
        if filename:
            suffix = Path(filename).suffix.lower().lstrip(".")
            if suffix:
                return suffix

        raw_path = str(file_data.get("path") or "").strip()
        if raw_path:
            return Path(raw_path).suffix.lower().lstrip(".")
        return ""
