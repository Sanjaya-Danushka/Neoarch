"""Dark-themed dialog helpers matching the Neoarch visual identity."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QWidget,
)

from neoarch.frontend.tokens import Colors

_DIALOG_STYLE = f"""
QDialog {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER_STRONG};
    border-radius: 14px;
}}
QLabel {{
    color: {Colors.TEXT};
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    border: none;
}}
QLineEdit {{
    background: {Colors.INPUT_BG};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER_INPUT};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: rgba(0, 191, 174, 0.3);
}}
QLineEdit:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}
QComboBox {{
    background: {Colors.INPUT_BG};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER_INPUT};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}
QComboBox:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border: none;
}}
QComboBox QAbstractItemView {{
    background: {Colors.SURFACE_2};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER_STRONG};
    border-radius: 8px;
    selection-background-color: rgba(0, 191, 174, 0.2);
    selection-color: {Colors.TEXT};
    padding: 4px;
}}
"""

_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {Colors.WHITE};
        color: {Colors.TEXT_ON_ACCENT};
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 8px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {Colors.WHITE_HOVER}; }}
    QPushButton:pressed {{ background-color: {Colors.WHITE_PRESSED}; }}
"""

_BTN_SECONDARY = f"""
    QPushButton {{
        background: transparent;
        color: {Colors.TEXT_2};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: rgba(255, 255, 255, 0.06);
        color: {Colors.TEXT};
    }}
"""

_BTN_DANGER = f"""
    QPushButton {{
        background-color: rgba(255, 80, 80, 0.15);
        color: #FF6B6B;
        border: 1px solid rgba(255, 80, 80, 0.30);
        border-radius: 8px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 80, 80, 0.25);
        border-color: rgba(255, 80, 80, 0.45);
    }}
"""


def _apply_dialog_flags(dialog):
    dialog.setWindowFlags(
        Qt.WindowType.Dialog
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)


def dark_input(parent, title, label, text=""):
    """Dark-themed text input dialog. Returns (text, ok)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(340)
    dlg.setStyleSheet(_DIALOG_STYLE)
    _apply_dialog_flags(dlg)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 20, 24, 16)
    root.setSpacing(14)

    lbl = QLabel(label)
    root.addWidget(lbl)

    le = QLineEdit(text)
    le.setPlaceholderText(label)
    root.addWidget(le)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel = QPushButton("Cancel")
    cancel.setStyleSheet(_BTN_SECONDARY)
    cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(cancel)
    ok = QPushButton("OK")
    ok.setStyleSheet(_BTN_PRIMARY)
    ok.clicked.connect(dlg.accept)
    btn_row.addWidget(ok)
    root.addLayout(btn_row)

    le.returnPressed.connect(dlg.accept)
    le.setFocus()

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return le.text(), True
    return "", False


def dark_pick(parent, title, label, items):
    """Dark-themed combo-picker dialog. Returns (selected_text, ok)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(360)
    dlg.setStyleSheet(_DIALOG_STYLE)
    _apply_dialog_flags(dlg)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 20, 24, 16)
    root.setSpacing(14)

    lbl = QLabel(label)
    root.addWidget(lbl)

    combo = QComboBox()
    combo.addItems(items)
    root.addWidget(combo)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel = QPushButton("Cancel")
    cancel.setStyleSheet(_BTN_SECONDARY)
    cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(cancel)
    ok = QPushButton("OK")
    ok.setStyleSheet(_BTN_PRIMARY)
    ok.clicked.connect(dlg.accept)
    btn_row.addWidget(ok)
    root.addLayout(btn_row)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return combo.currentText(), True
    return "", False


def dark_confirm(parent, title, message, danger=False):
    """Dark-themed confirmation dialog. Returns True if accepted."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(360)
    dlg.setStyleSheet(_DIALOG_STYLE)
    _apply_dialog_flags(dlg)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 20, 24, 16)
    root.setSpacing(14)

    lbl = QLabel(message)
    lbl.setWordWrap(True)
    root.addWidget(lbl)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel = QPushButton("Cancel")
    cancel.setStyleSheet(_BTN_SECONDARY)
    cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(cancel)
    confirm = QPushButton("Delete" if danger else "Confirm")
    confirm.setStyleSheet(_BTN_DANGER if danger else _BTN_PRIMARY)
    confirm.clicked.connect(dlg.accept)
    btn_row.addWidget(confirm)
    root.addLayout(btn_row)

    return dlg.exec() == QDialog.DialogCode.Accepted
