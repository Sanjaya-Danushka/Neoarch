"""Theme definitions for NeoArch.

Each theme is a dict that can be applied to update Colors, Fonts, Radii,
and regenerate QSS blocks.  The current dark theme is the DEFAULT — its
values match the existing tokens.py defaults exactly.
"""

__all__ = ["THEMES", "ThemeManager"]

import json
import os
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal


# ── Theme palette definitions ──────────────────────────────────────

DARK = {
    "name": "Dark",
    "description": "Default premium dark theme",
    "is_dark": True,
    "colors": {
        "BG": "#0C0C0E",
        "BG_SECONDARY": "#191A1F",
        "SURFACE": "#16171A",
        "SURFACE_2": "#1E1F24",
        "SURFACE_3": "#252730",
        "CARD": "#1C1E24",
        "CARD_HOVER": "#22242A",
        "INPUT_BG": "#121316",
        "INPUT_BG_FOCUS": "#141518",
        "SIDEBAR": "#0E0E10",
        "BORDER": "rgba(255, 255, 255, 0.06)",
        "BORDER_INPUT": "rgba(255, 255, 255, 0.08)",
        "BORDER_HOVER": "rgba(255, 255, 255, 0.10)",
        "BORDER_FOCUS": "rgba(0, 191, 174, 0.5)",
        "BORDER_STRONG": "rgba(255, 255, 255, 0.20)",
        "TEXT": "#EDEDEF",
        "TEXT_2": "#8B8D97",
        "TEXT_3": "#5C5E66",
        "TEXT_ON_ACCENT": "#0C0C0E",
        "ACCENT": "#00BFAE",
        "ACCENT_HOVER": "#00D4C1",
        "ACCENT_PRESSED": "#009688",
        "ACCENT_SOFT": "rgba(0, 191, 174, 0.12)",
        "ACCENT_BORDER": "rgba(0, 191, 174, 0.25)",
        "ACCENT_BORDER_STRONG": "rgba(0, 191, 174, 0.35)",
        "WHITE": "#FFFFFF",
        "WHITE_HOVER": "#E8EAF0",
        "WHITE_PRESSED": "#D3D6DE",
        "TEAL": "#00D4AA",
        "ORANGE": "#FF9F1C",
        "PURPLE": "#8B7CFF",
        "BLUE": "#4C9AFF",
        "GREEN": "#22C55E",
        "RED": "#FF6B6B",
        "YELLOW": "#FBBF24",
        "TOAST_INFO": "#4C9AFF",
        "TOAST_SUCCESS": "#22C55E",
        "TOAST_WARNING": "#FF9F1C",
        "TOAST_ERROR": "#FF6B6B",
    },
    "source_colors": {
        "pacman": "#4FC3F7",
        "AUR": "#FF8A65",
        "Flatpak": "#26A69A",
        "npm": "#E53935",
        "Local": "#A3A6B0",
        "Docker": "#2496ED",
        "Brew": "#8B5CF6",
    },
}

