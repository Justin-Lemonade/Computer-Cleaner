from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QFileSystemWatcher,
    QPoint,
    QParallelAnimationGroup,
    QProcess,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from database.Db import list_files
from logic.LabelHandler import LABEL_ARCHIVE, LABEL_KEEP, LABEL_NOT_NEEDED, save_label
from ui.FileCard import FileCard
from ui.InfoPanel import InfoPanel
from ui.KeyboardShortcuts import add_shortcut


class _ModeSelector(QFrame):
    def __init__(self, on_mode_clicked, button_size: QSize) -> None:
        super().__init__()
        self._on_mode_clicked = on_mode_clicked
        self._active_mode = "Training"
        self._button_size = button_size
        self._expanded = False
        self._width_anim: QPropertyAnimation | None = None
        self._mode_buttons: dict[str, QPushButton] = {}

        self.setObjectName("ModeSelector")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._current = QPushButton(self._active_mode)
        self._current.setObjectName("ModeButton")
        self._current.setFixedSize(self._button_size)
        self._current.setEnabled(False)
        self._current.setProperty("active", True)

        self._row = QWidget()
        row_layout = QHBoxLayout(self._row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        for mode_name in ("Training", "Review", "Sorting"):
            button = QPushButton(mode_name)
            button.setObjectName("ModeButton")
            button.setFixedSize(self._button_size)
            button.clicked.connect(lambda _checked=False, value=mode_name: self._mode_clicked(value))
            self._mode_buttons[mode_name] = button
            row_layout.addWidget(button)

        self._expanded_width = (self._button_size.width() * 3) + (8 * 2)
        self._row.setMaximumWidth(0)
        self._row.setMinimumWidth(0)
        self._row.hide()
        self._set_active_mode("Training")

        layout.addWidget(self._current)
        layout.addWidget(self._row)
        self.setStyleSheet(
            """
            QFrame#ModeSelector {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 12px;
            }
            QPushButton#ModeButton {
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                background: #212121;
                color: #b3b3b3;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 12px;
            }
            QPushButton#ModeButton:hover {
                background: #2a2a2a;
                border-color: #19c37d;
                color: #ffffff;
            }
            QPushButton#ModeButton[active="true"] {
                background: #1f2c26;
                border-color: #19c37d;
                color: #ffffff;
            }
            """
        )

    def enterEvent(self, event) -> None:
        self._set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_expanded(False)
        super().leaveEvent(event)

    def _mode_clicked(self, mode_name: str) -> None:
        self._set_active_mode(mode_name)
        self._on_mode_clicked(mode_name)

    def _set_active_mode(self, mode_name: str) -> None:
        self._active_mode = mode_name
        self._current.setText(mode_name)
        for name, button in self._mode_buttons.items():
            button.setProperty("active", name == mode_name)
            button.style().unpolish(button)
            button.style().polish(button)
        self._current.style().unpolish(self._current)
        self._current.style().polish(self._current)

    def _set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._expanded = expanded

        if expanded:
            self._current.hide()
            self._row.show()

        self._width_anim = QPropertyAnimation(self._row, b"maximumWidth", self)
        self._width_anim.setDuration(160)
        self._width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._width_anim.setStartValue(self._row.maximumWidth())
        self._width_anim.setEndValue(self._expanded_width if expanded else 0)
        self._width_anim.finished.connect(self._on_width_anim_finished)
        self._width_anim.start()

    def _on_width_anim_finished(self) -> None:
        if not self._expanded:
            self._row.hide()
            self._current.show()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("File Sorter AI")
        self.resize(1360, 900)

        self._files: list[dict[str, Any]] = []
        self._current_index = 0
        self._pending_index = 0
        self._is_animating = False
        self._active_animation: QParallelAnimationGroup | None = None
        self._run_mode_enabled = os.environ.get("FILE_SORTER_RUN_MODE") == "1"
        self._restart_pending = False
        self._watcher: QFileSystemWatcher | None = None

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        root_layout.addWidget(self._build_top_bar())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        self._info_panel = InfoPanel()
        body_layout.addWidget(self._info_panel, 0)

        self._preview_stage = QFrame()
        self._preview_stage.setObjectName("PreviewStage")
        self._preview_stage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview_stage.setMinimumWidth(900)

        self._preview_card = FileCard()
        self._preview_card.setParent(self._preview_stage)
        self._preview_effect = QGraphicsOpacityEffect(self._preview_card)
        self._preview_card.setGraphicsEffect(self._preview_effect)
        self._preview_effect.setOpacity(1.0)

        body_layout.addWidget(self._preview_stage, 1)
        root_layout.addWidget(body, 1)

        self._status = QLabel("Training mode active. Classify each file with one action.")
        self._status.setObjectName("StatusText")
        root_layout.addWidget(self._status)

        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        self._action_dock = self._build_action_dock()
        bottom_layout.addWidget(self._action_dock, 1)

        self._mode_selector = _ModeSelector(self._mode_clicked, QSize(138, 46))
        bottom_layout.addWidget(self._mode_selector, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        root_layout.addWidget(bottom)

        self.setCentralWidget(root)
        self._apply_dark_theme()
        self._install_shortcuts()
        self._load_files()
        self._render_current_file()
        self._start_auto_reload_if_enabled()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._is_animating:
            self._preview_card.setGeometry(self._preview_rect())

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

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self._run_button = QPushButton("RUN")
        self._run_button.setObjectName("RunButton")
        self._run_button.setFixedSize(96, 40)
        self._run_button.clicked.connect(self._run_clicked)

        menu_button = QToolButton()
        menu_button.setObjectName("MenuButton")
        menu_button.setText("Menu")
        menu_button.setFixedSize(96, 40)
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_button.setMenu(self._build_menu())

        controls_layout.addWidget(self._run_button)
        controls_layout.addWidget(menu_button)

        layout.addWidget(title_wrap, 1)
        layout.addWidget(controls, 0, Qt.AlignmentFlag.AlignTop)
        return top

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        for action_name in ("Settings", "History", "Search"):
            action = QAction(action_name, self)
            action.triggered.connect(lambda _checked=False, value=action_name: self._status.setText(f"{value} coming soon."))
            menu.addAction(action)
        return menu

    def _build_action_dock(self) -> QFrame:
        dock = QFrame()
        dock.setObjectName("ActionDock")
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        specs = [
            ("KEEP", "primary", self._on_keep, QStyle.StandardPixmap.SP_DialogApplyButton),
            ("ARCHIVE", "secondary", self._on_archive, QStyle.StandardPixmap.SP_DriveHDIcon),
            ("NOT NEEDED", "danger", self._on_not_needed, QStyle.StandardPixmap.SP_TrashIcon),
            ("MORE INFO", "secondary", self._toggle_details, QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("OPEN FILE", "secondary", self._open_file, QStyle.StandardPixmap.SP_DirOpenIcon),
        ]
        for text, role, callback, icon_id in specs:
            button = QPushButton(text)
            button.setObjectName("ActionButton")
            button.setProperty("role", role)
            button.setFixedSize(138, 46)
            button.setIcon(self.style().standardIcon(icon_id))
            button.setIconSize(QSize(20, 20))
            button.clicked.connect(callback)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        return dock

    def _apply_dark_theme(self) -> None:
        if self._run_mode_enabled:
            self._run_button.setText("RUNNING")

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
            QFrame#ActionDock {
                background: #171717;
                border: 1px solid #2f2f2f;
                border-radius: 12px;
            }
            QPushButton#ActionButton {
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                background: #212121;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
                padding: 8px 12px;
            }
            QPushButton#ActionButton:hover {
                background: #2a2a2a;
                border-color: #19c37d;
            }
            QPushButton#ActionButton[role="primary"] {
                background: #1f2c26;
                border-color: #19c37d;
                color: #ffffff;
            }
            QPushButton#ActionButton[role="danger"] {
                background: #322126;
                border-color: #5b2e36;
                color: #ffffff;
            }
            QPushButton#ActionButton[role="danger"]:hover {
                background: #3a242a;
                border-color: #6a3640;
            }
            QPushButton#RunButton {
                border: 1px solid #19c37d;
                border-radius: 10px;
                background: #1f2c26;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#RunButton:hover {
                background: #27392f;
            }
            QToolButton#MenuButton {
                border: 1px solid #2f2f2f;
                border-radius: 10px;
                background: #212121;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
            }
            QToolButton#MenuButton:hover {
                background: #2a2a2a;
                border-color: #19c37d;
            }
            QMenu {
                background: #171717;
                color: #ffffff;
                border: 1px solid #2f2f2f;
                padding: 6px;
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
        add_shortcut(self, "Space", self._toggle_details)

    def _load_files(self) -> None:
        try:
            rows = list_files(limit=400)
            self._files = [dict(row) for row in rows]
        except Exception as exc:
            self._files = []
            self._status.setText(f"Database read failed. Using local sample cards. ({exc})")

        if self._files:
            self._current_index = 0
            return

        self._files = [
            {
                "id": None,
                "filename": "Budget_Report_2024.pdf",
                "path": r"C:\Users\You\Downloads\Budget_Report_2024.pdf",
                "filetype": "pdf",
                "size": 328412,
                "created_date": "2024-05-10T08:12:00",
                "modified_date": "2024-12-20T17:24:00",
            },
            {
                "id": None,
                "filename": "Design_Notes.docx",
                "path": r"C:\Users\You\Documents\Design_Notes.docx",
                "filetype": "docx",
                "size": 87321,
                "created_date": "2022-11-01T13:15:00",
                "modified_date": "2023-02-06T11:03:00",
            },
            {
                "id": None,
                "filename": "Screenshot_4932.png",
                "path": r"C:\Users\You\Pictures\Screenshot_4932.png",
                "filetype": "png",
                "size": 1892240,
                "created_date": "2023-10-18T19:32:00",
                "modified_date": "2023-10-18T19:32:00",
            },
        ]
        self._current_index = 0

    def _render_current_file(self, *, action_text: str | None = None) -> None:
        if not self._files:
            return

        current = self._files[self._current_index]
        total = len(self._files)
        self._preview_card.set_file(current)
        self._info_panel.set_file(current, index=self._current_index + 1, total=total)
        self._preview_card.setGeometry(self._preview_rect())
        self._subtitle.setText(f"Training mode | File {self._current_index + 1} of {total}")
        if action_text:
            self._status.setText(f"{action_text} logged. Showing next file.")

    def _preview_rect(self) -> QRect:
        rect = self._preview_stage.contentsRect()
        width = max(760, rect.width() - 44)
        height = max(500, rect.height() - 44)
        width = min(1040, width)
        height = min(660, height)
        x = rect.x() + (rect.width() - width) // 2
        y = rect.y() + (rect.height() - height) // 2
        return QRect(x, y, width, height)

    def _current_file(self) -> dict[str, Any]:
        return self._files[self._current_index]

    def _on_keep(self) -> None:
        self._handle_decision("KEEP", LABEL_KEEP, QPoint(220, 0))

    def _on_archive(self) -> None:
        self._handle_decision("ARCHIVE", LABEL_ARCHIVE, QPoint(0, -170))

    def _on_not_needed(self) -> None:
        self._handle_decision("NOT NEEDED", LABEL_NOT_NEEDED, QPoint(-220, 0))

    def _handle_decision(self, action_name: str, label_name: str, offset: QPoint) -> None:
        if self._is_animating or not self._files:
            return

        current = self._current_file()
        file_id = current.get("id")
        if isinstance(file_id, int):
            try:
                save_label(file_id, label_name)
            except Exception as exc:
                self._status.setText(f"Label save failed ({exc})")

        self._pending_index = (self._current_index + 1) % len(self._files)
        self._animate_to_next(action_name, offset)

    def _animate_to_next(self, action_name: str, offset: QPoint) -> None:
        self._is_animating = True
        start = self._preview_card.geometry()
        end = QRect(start.x() + offset.x(), start.y() + offset.y(), start.width(), start.height())

        slide_out = QPropertyAnimation(self._preview_card, b"geometry", self)
        slide_out.setDuration(170)
        slide_out.setStartValue(start)
        slide_out.setEndValue(end)
        slide_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_out = QPropertyAnimation(self._preview_effect, b"opacity", self)
        fade_out.setDuration(170)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        out_group = QParallelAnimationGroup(self)
        out_group.addAnimation(slide_out)
        out_group.addAnimation(fade_out)
        out_group.finished.connect(lambda: self._show_next_file(action_name, offset))
        self._active_animation = out_group
        out_group.start()

    def _show_next_file(self, action_name: str, offset: QPoint) -> None:
        self._current_index = self._pending_index
        self._render_current_file(action_text=action_name)

        target = self._preview_rect()
        incoming = QRect(
            target.x() - int(offset.x() * 0.28),
            target.y() - int(offset.y() * 0.28),
            target.width(),
            target.height(),
        )
        self._preview_card.setGeometry(incoming)
        self._preview_effect.setOpacity(0.0)

        slide_in = QPropertyAnimation(self._preview_card, b"geometry", self)
        slide_in.setDuration(180)
        slide_in.setStartValue(incoming)
        slide_in.setEndValue(target)
        slide_in.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_in = QPropertyAnimation(self._preview_effect, b"opacity", self)
        fade_in.setDuration(180)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)

        in_group = QParallelAnimationGroup(self)
        in_group.addAnimation(slide_in)
        in_group.addAnimation(fade_in)
        in_group.finished.connect(self._finish_animation)
        self._active_animation = in_group
        in_group.start()

    def _finish_animation(self) -> None:
        self._is_animating = False
        self._preview_card.setGeometry(self._preview_rect())

    def _toggle_details(self) -> None:
        visible = self._info_panel.toggle_details()
        self._status.setText("Details expanded." if visible else "Details hidden.")

    def _open_file(self) -> None:
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

    def _run_clicked(self) -> None:
        self._run_mode_enabled = True
        os.environ["FILE_SORTER_RUN_MODE"] = "1"
        self._run_button.setText("RUNNING")
        self._status.setText("RUN enabled. Relaunching UI and watching source files.")
        self._start_auto_reload_if_enabled()
        QTimer.singleShot(120, self._restart_application)

    def _start_auto_reload_if_enabled(self) -> None:
        if not self._run_mode_enabled:
            return
        if self._watcher is not None:
            return

        project_root = Path(__file__).resolve().parents[1]
        ui_dir = project_root / "ui"
        watch_paths = [
            project_root / "App.py",
            project_root / "Config.py",
            ui_dir / "MainWindow.py",
            ui_dir / "FileCard.py",
            ui_dir / "InfoPanel.py",
            ui_dir / "KeyboardShortcuts.py",
        ]

        self._watcher = QFileSystemWatcher(self)
        existing = [str(path) for path in watch_paths if path.exists()]
        if existing:
            self._watcher.addPaths(existing)
        self._watcher.fileChanged.connect(self._source_changed)

    def _source_changed(self, path: str) -> None:
        if self._watcher is not None and path and os.path.exists(path) and path not in self._watcher.files():
            self._watcher.addPath(path)

        if not self._run_mode_enabled or self._restart_pending:
            return
        self._restart_pending = True
        self._status.setText("Source change detected. Relaunching updated UI.")
        QTimer.singleShot(200, self._restart_application)

    def _restart_application(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        app_entry = project_root / "App.py"
        executable = sys.executable

        if not executable or not Path(executable).exists():
            self._status.setText("Cannot relaunch: Python executable not found.")
            self._restart_pending = False
            return

        launched = QProcess.startDetached(executable, [str(app_entry)], str(project_root))
        if not launched:
            self._status.setText("Relaunch failed.")
            self._restart_pending = False
            return
        QApplication.instance().quit()
