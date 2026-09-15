"""Clean pill toggle switch styled to match the app's macOS-like dark theme.

A flat, minimal switch: a solid track that fills with the accent color when
enabled, a pure-white gradient knob with a soft recessed shadow, and a subtle
focus ring. No outer glow, no busy borders.
"""

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QAbstractButton


_ON_TOP = "#00D2BF"
_ON_BOTTOM = "#00A599"
_OFF_TOP = "#2E3138"
_OFF_BOTTOM = "#272A30"
_OFF_BORDER = "rgba(255, 255, 255, 0.10)"
_KNOB_TOP = "#FFFFFF"
_KNOB_BOTTOM = "#EFF0F2"


class ToggleSwitch(QAbstractButton):
    """Animated pill switch. API mirrors QCheckBox."""

    TRACK_W = 40
    TRACK_H = 22
    KNOB = 16
    PAD = 3

    def __init__(self, parent=None, name=""):
        super().__init__(parent)
        self.setFixedSize(self.TRACK_W + 8, self.TRACK_H + 6)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCheckable(True)
        if name:
            self.setAccessibleName(name)
        self._progress = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_progress)
        self.toggled.connect(self._on_toggled)

    def _set_progress(self, value):
        self._progress = float(value)
        self.update()

    def setChecked(self, checked, animate=True):
        super().setChecked(checked)
        if not animate:
            self._progress = 1.0 if checked else 0.0
            self.update()

    def _on_toggled(self, checked):
        target = 1.0 if checked else 0.0
        if not self.isVisible() or abs(self._progress - target) < 0.001:
            self._progress = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def _track_rect(self):
        return QRectF((self.width() - self.TRACK_W) / 2,
                      (self.height() - self.TRACK_H) / 2,
                      self.TRACK_W, self.TRACK_H)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track = self._track_rect()
        radius = track.height() / 2.0
        t = min(1.0, self._progress * 2)

        # Track — interpolate between the off and on gradients
        grad = QLinearGradient(QPointF(track.left(), track.top()),
                               QPointF(track.left(), track.bottom()))
        grad.setColorAt(0, _lerp(QColor(_OFF_TOP), QColor(_ON_TOP), t))
        grad.setColorAt(1, _lerp(QColor(_OFF_BOTTOM), QColor(_ON_BOTTOM), t))
        p.setBrush(grad)
        if self._progress >= 0.5:
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
        else:
            p.setPen(QPen(QColor(_OFF_BORDER), 1))
        p.drawRoundedRect(track, radius, radius)

        # Knob with a soft recessed shadow
        knob_x = track.left() + self.PAD + self._progress * (
            track.width() - 2 * self.PAD - self.KNOB)
        knob = QRectF(knob_x, track.top() + self.PAD, self.KNOB, self.KNOB)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, int(self._progress * 40 + 30)))
        p.drawEllipse(knob.translated(0, 1.3))

        kgrad = QLinearGradient(QPointF(knob.left(), knob.top()),
                                QPointF(knob.left(), knob.bottom()))
        kgrad.setColorAt(0, QColor(_KNOB_TOP))
        kgrad.setColorAt(1, QColor(_KNOB_BOTTOM))
        p.setBrush(kgrad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(knob)

        if not self.isEnabled():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawRoundedRect(track, radius, radius)

        if self.hasFocus():
            p.setPen(QPen(QColor(0, 191, 174, 150), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track.adjusted(-2.5, -2.5, 2.5, 2.5), radius + 2.5, radius + 2.5)


def _lerp(a, b, t):
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )