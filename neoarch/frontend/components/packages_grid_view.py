"""PackagesGridView - Card-based grid view alternative to the table."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QCheckBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from neoarch.resources.paths import PROJECT_ROOT

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PackageCard(QFrame):
    """A single package card for the grid view with neumorphic styling."""

    toggled = pyqtSignal(int, bool)

    def __init__(self, pkg: dict, row: int, parent=None):
        super().__init__(parent)
        self.row = row
        self.pkg = pkg
        self.setObjectName("packageCard")
        self.setFixedSize(240, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self._apply_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("cardCheckbox")
        self.checkbox.stateChanged.connect(self._on_check)
        self.checkbox.setStyleSheet("""
            QCheckBox#cardCheckbox::indicator {
                width: 16px; height: 16px; border-radius: 8px;
                border: 2px solid rgba(0, 191, 174, 0.35);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 42, 48, 0.9),
                    stop:1 rgba(28, 30, 36, 0.9));
            }
            QCheckBox#cardCheckbox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00BFAE,
                    stop:1 rgba(0, 95, 87, 1));
                border: 2px solid #00BFAE;
            }
            QCheckBox#cardCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.7);
            }
        """)
        cb_shadow = QGraphicsDropShadowEffect()
        cb_shadow.setBlurRadius(10)
        cb_shadow.setColor(QColor(0, 0, 0, 90))
        cb_shadow.setOffset(2, 2)
        self.checkbox.setGraphicsEffect(cb_shadow)
        top.addWidget(self.checkbox)

        self.name_label = QLabel(self.pkg.get("name", ""))
        f = QFont()
        f.setBold(True)
        f.setPointSize(11)
        self.name_label.setFont(f)
        self.name_label.setStyleSheet("color: #EDEDEF; background: transparent;")
        self.name_label.setWordWrap(True)
        top.addWidget(self.name_label, 1)

        layout.addLayout(top)

        self.id_label = QLabel(self.pkg.get("id", ""))
        self.id_label.setStyleSheet("color: #8B8D97; font-size: 9px; background: transparent;")
        self.id_label.setWordWrap(True)
        layout.addWidget(self.id_label)

        self.version_label = QLabel(self.pkg.get("version", ""))
        self.version_label.setStyleSheet("color: #5C5E66; font-size: 9px; background: transparent;")
        layout.addWidget(self.version_label)

        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.setSpacing(4)

        source = self.pkg.get("source", "")
        source_colors = {
            "pacman": "#4FC3F7",
            "AUR": "#FF8A65",
            "Flatpak": "#26A69A",
            "npm": "#E53935",
        }
        sc = source_colors.get(source, "#00BFAE")
        sc_rgb = QColor(sc)

        badge_container = QFrame()
        badge_container.setObjectName("sourceBadge")
        badge_container.setStyleSheet(f"""
            QFrame#sourceBadge {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba({sc_rgb.red()}, {sc_rgb.green()}, {sc_rgb.blue()}, 0.18),
                    stop:1 rgba({sc_rgb.red()}, {sc_rgb.green()}, {sc_rgb.blue()}, 0.10));
                border: 1px solid rgba({sc_rgb.red()}, {sc_rgb.green()}, {sc_rgb.blue()}, 0.2);
                border-radius: 5px;
                padding: 0px;
            }}
        """)
        badge_layout = QHBoxLayout(badge_container)
        badge_layout.setContentsMargins(5, 1, 5, 1)
        badge_layout.setSpacing(0)
        badge_text = QLabel(source)
        badge_text.setStyleSheet(f"color: {sc}; font-size: 8px; font-weight: 700; background: transparent; letter-spacing: 0.3px;")
        badge_layout.addWidget(badge_text)
        bottom.addWidget(badge_container)

        bottom.addStretch()

        installed = self.pkg.get("installed", False) or self.pkg.get("_installed", False)
        if installed:
            status = QLabel("Installed")
            status.setStyleSheet("color: #10B981; font-size: 8px; font-weight: 700; background: transparent; letter-spacing: 0.2px;")
            bottom.addWidget(status)

        layout.addLayout(bottom)

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#packageCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(34, 36, 42, 0.92),
                    stop:1 rgba(22, 24, 30, 0.92));
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
            QFrame#packageCard:hover {
                border: 1px solid rgba(0, 191, 174, 0.2);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(38, 40, 46, 0.92),
                    stop:1 rgba(26, 28, 34, 0.92));
            }
        """)
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(20)
        s.setColor(QColor(0, 0, 0, 140))
        s.setOffset(3, 4)
        self.setGraphicsEffect(s)

    def _on_check(self, state):
        self.toggled.emit(self.row, state)

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()


class PackagesGridView(QScrollArea):
    """Scrollable grid of package cards with neumorphic styling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setVisible(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.03);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self._container)

        self._cards: list[PackageCard] = []
        self._cols = 3

    def resizeEvent(self, e):
        w = self.viewport().width() - 12
        card_w = 240
        spacing = 14
        self._cols = max(3, (w + spacing) // (card_w + spacing))
        self._relayout()
        super().resizeEvent(e)

    def clear(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

    def add_package(self, pkg: dict, row: int):
        card = PackageCard(pkg, row)
        card.toggled.connect(self._on_card_toggled)
        self._cards.append(card)

    def _on_card_toggled(self, row: int, state: int):
        pass

    def _relayout(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
        if not self._cards:
            return
        for i, card in enumerate(self._cards):
            r, c = divmod(i, self._cols)
            self._grid.addWidget(card, r, c)

    def populate(self, packages: list[dict]):
        self.clear()
        for i, pkg in enumerate(packages):
            self.add_package(pkg, i)
        self._relayout()

    def get_checked_rows(self) -> list[int]:
        return [c.row for c in self._cards if c.is_checked()]

    def get_checked_packages(self) -> list[dict]:
        return [c.pkg for c in self._cards if c.is_checked()]
