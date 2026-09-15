"""Shared building blocks for the settings pages.

These are the flat "engine row" pieces used by the Auto Update page
(icon badge cards, title/subtitle rows, separators, quiet buttons, the
-- value + stepper and the selection dot). Extracted so other settings
pages (Notifications, ...) can build with the same visual language
without duplicating the private helpers.
"""

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from neoarch.frontend.tokens import Colors, Fonts, QSS, Radii

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_MINUS = '<line x1="5" y1="12" x2="19" y2="12"/>'
_ICON_PLUS = (
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
)

_STEPPER_QSS = f"""
    QFrame#stepper {{
        background-color: {Colors.INPUT_BG};
        border: 1px solid {Colors.BORDER_INPUT};
        border-radius: 10px;
    }}
    QFrame#stepper QPushButton#stepBtn {{
        background: transparent;
        border: none;
        border-radius: 7px;
        padding: 0;
    }}
    QFrame#stepper QPushButton#stepBtn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}
    QFrame#stepper QPushButton#stepBtn:pressed {{
        background-color: rgba(255, 255, 255, 0.15);
    }}
"""


def icon(svg_body, size=12, color=None):
    """Render a lucide-style stroke path to a QPixmap."""
    color = color or Colors.TEXT_2
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
        ' fill="none" stroke="{c}" stroke-width="2"'
        ' stroke-linecap="round" stroke-linejoin="round">{b}</svg>'
    ).format(c=color, b=svg_body)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    if renderer.isValid():
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
    return pm


def icon_pixmap(svg_body, size=14, color="#EDEDEF"):
    return icon(svg_body, size=size, color=color)


def make_card(title_text, svg_body=None, icon_color=None):
    """A flat settings card: icon badge header + stacked rows."""
    card = QFrame()
    card.setObjectName("settingsCard")
    card.setStyleSheet(QSS.CARD)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(20, 18, 20, 12)
    card_layout.setSpacing(0)

    header = QHBoxLayout()
    header.setSpacing(10)
    if svg_body is not None:
        badge = QLabel()
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background: {Colors.SURFACE_2}; border: none;"
            f" border-radius: {Radii.SM}px;")
        badge.setPixmap(icon_pixmap(svg_body, 15, color=icon_color or "#EDEDEF"))
        header.addWidget(badge)
    title = QLabel(title_text)
    title.setStyleSheet(
        f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
        f" color: {Colors.TEXT}; border: none; background: transparent;")
    header.addWidget(title)
    header.addStretch()
    card_layout.addLayout(header)

    pad = QWidget()
    pad.setStyleSheet("background: transparent;")
    pad.setFixedHeight(2)
    card_layout.addWidget(pad)
    return card, card_layout


def row(title_text, subtitle_text=None, subtitle_color=None, control=None):
    """Title + optional subtitle, with an optional aligned control."""
    row_widget = QWidget()
    row_widget.setStyleSheet("background: transparent;")
    row = QHBoxLayout(row_widget)
    row.setSpacing(16)
    row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    texts = QVBoxLayout()
    texts.setSpacing(2)

    title = QLabel(title_text)
    title.setStyleSheet(
        f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
        f" color: {Colors.TEXT}; border: none; background: transparent;")
    texts.addWidget(title)

    if subtitle_text:
        color = subtitle_color or Colors.TEXT_2
        subtitle = QLabel(subtitle_text)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {color};"
            " border: none; background: transparent;")
        texts.addWidget(subtitle)

    row.addLayout(texts, 1)
    if control is not None:
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
    return row_widget


def sep():
    """Thin hairline separator between rows."""
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(
        f"background: {Colors.BORDER}; border: none; margin: 4px 0;")
    return line


def btn(text, on_click=None):
    """Quiet light button — the About-page link look."""
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.06);
            color: {Colors.TEXT};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 8px 18px;
            font-size: {Fonts.BASE};
            font-weight: {Fonts.MEDIUM};
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.1);
            border-color: rgba(0, 191, 174, 0.4);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.14);
        }}
        QPushButton:disabled {{
            color: {Colors.TEXT_3};
            border-color: {Colors.BORDER};
            background-color: transparent;
        }}
    """)
    button.setFixedHeight(36)
    if on_click is not None:
        button.clicked.connect(lambda checked=False: on_click())
    return button


def actions_row(buttons):
    """A left-aligned row of action buttons."""
    row_widget = QWidget()
    row_widget.setStyleSheet("background: transparent;")
    row = QHBoxLayout(row_widget)
    row.setContentsMargins(0, 4, 0, 0)
    row.setSpacing(10)
    for button in buttons:
        row.addWidget(button)
    row.addStretch()
    return row_widget


class Dot(QFrame):
    """Small teal selection dot, same look as the theme selector."""

    def __init__(self, active=False, parent=None):
        super().__init__(parent)
        self._active = active
        self.setFixedSize(16, 16)

    def setActive(self, active):
        self._active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active:
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
            p.setBrush(QColor(Colors.ACCENT))
        else:
            p.setPen(QPen(QColor(Colors.BORDER), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(1.5, 1.5, 13, 13))
        p.end()


class Stepper(QFrame):
    """− value + compact stepper — a beautiful replacement for QSpinBox."""

    valueChanged = pyqtSignal(int)

    def __init__(self, minimum, maximum, step=1, suffix="",
                 on_text=None, pad=0, parent=None):
        super().__init__(parent)
        self._min, self._max, self._step = minimum, maximum, step
        self._suffix = suffix
        self._on_text = on_text
        self._pad = pad
        self._value = minimum

        self.setObjectName("stepper")
        self.setStyleSheet(_STEPPER_QSS)
        self.setFixedHeight(34)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(2)

        self._minus = QPushButton()
        self._minus.setObjectName("stepBtn")
        self._minus.setFixedSize(28, 26)
        self._minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus.setStyleSheet("border: none; background: transparent;")
        self._minus.clicked.connect(self._decrement)
        lay.addWidget(self._minus)

        self._value_label = QLabel()
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setMinimumWidth(56)
        self._value_label.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.SEMI}; border: none; background: transparent;")
        lay.addWidget(self._value_label, 1)

        self._plus = QPushButton()
        self._plus.setObjectName("stepBtn")
        self._plus.setFixedSize(28, 26)
        self._plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus.setStyleSheet("border: none; background: transparent;")
        self._plus.clicked.connect(self._increment)
        lay.addWidget(self._plus)

        self.setValue(minimum)

    def value(self):
        return self._value

    def setValue(self, value):
        value = max(self._min, min(self._max, int(value)))
        self._value = value

        if self._on_text is not None and value == 0:
            text = self._on_text
        else:
            text = f"{value:0{self._pad}d}{self._suffix}"
        self._value_label.setText(text)

        self._minus.setEnabled(value > self._min)
        self._plus.setEnabled(value < self._max)
        self._minus.setIcon(QIcon(icon(
            _ICON_MINUS,
            color=Colors.TEXT_2 if value > self._min else Colors.TEXT_3)))
        self._plus.setIcon(QIcon(icon(
            _ICON_PLUS,
            color=Colors.TEXT_2 if value < self._max else Colors.TEXT_3)))
        self.valueChanged.emit(value)

    def _increment(self):
        self.setValue(self._value + self._step)

    def _decrement(self):
        self.setValue(self._value - self._step)