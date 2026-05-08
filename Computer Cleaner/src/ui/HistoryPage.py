from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.models.swipe_model import SwipeDecision, SwipeFilters, SwipePagination, SwipeSort, SwipeSortField, SwipeSortOrder, SwipeSource
from backend.services.swipe_service import SwipeService


@dataclass
class _QueryState:
    page_size: int = 50
    offset: int = 0


class HistoryPage(QDialog):
    def __init__(self, swipe_service: SwipeService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = swipe_service
        self._query = _QueryState()
        self._records: list[Any] = []
        self._total = 0

        self.setWindowTitle("History")
        self.resize(1240, 760)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("History")
        title_font = QFont("Segoe UI", 30)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        root.addWidget(self._build_filters())
        root.addWidget(self._build_table(), 1)
        root.addWidget(self._build_detail_panel())

        self._load_page(reset=True)

    def _build_filters(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)

        self._decision_filter = QComboBox()
        self._decision_filter.addItems(["All decisions", "KEEP", "DELETE", "ARCHIVE", "UNSURE"])

        self._source_filter = QComboBox()
        self._source_filter.addItems(["All sources", "human", "AI", "rule engine"])

        self._type_filter = QLineEdit()
        self._type_filter.setPlaceholderText("File type (pdf, jpg...)")

        self._date_from = QLineEdit()
        self._date_from.setPlaceholderText("Date from (YYYY-MM-DD)")
        self._date_to = QLineEdit()
        self._date_to.setPlaceholderText("Date to (YYYY-MM-DD)")

        self._sort_field = QComboBox()
        self._sort_field.addItems(["Newest → Oldest", "Oldest → Newest", "File size", "Decision type"])

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search file name or path")

        self._page_size = QSpinBox()
        self._page_size.setRange(25, 200)
        self._page_size.setValue(50)

        apply_button = QPushButton("Apply Filters")
        apply_button.clicked.connect(lambda: self._load_page(reset=True))
        load_more_button = QPushButton("Load More")
        load_more_button.clicked.connect(lambda: self._load_page(reset=False))

        controls = [
            ("Decision", self._decision_filter),
            ("Source", self._source_filter),
            ("File Type", self._type_filter),
            ("Date From", self._date_from),
            ("Date To", self._date_to),
            ("Sort", self._sort_field),
            ("Search", self._search_input),
            ("Page Size", self._page_size),
        ]
        for i, (label, widget) in enumerate(controls):
            layout.addWidget(QLabel(label), i // 4 * 2, i % 4)
            layout.addWidget(widget, i // 4 * 2 + 1, i % 4)

        button_row = QHBoxLayout()
        button_row.addWidget(apply_button)
        button_row.addWidget(load_more_button)
        button_row.addStretch(1)
        self._summary = QLabel("0 records")
        button_row.addWidget(self._summary)
        layout.addLayout(button_row, 4, 0, 1, 4)
        return panel

    def _build_table(self) -> QWidget:
        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels([
            "File",
            "Path",
            "Decision",
            "Timestamp",
            "Source",
            "AI Suggestion",
            "Override",
            "Size",
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._sync_detail)
        return self._table

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        form = QFormLayout(panel)
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setFixedHeight(180)
        form.addRow("Expanded record", self._detail)
        return panel

    def _load_page(self, reset: bool) -> None:
        if reset:
            self._query.offset = 0
            self._records = []
            self._table.setRowCount(0)
        self._query.page_size = self._page_size.value()

        filters = SwipeFilters(
            decision=self._parse_decision(self._decision_filter.currentText()),
            file_type=(self._type_filter.text().strip() or None),
            date_from=(self._date_from.text().strip() or None),
            date_to=(self._date_to.text().strip() or None),
            source=self._parse_source(self._source_filter.currentText()),
            search=(self._search_input.text().strip() or None),
        )
        sort = self._parse_sort()
        page, total = self._service.get_swipes(filters=filters, pagination=SwipePagination(limit=self._query.page_size, offset=self._query.offset), sort=sort)
        self._total = total
        self._records.extend(page)
        self._append_rows(page)
        self._query.offset += len(page)
        self._summary.setText(f"{len(self._records)} / {self._total} records")

    def _append_rows(self, page: list[Any]) -> None:
        for rec in page:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                rec.file_name,
                self._truncate_path(rec.file_path),
                rec.decision.value,
                self._human_time(rec.timestamp),
                rec.source.value,
                rec.ai_suggestion.value if rec.ai_suggestion else "—",
                "Yes" if rec.user_override else "No",
                self._format_size(rec.file_size),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 2:
                    self._tint_decision(item, rec.decision)
                self._table.setItem(row, col, item)

    def _sync_detail(self) -> None:
        items = self._table.selectedItems()
        if not items:
            return
        idx = items[0].row()
        if idx >= len(self._records):
            return
        rec = self._records[idx]
        details = (
            f"File Name: {rec.file_name}\n"
            f"Full Path: {rec.file_path}\n"
            f"Type: {rec.file_type}\n"
            f"Decision: {rec.decision.value}\n"
            f"Source: {rec.source.value}\n"
            f"AI Suggestion: {rec.ai_suggestion.value if rec.ai_suggestion else 'None'}\n"
            f"Override: {rec.user_override}\n"
            f"Timestamp: {rec.timestamp}\n"
            f"Created Date: {datetime.fromisoformat(rec.timestamp.replace('Z', '+00:00')).date()}\n"
            f"Modified Date: {datetime.fromtimestamp(Path(rec.file_path).stat().st_mtime).isoformat() if Path(rec.file_path).exists() else 'Unavailable'}\n"
            f"Metadata: hash={rec.file_hash or 'None'}, reviewed={rec.reviewed}, active={rec.is_active}\n"
            f"Extracted Text Snippet: preview not available in this build."
        )
        self._detail.setPlainText(details)

    @staticmethod
    def _parse_decision(value: str) -> SwipeDecision | None:
        return SwipeDecision(value) if value in SwipeDecision._value2member_map_ else None

    @staticmethod
    def _parse_source(value: str) -> SwipeSource | None:
        return SwipeSource(value) if value in SwipeSource._value2member_map_ else None

    def _parse_sort(self) -> SwipeSort:
        value = self._sort_field.currentText()
        if value == "Oldest → Newest":
            return SwipeSort(field=SwipeSortField.TIMESTAMP, order=SwipeSortOrder.ASC)
        if value == "File size":
            return SwipeSort(field=SwipeSortField.FILE_SIZE, order=SwipeSortOrder.DESC)
        if value == "Decision type":
            return SwipeSort(field=SwipeSortField.DECISION, order=SwipeSortOrder.ASC)
        return SwipeSort(field=SwipeSortField.TIMESTAMP, order=SwipeSortOrder.DESC)

    @staticmethod
    def _truncate_path(path: str) -> str:
        return path if len(path) < 52 else f"…{path[-51:]}"

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        size = float(size_bytes)
        units = ["B", "KB", "MB", "GB"]
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size_bytes} B"

    @staticmethod
    def _human_time(ts: str) -> str:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ts

    @staticmethod
    def _tint_decision(item: QTableWidgetItem, decision: SwipeDecision) -> None:
        colors = {
            SwipeDecision.KEEP: "#19c37d",
            SwipeDecision.DELETE: "#ff5b5b",
            SwipeDecision.ARCHIVE: "#3b82f6",
            SwipeDecision.UNSURE: "#d4a72c",
        }
        item.setForeground(QColor(colors.get(decision, "#c8c8c8")))
