"""LoadingSpinner Component - Reusable loading spinner widget"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen


_SIZE = 48
_CYCLE_MS = 2000


class _SpinnerCanvas(QLabel):
    """Draws the pulse animation directly via paintEvent — no QPixmap."""

    def __init__(self):
        super().__init__()
        self._progress = 0.0
        self.setFixedSize(_SIZE, _SIZE)

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = cy = _SIZE / 2
        t = self._progress

        for color, delay in [("#FF6B6B", 0.0), ("#E53E3E", 0.5)]:
            ft = (t - delay) % 1.0
            s = max(0.01, ft)
            half = s * _SIZE / 2

            pen = QPen(QColor(color), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                int(cx - half), int(cy - half),
                int(s * _SIZE), int(s * _SIZE),
            )


class LoadingSpinner(QWidget):
    """Modern loading spinner with expanding-ring pulse animation.

    Uses QPropertyAnimation + direct paintEvent — zero runtime allocations,
    no QTimer, no QPixmap overhead.
    """

    def __init__(self, parent=None, message="Loading..."):
        super().__init__(parent)
        self.message = message

        self._canvas = _SpinnerCanvas()
        self._anim = QPropertyAnimation(self._canvas, b"progress")
        self._anim.setLoopCount(-1)
        self._anim.setDuration(_CYCLE_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

        self._msg_label = QLabel(message)
        self._msg_label.setObjectName("spinnerMsgLabel")
        self._msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_label.setMinimumWidth(360)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFixedWidth(360)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 40)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._msg_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            LoadingSpinner {
                background-color: transparent;
                border: none;
            }
            LoadingSpinner QLabel#spinnerMsgLabel {
                background-color: transparent;
                color: #E8E8E8;
                font-size: 20px;
                font-weight: 500;
            }
            LoadingSpinner QProgressBar {
                border: none;
                border-radius: 4px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.08);
            }
            LoadingSpinner QProgressBar::chunk {
                background-color: #E53E3E;
                border-radius: 4px;
            }
        """)

    def start_animation(self, message=None):
        if message:
            self._msg_label.setText(message)
        self._anim.start()

    def stop_animation(self):
        self._anim.stop()
        self._canvas.progress = 0.0
        self._canvas.update()

    def set_message(self, message):
        self._msg_label.setText(message)

    def set_progress(self, percent):
        if percent < 0:
            self._progress_bar.setRange(0, 0)
            self._progress_bar.setVisible(True)
        else:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(min(100, max(0, percent)))
            self._progress_bar.setVisible(True)

    def hide_progress(self):
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setValue(0)

    def is_animating(self):
        return self._anim.state() == QPropertyAnimation.State.Running