LIGHT = {
    "name": "Light",
    "description": "Clean light theme for bright environments",
    "is_dark": False,
    "colors": {
        "BG": "#F5F5F7",
        "BG_SECONDARY": "#ECECEF",
        "SURFACE": "#FFFFFF",
        "SURFACE_2": "#F0F0F2",
        "SURFACE_3": "#E8E8EC",
        "CARD": "#FFFFFF",
        "CARD_HOVER": "#F5F5F7",
        "INPUT_BG": "#F0F0F2",
        "INPUT_BG_FOCUS": "#FFFFFF",
        "SIDEBAR": "#ECECEF",
        "BORDER": "rgba(0, 0, 0, 0.08)",
        "BORDER_INPUT": "rgba(0, 0, 0, 0.12)",
        "BORDER_HOVER": "rgba(0, 0, 0, 0.15)",
        "BORDER_FOCUS": "rgba(0, 150, 136, 0.5)",
        "BORDER_STRONG": "rgba(0, 0, 0, 0.20)",
        "TEXT": "#1A1A2E",
        "TEXT_2": "#6B7280",
        "TEXT_3": "#9CA3AF",
        "TEXT_ON_ACCENT": "#FFFFFF",
        "ACCENT": "#009688",
        "ACCENT_HOVER": "#00796B",
        "ACCENT_PRESSED": "#004D40",
        "ACCENT_SOFT": "rgba(0, 150, 136, 0.10)",
        "ACCENT_BORDER": "rgba(0, 150, 136, 0.25)",
        "ACCENT_BORDER_STRONG": "rgba(0, 150, 136, 0.35)",
        "WHITE": "#FFFFFF",
        "WHITE_HOVER": "#F0F0F2",
        "WHITE_PRESSED": "#E0E0E4",
        "TEAL": "#00897B",
        "ORANGE": "#E65100",
        "PURPLE": "#5C6BC0",
        "BLUE": "#1976D2",
        "GREEN": "#2E7D32",
        "RED": "#D32F2F",
        "YELLOW": "#F9A825",
        "TOAST_INFO": "#1976D2",
        "TOAST_SUCCESS": "#2E7D32",
        "TOAST_WARNING": "#E65100",
        "TOAST_ERROR": "#D32F2F",
    },
    "source_colors": {
        "pacman": "#1976D2",
        "AUR": "#E65100",
        "Flatpak": "#00897B",
        "npm": "#D32F2F",
        "Local": "#6B7280",
        "Docker": "#1565C0",
        "Brew": "#5C6BC0",
    },
}

DRACULA = {
    "name": "Dracula",
    "description": "Popular dark theme with purple accents",
    "is_dark": True,
    "colors": {
        "BG": "#282A36",
        "BG_SECONDARY": "#2E303E",
        "SURFACE": "#343746",
        "SURFACE_2": "#3C3F58",
        "SURFACE_3": "#44475A",
        "CARD": "#343746",
        "CARD_HOVER": "#3C3F58",
        "INPUT_BG": "#2E303E",
        "INPUT_BG_FOCUS": "#343746",
        "SIDEBAR": "#21222C",
        "BORDER": "rgba(255, 255, 255, 0.06)",
        "BORDER_INPUT": "rgba(255, 255, 255, 0.08)",
        "BORDER_HOVER": "rgba(255, 255, 255, 0.10)",
        "BORDER_FOCUS": "rgba(189, 147, 249, 0.5)",
        "BORDER_STRONG": "rgba(255, 255, 255, 0.20)",
        "TEXT": "#F8F8F2",
        "TEXT_2": "#6272A4",
        "TEXT_3": "#44475A",
        "TEXT_ON_ACCENT": "#282A36",
        "ACCENT": "#BD93F9",
        "ACCENT_HOVER": "#CAA8FB",
        "ACCENT_PRESSED": "#A37FDB",
        "ACCENT_SOFT": "rgba(189, 147, 249, 0.12)",
        "ACCENT_BORDER": "rgba(189, 147, 249, 0.25)",
        "ACCENT_BORDER_STRONG": "rgba(189, 147, 249, 0.35)",
        "WHITE": "#FFFFFF",
        "WHITE_HOVER": "#F0F0F2",
        "WHITE_PRESSED": "#D3D6DE",
        "TEAL": "#50FA7B",
        "ORANGE": "#FFB86C",
        "PURPLE": "#BD93F9",
        "BLUE": "#8BE9FD",
        "GREEN": "#50FA7B",
        "RED": "#FF5555",
        "YELLOW": "#F1FA8C",
        "TOAST_INFO": "#8BE9FD",
        "TOAST_SUCCESS": "#50FA7B",
        "TOAST_WARNING": "#FFB86C",
        "TOAST_ERROR": "#FF5555",
    },
    "source_colors": {
        "pacman": "#8BE9FD",
        "AUR": "#FFB86C",
        "Flatpak": "#50FA7B",
        "npm": "#FF5555",
        "Local": "#6272A4",
        "Docker": "#8BE9FD",
        "Brew": "#BD93F9",
    },
}

