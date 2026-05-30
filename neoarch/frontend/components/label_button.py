"""LabelButton Component - Clickable label that acts as a button"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal


class LabelButton(QLabel):
    """A label that behaves like a clickable button"""

    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
