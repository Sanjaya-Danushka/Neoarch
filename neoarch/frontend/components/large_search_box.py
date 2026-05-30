"""LargeSearchBox - Premium dashboard home for NeoArch."""

from __future__ import annotations

import os
import re
import subprocess
import datetime

import psutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QFrame, QProgressBar, QGraphicsDropShadowEffect,
    QGridLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QRectF, QSize
from PyQt6.QtGui import QColor, QPixmap, QPainter, QResizeEvent
from PyQt6.QtSvg import QSvgRenderer

from neoarch.resources.paths import PROJECT_ROOT

# ── Theme helpers (mirrored from styles.py for inline cleanliness) ─
_C = {
    "bg": "#0C0C0E",
    "surface": "rgba(22, 23, 26, 0.85)",
    "card": "rgba(28, 30, 36, 0.75)",
    "card_hover": "rgba(34, 36, 42, 0.85)",
    "border": "rgba(255, 255, 255, 0.06)",
    "border_hover": "rgba(255, 255, 255, 0.12)",
    "accent": "#00BFAE",
    "accent_soft": "rgba(0, 191, 174, 0.12)",
    "text": "#EDEDEF",
    "text_sec": "#8B8D97",
    "text_muted": "#5C5E66",
}


class LargeSearchBox(QWidget):
    """Premium dashboard home for NeoArch with search, cards, and system status."""

    search_requested = pyqtSignal(str)
    search_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_timer = QTimer()
        self.search_timer.setInterval(800)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_auto_search)

        # System data
        self.cpu_value: QLabel | None = None
        self.cpu_bar: QProgressBar | None = None
        self.mem_value: QLabel | None = None
        self.mem_bar: QProgressBar | None = None
        self.disk_value: QLabel | None = None
        self.disk_bar: QProgressBar | None = None

        # Dashboard counters
        self.installed_count_label: QLabel | None = None
        self.updates_count_label: QLabel | None = None
        self.sources_count_label: QLabel | None = None

        self.system_timer = QTimer()
        self.system_timer.setInterval(3000)
        self.system_timer.timeout.connect(self.update_health)

        self._cache: dict = {}
        self._cache_ts: float = 0

        self._build()

    # ── Public API ──────────────────────────────────────────────────
    def refresh_counts(self, installed: int | None = None,
                       updates: int | None = None,
                       sources: int | None = None):
        if installed is not None and self.installed_count_label:
            self.installed_count_label.setText(self._fmt(installed))
        if updates is not None and self.updates_count_label:
            self.updates_count_label.setText(self._fmt(updates))
        if sources is not None and self.sources_count_label:
            self.sources_count_label.setText(str(sources))

    # ── Build ───────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(28)

        # ── Hero Search ──
        root.addLayout(self._hero_search())

        # ── Dashboard Cards ──
        root.addLayout(self._dashboard_cards())

        # ── Quick Actions ──
        root.addLayout(self._quick_actions())

        # ── Source Indicators ──
        root.addLayout(self._source_indicators())

        # ── System Health ──
        root.addLayout(self._system_health())

        root.addStretch()

        self.setStyleSheet(self._qss())

    # ── Hero Search ────────────────────────────────────────────────
    def _hero_search(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("heroSearchCard")
        container.setFixedHeight(72)
        container.setStyleSheet(f"""
            QFrame#heroSearchCard {{
                background-color: rgba(18, 19, 22, 0.9);
                border: 1px solid {_C['border']};
                border-radius: 20px;
            }}
            QFrame#heroSearchCard:hover {{
                border-color: rgba(0, 191, 174, 0.3);
            }}
        """)

        self._shadow(container, 24, QColor(0, 0, 0, 60))

        lay = QHBoxLayout(container)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        icon = QLabel()
        icon.setFixedSize(28, 28)
        self._set_svg_icon(icon, "discover/search.svg", 28, "#5C5E66")
        lay.addWidget(icon)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Search packages across pacman, AUR, Flatpak, npm…")
        self.input.setFixedHeight(48)
        self.input.returnPressed.connect(self._on_submit)
        self.input.textChanged.connect(self._on_text)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {_C['text']};
                font-size: 16px;
                font-weight: 400;
                padding: 0;
            }}
            QLineEdit::placeholder {{
                color: {_C['text_muted']};
                font-size: 15px;
            }}
            QLineEdit:focus {{ outline: none; }}
        """)
        lay.addWidget(self.input, 1)

        btn = QPushButton("Search")
        btn.setFixedHeight(40)
        btn.setMinimumWidth(100)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_C['accent']};
                color: #0C0C0E;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: #00D4C1; }}
            QPushButton:pressed {{ background-color: #009688; }}
        """)
        btn.clicked.connect(self._on_submit)
        lay.addWidget(btn)

        row.addWidget(container)
        return row

    # ── Dashboard Cards ─────────────────────────────────────────────
    def _dashboard_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        cards = [
            ("📦", "Installed Packages", "—", "rgba(0, 191, 174, 0.12)", _C["accent"]),
            ("🔄", "Available Updates", "—", "rgba(255, 159, 67, 0.12)", "#FF9F43"),
            ("📡", "Active Sources", "—", "rgba(88, 101, 242, 0.12)", "#5865F2"),
        ]

        for emoji, title, _, bg, accent in cards:
            card = self._stat_card(emoji, title, bg, accent)
            row.addWidget(card, 1)

        return row

    def _stat_card(self, emoji: str, title: str,
                   bg: str, accent: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(130)
        card.setStyleSheet(f"""
            background-color: {_C['card']};
            border: 1px solid {_C['border']};
            border-radius: 20px;
        """)
        self._shadow(card, 20, QColor(0, 0, 0, 50))

        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(42, 42)
        icon_frame.setStyleSheet(f"""
            background-color: {bg};
            border-radius: 14px;
            border: 1px solid {accent}33;
        """)
        il = QHBoxLayout(icon_frame)
        il.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(emoji)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 20px; background: transparent;")
        il.addWidget(lbl)
        top.addWidget(icon_frame)

        top.addStretch()
        lay.addLayout(top)

        val = QLabel("—")
        val.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {accent}; background: transparent;")
        lay.addWidget(val)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {_C['text_sec']}; background: transparent;")
        lay.addWidget(lbl_title)

        # Store reference
        if "Installed" in title:
            self.installed_count_label = val
        elif "Updates" in title:
            self.updates_count_label = val
        elif "Sources" in title:
            self.sources_count_label = val

        return card

    # ── Quick Actions ───────────────────────────────────────────────
    def _quick_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        actions = [
            ("⬆", "Update All", self._on_update_all),
            ("🔄", "Refresh Databases", self._on_refresh),
            ("🧹", "Clean Cache", self._on_clean),
        ]

        for icon, text, cb in actions:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {_C['card']};
                    color: {_C['text']};
                    border: 1px solid {_C['border']};
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {_C['card_hover']};
                    border-color: {_C['border_hover']};
                }}
            """)
            btn.clicked.connect(cb)
            row.addWidget(btn)

        row.addStretch()
        return row

    # ── Source Indicators ───────────────────────────────────────────
    def _source_indicators(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        label = QLabel("Source Status")
        label.setStyleSheet(f"font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; color: {_C['text_muted']}; background: transparent;")
        col.addWidget(label)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)
        chips_row.setContentsMargins(0, 0, 0, 0)

        sources = [
            ("pacman", "#4FC3F7"),
            ("AUR", "#FF8A65"),
            ("Flatpak", "#26A69A"),
            ("npm", "#E53935"),
            ("Docker", "#2496ED"),
        ]

        for name, color in sources:
            chip = self._source_chip(name, color)
            chips_row.addWidget(chip)

        chips_row.addStretch()
        col.addLayout(chips_row)
        return col

    def _source_chip(self, name: str, color: str) -> QFrame:
        chip = QFrame()
        chip.setFixedHeight(32)
        chip.setStyleSheet(f"""
            background-color: {color}11;
            border: 1px solid {color}44;
            border-radius: 8px;
        """)

        lay = QHBoxLayout(chip)
        lay.setContentsMargins(12, 0, 14, 0)
        lay.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(f"font-size: 8px; color: {color}; background: transparent;")
        lay.addWidget(dot)

        lbl = QLabel(name)
        lbl.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {_C['text_sec']}; background: transparent;")
        lay.addWidget(lbl)

        return chip

    # ── System Health ───────────────────────────────────────────────
    def _system_health(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        metrics = [
            ("🖥", "CPU", self._cpu_card),
            ("💾", "Memory", self._mem_card),
            ("💿", "Disk", self._disk_card),
        ]

        for emoji, name, builder in metrics:
            card = builder(emoji, name)
            row.addWidget(card, 1)

        return row

    def _metric_card(self, emoji: str, name: str,
                     color: str) -> tuple[QFrame, QLabel, QProgressBar]:
        card = QFrame()
        card.setFixedHeight(90)
        card.setStyleSheet(f"""
            background-color: {_C['card']};
            border: 1px solid {_C['border']};
            border-radius: 16px;
        """)
        self._shadow(card, 16, QColor(0, 0, 0, 40))

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon_lbl = QLabel(emoji)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        top.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {_C['text_sec']}; background: transparent;")
        top.addWidget(name_lbl, 1)

        val = QLabel("—")
        val.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {color}; background: transparent;")
        top.addWidget(val)

        lay.addLayout(top)

        bar = QProgressBar()
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(5)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(18, 19, 22, 0.8);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        lay.addWidget(bar)

        return card, val, bar

    def _cpu_card(self, emoji: str, name: str) -> QFrame:
        card, val, bar = self._metric_card(emoji, name, "#FF9F43")
        self.cpu_value = val
        self.cpu_bar = bar
        return card

    def _mem_card(self, emoji: str, name: str) -> QFrame:
        card, val, bar = self._metric_card(emoji, name, _C["accent"])
        self.mem_value = val
        self.mem_bar = bar
        return card

    def _disk_card(self, emoji: str, name: str) -> QFrame:
        card, val, bar = self._metric_card(emoji, name, "#A29BFE")
        self.disk_value = val
        self.disk_bar = bar
        return card

    # ── System health data ──────────────────────────────────────────
    def update_health(self):
        try:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            if self.cpu_value and self.cpu_bar:
                self.cpu_value.setText(f"{cpu:.0f}%")
                self.cpu_bar.setValue(int(cpu))
            if self.mem_value and self.mem_bar:
                self.mem_value.setText(f"{mem.percent:.0f}%")
                self.mem_bar.setValue(int(mem.percent))
            if self.disk_value and self.disk_bar:
                pct = (disk.used / disk.total) * 100
                self.disk_value.setText(f"{pct:.0f}%")
                self.disk_bar.setValue(int(pct))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if not self.system_timer.isActive():
            self.system_timer.start()
        QTimer.singleShot(200, self.update_health)
        QTimer.singleShot(300, self._load_system_counts)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.system_timer.stop()

    def _load_system_counts(self):
        try:
            r = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                count = len(r.stdout.strip().split("\n"))
                self.refresh_counts(installed=count)
        except Exception:
            pass

        try:
            r = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                count = len(r.stdout.strip().split("\n"))
                self.refresh_counts(updates=count)
            else:
                self.refresh_counts(updates=0)
        except Exception:
            pass

        sources = self._count_sources()
        self.refresh_counts(sources=sources)

    @staticmethod
    def _count_sources() -> int:
        count = 1  # pacman always
        try:
            r = subprocess.run(["which", "yay", "paru"], capture_output=True, text=True, timeout=2)
            if r.stdout.strip():
                count += 1
        except Exception:
            pass
        try:
            r = subprocess.run(["flatpak", "list"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                count += 1
        except Exception:
            pass
        try:
            r = subprocess.run(["which", "npm"], capture_output=True, text=True, timeout=2)
            if r.stdout.strip():
                count += 1
        except Exception:
            pass
        try:
            r = subprocess.run(["which", "docker"], capture_output=True, text=True, timeout=2)
            if r.stdout.strip():
                count += 1
        except Exception:
            pass
        return count

    # ── Actions ─────────────────────────────────────────────────────
    def _on_update_all(self):
        self.search_requested.emit("__UPDATE_ALL__")

    def _on_refresh(self):
        self.search_requested.emit("__REFRESH_DB__")

    def _on_clean(self):
        self.search_requested.emit("__CLEAN_CACHE__")

    def _on_submit(self):
        q = self.input.text().strip()
        if q:
            self.search_timer.stop()
            self.search_submitted.emit(q)

    def _on_text(self):
        self.search_timer.start()

    def on_auto_search(self):
        q = self.input.text().strip()
        if len(q) >= 3:
            self.search_requested.emit(q)

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _shadow(widget: QWidget, radius: int, color: QColor):
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(radius)
        s.setColor(color)
        s.setOffset(0, radius // 4)
        widget.setGraphicsEffect(s)

    @staticmethod
    def _fmt(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)

    @staticmethod
    def _set_svg_icon(label: QLabel, rel_path: str, size: int, color: str):
        path = os.path.join(PROJECT_ROOT, "assets", "icons", rel_path)
        try:
            r = QSvgRenderer(path)
            if r.isValid():
                pm = QPixmap(size, size)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                r.render(p, QRectF(0, 0, size, size))
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p.fillRect(QRectF(0, 0, size, size), QColor(color))
                p.end()
                label.setPixmap(pm)
                return
        except Exception:
            pass
        label.setText("🔍")

    def _qss(self):
        return """
            LargeSearchBox {
                background-color: transparent;
            }
        """
