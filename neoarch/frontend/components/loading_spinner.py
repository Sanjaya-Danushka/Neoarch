"""LoadingSpinner Component - Reusable loading spinner widget"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen


class LoadingSpinner(QWidget):
    """Reusable loading spinner component"""

    def __init__(self, parent=None, message="Loading..."):
        super().__init__(parent)
        self.message = message
        self.spinner_angle = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(48, 48)
        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.animate_spinner)

        self.loading_label = QLabel(self.message)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)

        self.setStyleSheet("""
            LoadingSpinner {
                background-color: transparent;
                border: none;
            }
            LoadingSpinner QLabel {
                background-color: transparent;
                color: #00BFAE;
                font-size: 14px;
                font-weight: 500;
            }
        """)

    def animate_spinner(self):
        self.spinner_angle = (self.spinner_angle + 15) % 360

        pixmap = QPixmap(48, 48)
        if pixmap.isNull():
            return
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        if not painter.isActive():
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rainbow_colors = [
            QColor("#FF6B6B"), QColor("#FFD93D"), QColor("#6BCF7F"),
            QColor("#4ECDC4"), QColor("#45B7D1"), QColor("#96CEB4"),
            QColor("#FECA57"), QColor("#FF9FF3"),
        ]

        for i in range(8):
            angle = (self.spinner_angle + i * 45) % 360
            progress = (angle / 360.0)
            opacity = 0.2 + 0.8 * (1 - abs(progress - 0.5) * 2)

            color = rainbow_colors[i].lighter(120)
            color.setAlphaF(opacity)

            painter.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            start_angle = angle * 16
            span_angle = 35 * 16

            rect = QRectF(8, 8, 32, 32)
            painter.drawArc(rect, start_angle, span_angle)

        painter.end()
        self.spinner_label.setPixmap(pixmap)

    def start_animation(self, message=None):
        if message:
            self.loading_label.setText(message)
        self.spinner_timer.start(100)

    def stop_animation(self):
        self.spinner_timer.stop()

    def set_message(self, message):
        self.loading_label.setText(message)

    def is_animating(self):
        return self.spinner_timer.isActive()
