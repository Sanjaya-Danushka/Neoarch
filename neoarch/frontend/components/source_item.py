"""SourceItem Component - Individual source selection widget"""

import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtSvg import QSvgRenderer


class ToggleSwitch(QWidget):
    """macOS-style toggle switch with smooth animation."""

    toggled = pyqtSignal(bool)

    def __init__(self, accent_color="#00BFAE", parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = True
        self._knob_pos = 1.0
        self._on_color = QColor(accent_color)
        self._off_color = QColor(72, 72, 77)
        self._animation = QPropertyAnimation(self, b"knob_pos", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_accent_color(self, color):
        self._on_color = QColor(color)
        self.update()

    def get_knob_pos(self):
        return self._knob_pos

    def set_knob_pos(self, value):
        self._knob_pos = value
        self.update()

    knob_pos = pyqtProperty(float, get_knob_pos, set_knob_pos)

    def _animate_to(self, checked):
        self._animation.stop()
        target = 1.0 if checked else 0.0
        self._animation.setStartValue(self._knob_pos)
        self._animation.setEndValue(target)
        self._animation.start()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self._animate_to(checked)
            self.toggled.emit(checked)

    def toggle(self):
        self.setChecked(not self._checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        track_h = 20
        track_y = (h - track_h) / 2
        radius = track_h / 2

        knob_pos = self._knob_pos
        knob_diam = h - 4
        min_knob_x = 2
        max_knob_x = w - knob_diam - 2

        if self._checked:
            t = knob_pos
        else:
            t = 1.0 - knob_pos

        on_color = self._on_color
        off_color = self._off_color
        if knob_pos > 0.01:
            r = int(off_color.red() + (on_color.red() - off_color.red()) * knob_pos)
            g = int(off_color.green() + (on_color.green() - off_color.green()) * knob_pos)
            b = int(off_color.blue() + (on_color.blue() - off_color.blue()) * knob_pos)
            track_color = QColor(r, g, b)
        else:
            track_color = off_color

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0, track_y, w, track_h), radius, radius)

        knob_pos_x = min_knob_x + (max_knob_x - min_knob_x) * knob_pos
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0, 30), 0.5))
        painter.drawEllipse(QRectF(knob_pos_x, 1, knob_diam, knob_diam))

        painter.end()


class SourceItem(QWidget):
    """Component for individual source selection with toggle and icon."""

    def __init__(self, source_name, icon_path, parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self.icon_path = icon_path
        self._checked = True
        self.accent_hex = self.get_accent_color(self.source_name)
        self.accent_color = QColor(self.accent_hex)
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_icon(self.icon_path)
        layout.addWidget(self.icon_label)

        self.name_label = QLabel(self.source_name)
        self.name_label.setObjectName("sourceItemName")
        layout.addWidget(self.name_label, 1)

        self.toggle = ToggleSwitch(accent_color=self.accent_hex)
        self.toggle.setChecked(self._checked)
        self.toggle.toggled.connect(self.on_toggled)
        layout.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(f"Toggle {self.source_name}")

        self.update_visual_state()

    def set_icon(self, icon_path):
        source_key = self.source_name.lower()

        if self._try_load_svg(icon_path):
            return

        icon_styles = {
            "pacman": {"text": "", "color": "#4FC3F7"},
            "aur": {"text": "", "color": "#FF8A65"},
            "flatpak": {"text": "", "color": "#26A69A"},
            "npm": {"text": "", "color": "#E53935"},
            "local": {"text": "", "color": "#00BFAE"},
        }

        style = icon_styles.get(source_key, {"text": "●", "color": "#8B8D97"})
        self.icon_label.setText(style["text"])
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {style["color"]};
                background: transparent;
                border: none;
            }}
        """)

    def _try_load_svg(self, icon_path):
        try:
            if not os.path.exists(icon_path):
                return False
            svg_renderer = QSvgRenderer(icon_path)
            if not svg_renderer.isValid():
                return False
            size = 22
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            svg_renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap)
                self.icon_label.setStyleSheet("background: transparent; border: none; padding: 0; margin: 0;")
                return True
            return False
        except Exception:
            return False

    def get_accent_color(self, name):
        n = name.lower()
        mapping = {"pacman": "#4FC3F7", "aur": "#FF8A65", "flatpak": "#26A69A", "npm": "#E53935"}
        return mapping.get(n, "#00BFAE")

    def on_toggled(self, state):
        self._checked = state
        self.update_visual_state()

    def update_visual_state(self):
        if self._checked:
            self.setStyleSheet(f"""
                SourceItem {{
                    background-color: rgba({self.accent_color.red()}, {self.accent_color.green()}, {self.accent_color.blue()}, 0.06);
                    border-radius: 8px;
                    border: 1px solid rgba({self.accent_color.red()}, {self.accent_color.green()}, {self.accent_color.blue()}, 0.15);
                }}
                QLabel#sourceItemName {{
                    color: #5C5E66;
                    font-size: 13px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            self.setStyleSheet("""
                SourceItem {
                    background-color: transparent;
                    border-radius: 8px;
                    border: 1px solid transparent;
                }
                QLabel#sourceItemName {
                    color: #5C5E66;
                    font-size: 13px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }
            """)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            child = self.childAt(pos)
            if child is not self.toggle:
                self.toggle.toggle()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.toggle.toggle()
            return
        super().keyPressEvent(event)

    def is_checked(self):
        return self._checked

    def set_checked(self, checked):
        self._checked = checked
        self.toggle.setChecked(checked)
        self.update_visual_state()
