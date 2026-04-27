from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import QEasingCurve, QPoint, QParallelAnimationGroup, QPropertyAnimation, QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from database.Db import list_files
from logic.LabelHandler import LABEL_ARCHIVE, LABEL_KEEP, LABEL_NOT_NEEDED, save_label
from ui.FileCard import FileCard
from ui.InfoPanel import InfoPanel
from ui.KeyboardShortcuts import add_shortcut


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
        self._stack_x = self._padding + (2 * (width + self._spacing))
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
        is_collapsed = not self._expanded
        for mode, button in self._buttons.items():
            is_active = mode == self._active_mode
            should_enable = self._expanded or is_active
            target_opacity = 1.0 if self._expanded or is_active else 0.0

            button.setEnabled(should_enable)
            button.setStyleSheet(self._ACTIVE_MODE_STYLE if is_active else self._INACTIVE_MODE_STYLE)
            if sync_opacity:
                self._effects[mode].setOpacity(target_opacity)
            elif is_collapsed and is_active:
                self._effects[mode].setOpacity(1.0)
            else:
                continue

    def _arrange(self, *, immediate: bool) -> None:
        others = [mode for mode in self._modes if mode != self._active_mode]
        left_positions = {
            others[0]: self._padding,
            others[1]: self._padding + self._button_size.width() + self._spacing,
            self._active_mode: self._stack_x,
        }
        self._apply_mode_visual_state()

        if immediate:
            self.setMinimumWidth(self._collapsed_width if not self._expanded else self._expanded_width)
            self.setMaximumWidth(self._collapsed_width if not self._expanded else self._expanded_width)
            self._apply_mode_visual_state(sync_opacity=True)
            for mode, button in self._buttons.items():
                x = left_positions[mode] if self._expanded else self._stack_x
                button.move(x, self._padding)
            return

        group = QParallelAnimationGroup(self)

        min_width_anim = QPropertyAnimation(self, b"minimumWidth", self)
        min_width_anim.setDuration(130)
        min_width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        min_width_anim.setStartValue(self.minimumWidth())
        min_width_anim.setEndValue(self._expanded_width if self._expanded else self._collapsed_width)
        group.addAnimation(min_width_anim)

        max_width_anim = QPropertyAnimation(self, b"maximumWidth", self)
        max_width_anim.setDuration(130)
        max_width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        max_width_anim.setStartValue(self.maximumWidth())
        max_width_anim.setEndValue(self._expanded_width if self._expanded else self._collapsed_width)
        group.addAnimation(max_width_anim)

        for mode, button in self._buttons.items():
            target_x = left_positions[mode] if self._expanded else self._stack_x

            move_anim = QPropertyAnimation(button, b"pos", self)
            move_anim.setDuration(130)
            move_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            move_anim.setStartValue(button.pos())
            move_anim.setEndValue(QPoint(target_x, self._padding))
            group.addAnimation(move_anim)

            fade_anim = QPropertyAnimation(self._effects[mode], b"opacity", self)
            fade_anim.setDuration(115)
            fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            fade_anim.setStartValue(self._effects[mode].opacity())
            target_opacity = 1.0 if self._expanded or mode == self._active_mode else 0.0
            fade_anim.setEndValue(target_opacity)
            group.addAnimation(fade_anim)

        self._active_animation = group
        group.start()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("File Sorter AI")
        self.resize(1320, 860)

        self._files: list[dict[str, Any]] = []
        self._current_index = 0
        self._pending_index = 0
        self._is_animating = False
        self._active_animation: QParallelAnimationGroup | None = None

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

        self._preview_card = FileCard()
        self._preview_card.setParent(self._preview_stage)
        self._preview_effect = QGraphicsOpacityEffect(self._preview_card)
        self._preview_card.setGraphicsEffect(self._preview_effect)
        self._preview_effect.setOpacity(1.0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setObjectName("MainSplitter")
        splitter.addWidget(self._info_panel)
        splitter.addWidget(self._preview_stage)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 980])
        root_layout.addWidget(splitter, 1)

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
        for action_name in ("Settings", "History", "Search"):
            action = QAction(action_name, self)
            action.triggered.connect(
                lambda _checked=False, value=action_name: self._status.setText(f"{value} coming soon.")
            )
            menu.addAction(action)
        return menu

    def _build_action_dock(self) -> QWidget:
        dock = QWidget()
        dock.setObjectName("ActionDock")
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

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

        return dock

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
        width = min(max(rect.width() - 36, 520), 1100)
        height = min(max(rect.height() - 36, 340), 680)
        x = rect.x() + (rect.width() - width) // 2
        y = rect.y() + (rect.height() - height) // 2
        return QRect(x, y, width, height)

    def _current_file(self) -> dict[str, Any]:
        return self._files[self._current_index]

    def _on_keep(self) -> None:
        self._handle_decision("KEEP", LABEL_KEEP, QPoint(260, 0))

    def _on_archive(self) -> None:
        self._handle_decision("ARCHIVE", LABEL_ARCHIVE, QPoint(0, -220))

    def _on_not_needed(self) -> None:
        self._handle_decision("NOT NEEDED", LABEL_NOT_NEEDED, QPoint(-260, 0))

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
        weight_drop = 14 if offset.x != 0 else 8
        if offset.y < 0:
            mid = QRect(start.x(), start.y() + 12, start.width(), start.height())
        else:
            mid = QRect(
                start.x() + int(offset.x() * 0.30),
                start.y() + int(offset.y() * 0.25) + weight_drop,
                start.width(),
                start.height(),
            )
        end = QRect(
            start.x() + int(offset.x() * 1.15),
            start.y() + int(offset.y() * 1.08),
            int(start.width() * 0.96),
            int(start.height() * 0.96),
        )

        slide_out = QPropertyAnimation(self._preview_card, b"geometry", self)
        slide_out.setDuration(210)
        slide_out.setEasingCurve(QEasingCurve.Type.InCubic)
        slide_out.setStartValue(start)
        slide_out.setKeyValueAt(0.35, mid)
        slide_out.setEndValue(end)

        fade_out = QPropertyAnimation(self._preview_effect, b"opacity", self)
        fade_out.setDuration(170)
        fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)

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
            target.x() - int(offset.x() * 0.48),
            target.y() - int(offset.y() * 0.40) + 10,
            target.width(),
            target.height(),
        )
        overshoot = QRect(
            target.x() + int(offset.x() * 0.07),
            target.y() + int(offset.y() * 0.05),
            target.width(),
            target.height(),
        )

        self._preview_card.setGeometry(incoming)
        self._preview_effect.setOpacity(0.0)

        slide_in = QPropertyAnimation(self._preview_card, b"geometry", self)
        slide_in.setDuration(220)
        slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide_in.setStartValue(incoming)
        slide_in.setKeyValueAt(0.80, overshoot)
        slide_in.setEndValue(target)

        fade_in = QPropertyAnimation(self._preview_effect, b"opacity", self)
        fade_in.setDuration(180)
        fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)

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
