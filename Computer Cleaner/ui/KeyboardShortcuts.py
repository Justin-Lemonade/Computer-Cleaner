from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget


def add_shortcut(widget: QWidget, sequence: str, callback) -> QShortcut:
    shortcut = QShortcut(QKeySequence(sequence), widget)
    shortcut.activated.connect(callback)
    return shortcut

