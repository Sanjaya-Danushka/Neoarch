"""FeatureCard - Premium card component matching SourceCard visual language."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QEvent, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QPainter, QPainterPath, QIcon
from PyQt6.QtSvg import QSvgRenderer


def _render_svg_pixmap(svg_path, size=18):
    try:
        if not os.path.exists(svg_path):
            return None
        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            return None
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return pixmap
    except Exception:
        return None


def _make_icon_pixmap(draw_func, size=14):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#8B8D97"))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    draw_func(painter, size)
    painter.end()
    return pixmap


def _draw_clone(p, s):
    mid = s // 2
    path = QPainterPath()
    path.moveTo(mid, 2)
    path.lineTo(mid, s - 5)
    path.moveTo(4, s - 9)
    path.lineTo(mid, s - 5)
    path.lineTo(s - 4, s - 9)
    p.drawPath(path)
    p.drawRoundedRect(QRectF(3, s - 3, s - 6, 2), 1, 1)


def _draw_open(p, s):
    hh = s // 2
    p.drawRoundedRect(QRectF(2, hh - 1, s - 4, hh - 1), 2, 2)
    path = QPainterPath()
    path.moveTo(2, hh - 1)
    path.lineTo(6, 3)
    path.lineTo(hh + 2, 3)
    path.lineTo(hh + 4, hh - 1)
    p.drawPath(path)


def _draw_update(p, s):
    center = QRectF(3, 3, s - 8, s - 8)
    p.drawArc(center, 0, 2880)
    mid = s // 2
    path = QPainterPath()
    path.moveTo(s - 5, mid - 4)
    path.lineTo(s - 2, mid)
    path.lineTo(s - 8, mid)
    p.drawPath(path)


def _draw_clean(p, s):
    hh = s // 2
    p.drawRoundedRect(QRectF(3, hh - 2, s - 6, hh + 2), 1, 1)
    path = QPainterPath()
    path.moveTo(4, hh - 2)
    path.lineTo(hh, hh - 2)
    path.lineTo(s - 4, hh - 2)
    p.drawPath(path)
    p.drawRect(QRectF(hh - 2, 2, 3, hh - 4))


def _draw_list(p, s):
    for i in range(3):
        y = 3 + i * (s - 6) // 2
        p.drawRoundedRect(QRectF(3, y, s - 6, 2), 1, 1)


def _draw_stop(p, s):
    p.drawRoundedRect(QRectF(3, 3, s - 6, s - 6), 2, 2)


def _draw_shell(p, s):
    mid = s // 2
    path = QPainterPath()
    path.moveTo(4, 4)
    path.lineTo(mid, mid)
    path.lineTo(4, s - 4)
    p.drawPath(path)
    p.drawLine(mid + 2, s - 4, s - 4, s - 4)


def _draw_play(p, s):
    path = QPainterPath()
    path.moveTo(4, 3)
    path.lineTo(s - 3, s // 2)
    path.lineTo(4, s - 3)
    path.closeSubpath()
    p.drawPath(path)


ICON_DRAW_FUNCS = {
    "clone": _draw_clone,
    "open": _draw_open,
    "update": _draw_update,
    "clean": _draw_clean,
    "list": _draw_list,
    "stop": _draw_stop,
    "shell": _draw_shell,
    "run": _draw_play,
}


def _get_icon_pixmap(name, size=14):
    draw = ICON_DRAW_FUNCS.get(name)
    if draw:
        return _make_icon_pixmap(draw, size)
    return None


class FeatureCard(QWidget):
    """Premium card for Git, Docker sections — matches SourceCard visual language.

    Card structure:
      ┌──────────────────────────────┐
      │ [icon]  Title        [badge] │
      ├──────────────────────────────┤
      │     [ Primary Action ]       │
      │  ┌──────┐  ┌──────┐         │
      │  │ icon │  │ icon │         │
      │  │ text │  │ text │         │
      │  ├──────┤  ├──────┤         │
      │  │ icon │  │ icon │         │
      │  │ text │  │ text │         │
      │  └──────┘  └──────┘         │
      └──────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FeatureCard")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._header_widget = None
        self._primary_btn = None
        self._badge_label = None
        self._grid_widget = None

        self.setStyleSheet("""
            QWidget#FeatureCard {
                background-color: rgba(22, 23, 26, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """)

    def build_header(self, icon_path, title, badge_text=None):
        self._header_widget = QWidget()
        self._header_widget.setObjectName("featureCardHeader")
        hl = QHBoxLayout(self._header_widget)
        hl.setContentsMargins(14, 10, 14, 6)
        hl.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(16, 16)
        pix = _render_svg_pixmap(icon_path, 16)
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("""
            color: #EDEDEF;
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        hl.addWidget(title_lbl)
        hl.addStretch()

        self._badge_label = QLabel()
        self._badge_label.setObjectName("featureCardBadge")
        self._badge_label.setStyleSheet("""
            QLabel#featureCardBadge {
                background: rgba(0, 191, 174, 0.1);
                color: #00BFAE;
                border: 1px solid rgba(0, 191, 174, 0.2);
                border-radius: 7px;
                padding: 0 5px;
                font-size: 9px;
                font-weight: 600;
                min-width: 14px;
                min-height: 14px;
            }
        """)
        self.set_badge(badge_text)
        hl.addWidget(self._badge_label)

        self._layout.addWidget(self._header_widget)
        return self._header_widget

    def set_badge(self, text):
        if text is not None and str(text).strip():
            self._badge_label.setText(str(text))
            self._badge_label.setVisible(True)
        else:
            self._badge_label.setVisible(False)

    def build_primary_action(self, text, callback):
        container = QWidget()
        container.setObjectName("primaryActionContainer")
        container.setStyleSheet("background: transparent; border: none;")
        cl = QHBoxLayout(container)
        cl.setContentsMargins(12, 6, 12, 8)
        cl.setSpacing(0)

        btn = QPushButton(text)
        btn.setObjectName("primaryActionBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton#primaryActionBtn {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00BFAE,
                    stop: 1 #00CCBB
                );
                color: #0C0C0E;
                border: none;
                border-radius: 9px;
                font-size: 12px;
                font-weight: 600;
                padding: 0;
            }
            QPushButton#primaryActionBtn:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00D4C1,
                    stop: 1 #00E0CF
                );
            }
            QPushButton#primaryActionBtn:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #009688,
                    stop: 1 #00A595
                );
            }
        """)
        cl.addWidget(btn)

        btn_shadow = QGraphicsDropShadowEffect(btn)
        btn_shadow.setBlurRadius(14)
        btn_shadow.setOffset(0, 2)
        btn_shadow.setColor(QColor(0, 191, 174, 50))
        btn.setGraphicsEffect(btn_shadow)

        self._primary_btn = btn
        self._layout.addWidget(container)
        return btn

    def build_action_grid(self, actions):
        self._grid_widget = QWidget()
        self._grid_widget.setObjectName("actionGridContainer")
        self._grid_widget.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(self._grid_widget)
        grid.setContentsMargins(10, 2, 10, 12)
        grid.setSpacing(6)

        for idx, (text, icon_name, callback) in enumerate(actions):
            if idx >= 4:
                break
            btn = _GridActionButton(text, icon_name)
            btn.clicked.connect(callback)
            row, col = divmod(idx, 2)
            grid.addWidget(btn, row, col)

        self._layout.addWidget(self._grid_widget)
        return self._grid_widget


