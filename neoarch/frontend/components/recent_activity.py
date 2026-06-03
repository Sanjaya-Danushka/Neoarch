"""RecentActivity - Neumorphic card showing recent package operations."""

import re
import subprocess
from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


_ACTION_STYLES = {
    "installed": ("+", "#00BFAE"),
    "upgraded": ("↑", "#FF9F43"),
    "removed": ("−", "#FF6B6B"),
    "downgraded": ("↓", "#A29BFE"),
}

_PACMAN_RE = re.compile(
    r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})[^\]]*\] \[ALPM\] "
    r"(installed|upgraded|removed|downgraded) (\S+)"
)


class RecentActivity(QFrame):
    """Neumorphic dashboard card listing recent package operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recentActivity")
        self._setup_style()
        self._build()
        QTimer.singleShot(0, self._load)

    def _setup_style(self):
        self.setStyleSheet("""
            QFrame#recentActivity {
                background-color: rgba(28, 30, 36, 0.85);
                border-top: 1px solid rgba(255, 255, 255, 0.06);
                border-left: 1px solid rgba(255, 255, 255, 0.06);
                border-right: 1px solid rgba(0, 0, 0, 0.25);
                border-bottom: 2px solid rgba(0, 0, 0, 0.35);
                border-radius: 18px;
            }
        """)
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(22)
        s.setColor(QColor(0, 0, 0, 130))
        s.setOffset(4, 5)
        self.setGraphicsEffect(s)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background-color: #00BFAE; border-radius: 4px;")
        hdr.addWidget(dot)
        hdr.addSpacing(10)

        title = QLabel("Recent Activity")
        title.setStyleSheet(
            "font-size: 12px; font-weight: 500; color: #8B8D97;"
            " background: transparent; letter-spacing: 0.3px;"
        )
        hdr.addWidget(title)
        hdr.addStretch()
        lay.addLayout(hdr)

        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(5)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self.items_layout)
        lay.addStretch()

    def _load(self):
        entries = self._parse_log()
        if not entries:
            self._show_empty()
            return
        for action, pkg, ts in entries[:7]:
            self._add_row(action, pkg, ts)

    def _parse_log(self):
        try:
            r = subprocess.run(
                ["/usr/bin/tail", "-n", "40", "/var/log/pacman.log"],
                capture_output=True, text=True, timeout=2,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return []
        except Exception:
            return []

        entries = []
        for line in r.stdout.strip().split("\n"):
            m = _PACMAN_RE.match(line)
            if m:
                entries.append((m.group(2), m.group(3), m.group(1)))
        entries.reverse()
        return entries

    def _show_empty(self):
        lbl = QLabel("No recent package activity found")
        lbl.setStyleSheet(
            "font-size: 12px; color: #5C5E66; background: transparent; padding: 6px 0;"
        )
        self.items_layout.addWidget(lbl)

    def _add_row(self, action: str, pkg: str, timestamp: str):
        symbol, color = _ACTION_STYLES.get(action, ("•", "#8B8D97"))

        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        icon = QLabel(symbol)
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {color}; background: transparent;"
        )
        row.addWidget(icon)

        name = QLabel(pkg)
        name.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #EDEDEF; background: transparent;"
        )
        row.addWidget(name)

        row.addStretch()

        try:
            dt = _parse_iso_timestamp(timestamp)
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = timestamp[11:16] if len(timestamp) >= 16 else timestamp

        ts = QLabel(time_str)
        ts.setStyleSheet(
            "font-size: 11px; font-weight: 400; color: #5C5E66; background: transparent;"
        )
        row.addWidget(ts)

        c = QFrame()
        c.setStyleSheet("background: transparent;")
        cl = QHBoxLayout(c)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addLayout(row)
        self.items_layout.addWidget(c)


def _parse_iso_timestamp(s: str):
    return datetime.fromisoformat(s)
