"""Dark-themed dialog helpers matching the Neoarch visual identity."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.frontend.styles import Styles
from neoarch.backend.services.i18n import _


_DIALOG_STYLE = f"""
QDialog {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER_STRONG};
    border-radius: 14px;
}}
QLabel {{
    color: {Colors.TEXT};
    font-size: {Fonts.BASE};
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
    font-size: {Fonts.BASE};
    selection-background-color: {Colors.ACCENT};
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
    font-size: {Fonts.BASE};
}}
QComboBox:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}
QComboBox QAbstractItemView {{
    background: {Colors.SURFACE_2};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER_STRONG};
    border-radius: 8px;
    selection-background-color: {Colors.ACCENT_SOFT};
    selection-color: {Colors.TEXT};
    padding: 4px;
}}
"""


_BTN_PRIMARY = Styles.btn_white()
_BTN_SECONDARY = Styles.btn_secondary()
_BTN_DANGER = Styles.btn_danger()


class _DialogTitleBar(QWidget):
    """macOS-style traffic light title bar for dialogs."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("dialogTitleBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: {Fonts.MD}; font-weight: 500; background: transparent; border: none;")
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(lbl)

        layout.addStretch()

        self.close_btn = self._traffic_light("\u2715", "dlgCloseBtn", "#FF5F57")
        self.close_btn.clicked.connect(lambda: self.window().close())
        layout.addWidget(self.close_btn)

    def _traffic_light(self, symbol, obj_name, color):
        btn = QPushButton(symbol)
        btn.setObjectName(obj_name)
        btn.setFixedSize(14, 14)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: transparent;
                border: none;
                border-radius: 7px;
                font-size: 0px;
            }}
            QPushButton:hover {{
                color: rgba(0, 0, 0, 0.6);
                font-size: {Fonts.MICRO};
            }}
        """)
        return btn

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.window().windowHandle()
            if w:
                w.startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)


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
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    title_bar = _DialogTitleBar(title)
    root.addWidget(title_bar)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(24, 4, 24, 16)
    content_layout.setSpacing(14)

    lbl = QLabel(label)
    content_layout.addWidget(lbl)

    le = QLineEdit(text)
    le.setPlaceholderText(label)
    content_layout.addWidget(le)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel = QPushButton(_("Cancel"))
    cancel.setStyleSheet(_BTN_SECONDARY)
    cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(cancel)
    ok = QPushButton(_("OK"))
    ok.setStyleSheet(_BTN_PRIMARY)
    ok.clicked.connect(dlg.accept)
    btn_row.addWidget(ok)
    content_layout.addLayout(btn_row)

    root.addWidget(content)

    le.returnPressed.connect(dlg.accept)
    le.setFocus()

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return le.text(), True
    return "", False


def dark_confirm(parent, title, message, danger=False):
    """Dark-themed confirmation dialog. Returns True if accepted."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(360)
    dlg.setStyleSheet(_DIALOG_STYLE)
    _apply_dialog_flags(dlg)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    title_bar = _DialogTitleBar(title)
    root.addWidget(title_bar)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(24, 4, 24, 16)
    content_layout.setSpacing(14)

    lbl = QLabel(message)
    lbl.setWordWrap(True)
    content_layout.addWidget(lbl)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel = QPushButton(_("Cancel"))
    cancel.setStyleSheet(_BTN_SECONDARY)
    cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(cancel)
    confirm = QPushButton(_("Delete") if danger else _("Confirm"))
    confirm.setStyleSheet(_BTN_DANGER if danger else _BTN_PRIMARY)
    confirm.clicked.connect(dlg.accept)
    btn_row.addWidget(confirm)
    content_layout.addLayout(btn_row)

    root.addWidget(content)

    return dlg.exec() == QDialog.DialogCode.Accepted