class _GridActionButton(QWidget):
    """Premium grid action button with icon + label and proper hover states."""

    def __init__(self, text, icon_name, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("gridActionBtn")

        self._hovered = False
        self._pressed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_pix = _get_icon_pixmap(icon_name, 12)
        if icon_pix is not None:
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(12, 12)
            icon_lbl.setPixmap(icon_pix)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(icon_lbl)

        self._text_lbl = QLabel(text)
        self._text_lbl.setStyleSheet("""
            color: #A0A2A8;
            font-size: 10px;
            font-weight: 500;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._text_lbl)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.installEventFilter(self)

        self._update_style()

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def _update_style(self):
        if self._pressed:
            bg = "rgba(255, 255, 255, 0.06)"
            border = "rgba(255, 255, 255, 0.08)"
        elif self._hovered:
            bg = "rgba(255, 255, 255, 0.06)"
            border = "rgba(255, 255, 255, 0.1)"
        else:
            bg = "rgba(255, 255, 255, 0.03)"
            border = "rgba(255, 255, 255, 0.05)"

        self.setStyleSheet(f"""
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 7px;
        """)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == QEvent.Type.HoverEnter:
                self._hovered = True
                self._update_style()
                if self._text_lbl:
                    self._text_lbl.setStyleSheet("""
                        color: #EDEDEF;
                        font-size: 10px;
                        font-weight: 500;
                        background: transparent;
                        border: none;
                    """)
            elif event.type() == QEvent.Type.HoverLeave:
                self._hovered = False
                self._pressed = False
                self._update_style()
                if self._text_lbl:
                    self._text_lbl.setStyleSheet("""
                        color: #A0A2A8;
                        font-size: 10px;
                        font-weight: 500;
                        background: transparent;
                        border: none;
                    """)
            elif event.type() == QEvent.Type.MouseButtonPress:
                self._pressed = True
                self._update_style()
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._pressed = False
                self._update_style()
                if self._hovered:
                    self.clicked.emit()
        return super().eventFilter(obj, event)

    clicked = pyqtSignal()
