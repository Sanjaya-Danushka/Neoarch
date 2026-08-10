"""SourceItem Component — macOS-style list row for package source selection."""

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPalette, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtSvg import QSvgRenderer


class ToggleSwitch(QWidget):
    """macOS-style toggle switch with spring animation and blue accent."""

    toggled = pyqtSignal(bool)

    def __init__(self, accent_color="#3B82F6", parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = True
        self._knob_pos = 1.0
        self._on_color = QColor(accent_color)
        self._off_color = QColor(48, 50, 58, 220)
        self._animation = QPropertyAnimation(self, b"knob_pos", self)
        self._animation.setDuration(180)
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
        track_h = 18
        track_y = (h - track_h) / 2
        radius = track_h / 2

        knob_pos = self._knob_pos
        knob_diam = 14
        min_knob_x = 3
        max_knob_x = w - knob_diam - 3

        on_color = self._on_color
        off_color = self._off_color
        if knob_pos > 0.01:
            r = int(off_color.red() + (on_color.red() - off_color.red()) * knob_pos)
            g = int(off_color.green() + (on_color.green() - off_color.green()) * knob_pos)
            b = int(off_color.blue() + (on_color.blue() - off_color.blue()) * knob_pos)
            track_color = QColor(r, g, b)
        else:
            track_color = off_color

        painter.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0, track_y, w, track_h), radius, radius)

        knob_x = min_knob_x + (max_knob_x - min_knob_x) * knob_pos
        knob_rect = QRectF(knob_x, (h - knob_diam) / 2, knob_diam, knob_diam)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawEllipse(knob_rect.translated(0, 1))

        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0, 15), 0.5))
        painter.drawEllipse(knob_rect)

        painter.end()


class _ElideLabel(QLabel):
    """QLabel that elides text to the right when space is tight."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        color = self.palette().color(QPalette.ColorRole.WindowText)
        if not color.isValid():
            color = QColor(245, 246, 250)
        painter.setPen(color)
        fm = QFontMetrics(self.font())
        text = fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.end()


class SourceItem(QWidget):
    """macOS preference-style list row.

    Layout: [icon]  Source Name  [badge]  [toggle]
    - Height 54px, radius 14px
    - Soft hover surface, selected row uses subtle blue surface
    - Capsule badge with semi-transparent dark background
    """

    def __init__(self, source_name, icon_path, parent=None, count=None, size=None):
        super().__init__(parent)
        self.source_name = source_name
        self.icon_path = icon_path
        self._checked = True
        self._hover = False
        self.accent_hex = self.get_accent_color(self.source_name)
        self.accent_color = QColor(self.accent_hex)
        self.init_ui(count, size)

    def init_ui(self, count=None, size=None):
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none; padding: 0; margin: 0;")
        self.set_icon(self.icon_path)
        layout.addWidget(self.icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.name_label = _ElideLabel(self.source_name)
        self.name_label.setObjectName("sourceItemName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_col.addWidget(self.name_label)

        layout.addLayout(text_col, 1)

        self.count_label = QLabel()
        self.count_label.setObjectName("sourceItemCount")
        self.count_label.setMinimumWidth(26)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setVisible(count is not None)
        self.set_count_label(count)
        layout.addWidget(self.count_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.toggle = ToggleSwitch(accent_color=self.accent_hex)
        self.toggle.setChecked(self._checked)
        self.toggle.toggled.connect(self.on_toggled)
        layout.addWidget(self.toggle)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(f"Toggle {self.source_name}")

        self.update_visual_state()

    def set_count_label(self, count):
        if count is None:
            self.count_label.setVisible(False)
            return
        c_int = int(count) if (isinstance(count, (int, str)) and str(count).isdigit()) else 0
        self.count_label.setText(str(c_int) if c_int > 0 else "")
        self.count_label.setVisible(c_int > 0)

    def set_count(self, count, size_text=None):
        self.set_count_label(count)
        if size_text:
            self.setToolTip(f"{self.source_name}: {count} updates ({size_text})")
        else:
            self.setToolTip(f"Toggle {self.source_name}")

    def set_icon(self, icon_path):
        if self._try_load_svg(icon_path):
            return

        icon_styles = {
            "pacman": {"text": "\u25C9", "color": "#4FC3F7"},
            "aur": {"text": "\u25C9", "color": "#FF8A65"},
            "flatpak": {"text": "\u25C9", "color": "#26A69A"},
            "npm": {"text": "\u25C9", "color": "#E53935"},
            "local": {"text": "\u25C9", "color": "#3B82F6"},
        }
        style = icon_styles.get(self.source_name.lower(), {"text": "\u25C9", "color": "#727B89"})
        self.icon_label.setText(style["text"])
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
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
        mapping = {"pacman": "#3B82F6", "aur": "#F59E0B", "flatpak": "#10B981", "npm": "#EF4444", "local": "#3B82F6"}
        return mapping.get(n, "#3B82F6")

    def on_toggled(self, state):
        self._checked = state
        self.update_visual_state()

    def update_visual_state(self):
        if self._checked:
            self.setStyleSheet("""
                SourceItem {
                    border: none;
                    border-radius: 14px;
                }
                QLabel#sourceItemName {
                    color: #F5F6FA;
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }
                QLabel#sourceItemSubtitle {
                    color: #6B7280;
                    font-size: 10px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
                QLabel#sourceItemCount {
                    color: #F5F6FA;
                    font-size: 10px;
                    font-weight: 600;
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 10px;
                    padding: 1px 7px;
                    margin: 0;
                }
            """)
        else:
            self.setStyleSheet("""
                SourceItem {
                    border: none;
                    border-radius: 14px;
                }
                QLabel#sourceItemName {
                    color: #A7B1C2;
                    font-size: 12px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }
                QLabel#sourceItemSubtitle {
                    color: #6B7280;
                    font-size: 10px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
                QLabel#sourceItemCount {
                    color: #A7B1C2;
                    font-size: 10px;
                    font-weight: 600;
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                    padding: 1px 7px;
                    margin: 0;
                }
            """)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        if self._checked:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.drawRoundedRect(rect, 14, 14)
        elif self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
            painter.setBrush(QColor("#202733"))
            painter.drawRoundedRect(rect, 14, 14)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.drawRoundedRect(rect, 14, 14)

        painter.end()
        super().paintEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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
