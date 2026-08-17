"""Appearance settings — theme selector with live preview."""

from typing import Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.frontend.themes import THEMES


class _ThemePreview(QFrame):
    """Small color swatch preview of a theme."""

    def __init__(self, theme_data, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 100)
        self._c = theme_data["colors"]
        self._is_dark = theme_data["is_dark"]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        bg = QColor(self._c["BG"])
        p.fillRect(0, 0, w, h, bg)

        # Sidebar strip
        sidebar = QColor(self._c["SIDEBAR"])
        p.fillRect(0, 0, 28, h, sidebar)

        # Card
        card = QColor(self._c["SURFACE"])
        border = QColor(self._c["BORDER"])
        p.setPen(QPen(border, 1))
        p.setBrush(card)
        p.drawRoundedRect(36, 8, w - 44, h - 16, 6, 6)

        # Accent dot
        accent = QColor(self._c["ACCENT"])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawEllipse(48, 20, 10, 10)

        # Text lines
        text = QColor(self._c["TEXT"])
        text2 = QColor(self._c["TEXT_2"])
        p.setBrush(text)
        p.drawRect(64, 22, 50, 4)
        p.setBrush(text2)
        p.drawRect(64, 32, 35, 3)
        p.drawRect(48, 46, w - 60, 3)
        p.drawRect(48, 54, w - 70, 3)
        p.drawRect(48, 62, w - 80, 3)

        # Sidebar nav items
        p.setBrush(accent)
        p.drawRoundedRect(4, 16, 20, 4, 2, 2)
        p.setBrush(text2)
        p.drawRoundedRect(4, 28, 20, 4, 2, 2)
        p.drawRoundedRect(4, 40, 20, 4, 2, 2)

        p.end()


class _ThemeCard(QFrame):
    """Clickable theme card with preview and label."""

    def __init__(self, theme_id, theme_data, is_selected, on_select, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self._on_select = on_select
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 2px solid {Colors.ACCENT if is_selected else Colors.BORDER};
                border-radius: {Radii.XL}px;
            }}
            QFrame:hover {{
                border-color: {Colors.ACCENT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Preview
        preview = _ThemePreview(theme_data)
        layout.addWidget(preview)

        # Label row
        label_row = QHBoxLayout()
        name = QLabel(theme_data["name"])
        name.setStyleSheet(f"""
            color: {Colors.TEXT}; font-size: {Fonts.BASE};
            font-weight: {Fonts.SEMI}; border: none;
        """)
        label_row.addWidget(name)

        if is_selected:
            badge = QLabel("Active")
            badge.setStyleSheet(f"""
                color: {Colors.ACCENT}; font-size: {Fonts.SM};
                font-weight: {Fonts.SEMI}; border: none;
            """)
            label_row.addWidget(badge)

        label_row.addStretch()
        layout.addLayout(label_row)

        desc = QLabel(theme_data["description"])
        desc.setStyleSheet(f"""
            color: {Colors.TEXT_2}; font-size: {Fonts.SM}; border: none;
        """)
        layout.addWidget(desc)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_select(self.theme_id)


class AppearanceSettingsWidget(QWidget):
    """Appearance settings with theme selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self._cards = {}
        self.setup_ui()

    def setup_ui(self):
        title = QLabel("Appearance")
        title.setStyleSheet(f"""
            font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};
            color: {Colors.TEXT}; letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)

        subtitle = QLabel("Choose a theme for NeoArch. Changes apply instantly.")
        subtitle.setStyleSheet(f"""
            font-size: {Fonts.BASE}; color: {Colors.TEXT_2};
            margin-top: -16px;
        """)
        self.layout.addWidget(subtitle)

        # Theme grid
        grid = QHBoxLayout()
        grid.setSpacing(16)

        current = getattr(self.app, '_theme_manager', None)
        current_id = current.current_id if current else "dark"

        for theme_id, theme_data in THEMES.items():
            card = _ThemeCard(
                theme_id, theme_data,
                is_selected=(theme_id == current_id),
                on_select=self._apply_theme,
            )
            self._cards[theme_id] = card
            grid.addWidget(card)

        grid.addStretch()
        self.layout.addLayout(grid)
        self.layout.addStretch()

    def _apply_theme(self, theme_id):
        manager = getattr(self.app, '_theme_manager', None)
        if manager:
            manager.apply_theme(theme_id)
            # Rebuild settings UI to reflect new theme
            self.app.build_settings_ui()

    def refresh_theme(self):
        """Rebuild cards to update selection state."""
        # Clear and rebuild
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        self.setup_ui()
