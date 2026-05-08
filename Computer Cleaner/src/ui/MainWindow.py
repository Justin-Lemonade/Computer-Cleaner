from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QParallelAnimationGroup, QProcess, QPropertyAnimation, QRect, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from Config import CONFIG
from backend.models.swipe_model import SwipeCreate, SwipeDecision, SwipeSource
from backend.services.swipe_service import SwipeService
from database.Db import get_connection, list_files, upsert_file
from logic.LabelHandler import LABEL_ARCHIVE, LABEL_KEEP, LABEL_NOT_NEEDED, save_label
from preview.PreviewManager import build_preview
from scanner.Metadata import get_basic_metadata
from scanner.ScanFiles import iter_files
from ui.FileCard import FileCard
from ui.InfoPanel import InfoPanel
from ui.KeyboardShortcuts import add_shortcut

LOGGER = logging.getLogger(__name__)
PREFETCH_TICK_MS = 80
DECISION_TIMEOUT_MS = 20000
HASH_MAX_BYTES = 64 * 1024 * 1024
MAX_PREVIEW_FILE_SIZE_BYTES = 200 * 1024 * 1024


@dataclass
class _QueuedPreviewRow:
    row: dict[str, Any] | None
    source_path: str
    elapsed_seconds: float
    error: str | None = None


class _ActionButton(QPushButton):
    _ROLE_COLORS = {
        "save": "#19c37d",
        "archive": "#e3ad2b",
        "delete": "#ff5b5b",
        "neutral": "#8e8e8e",
    }

    def __init__(self, text: str, role: str) -> None:
        super().__init__(text)
        self._base_size = QSize(138, 46)
        self._role = role
        self.setFixedSize(self._base_size)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 10)
        self._shadow.setBlurRadius(16)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event) -> None:
        self._shadow.setBlurRadius(34)
        self._shadow.setOffset(0, 12)
        color = QColor(self._ROLE_COLORS.get(self._role, "#8e8e8e"))
        color.setAlpha(170)
        self._shadow.setColor(color)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._shadow.setBlurRadius(16)
        self._shadow.setOffset(0, 10)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        super().leaveEvent(event)


class _AlignedMenuButton(QToolButton):
    def showMenu(self) -> None:
        menu = self.menu()
        if menu is None:
            return
        menu.ensurePolished()
        menu_size = menu.sizeHint()
        local_point = self.rect().bottomRight() - QPoint(menu_size.width(), -4)
        menu.exec(self.mapToGlobal(local_point))


class _ModeSelector(QFrame):
    _ACTIVE_MODE_STYLE = (
        "QPushButton {"
        "border: 1px solid #19c37d;"
        "border-radius: 10px;"
        "background: #121212;"
        "color: #ffffff;"
        "font-size: 12px;"
        "font-weight: 600;"
        "padding: 8px 12px;"
        "text-align: center;"
        "}"
        "QPushButton:hover {"
        "border: 1px solid #19c37d;"
        "background: #1a1a1a;"
        "color: #ffffff;"
        "}"
    )
    _INACTIVE_MODE_STYLE = (
        "QPushButton {"
        "border: 1px solid #2f2f2f;"
        "border-radius: 10px;"
        "background: #121212;"
        "color: #ffffff;"
        "font-size: 12px;"
        "font-weight: 600;"
        "padding: 8px 12px;"
        "text-align: center;"
        "}"
        "QPushButton:hover {"
        "background: #1a1a1a;"
        "border: 1px solid #19c37d;"
        "color: #19c37d;"
        "}"
    )

    def __init__(self, on_mode_clicked, button_size: QSize) -> None:
        super().__init__()
        self._on_mode_clicked = on_mode_clicked
        self._modes = ["Training", "Testing", "Automation"]
        self._active_mode = "Training"
        self._button_size = button_size
        self._padding = 8
        self._spacing = 10
        self._expanded = False
        self._active_animation: QParallelAnimationGroup | None = None
        self._buttons: dict[str, QPushButton] = {}
        self._effects: dict[str, QGraphicsOpacityEffect] = {}

        width = self._button_size.width()
        height = self._button_size.height()

        # In collapsed state: active button sits at _padding (leftmost, always visible)
        # In expanded state: three buttons laid out left-to-right; active is rightmost
        self._collapsed_x = self._padding
        self._expanded_positions_offsets = [0, width + self._spacing, 2 * (width + self._spacing)]

        self._collapsed_width = (2 * self._padding) + width
        self._expanded_width = (2 * self._padding) + (3 * width) + (2 * self._spacing)
        total_height = (2 * self._padding) + height

        self.setObjectName("ModeSelector")
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        for mode in self._modes:
            button = QPushButton(mode, self)
            button.setObjectName("ModeButton")
            button.setFixedSize(self._button_size)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=mode: self._select_mode(value))
            effect = QGraphicsOpacityEffect(button)
            button.setGraphicsEffect(effect)
            self._buttons[mode] = button
            self._effects[mode] = effect

        self._arrange(immediate=True)
        self.setStyleSheet(
            """
            QFrame#ModeSelector {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 12px;
            }
            """
        )

    def _expanded_x_for(self, mode: str) -> int:
        """Return the x position of a mode button in the expanded state."""
        # Order: inactive modes left-to-right, then active mode at the right
        others = [m for m in self._modes if m != self._active_mode]
        order = others + [self._active_mode]
        idx = order.index(mode)
        return self._padding + idx * (self._button_size.width() + self._spacing)

    def enterEvent(self, event) -> None:
        self._expanded = True
        self._arrange(immediate=False)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._expanded = False
        self._arrange(immediate=False)
        super().leaveEvent(event)

    def _select_mode(self, mode_name: str) -> None:
        self._active_mode = mode_name
        self._apply_mode_visual_state()
        self._on_mode_clicked(mode_name)
        self._expanded = False
        self._arrange(immediate=False)

    def _apply_mode_visual_state(self, *, sync_opacity: bool = False) -> None:
        for mode, button in self._buttons.items():
            is_active = mode == self._active_mode
            # Only the active button is interactive when collapsed
            should_enable = self._expanded or is_active
            # Active button always visible; others only when expanded
            target_opacity = 1.0 if (self._expanded or is_active) else 0.0

            button.setEnabled(should_enable)
            button.setStyleSheet(self._ACTIVE_MODE_STYLE if is_active else self._INACTIVE_MODE_STYLE)

            if sync_opacity:
                self._effects[mode].setOpacity(target_opacity)
            elif not self._expanded and is_active:
                # Always keep active button fully visible when collapsed
                self._effects[mode].setOpacity(1.0)

    def _arrange(self, *, immediate: bool) -> None:
        self._apply_mode_visual_state()

        target_width = self._expanded_width if self._expanded else self._collapsed_width

        if immediate:
            self.setMinimumWidth(target_width)
            self.setMaximumWidth(target_width)
            self._apply_mode_visual_state(sync_opacity=True)
            for mode, button in self._buttons.items():
                if self._expanded:
                    x = self._expanded_x_for(mode)
                else:
                    # All buttons at collapsed_x; only active is visible (others opacity=0)
                    x = self._collapsed_x
                button.move(x, self._padding)
            return

        group = QParallelAnimationGroup(self)

        min_width_anim = QPropertyAnimation(self, b"minimumWidth", self)
        min_width_anim.setDuration(150)
        min_width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        min_width_anim.setStartValue(self.minimumWidth())
        min_width_anim.setEndValue(target_width)
        group.addAnimation(min_width_anim)

        max_width_anim = QPropertyAnimation(self, b"maximumWidth", self)
        max_width_anim.setDuration(150)
        max_width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        max_width_anim.setStartValue(self.maximumWidth())
        max_width_anim.setEndValue(target_width)
        group.addAnimation(max_width_anim)

        for mode, button in self._buttons.items():
            if self._expanded:
                target_x = self._expanded_x_for(mode)
            else:
                # Collapse: all buttons slide to the collapsed position
                target_x = self._collapsed_x

            move_anim = QPropertyAnimation(button, b"pos", self)
            move_anim.setDuration(150)
            move_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            move_anim.setStartValue(button.pos())
            move_anim.setEndValue(QPoint(target_x, self._padding))
            group.addAnimation(move_anim)

            fade_anim = QPropertyAnimation(self._effects[mode], b"opacity", self)
            fade_anim.setDuration(120)
            fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            fade_anim.setStartValue(self._effects[mode].opacity())
            target_opacity = 1.0 if (self._expanded or mode == self._active_mode) else 0.0
            fade_anim.setEndValue(target_opacity)
            group.addAnimation(fade_anim)

        self._active_animation = group
        group.start()


