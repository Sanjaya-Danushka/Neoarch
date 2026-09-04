"""Signal strength indicator for the main header.

Shows one of four static icons based on the recently measured network
latency: no signal, low, medium or high. Icons live in
``assets/icons/navbar``.
"""

import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from neoarch.backend.services import network_latency
from neoarch.resources.paths import PROJECT_ROOT

_ICON_DIR = os.path.join(str(PROJECT_ROOT), "assets", "icons", "status")

_ICONS = {
    "nosignal": "nosignal.png",
    "low": "signal-low.png",
    "medium": "signal-medium.png",
    "high": "signal-high.png",
}

_TIER_LABELS = {
    "nosignal": "No signal",
    "low": "Low signal",
    "medium": "Medium signal",
    "high": "High signal",
}


def _fmt(seconds):
    if seconds is None:
        return ""
    if seconds < 1.0:
        return f"{int(seconds * 1000)} ms"
    return f"{seconds:.1f} s"


def _state_for(avg):
    if avg is None:
        return "nosignal"
    if avg < 0.3:
        return "high"
    if avg < 0.8:
        return "medium"
    return "low"


class SignalIndicator(QLabel):
    """Displays one of the four signal-state icons for the current latency."""

    no_signal = pyqtSignal()
    connection_restored = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._pixmaps = {}
        for state, filename in _ICONS.items():
            path = os.path.join(_ICON_DIR, filename)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._pixmaps[state] = pixmap

        self._state = "nosignal"
        self._prev_state = None
        self._render(self._state, None)

        self._timer = QTimer(self)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self.refresh_state)
        self._baseline_set = False
        self._suppress_next_notify = False
        self._timer.start()

    def refresh_state(self):
        if not self._baseline_set:
            if not network_latency.has_samples():
                return
            self._baseline_set = True
            self._suppress_next_notify = True

        if not network_latency.is_online():
            self._render("nosignal", None)
            return

        avg = network_latency.average()
        self._render(_state_for(avg), avg)

    def _render(self, state, avg):
        if (self._prev_state is not None
                and state != self._prev_state
                and not self._suppress_next_notify):
            if state == "nosignal" and self._prev_state != "nosignal":
                self.no_signal.emit()
            elif state != "nosignal" and self._prev_state == "nosignal":
                self.connection_restored.emit()
        self._suppress_next_notify = False
        self._prev_state = state
        self._state = state
        pixmap = self._pixmaps.get(state)
        if pixmap is not None:
            self.setPixmap(pixmap.scaled(
                28, 28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        label = _TIER_LABELS.get(state, state)
        if avg is not None:
            label += f" \u2014 {_fmt(avg)}"
        self.setToolTip(label)

    def is_online(self):
        return self._state != "nosignal"
