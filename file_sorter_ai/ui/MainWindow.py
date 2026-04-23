from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from database.Db import list_files
from scanner.ScanFiles import scan_and_store
from ui.InfoPanel import InfoPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("File Sorter AI")
        self.resize(1100, 700)

        self._preview_label = QLabel("No file selected")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(300)

        self._info_panel = InfoPanel()

        scan_button = QPushButton("Scan Folder…")
        scan_button.clicked.connect(self._scan_folder)

        refresh_button = QPushButton("Refresh List")
        refresh_button.clicked.connect(self._refresh)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(scan_button)
        left_layout.addWidget(refresh_button)
        self._list_label = QLabel()
        self._list_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        left_layout.addWidget(self._list_label, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._preview_label)
        right_layout.addWidget(self._info_panel)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self._build_menu()
        self._refresh()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        scan_action = QAction("Scan Folder…", self)
        scan_action.triggered.connect(self._scan_folder)
        file_menu.addAction(scan_action)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _scan_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if not folder:
            return
        n = scan_and_store(Path(folder))
        QMessageBox.information(self, "Scan complete", f"Scanned {n} files.")
        self._refresh()

    def _refresh(self) -> None:
        rows = list_files(limit=100)
        if not rows:
            self._list_label.setText("No files in database yet.\nClick “Scan Folder…” to begin.")
            return
        text = "\n".join(f"{r['id']:>4}  {r['filename']}  —  {r['path']}" for r in rows)
        self._list_label.setText(text)