class _BottomBar(QWidget):
    """
    Custom bottom bar that keeps action buttons centered in the full window width
    and positions the mode selector at the bottom-right, shifting buttons left
    only when necessary to prevent overlap.
    """

    _GAP = 16  # minimum gap between action dock and mode selector

    def __init__(self, action_dock: QWidget, mode_selector: _ModeSelector) -> None:
        super().__init__()
        self._action_dock = action_dock
        self._mode_selector = mode_selector

        # Both widgets become children of this bar (no layout manager — manual geometry)
        action_dock.setParent(self)
        mode_selector.setParent(self)

        # Watch the mode selector for size changes so we can relayout during animations
        mode_selector.installEventFilter(self)

        self.setMinimumHeight(70)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def eventFilter(self, watched, event) -> bool:
        # Whenever the mode selector is resized (e.g. during expand/collapse animation)
        # we reposition the action dock immediately.
        if watched is self._mode_selector and event.type() == QEvent.Type.Resize:
            self._relayout()
        return super().eventFilter(watched, event)

    def sizeHint(self) -> QSize:
        dh = self._action_dock.sizeHint().height()
        mh = self._mode_selector.sizeHint().height()
        return QSize(600, max(dh, mh) + 16)

    # ------------------------------------------------------------------
    # Layout logic
    # ------------------------------------------------------------------

    def _relayout(self) -> None:
        bar_w = self.width()
        bar_h = self.height()

        # ── Mode selector: anchor to bottom-right ──────────────────────
        ms_w = self._mode_selector.width()
        ms_h = self._mode_selector.height()
        ms_y = bar_h - ms_h
        ms_x = bar_w - ms_w
        self._mode_selector.move(ms_x, ms_y)

        # ── Action dock: center in full bar width, shift left if needed ─
        dock_hint = self._action_dock.sizeHint()
        dock_w = dock_hint.width()
        dock_h = dock_hint.height()
        dock_y = (bar_h - dock_h) // 2

        # Ideal: centered relative to full bar width
        ideal_x = (bar_w - dock_w) // 2

        # Maximum allowed x so we don't overlap the mode selector
        max_x = ms_x - dock_w - self._GAP

        # Use ideal center, but clamp so buttons never overlap the mode selector
        dock_x = min(ideal_x, max_x)
        dock_x = max(dock_x, 0)  # never go off the left edge

        self._action_dock.setGeometry(dock_x, dock_y, dock_w, dock_h)