NORD = {
    "name": "Nord",
    "description": "Arctic blue color palette",
    "is_dark": True,
    "colors": {
        "BG": "#2E3440",
        "BG_SECONDARY": "#3B4252",
        "SURFACE": "#3B4252",
        "SURFACE_2": "#434C5E",
        "SURFACE_3": "#4C566A",
        "CARD": "#3B4252",
        "CARD_HOVER": "#434C5E",
        "INPUT_BG": "#2E3440",
        "INPUT_BG_FOCUS": "#3B4252",
        "SIDEBAR": "#2E3440",
        "BORDER": "rgba(255, 255, 255, 0.06)",
        "BORDER_INPUT": "rgba(255, 255, 255, 0.08)",
        "BORDER_HOVER": "rgba(255, 255, 255, 0.10)",
        "BORDER_FOCUS": "rgba(136, 192, 208, 0.5)",
        "BORDER_STRONG": "rgba(255, 255, 255, 0.20)",
        "TEXT": "#ECEFF4",
        "TEXT_2": "#616E88",
        "TEXT_3": "#4C566A",
        "TEXT_ON_ACCENT": "#2E3440",
        "ACCENT": "#88C0D0",
        "ACCENT_HOVER": "#8FBCBB",
        "ACCENT_PRESSED": "#81A1C1",
        "ACCENT_SOFT": "rgba(136, 192, 208, 0.12)",
        "ACCENT_BORDER": "rgba(136, 192, 208, 0.25)",
        "ACCENT_BORDER_STRONG": "rgba(136, 192, 208, 0.35)",
        "WHITE": "#FFFFFF",
        "WHITE_HOVER": "#ECEFF4",
        "WHITE_PRESSED": "#D8DEE9",
        "TEAL": "#88C0D0",
        "ORANGE": "#D08770",
        "PURPLE": "#B48EAD",
        "BLUE": "#81A1C1",
        "GREEN": "#A3BE8C",
        "RED": "#BF616A",
        "YELLOW": "#EBCB8B",
        "TOAST_INFO": "#81A1C1",
        "TOAST_SUCCESS": "#A3BE8C",
        "TOAST_WARNING": "#D08770",
        "TOAST_ERROR": "#BF616A",
    },
    "source_colors": {
        "pacman": "#81A1C1",
        "AUR": "#D08770",
        "Flatpak": "#A3BE8C",
        "npm": "#BF616A",
        "Local": "#616E88",
        "Docker": "#88C0D0",
        "Brew": "#B48EAD",
    },
}


THEMES = {
    "dark": DARK,
    "light": LIGHT,
    "dracula": DRACULA,
    "nord": NORD,
}


# ── Theme manager ──────────────────────────────────────────────────

class ThemeManager(QObject):
    """Applies themes to the token system and emits change signals."""

    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_id = "dark"
        self._settings_path = os.path.join(
            os.path.expanduser("~"), ".config", "neoarch", "theme.json")

    @property
    def current_id(self):
        return self._current_id

    def apply_theme(self, theme_id):
        """Apply a theme by id. Updates Colors, Fonts, Radii, SourceColors,
        and regenerates QSS blocks."""
        if theme_id not in THEMES:
            return
        theme = THEMES[theme_id]
        self._current_id = theme_id

        from neoarch.frontend import tokens

        # Update Colors
        for key, val in theme["colors"].items():
            if hasattr(tokens.Colors, key):
                setattr(tokens.Colors, key, val)

        # Update SourceColors
        tokens.SourceColors.clear()
        tokens.SourceColors.update(theme["source_colors"])

        # Regenerate QSS blocks
        tokens.QSS._regenerate()

        # Rebuild DARK_STYLESHEET
        tokens.rebuild_stylesheet()

        self._save()
        self.theme_changed.emit(theme_id)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            with open(self._settings_path, "w") as f:
                json.dump({"theme": self._current_id}, f)
        except Exception:
            pass

    def load_saved(self):
        """Load the saved theme from disk."""
        try:
            with open(self._settings_path) as f:
                data = json.load(f)
                theme_id = data.get("theme", "dark")
                if theme_id in THEMES:
                    self.apply_theme(theme_id)
        except Exception:
            pass
