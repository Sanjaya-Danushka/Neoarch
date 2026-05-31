"""LargeSearchBox - Premium dashboard home for NeoArch."""

from __future__ import annotations

import os
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QTimer, QRectF
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from neoarch.resources.paths import PROJECT_ROOT

_C = {
    "bg": "#0C0C0E",
    "surface": "rgba(255, 255, 255, 0.03)",
    "card": "rgba(255, 255, 255, 0.04)",
    "card_hover": "rgba(255, 255, 255, 0.07)",
    "border": "rgba(255, 255, 255, 0.06)",
    "border_hover": "rgba(255, 255, 255, 0.12)",
    "accent": "#00BFAE",
    "accent_soft": "rgba(0, 191, 174, 0.10)",
    "text": "#EDEDEF",
    "text_sec": "#8B8D97",
    "text_muted": "#5C5E66",
}


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class LargeSearchBox(QWidget):
    """Premium dashboard home for NeoArch with search, stat cards, and actions."""

    search_requested = pyqtSignal(str)
    search_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_timer = QTimer()
        self.search_timer.setInterval(800)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_auto_search)

        self.installed_count_label: QLabel | None = None
        self.updates_count_label: QLabel | None = None
        self.sources_count_label: QLabel | None = None

        self.dashboard_timer = QTimer()
        self.dashboard_timer.setInterval(30000)
        self.dashboard_timer.timeout.connect(self._load_system_counts)

        self._build()

    def refresh_counts(self, installed: int | None = None,
                       updates: int | None = None,
                       sources: int | None = None):
        if installed is not None and self.installed_count_label:
            self.installed_count_label.setText(self._fmt(installed))
        if updates is not None and self.updates_count_label:
            self.updates_count_label.setText(self._fmt(updates))
        if sources is not None and self.sources_count_label:
            self.sources_count_label.setText(str(sources))

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(28)

        root.addLayout(self._hero_search())
        root.addLayout(self._dashboard_cards())
        root.addLayout(self._actions_row())

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
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid {_C['border']};
                border-radius: 20px;
            }}
            QFrame#heroSearchCard:hover {{
                border-color: rgba(0, 191, 174, 0.25);
            }}
        """)
        self._shadow(container, 28, QColor(0, 0, 0, 80))

        lay = QHBoxLayout(container)
        lay.setContentsMargins(22, 0, 16, 0)
        lay.setSpacing(14)

        icon = QLabel()
        icon.setFixedSize(24, 24)
        self._set_svg_icon(icon, "discover/search.svg", 24, "#5C5E66")
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
                font-size: 15px;
                font-weight: 400;
                padding: 0;
            }}
            QLineEdit::placeholder {{
                color: {_C['text_muted']};
                font-size: 14px;
            }}
            QLineEdit:focus {{ outline: none; }}
        """)
        lay.addWidget(self.input, 1)

        btn = QPushButton("Search")
        btn.setFixedHeight(40)
        btn.setMinimumWidth(100)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(28, 30, 36, 0.85);
                color: {_C['accent']};
                border: 1px solid {_C['border']};
                border-radius: 12px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 22px;
            }}
            QPushButton:hover {{
                background-color: rgba(34, 36, 42, 0.85);
                border-color: rgba(0, 191, 174, 0.4);
            }}
            QPushButton:pressed {{
                background-color: rgba(38, 40, 48, 0.9);
            }}
        """)
        self._shadow(btn, 16, QColor(0, 0, 0, 80))
        btn.clicked.connect(self._on_submit)
        lay.addWidget(btn)

        row.addWidget(container)
        return row

    # ── Dashboard Cards ─────────────────────────────────────────────
    def _dashboard_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(self._make_card(
            "Installed Packages", _C["accent"], "installed_count_label"), 1)
        row.addWidget(self._make_card(
            "Available Updates", "#FF9F43", "updates_count_label"), 1)
        row.addWidget(self._make_card(
            "System Status", "#A29BFE", "sources_count_label"), 1)
        return row

    def _make_card(self, title: str, accent: str,
                   label_attr: str) -> QFrame:
        card = QFrame()
        card.setObjectName("dashCard")
        card.setFixedHeight(124)
        card.setStyleSheet(f"""
            QFrame#dashCard {{
                background-color: {_C['card']};
                border: 1px solid {_C['border']};
                border-radius: 18px;
            }}
            QFrame#dashCard:hover {{
                background-color: {_C['card_hover']};
                border-color: {_hex_to_rgba(accent, 0.33)};
            }}
        """)
        self._shadow(card, 28, QColor(0, 0, 0, 80))

        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        indicator = QFrame()
        indicator.setFixedSize(8, 8)
        indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {accent};
                border-radius: 4px;
            }}
        """)
        hdr.addWidget(indicator)
        hdr.addSpacing(10)

        label = QLabel(title)
        label.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {_C['text_sec']}; background: transparent; letter-spacing: 0.3px;")
        hdr.addWidget(label)

        hdr.addStretch()
        lay.addLayout(hdr)

        val = QLabel("—")
        val.setStyleSheet(
            f"font-size: 36px; font-weight: 700; color: {accent}; background: transparent; "
            f"letter-spacing: -1px;")
        lay.addWidget(val)

        lay.addStretch()

        setattr(self, label_attr, val)
        return card

    # ── Action Buttons ──────────────────────────────────────────────
    def _actions_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        actions = [
            ("discover/updateall.svg", "Update All", self._on_update_all, True),
            ("discover/refreshdb.svg", "Refresh Databases", self._on_refresh, False),
            ("discover/clean.svg", "Clean Cache", self._on_clean, False),
        ]

        for svg_rel, text, cb, primary in actions:
            path = os.path.join(PROJECT_ROOT, "assets", "icons", svg_rel)
            btn = QPushButton(QIcon(path), f"  {text}")
            btn.setIconSize(QSize(17, 17))
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if primary:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(28, 30, 36, 0.85);
                        color: {_C['text']};
                        border: 1px solid rgba(0, 191, 174, 0.3);
                        border-radius: 14px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 28px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(34, 36, 42, 0.85);
                        border-color: {_C['accent']};
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(38, 40, 48, 0.9);
                    }}
                """)
                self._shadow(btn, 18, QColor(0, 0, 0, 80))
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.03);
                        color: {_C['text_sec']};
                        border: 1px solid {_C['border']};
                        border-radius: 14px;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 0 24px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.07);
                        color: {_C['text']};
                        border-color: {_C['border_hover']};
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(255, 255, 255, 0.04);
                    }}
                """)

            btn.clicked.connect(cb)
            row.addWidget(btn)

        row.addStretch()
        return row

    # ── Data ────────────────────────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        if not self.dashboard_timer.isActive():
            self.dashboard_timer.start()
        QTimer.singleShot(300, self._load_system_counts)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.dashboard_timer.stop()

    def _load_system_counts(self):
        installed_count = 0
        try:
            r = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                installed_count = len([l for l in r.stdout.strip().split("\n") if l.strip()])
        except Exception:
            pass

        updates_count = 0
        try:
            r = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                updates_count = len(r.stdout.strip().split("\n"))
        except Exception:
            pass

        sources_count = 1
        for cmd in (["which", "yay", "paru"], ["flatpak", "list"],
                    ["which", "npm"], ["which", "docker"]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    sources_count += 1
            except Exception:
                pass

        self.refresh_counts(
            installed=installed_count,
            updates=updates_count,
            sources=sources_count,
        )

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