class _SettingsDialog(QDialog):
    def __init__(self, *, queue_limit: int, auto_generate_preview: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self._queue_limit = QSpinBox()
        self._queue_limit.setRange(5, 500)
        self._queue_limit.setValue(queue_limit)
        self._queue_limit.setSingleStep(5)
        form.addRow("Preview Queue Limit", self._queue_limit)

        self._auto_generate = QCheckBox("Enable auto-generate preview")
        self._auto_generate.setChecked(auto_generate_preview)
        form.addRow("Auto-Generate Preview", self._auto_generate)
        layout.addLayout(form)

        hint = QLabel("When enabled, confirmed decisions trigger background preview generation.")
        hint.setObjectName("SettingsHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLabel#SettingsHint {
                color: #9c9c9c;
                font-size: 11px;
            }
            QSpinBox {
                border: 1px solid #3b3b3b;
                border-radius: 8px;
                background: #0e0e0e;
                color: #ffffff;
                min-height: 30px;
                padding: 0 8px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                background: #0e0e0e;
            }
            QCheckBox::indicator:checked {
                background: #19c37d;
                border-color: #19c37d;
            }
            QPushButton {
                border: 1px solid #3b3b3b;
                border-radius: 8px;
                background: #121212;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 7px 12px;
                min-width: 72px;
            }
            QPushButton:hover {
                border-color: #19c37d;
                color: #19c37d;
            }
            """
        )

    @property
    def queue_limit(self) -> int:
        return int(self._queue_limit.value())

    @property
    def auto_generate_preview(self) -> bool:
        return self._auto_generate.isChecked()


class MainWindow(QMainWindow):
    _REASON_PRESETS = {
        LABEL_KEEP: ["Used recently", "Important", "Needed for work", "Reference material"],
        LABEL_ARCHIVE: ["Sentimental value", "Important", "Need later", "Store without clutter"],
        LABEL_NOT_NEEDED: ["Not using", "Too big", "Duplicate", "Outdated"],
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("File Sorter AI")
        self.resize(1320, 860)

        self._files: list[dict[str, Any]] = []
        self._current_index = 0
        self._is_animating = False
        self._active_animation: QParallelAnimationGroup | None = None
        self._pending_decision: dict[str, Any] | None = None
        self._pending_action_text: str | None = None
        self._reason_option_buttons: list[QPushButton] = []
        self._settings = QSettings("FileSorterAI", "DesktopUI")
        self._queue_limit = int(self._settings.value("queue_limit", 20))
        self._auto_generate_preview = str(self._settings.value("auto_generate_preview", "false")).lower() in {
            "true",
            "1",
            "yes",
        }
        self._source_folder: Path | None = None
        self._pending_files: list[Path] = []
        self._pending_cursor = 0
        self._scan_iter: Any | None = None
        self._background_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ui-background")
        self._prefetch_future: Future[list[_QueuedPreviewRow]] | None = None
        self._swipe_future: Future[tuple[bool, str | None]] | None = None
        self._prefetch_timer = QTimer(self)
        self._prefetch_timer.setInterval(PREFETCH_TICK_MS)
        self._prefetch_timer.timeout.connect(self._process_prefetch_batch)
        self._is_prefetching = False
        self._swipe_poll_timer = QTimer(self)
        self._swipe_poll_timer.setInterval(60)
        self._swipe_poll_timer.timeout.connect(self._poll_swipe_future)
        self._swipe_watchdog = QTimer(self)
        self._swipe_watchdog.setSingleShot(True)
        self._swipe_watchdog.timeout.connect(self._on_swipe_timeout)
        self._pending_post_reason: dict[str, Any] | None = None
        self._swipe_service = SwipeService(CONFIG.db_path)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)
        root_layout.addWidget(self._build_top_bar())

        self._info_panel = InfoPanel()

        self._preview_stage = QFrame()
        self._preview_stage.setObjectName("PreviewStage")
        self._preview_stage.setMinimumWidth(420)
        self._preview_stage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._active_card = FileCard()
        self._active_card.setParent(self._preview_stage)
        self._active_effect = QGraphicsOpacityEffect(self._active_card)
        self._active_card.setGraphicsEffect(self._active_effect)
        self._active_effect.setOpacity(1.0)

        self._incoming_card = FileCard()
        self._incoming_card.setParent(self._preview_stage)
        self._incoming_effect = QGraphicsOpacityEffect(self._incoming_card)
        self._incoming_card.setGraphicsEffect(self._incoming_effect)
        self._incoming_effect.setOpacity(0.0)
        self._incoming_card.setVisible(False)

        self._empty_state = self._build_empty_state()
        self._empty_state.setParent(self._preview_stage)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setObjectName("MainSplitter")
        splitter.addWidget(self._info_panel)
        splitter.addWidget(self._preview_stage)
        self._reason_panel = self._build_reason_panel()
        splitter.addWidget(self._reason_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([320, 980, 0])
        root_layout.addWidget(splitter, 1)
        self._main_splitter = splitter

        self._status = QLabel("Training mode active. Classify each file with one action.")
        self._status.setObjectName("StatusText")
        root_layout.addWidget(self._status)

        # ── Bottom bar: centered action dock + mode selector ────────────
        self._action_dock = self._build_action_dock()
        self._mode_selector = _ModeSelector(self._mode_clicked, QSize(138, 46))
        self._bottom_bar = _BottomBar(self._action_dock, self._mode_selector)
        root_layout.addWidget(self._bottom_bar)

        self.setCentralWidget(root)
        self._apply_dark_theme()
        self._install_shortcuts()
        self._load_files()
        self._render_current_file()
        if self._auto_generate_preview:
            self._start_prefetch_if_needed()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._empty_state.setGeometry(self._preview_rect())
        if not self._is_animating:
            target = self._preview_rect()
            self._active_card.setGeometry(target)
            self._incoming_card.setGeometry(target)

    def closeEvent(self, event) -> None:
        self._stop_prefetch()
        if self._swipe_poll_timer.isActive():
            self._swipe_poll_timer.stop()
        if self._swipe_watchdog.isActive():
            self._swipe_watchdog.stop()
        self._background_executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

    def _build_top_bar(self) -> QWidget:
        top = QWidget()
        layout = QHBoxLayout(top)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_wrap = QWidget()
        title_layout = QVBoxLayout(title_wrap)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title = QLabel("Training")
        title_font = QFont("Segoe UI", 30)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setObjectName("PageTitle")

        self._subtitle = QLabel("Preview-first interface. One decision at a time.")
        self._subtitle.setObjectName("PageSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(self._subtitle)

        menu_button = _AlignedMenuButton()
        menu_button.setObjectName("MenuButton")
        menu_button.setText("Menu")
        menu_button.setFixedSize(96, 40)
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        menu_button.setMenu(self._build_menu())

        layout.addWidget(title_wrap, 1)
        layout.addWidget(menu_button, 0, Qt.AlignmentFlag.AlignTop)
        return top

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        scan_action = QAction("Scan Folder", self)
        scan_action.triggered.connect(self._choose_and_scan_folder)
        menu.addAction(scan_action)
        menu.addSeparator()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        clear_cache_action = QAction("Clear Cache", self)
        clear_cache_action.triggered.connect(self._clear_cache_and_restart)
        menu.addAction(clear_cache_action)

        for action_name in ("History", "Search"):
            action = QAction(action_name, self)
            action.triggered.connect(lambda _checked=False, value=action_name: self._status.setText(f"{value} coming soon."))
            menu.addAction(action)
        return menu

    def _open_settings(self) -> None:
        dialog = _SettingsDialog(
            queue_limit=self._queue_limit,
            auto_generate_preview=self._auto_generate_preview,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._queue_limit = dialog.queue_limit
        self._auto_generate_preview = dialog.auto_generate_preview
        self._settings.setValue("queue_limit", self._queue_limit)
        self._settings.setValue("auto_generate_preview", self._auto_generate_preview)
        self._status.setText(
            f"Settings saved. Queue limit: {self._queue_limit}. Auto-generate: {'On' if self._auto_generate_preview else 'Off'}."
        )
        self._trim_queue_to_limit()
        if self._auto_generate_preview:
            self._start_prefetch_if_needed()
        else:
            self._stop_prefetch()

    def _clear_cache_and_restart(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear Cache",
            "Clear queue data and restart the app?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._stop_prefetch()
        if self._swipe_watchdog.isActive():
            self._swipe_watchdog.stop()
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM labels;")
                conn.execute("DELETE FROM features;")
                conn.execute("DELETE FROM files;")
        except Exception as exc:
            self._status.setText(f"Cache clear failed ({exc}). Resetting UI state only.")
            self._reset_to_default_state()
            return

        self._reset_to_default_state()
        self._restart_application()

    def _restart_application(self) -> None:
        try:
            python_exec = sys.executable
            argv = list(sys.argv)
            if not argv:
                argv = [str(Path(__file__).resolve().parents[2] / "App.py")]
            ok = QProcess.startDetached(python_exec, argv, str(Path.cwd()))
            if ok:
                self.close()
                return
            self._status.setText("Restart failed to start detached process. Queue cleared and UI reset.")
        except Exception as exc:
            LOGGER.exception("Restart failed")
            self._status.setText(f"Restart failed ({exc}). Queue cleared and UI reset.")

    def _reset_to_default_state(self) -> None:
        self._source_folder = None
        self._pending_files = []
        self._pending_cursor = 0
        self._scan_iter = None
        self._files = []
        self._reset_indices()
        self._pending_decision = None
        self._pending_post_reason = None
        if self._swipe_poll_timer.isActive():
            self._swipe_poll_timer.stop()
        if self._swipe_watchdog.isActive():
            self._swipe_watchdog.stop()
        if self._prefetch_future and not self._prefetch_future.done():
            self._prefetch_future.cancel()
        if self._swipe_future and not self._swipe_future.done():
            self._swipe_future.cancel()
        self._prefetch_future = None
        self._swipe_future = None
        self._reason_panel.setVisible(False)
        self._render_current_file()

    def _build_action_dock(self) -> QWidget:
        dock = QWidget()
        dock.setObjectName("ActionDock")
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        specs = [
            ("DELETE", "delete", self._on_not_needed),
            ("ARCHIVE", "archive", self._on_archive),
            ("MORE INFO", "neutral", self._toggle_details),
            ("OPEN FILE", "neutral", self._open_file),
            ("SAVE", "save", self._on_keep),
        ]
        for text, role, callback in specs:
            button = _ActionButton(text, role)
            button.setObjectName("ActionButton")
            button.setProperty("role", role)
            button.clicked.connect(callback)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        # Dock sizes itself to its buttons — no stretch needed
        dock.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return dock

    def _build_reason_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ReasonPanel")
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(320)
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        panel.setVisible(False)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Reason")
        title.setObjectName("ReasonTitle")
        layout.addWidget(title)

        self._reason_hint = QLabel("Choose why this decision was made.")
        self._reason_hint.setWordWrap(True)
        self._reason_hint.setObjectName("ReasonHint")
        layout.addWidget(self._reason_hint)

        self._reason_buttons_wrap = QWidget()
        self._reason_buttons_layout = QVBoxLayout(self._reason_buttons_wrap)
        self._reason_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self._reason_buttons_layout.setSpacing(8)
        layout.addWidget(self._reason_buttons_wrap)

        self._custom_reason_input = QLineEdit()
        self._custom_reason_input.setObjectName("ReasonInput")
        self._custom_reason_input.setPlaceholderText("Enter custom reason")
        self._custom_reason_input.setVisible(False)
        self._custom_reason_input.returnPressed.connect(self._submit_custom_reason)
        layout.addWidget(self._custom_reason_input)

        self._custom_submit_button = QPushButton("Save custom reason")
        self._custom_submit_button.setObjectName("ReasonCustomSubmit")
        self._custom_submit_button.clicked.connect(self._submit_custom_reason)
        self._custom_submit_button.setVisible(False)
        layout.addWidget(self._custom_submit_button)
        layout.addStretch(1)
        return panel

    def _build_empty_state(self) -> QFrame:
        state = QFrame()
        state.setObjectName("EmptyQueueState")

        layout = QVBoxLayout(state)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("No files in your queue yet")
        title.setObjectName("EmptyQueueTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Pick a folder to scan and generate previews before you start swiping.")
        hint.setObjectName("EmptyQueueHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 4, 0, 0)
        actions_layout.setSpacing(12)

        random_button = _ActionButton("Choose Random Folder", "neutral")
        random_button.setObjectName("EmptyStateActionButton")
        random_button.clicked.connect(self._choose_random_folder)

        select_button = _ActionButton("Select", "save")
        select_button.setObjectName("EmptyStateActionButton")
        select_button.clicked.connect(self._select_folder)

        actions_layout.addWidget(random_button)
        actions_layout.addWidget(select_button)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(actions, 0, Qt.AlignmentFlag.AlignCenter)
        return state

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #0f0f0f;
            }
            QFrame#PreviewStage {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 16px;
            }
            QSplitter#MainSplitter::handle {
                background: #2f2f2f;
            }
            QLabel#PageTitle {
                color: #ffffff;
            }
            QLabel#PageSubtitle {
                color: #b3b3b3;
                font-size: 13px;
            }
            QLabel#StatusText {
                color: #b3b3b3;
                font-size: 12px;
            }
            QWidget#ActionDock {
                background: transparent;
                border: none;
                border-radius: 0px;
            }
            QFrame#EmptyQueueState {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 16px;
            }
            QLabel#EmptyQueueTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#EmptyQueueHint {
                color: #b3b3b3;
                font-size: 13px;
            }
            QFrame#ReasonPanel {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 14px;
            }
            QLabel#ReasonTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#ReasonHint {
                color: #b3b3b3;
                font-size: 12px;
            }
            QPushButton#ReasonChoice {
                border: 1px solid #3b3b3b;
                border-radius: 8px;
                background: #0e0e0e;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
                padding: 8px 10px;
            }
            QPushButton#ReasonChoice:hover {
                border-color: #19c37d;
                color: #19c37d;
            }
            QLineEdit#ReasonInput {
                border: 1px solid #3b3b3b;
                border-radius: 8px;
                background: #0e0e0e;
                color: #ffffff;
                padding: 7px 10px;
            }
            QPushButton#ReasonCustomSubmit {
                border: 1px solid #2f2f2f;
                border-radius: 8px;
                background: #121212;
                color: #ffffff;
                font-size: 12px;
                padding: 8px 10px;
            }
            QPushButton#ActionButton {
                border: 1px solid #3b3b3b;
                border-radius: 10px;
                background: #0e0e0e;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
                padding: 8px 10px;
            }
            QPushButton#ActionButton[role="neutral"] {
                border-color: #5a5a5a;
            }
            QPushButton#ActionButton[role="neutral"]:hover {
                color: #d1d1d1;
            }
            QPushButton#ActionButton[role="save"] {
                border-color: #19c37d;
            }
            QPushButton#ActionButton[role="save"]:hover {
                color: #19c37d;
            }
            QPushButton#ActionButton[role="archive"] {
                border-color: #e3ad2b;
            }
            QPushButton#ActionButton[role="archive"]:hover {
                color: #e3ad2b;
            }
            QPushButton#ActionButton[role="delete"] {
                border-color: #ff5b5b;
            }
            QPushButton#ActionButton[role="delete"]:hover {
                color: #ff5b5b;
            }
            QToolButton#MenuButton {
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                background: #212121;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 14px;
            }
            QToolButton#MenuButton:hover {
                background: #2a2a2a;
                border-color: #19c37d;
            }
            QToolButton#MenuButton::menu-indicator {
                image: none;
                width: 0px;
            }
            QMenu {
                background: #171717;
                color: #ffffff;
                border: 1px solid #2f2f2f;
                padding: 6px;
                margin-top: 6px;
            }
            QMenu::item {
                background: transparent;
                padding: 8px 12px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background: #2a2a2a;
            }
            """
        )

    def _install_shortcuts(self) -> None:
        add_shortcut(self, "Left", self._on_not_needed)
        add_shortcut(self, "A", self._on_not_needed)
        add_shortcut(self, "Right", self._on_keep)
        add_shortcut(self, "D", self._on_keep)
        add_shortcut(self, "Up", self._on_archive)
        add_shortcut(self, "W", self._on_archive)
        add_shortcut(self, "Down", self._toggle_details)
        add_shortcut(self, "S", self._toggle_details)
        add_shortcut(self, "Space", self._open_file)

    def _load_files(self) -> None:
        try:
            rows = list_files(limit=self._queue_limit)
            self._files = [dict(row) for row in rows]
            self._reset_indices()
        except Exception as exc:
            self._files = []
            self._reset_indices()
            self._status.setText(f"Database read failed. ({exc})")

        if self._files:
            return

        self._status.setText("No scanned files found. Use Menu → Scan Folder to start.")

    def _choose_and_scan_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder to scan", str(Path.home()))
        if not folder:
            self._status.setText("Folder scan canceled.")
            return
        self._scan_folder(Path(folder))

    def _scan_folder(self, folder: Path) -> None:
        try:
            self._scan_folder_and_prepare_queue(folder)
        except Exception as exc:
            self._status.setText(f"Folder scan failed ({exc})")
        self._current_index = 0

    def _render_current_file(self, *, action_text: str | None = None) -> None:
        self._empty_state.setGeometry(self._preview_rect())
        if not self._files:
            self._set_empty_state_visible(True)
            self._subtitle.setText("Training mode | Queue is empty")
            return

        self._set_empty_state_visible(False)
        current = self._files[self._current_index]
        total = len(self._files)
        self._active_card.set_file(current)
        self._active_card.set_loading_state(False)
        self._incoming_card.set_loading_state(False)
        self._info_panel.set_file(current, index=self._current_index + 1, total=total)
        self._active_card.setGeometry(self._preview_rect())
        self._active_effect.setOpacity(1.0)
        self._incoming_effect.setOpacity(0.0)
        self._incoming_card.setVisible(False)
        self._subtitle.setText(f"Training mode | File {self._current_index + 1} of {total}")
        if action_text:
            self._status.setText(f"{action_text} logged. Showing next file.")

    def _preview_rect(self) -> QRect:
        rect = self._preview_stage.contentsRect()
        width = min(max(rect.width() - 36, 520), 1100)
        height = min(max(rect.height() - 36, 340), 680)
        x = rect.x() + (rect.width() - width) // 2
        y = rect.y() + (rect.height() - height) // 2
        return QRect(x, y, width, height)

    def _current_file(self) -> dict[str, Any]:
        return self._files[self._current_index]

    def _reset_indices(self) -> None:
        self._current_index = 0

    def _set_empty_state_visible(self, is_visible: bool) -> None:
        self._empty_state.setVisible(is_visible)
        self._active_card.setVisible(not is_visible)
        self._incoming_card.setVisible(False)
        self._action_dock.setEnabled(not is_visible)

    def _prefetch_batch_size(self) -> int:
        return max(1, min(5, self._queue_limit))

    def _has_pending_files(self) -> bool:
        if self._pending_cursor < len(self._pending_files):
            return True
        return self._scan_iter is not None

    def _trim_queue_to_limit(self) -> None:
        if len(self._files) <= self._queue_limit:
            return
        self._files = self._files[: self._queue_limit]
        if self._current_index >= len(self._files):
            self._current_index = 0
        self._render_current_file()

    def _next_pending_path(self) -> Path | None:
        if self._pending_cursor < len(self._pending_files):
            path = self._pending_files[self._pending_cursor]
            self._pending_cursor += 1
            return path
        if self._scan_iter is None:
            return None
        try:
            return next(self._scan_iter)
        except StopIteration:
            self._scan_iter = None
            return None

    def _fill_queue_sync(self, *, max_items: int) -> int:
        if max_items <= 0:
            return 0

        generated = 0
        while generated < max_items and len(self._files) < self._queue_limit and self._has_pending_files():
            file_path = self._next_pending_path()
            if file_path is None:
                break
            try:
                row = self._build_row_for_path(file_path)
                self._files.append(row)
                generated += 1
            except Exception:
                # Skip problematic files (e.g., malformed office docs) without crashing queue generation.
                LOGGER.exception("Queue generation failed for %s", file_path)
                continue
        return generated

    def _start_prefetch_if_needed(self) -> None:
        if not self._auto_generate_preview:
            return
        if not self._has_pending_files():
            return
        if len(self._files) >= self._queue_limit:
            return
        if not self._prefetch_timer.isActive():
            self._prefetch_timer.start()

    def _stop_prefetch(self) -> None:
        if self._prefetch_timer.isActive():
            self._prefetch_timer.stop()
        self._is_prefetching = False
        if self._prefetch_future and self._prefetch_future.done():
            self._prefetch_future = None

    def _process_prefetch_batch(self) -> None:
        if self._is_prefetching:
            return
        self._is_prefetching = True
        try:
            if len(self._files) >= self._queue_limit or not self._has_pending_files():
                self._stop_prefetch()
                return

            if self._prefetch_future is None:
                batch_paths: list[Path] = []
                for _ in range(self._prefetch_batch_size()):
                    next_path = self._next_pending_path()
                    if next_path is None:
                        break
                    batch_paths.append(next_path)
                if not batch_paths:
                    self._stop_prefetch()
                    return
                self._prefetch_future = self._background_executor.submit(self._build_rows_for_batch, batch_paths)
                return

            if not self._prefetch_future.done():
                return

            try:
                results = self._prefetch_future.result(timeout=0.01)
            except Exception:
                LOGGER.exception("Background prefetch batch failed")
                results = []
            finally:
                self._prefetch_future = None

            added = self._apply_prefetch_results(results)
            if added <= 0 and not self._has_pending_files():
                self._stop_prefetch()
                return
            if not self._auto_generate_preview and self._files:
                self._stop_prefetch()
                return
            if len(self._files) >= self._queue_limit or not self._has_pending_files():
                self._stop_prefetch()
        finally:
            self._is_prefetching = False

    def _build_rows_for_batch(self, batch_paths: list[Path]) -> list[_QueuedPreviewRow]:
        results: list[_QueuedPreviewRow] = []
        for path in batch_paths:
            started = time.perf_counter()
            try:
                row = self._build_row_for_path(path)
                elapsed = time.perf_counter() - started
                results.append(_QueuedPreviewRow(row=row, source_path=str(path), elapsed_seconds=elapsed))
            except Exception as exc:
                elapsed = time.perf_counter() - started
                results.append(_QueuedPreviewRow(row=None, source_path=str(path), elapsed_seconds=elapsed, error=str(exc)))
        return results

    def _apply_prefetch_results(self, results: list[_QueuedPreviewRow]) -> int:
        had_no_files = not self._files
        added = 0
        for result in results:
            if result.row is None:
                LOGGER.warning(
                    "Skipped preview build for %s in %.2fs (%s)",
                    result.source_path,
                    result.elapsed_seconds,
                    result.error or "unknown error",
                )
                continue
            self._files.append(result.row)
            added += 1
            LOGGER.info(
                "Queued %s in %.2fs (queue=%d/%d)",
                result.source_path,
                result.elapsed_seconds,
                len(self._files),
                self._queue_limit,
            )
        if had_no_files and added > 0 and not self._is_animating and self._pending_post_reason is None:
            self._render_current_file()
        return added

    def _build_row_for_path(self, file_path: Path) -> dict[str, Any]:
        metadata = get_basic_metadata(file_path)
        preview_path = None
        size = int(metadata.size or 0)
        if size <= MAX_PREVIEW_FILE_SIZE_BYTES:
            preview_path = build_preview(file_path, mime_type=metadata.mime_type, filetype=metadata.filetype)
        else:
            LOGGER.info("Skipping preview generation for large file %s (%d bytes)", file_path, size)
        return {
            "id": upsert_file(
                {
                    "path": str(metadata.path),
                    "filename": metadata.filename,
                    "filetype": metadata.filetype,
                    "mime_type": metadata.mime_type,
                    "size": size,
                    "created_date": metadata.created_date,
                    "modified_date": metadata.modified_date,
                    "preview_path": str(preview_path) if preview_path else None,
                }
            ),
            "path": str(metadata.path),
            "filename": metadata.filename,
            "filetype": metadata.filetype,
            "mime_type": metadata.mime_type,
            "size": size,
            "created_date": metadata.created_date.isoformat() if metadata.created_date else None,
            "modified_date": metadata.modified_date.isoformat() if metadata.modified_date else None,
            "preview_path": str(preview_path) if preview_path else None,
        }

    def _common_user_folders(self) -> list[Path]:
        home = Path.home()
        candidates = [
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "Pictures",
            home / "Videos",
            home / "Music",
        ]
        return [folder for folder in candidates if folder.exists() and folder.is_dir()]

    def _deterministic_folder_choice(self) -> Path | None:
        folders = sorted(self._common_user_folders(), key=lambda item: str(item).lower())
        if not folders:
            return None
        digest = sha256(str(Path.home()).encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(folders)
        return folders[index]

    def _select_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select folder to scan", str(Path.home()))
        if not selected:
            self._status.setText("Folder selection cancelled.")
            return
        self._scan_folder_and_prepare_queue(Path(selected))

    def _choose_random_folder(self) -> None:
        selected = self._deterministic_folder_choice()
        if selected is None:
            self._status.setText("No common user folders were found.")
            return
        self._scan_folder_and_prepare_queue(selected)

    def _scan_folder_and_prepare_queue(self, folder: Path) -> None:
        folder = folder.expanduser()
        if not folder.exists() or not folder.is_dir():
            self._status.setText(f"Invalid folder selected: {folder}")
            return

        try:
            self._stop_prefetch()
            if self._swipe_poll_timer.isActive():
                self._swipe_poll_timer.stop()
            if self._prefetch_future and not self._prefetch_future.done():
                self._prefetch_future.cancel()
            self._prefetch_future = None
            scan_started = time.perf_counter()
            self._source_folder = folder
            self._scan_iter = iter_files(folder)
            self._pending_files = []
            self._pending_cursor = 0
            self._files = []
            self._reset_indices()
            initial_batch = min(self._prefetch_batch_size(), self._queue_limit)
            self._fill_queue_sync(max_items=initial_batch)
            self._render_current_file()
            elapsed = time.perf_counter() - scan_started
            if self._files:
                self._status.setText(
                    f"Queued {len(self._files)} files from {folder} in {elapsed:.2f}s. "
                    f"Background prefetch {'enabled' if self._auto_generate_preview else 'disabled'}."
                )
                LOGGER.info(
                    "Folder scan initialized for %s: queue=%d/%d, elapsed=%.2fs",
                    folder,
                    len(self._files),
                    self._queue_limit,
                    elapsed,
                )
            else:
                self._status.setText("Scan completed but no queueable files were found.")
                LOGGER.info("Folder scan found no queueable files for %s", folder)
            if self._auto_generate_preview:
                self._start_prefetch_if_needed()
            else:
                self._stop_prefetch()
        except Exception as exc:
            LOGGER.exception("Folder processing failed for %s", folder)
            self._status.setText(f"Folder processing failed ({exc})")

    def _on_keep(self) -> None:
        self._handle_decision("KEEP", LABEL_KEEP, SwipeDecision.KEEP, QPoint(260, 0))

    def _on_archive(self) -> None:
        self._handle_decision("ARCHIVE", LABEL_ARCHIVE, SwipeDecision.ARCHIVE, QPoint(0, -220))

    def _on_not_needed(self) -> None:
        self._handle_decision("NOT NEEDED", LABEL_NOT_NEEDED, SwipeDecision.DELETE, QPoint(-260, 0))

    def _handle_decision(self, action_name: str, label_name: str, decision: SwipeDecision, offset: QPoint) -> None:
        if self._is_animating or not self._files:
            return

        had_pending_decision = self._pending_decision is not None
        LOGGER.info(
            "Decision selected: action=%s label=%s file=%s",
            action_name,
            label_name,
            self._current_file().get("path"),
        )
        self._pending_decision = {
            "action_name": action_name,
            "label_name": label_name,
            "decision": decision,
            "offset": offset,
        }
        self._show_reason_panel(action_name, label_name)
        if had_pending_decision:
            self._status.setText(f"Decision changed to {action_name}. Choose a reason to continue.")

    def _show_reason_panel(self, action_name: str, label_name: str) -> None:
        self._reason_panel.setVisible(True)
        self._reason_hint.setText(f"Decision: {action_name}. Select a reason for this swipe.")
        self._custom_reason_input.clear()
        self._custom_reason_input.setVisible(False)
        self._custom_reason_input.setEnabled(True)
        self._custom_submit_button.setVisible(False)
        self._custom_submit_button.setEnabled(True)
        self._reason_option_buttons = []

        while self._reason_buttons_layout.count():
            item = self._reason_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        options = self._REASON_PRESETS.get(label_name, [])
        for option in options:
            button = QPushButton(option)
            button.setObjectName("ReasonChoice")
            button.clicked.connect(lambda _checked=False, reason=option: self._submit_reason(reason))
            self._reason_buttons_layout.addWidget(button)
            self._reason_option_buttons.append(button)

        custom_button = QPushButton("Different option")
        custom_button.setObjectName("ReasonChoice")
        custom_button.clicked.connect(self._open_custom_reason_input)
        self._reason_buttons_layout.addWidget(custom_button)
        self._reason_option_buttons.append(custom_button)
        self._main_splitter.setSizes([300, 760, 260])
        self._status.setText(f"{action_name} selected. Add a reason to continue.")

    def _open_custom_reason_input(self) -> None:
        self._custom_reason_input.setVisible(True)
        self._custom_submit_button.setVisible(True)
        self._custom_reason_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _submit_custom_reason(self) -> None:
        reason = self._custom_reason_input.text().strip()
        if not reason:
            self._status.setText("Custom reason cannot be empty.")
            return
        self._submit_reason(reason)

    def _submit_reason(self, reason: str) -> None:
        if not self._pending_decision:
            return
        if self._swipe_future and not self._swipe_future.done():
            self._status.setText("Still saving the previous decision. Please wait.")
            return
        for button in self._reason_option_buttons:
            button.setEnabled(False)
        self._custom_reason_input.setEnabled(False)
        self._custom_submit_button.setEnabled(False)

        current = self._current_file()
        file_id = current.get("id")
        label_name = self._pending_decision["label_name"]
        decision = self._pending_decision["decision"]
        action_name = self._pending_decision["action_name"]
        offset = self._pending_decision["offset"]
        path = str(current.get("path") or "")
        filename = str(current.get("filename") or Path(path).name or "unknown")
        filetype = str(current.get("filetype") or Path(path).suffix.lstrip(".") or "unknown")
        size = int(current.get("size") or 0)

        payload = {
            "file_id": file_id,
            "label_name": label_name,
            "decision": decision,
            "action_name": action_name,
            "offset": offset,
            "reason": reason,
            "path": path,
            "filename": filename,
            "filetype": filetype,
            "size": max(size, 0),
        }
        self._pending_decision = None
        self._pending_post_reason = payload
        self._active_card.set_loading_state(True)
        self._incoming_card.set_loading_state(True)
        self._status.setText("Saving decision...")

        self._swipe_future = self._background_executor.submit(self._persist_decision_payload, payload)
        if not self._swipe_poll_timer.isActive():
            self._swipe_poll_timer.start()
        self._swipe_watchdog.start(DECISION_TIMEOUT_MS)

    def _persist_decision_payload(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        started = time.perf_counter()
        errors: list[str] = []

        file_id = payload.get("file_id")
        if isinstance(file_id, int):
            try:
                save_label(file_id, str(payload["label_name"]), notes=str(payload["reason"]))
            except Exception as exc:
                errors.append(f"label save failed: {exc}")

        path = str(payload.get("path") or "")
        if path:
            try:
                hash_value = self._compute_file_hash(path, max_bytes=HASH_MAX_BYTES)
                self._swipe_service.save_swipe(
                    SwipeCreate(
                        file_path=path,
                        file_name=str(payload["filename"]),
                        file_type=str(payload["filetype"]),
                        file_size=int(payload["size"]),
                        file_hash=hash_value,
                        decision=payload["decision"],
                        source=SwipeSource.HUMAN,
                        reason=str(payload["reason"]),
                    )
                )
            except Exception as exc:
                errors.append(f"swipe save failed: {exc}")

        elapsed = time.perf_counter() - started
        if errors:
            LOGGER.warning("Decision persistence completed with errors in %.2fs: %s", elapsed, "; ".join(errors))
            return False, "; ".join(errors)
        LOGGER.info("Decision persistence succeeded in %.2fs for %s", elapsed, path)
        return True, None

    def _poll_swipe_future(self) -> None:
        if self._swipe_future is None:
            if self._swipe_poll_timer.isActive():
                self._swipe_poll_timer.stop()
            return
        if not self._swipe_future.done():
            return

        if self._swipe_watchdog.isActive():
            self._swipe_watchdog.stop()
        if self._swipe_poll_timer.isActive():
            self._swipe_poll_timer.stop()

        success = False
        error_message: str | None = None
        try:
            success, error_message = self._swipe_future.result(timeout=0.01)
        except Exception as exc:
            error_message = str(exc)
            LOGGER.exception("Decision persistence future failed")
        finally:
            self._swipe_future = None

        self._complete_post_reason_flow(persist_success=success, persist_error=error_message)

    def _on_swipe_timeout(self) -> None:
        if self._swipe_future is None:
            return
        LOGGER.error("Decision persistence timed out after %sms", DECISION_TIMEOUT_MS)
        if self._swipe_poll_timer.isActive():
            self._swipe_poll_timer.stop()
        self._swipe_future.cancel()
        self._swipe_future = None
        self._complete_post_reason_flow(
            persist_success=False,
            persist_error=f"timed out after {DECISION_TIMEOUT_MS // 1000}s",
        )

    def _complete_post_reason_flow(self, *, persist_success: bool, persist_error: str | None) -> None:
        payload = self._pending_post_reason
        self._pending_post_reason = None
        if payload is None:
            self._active_card.set_loading_state(False)
            self._incoming_card.set_loading_state(False)
            return

        action_name = str(payload["action_name"])
        reason = str(payload["reason"])
        offset = payload["offset"]

        self._reason_panel.setVisible(False)
        if self._files:
            self._files.pop(self._current_index)
        if self._current_index >= len(self._files):
            self._current_index = 0

        if not self._files and self._has_pending_files():
            self._start_prefetch_on_demand()
        elif self._auto_generate_preview:
            self._start_prefetch_if_needed()

        action_text = f"{action_name} ({reason})"
        if not persist_success and persist_error:
            self._status.setText(f"{action_text} applied with persistence warning: {persist_error}")

        if not self._files:
            self._active_card.set_loading_state(False)
            self._incoming_card.set_loading_state(False)
            self._render_current_file(action_text=action_text)
            if persist_success:
                self._status.setText(f"{action_text} logged. Queue finished.")
            return

        self._animate_to_next(action_text, offset)

    def _start_prefetch_on_demand(self) -> None:
        if not self._has_pending_files():
            return
        if len(self._files) >= self._queue_limit:
            return
        if not self._prefetch_timer.isActive():
            self._prefetch_timer.start()

    def _animate_to_next(self, action_name: str, offset: QPoint) -> None:
        if not self._files:
            return

        try:
            self._is_animating = True
            self._pending_action_text = action_name
            self._active_card.set_loading_state(True)
            self._incoming_card.set_loading_state(True)

            next_file = self._files[self._current_index]
            total = len(self._files)
            self._incoming_card.set_file(next_file)
            self._incoming_card.setVisible(True)
            self._info_panel.set_file(next_file, index=self._current_index + 1, total=total)
            self._subtitle.setText(f"Training mode | File {self._current_index + 1} of {total}")

            target = self._preview_rect()
            outgoing_start = self._active_card.geometry()
            lateral_sign = 1 if offset.x() > 0 else (-1 if offset.x() < 0 else 1)
            outgoing_mid = self._scaled_rect(
                outgoing_start,
                0.88,
                dx=int(offset.x() * 0.48) + int(24 * lateral_sign),
                dy=int(offset.y() * 0.40) + (22 if offset.x() != 0 else 12),
            )
            outgoing_end = self._scaled_rect(
                outgoing_start,
                0.68,
                dx=int(offset.x() * 1.45) + int(34 * lateral_sign),
                dy=int(offset.y() * 1.34) + (36 if offset.x() != 0 else 20),
            )

            incoming_start = self._scaled_rect(
                target,
                0.72,
                dx=int(-offset.x() * 0.22),
                dy=int(-offset.y() * 0.18) + 12,
            )
            incoming_overshoot = self._scaled_rect(
                target,
                1.04,
                dx=int(offset.x() * 0.06),
                dy=int(offset.y() * 0.04),
            )
            self._incoming_card.setGeometry(incoming_start)
            self._incoming_effect.setOpacity(0.0)

            out_geometry = QPropertyAnimation(self._active_card, b"geometry", self)
            out_geometry.setDuration(420)
            out_geometry.setEasingCurve(QEasingCurve.Type.InBack)
            out_geometry.setStartValue(outgoing_start)
            out_geometry.setKeyValueAt(0.44, outgoing_mid)
            out_geometry.setEndValue(outgoing_end)

            out_fade = QPropertyAnimation(self._active_effect, b"opacity", self)
            out_fade.setDuration(360)
            out_fade.setEasingCurve(QEasingCurve.Type.InCubic)
            out_fade.setStartValue(1.0)
            out_fade.setEndValue(0.0)

            in_geometry = QPropertyAnimation(self._incoming_card, b"geometry", self)
            in_geometry.setDuration(470)
            in_geometry.setEasingCurve(QEasingCurve.Type.OutCubic)
            in_geometry.setStartValue(incoming_start)
            in_geometry.setKeyValueAt(0.22, incoming_start)
            in_geometry.setKeyValueAt(0.86, incoming_overshoot)
            in_geometry.setEndValue(target)

            in_fade = QPropertyAnimation(self._incoming_effect, b"opacity", self)
            in_fade.setDuration(380)
            in_fade.setEasingCurve(QEasingCurve.Type.OutQuad)
            in_fade.setStartValue(0.0)
            in_fade.setKeyValueAt(0.22, 0.0)
            in_fade.setEndValue(1.0)

            transition = QParallelAnimationGroup(self)
            transition.addAnimation(out_geometry)
            transition.addAnimation(out_fade)
            transition.addAnimation(in_geometry)
            transition.addAnimation(in_fade)
            transition.finished.connect(self._finish_animation)
            self._active_animation = transition
            transition.start()
            LOGGER.info("Started transition animation for %s", action_name)
        except Exception:
            LOGGER.exception("Transition animation failed")
            self._is_animating = False
            self._pending_action_text = None
            self._active_card.set_loading_state(False)
            self._incoming_card.set_loading_state(False)
            self._render_current_file()
            self._status.setText("Transition failed. Recovered to current file.")

    def _finish_animation(self) -> None:
        self._is_animating = False
        previous_active = self._active_card
        previous_active_effect = self._active_effect

        self._active_card = self._incoming_card
        self._active_effect = self._incoming_effect
        self._incoming_card = previous_active
        self._incoming_effect = previous_active_effect

        target = self._preview_rect()
        self._active_card.setGeometry(target)
        self._active_card.setVisible(True)
        self._active_effect.setOpacity(1.0)
        self._active_card.set_loading_state(False)

        self._incoming_card.setGeometry(target)
        self._incoming_card.setVisible(False)
        self._incoming_effect.setOpacity(0.0)
        self._incoming_card.set_loading_state(False)

        if self._pending_action_text:
            self._status.setText(f"{self._pending_action_text} logged. Showing next file.")
            LOGGER.info("Completed transition animation for %s", self._pending_action_text)
        self._pending_action_text = None
        self._active_animation = None

    def _scaled_rect(self, rect: QRect, scale: float, *, dx: int = 0, dy: int = 0) -> QRect:
        width = max(120, int(rect.width() * scale))
        height = max(90, int(rect.height() * scale))
        center = rect.center()
        x = center.x() - (width // 2) + dx
        y = center.y() - (height // 2) + dy
        return QRect(x, y, width, height)

    def _toggle_details(self) -> None:
        visible = self._info_panel.toggle_details()
        self._status.setText("Details expanded." if visible else "Details hidden.")

    def _open_file(self) -> None:
        if not self._files:
            self._status.setText("Queue is empty.")
            return
        current = self._current_file()
        raw_path = current.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            self._status.setText("No file path available.")
            return
        if not os.path.exists(raw_path):
            self._status.setText("File not found on disk.")
            return
        try:
            os.startfile(raw_path)  # type: ignore[attr-defined]
            self._status.setText("Opened file.")
        except Exception as exc:
            self._status.setText(f"Open failed ({exc})")

    def _mode_clicked(self, mode_name: str) -> None:
        if mode_name != "Training":
            self._status.setText(f"{mode_name} mode layout is staged and not yet active.")
            return
        self._status.setText("Training mode active.")

    def _compute_file_hash(self, raw_path: str, *, max_bytes: int | None = None) -> str | None:
        file_path = Path(raw_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        digest = sha256()
        consumed = 0
        try:
            with file_path.open("rb") as handle:
                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        break
                    if max_bytes is not None and consumed >= max_bytes:
                        break
                    if max_bytes is not None and consumed + len(block) > max_bytes:
                        block = block[: max_bytes - consumed]
                    digest.update(block)
                    consumed += len(block)
                    if max_bytes is not None and consumed >= max_bytes:
                        LOGGER.info(
                            "Partial hash generated for %s at %d bytes (limit=%d)",
                            raw_path,
                            consumed,
                            max_bytes,
                        )
                        break
        except Exception:
            return None
        return digest.hexdigest()
