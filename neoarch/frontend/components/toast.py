"""In-app toast notification widget.

A lightweight, frameless, always-on-top bubble that fades in at the
bottom-right of the parent window and auto-dismisses. Used by the
notification dispatch in the views mixin (desktop + in-app channels).
"""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout

from neoarch.frontend.tokens import Colors

_LEVEL_COLORS = {
    "info": QColor(0, 191, 174),
    "success": QColor(88, 202, 143),
    "error": QColor(248, 113, 113),
    "warning": QColor(251, 191, 36),
}


class Toast(QWidget):
    """Frameless toast bubble with a colored level dot and message text."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._duration = 4000
        self._level = "info"
        self._text = ""
        self._progress = 1.0

        self._label = QLabel(self)
        self._label.setStyleSheet(f"color: {Colors.TEXT}; background: transparent; border: none;")
        self._label.setWordWrap(True)
        self._label.setMinimumWidth(220)
        self._label.setMaximumWidth(420)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)
        layout.addWidget(self._label)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(240)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)
        self._fade.finished.connect(self._on_faded_out)
        self._fading_out = False

        self._on_click = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def show_toast(self, text, level="info", duration=4000, on_click=None):
        self._text = text
        self._level = level if level in _LEVEL_COLORS else "info"
        self._duration = int(duration)
        self._on_click = on_click
        self._label.setText(text)
        self.adjustSize()
        self._reposition()
        self._fading_out = False
        self.setWindowOpacity(0.0)
        self.show()
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._timer.start(self._duration)

    def _reposition(self):
        parent = self.parent()
        if parent is not None and parent.isVisible():
            try:
                geo = parent.frameGeometry()
                w, h = self.width(), self.height()
                self.move(geo.right() - w - 24, geo.bottom() - h - 24)
            except Exception:
                self._reposition_on_screen()
        else:
            self._reposition_on_screen()

    def _reposition_on_screen(self):
        screen = self.screen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 24, geo.bottom() - self.height() - 24)

    def mousePressEvent(self, event):
        cb = self._on_click
        if cb:
            self._on_click = None
            self._dismiss()
            QTimer.singleShot(0, cb)
        super().mousePressEvent(event)

    def _dismiss(self):
        self._timer.stop()
        self._fade.stop()
        self._fading_out = True
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_faded_out(self):
        if self._fading_out:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.setBrush(QColor(24, 26, 32, 235))
        painter.drawRoundedRect(r, 12, 12)

        dot = 8
        cx = 18 + dot // 2
        cy = self.height() // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_LEVEL_COLORS.get(self._level, _LEVEL_COLORS["info"]))
        painter.drawEllipse(cx - dot // 2, cy - dot // 2, dot, dot)

        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()
