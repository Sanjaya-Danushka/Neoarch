"""Centralized design tokens for NeoArch.

Single source of truth for ALL colors, fonts, spacing, and radius values.
Every component should import from here instead of defining its own tokens.

Supports dynamic theme switching — call QSS._regenerate() after updating
Colors/Fonts/Radii to rebuild all QSS blocks.

Usage:
    from neoarch.frontend.tokens import T, Colors, Fonts, Radii, Spacing, QSS
"""

__all__ = ["T", "Colors", "Fonts", "Radii", "Spacing", "SourceColors", "QSS",
           "DARK_STYLESHEET", "rebuild_stylesheet"]


# ── Core palette ───────────────────────────────────────────────────

class Colors:
    """All color tokens."""

    # Backgrounds (darkest → lightest)
    BG = "#0C0C0E"
    BG_SECONDARY = "#191A1F"
    SURFACE = "#16171A"
    SURFACE_2 = "#1E1F24"
    SURFACE_3 = "#252730"
    CARD = "#1C1E24"
    CARD_HOVER = "#22242A"
    INPUT_BG = "#121316"
    INPUT_BG_FOCUS = "#141518"
    SIDEBAR = "#0E0E10"

    # Borders
    BORDER = "rgba(255, 255, 255, 0.06)"
    BORDER_INPUT = "rgba(255, 255, 255, 0.08)"
    BORDER_HOVER = "rgba(255, 255, 255, 0.10)"
    BORDER_FOCUS = "rgba(0, 191, 174, 0.5)"
    BORDER_STRONG = "rgba(255, 255, 255, 0.20)"

    # Text
    TEXT = "#EDEDEF"
    TEXT_2 = "#8B8D97"
    TEXT_3 = "#5C5E66"
    TEXT_ON_ACCENT = "#0C0C0E"

    # Primary accent
    ACCENT = "#00BFAE"
    ACCENT_HOVER = "#00D4C1"
    ACCENT_PRESSED = "#009688"
    ACCENT_SOFT = "rgba(0, 191, 174, 0.12)"
    ACCENT_BORDER = "rgba(0, 191, 174, 0.25)"
    ACCENT_BORDER_STRONG = "rgba(0, 191, 174, 0.35)"

    # White button (primary action like Clone, Run Container)
    WHITE = "#FFFFFF"
    WHITE_HOVER = "#E8EAF0"
    WHITE_PRESSED = "#D3D6DE"

    # Semantic colors
    TEAL = "#00D4AA"
    ORANGE = "#FF9F1C"
    PURPLE = "#8B7CFF"
    BLUE = "#4C9AFF"
    GREEN = "#22C55E"
    RED = "#FF6B6B"
    YELLOW = "#FBBF24"

    # Source colors (canonical — ONE palette for all sources)
    SRC_PACMAN = "#4FC3F7"
    SRC_AUR = "#FF8A65"
    SRC_FLATPAK = "#26A69A"
    SRC_NPM = "#E53935"
    SRC_LOCAL = "#A3A6B0"
    SRC_DOCKER = "#2496ED"
    SRC_BREW = "#8B5CF6"

    # Toast
    TOAST_INFO = "#4C9AFF"
    TOAST_SUCCESS = "#22C55E"
    TOAST_WARNING = "#FF9F1C"
    TOAST_ERROR = "#FF6B6B"


# ── Source color map ───────────────────────────────────────────────

SourceColors = {
    "pacman": Colors.SRC_PACMAN,
    "AUR": Colors.SRC_AUR,
    "Flatpak": Colors.SRC_FLATPAK,
    "npm": Colors.SRC_NPM,
    "Local": Colors.SRC_LOCAL,
    "Docker": Colors.SRC_DOCKER,
    "Brew": Colors.SRC_BREW,
}


# ── Typography ─────────────────────────────────────────────────────

class Fonts:
    """Font families, sizes, and weights."""

    FAMILY = "'Segoe UI', -apple-system, sans-serif"
    MONO = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"

    # Size scale (px)
    XS = "10px"
    SM = "11px"
    MD = "12px"
    BASE = "13px"
    LG = "14px"
    CARD_TITLE = "15px"
    XL = "16px"
    XXL = "18px"
    HERO = "20px"
    DISPLAY = "24px"
    PAGE_TITLE = "28px"

    # Weights
    REGULAR = "400"
    MEDIUM = "500"
    SEMI = "600"
    BOLD = "700"


# ── Border radius ──────────────────────────────────────────────────

class Radii:
    """Border radius scale (px)."""

    NONE = "0"
    SM = "4"
    CHECKBOX = "5"
    MD = "8"
    LG = "12"
    XL = "14"
    FULL = "9999"


# ── Spacing ────────────────────────────────────────────────────────

class Spacing:
    """Spacing scale (px)."""

    XS = "4"
    SM = "8"
    MD = "12"
    LG = "16"
    XL = "20"
    XXL = "24"
    XXXL = "32"


# ── Shared QSS blocks for settings views ───────────────────────────

def _build_qss():
    """Generate QSS blocks from current Colors/Fonts/Radii values."""
    return {
        "CARD": f"""
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radii.XL}px;
        """,
        "CHECKBOX": f"""
            QCheckBox {{
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {Radii.CHECKBOX}px;
                border: 1.5px solid {Colors.TEXT_3};
                background-color: {Colors.INPUT_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.ACCENT};
                border: 1.5px solid {Colors.ACCENT};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.ACCENT};
            }}
        """,
        "COMBO": f"""
            QComboBox {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 12px;
            }}
            QComboBox:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QComboBox:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Colors.TEXT_2};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE_2};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                selection-background-color: {Colors.ACCENT_SOFT};
                padding: 4px;
            }}
        """,
        "SPINBOX": f"""
            QSpinBox {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 8px;
            }}
            QSpinBox:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QSpinBox:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: transparent;
                border: none;
                width: 16px;
            }}
            QSpinBox::up-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid {Colors.TEXT_2};
            }}
            QSpinBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {Colors.TEXT_2};
            }}
        """,
        "LINEEDIT": f"""
            QLineEdit {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 12px;
            }}
            QLineEdit:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
        """,
        "BTN_OUTLINE": f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT_BORDER_STRONG};
                border-radius: {Radii.MD}px;
                padding: 8px 16px;
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_SOFT};
                border-color: {Colors.ACCENT};
            }}
        """,
        "BTN_GHOST": f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_2};
                border: 1px solid {Colors.BORDER_HOVER};
                border-radius: {Radii.MD}px;
                padding: 8px 16px;
                font-size: {Fonts.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                border-color: {Colors.BORDER_STRONG};
                color: {Colors.TEXT};
            }}
        """,
        "HINT": f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; border: none;",
        "SCROLL_AREA": (
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 3px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"),
    }


class _QSS:
    """Dynamic QSS blocks — call _regenerate() after changing tokens."""

    def _regenerate(self):
        for k, v in _build_qss().items():
            setattr(self, k, v)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        self._regenerate()
        return object.__getattribute__(self, name)


QSS = _QSS()
QSS._regenerate()


# ── Main window stylesheet (rebuilt on theme change) ───────────────

# Window frame effects — runtime-overridden from user settings by
# the main window's apply_window_effects(). Glow border is OFF by
# default because translucent rims can leave artifacts on some
# compositors/GPU drivers.
WINDOW_GLOW = False
WINDOW_RADIUS = 8


def _build_main_stylesheet():
    frame_border = (
        f"border: 1px solid {Colors.ACCENT_SOFT};" if WINDOW_GLOW
        else "border: none;")
    return f"""
QMainWindow {{
    background-color: transparent;
    color: {Colors.TEXT};
}}

QWidget#appOuter {{
    background-color: transparent;
}}

QFrame#appWindow {{
    background-color: rgba(12, 12, 14, 0.75);
    {frame_border}
    border-radius: {WINDOW_RADIUS}px;
}}

QWidget#appTitleBar {{
    background-color: transparent;
    border-bottom: 1px solid {Colors.BORDER};
    border-top-left-radius: {WINDOW_RADIUS}px;
    border-top-right-radius: {WINDOW_RADIUS}px;
}}

QLabel#titleBarLabel {{
    color: {Colors.TEXT_2};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#titleBarCloseBtn,
QPushButton#titleBarMinBtn,
QPushButton#titleBarMaxBtn {{
    border: none;
    border-radius: 7px;
    font-size: 11px;
    font-weight: 700;
    padding: 0;
}}

QPushButton#titleBarCloseBtn {{
    background-color: #FF5F57;
    color: transparent;
}}
QPushButton#titleBarCloseBtn:hover {{
    background-color: #FF5F57;
    color: rgba(80, 20, 20, 0.7);
}}

QPushButton#titleBarMinBtn {{
    background-color: #FEBC2E;
    color: transparent;
}}
QPushButton#titleBarMinBtn:hover {{
    background-color: #FEBC2E;
    color: rgba(120, 80, 10, 0.7);
}}

QPushButton#titleBarMaxBtn {{
    background-color: #29C840;
    color: transparent;
}}
QPushButton#titleBarMaxBtn:hover {{
    background-color: #29C840;
    color: rgba(10, 70, 20, 0.7);
}}

QWidget#appBody {{
    background-color: transparent;
}}

QWidget {{
    background-color: transparent;
    color: {Colors.TEXT};
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}}

QLineEdit {{
    background-color: {Colors.INPUT_BG};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    selection-background-color: {Colors.ACCENT};
}}

QLineEdit:focus {{
    background-color: {Colors.INPUT_BG_FOCUS};
    border: 1px solid {Colors.BORDER_FOCUS};
}}

QPushButton {{
    background-color: {Colors.CARD};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {Colors.CARD_HOVER};
    border-color: {Colors.BORDER_HOVER};
}}

QPushButton:pressed {{
    background-color: {Colors.SURFACE_3};
}}

QPushButton#loadMoreBtn {{
    background-color: {Colors.CARD};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#loadMoreBtn:hover {{
    background-color: {Colors.CARD_HOVER};
    border-color: {Colors.ACCENT};
    color: {Colors.TEXT};
}}

QPushButton#loadMoreBtn:pressed {{
    background-color: {Colors.SURFACE_3};
}}

QWidget#sidebar {{
    background-color: {Colors.SIDEBAR};
    border-right: 1px solid {Colors.BORDER};
}}

QPushButton#sidebarBtn {{
    background-color: transparent;
    border: none;
    color: {Colors.TEXT_2};
    padding: 0;
    text-align: center;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
}}

QPushButton#sidebarBtn:hover {{
    background-color: {Colors.BORDER};
    color: {Colors.TEXT};
}}

QPushButton#sidebarBtn:checked {{
    background-color: {Colors.ACCENT_SOFT};
    color: {Colors.TEXT};
}}

QWidget#sidebarNavIcon {{
    background-color: transparent;
    font-size: 24px;
    color: {Colors.TEXT_2};
}}

QLabel#sidebarLabel {{
    color: {Colors.TEXT_2};
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}

QPushButton#sidebarBtn:hover QWidget#sidebarNavIcon {{
    color: {Colors.TEXT};
}}

QPushButton#sidebarBtn:checked QWidget#sidebarNavIcon {{
    color: {Colors.ACCENT};
}}

QLabel#sidebarSection {{
    color: {Colors.TEXT_3};
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 0;
    max-height: 0;
}}

QLabel#sidebarLogo {{
    font-size: 20px;
}}

QLabel#navBadge {{
    color: {Colors.ACCENT};
    background: transparent;
    font-size: 11px;
    font-weight: 700;
}}

QFrame#appHeader {{
    background-color: {Colors.SIDEBAR};
    border-bottom: 1px solid {Colors.BORDER};
}}

QLabel#headerLabel {{
    color: {Colors.TEXT};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#headerInfo {{
    color: {Colors.TEXT_2};
    font-size: 12px;
}}

QTableWidget {{
    background-color: {Colors.INPUT_BG};
    alternate-background-color: {Colors.SURFACE};
    gridline-color: {Colors.BORDER};
    border: 1px solid {Colors.BORDER};
    border-radius: 14px;
    selection-background-color: {Colors.ACCENT_SOFT};
    selection-color: {Colors.TEXT};
}}

QTableWidget::item {{
    padding: 12px 10px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTableWidget::item:hover {{
    background-color: {Colors.BORDER};
    border-bottom: 1px solid {Colors.ACCENT_SOFT};
}}

QTableWidget::item:selected {{
    background-color: {Colors.ACCENT_SOFT};
    color: {Colors.TEXT};
}}

QTableView#updatesTable {{
    background-color: {Colors.SIDEBAR};
    border: 1px solid {Colors.BORDER};
    border-radius: 14px;
}}

QHeaderView::section {{
    background-color: {Colors.SIDEBAR};
    color: {Colors.TEXT_2};
    padding: 10px 10px;
    border: none;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTextEdit {{
    background-color: {Colors.SIDEBAR};
    color: {Colors.TEXT_2};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
}}

QLabel {{
    color: {Colors.TEXT};
}}

QLabel#sectionLabel {{
    color: {Colors.TEXT_2};
    font-size: 10px;
    font-weight: 500;
    background: transparent;
    border: none;
}}

QFrame {{
    background-color: transparent;
    border: none;
}}

QCheckBox {{
    color: {Colors.TEXT};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {Colors.TEXT_3};
    background-color: {Colors.INPUT_BG};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border: 1.5px solid {Colors.ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}

QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item:hover {{
    background-color: {Colors.ACCENT_SOFT};
    border-radius: 8px;
}}

QListWidget::item:selected {{
    background-color: {Colors.ACCENT};
    color: {Colors.TEXT_ON_ACCENT};
    border-radius: 8px;
}}

QWidget#sourceChip {{
    background-color: {Colors.ACCENT_SOFT};
    border: 1px solid {Colors.ACCENT_BORDER};
    border-radius: 6px;
}}

QWidget#sourceChip QLabel {{
    color: {Colors.ACCENT};
    font-size: 11px;
    padding: 0 4px;
}}

QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background-color: {Colors.INPUT_BG};
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 4px;
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {Colors.TEXT_3};
    border-radius: 4px;
    min-height: 24px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_2};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: transparent;
    height: 0;
}}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
    border: none;
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.TEXT_3};
    border-radius: 4px;
    min-width: 24px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {Colors.TEXT_2};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: transparent;
    width: 0;
}}

QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
    border: none;
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

QScrollArea::corner {{
    background: transparent;
    border: none;
}}
"""


DARK_STYLESHEET = _build_main_stylesheet()


def rebuild_stylesheet():
    """Rebuild DARK_STYLESHEET after a theme change."""
    global DARK_STYLESHEET
    DARK_STYLESHEET = _build_main_stylesheet()


# ── Convenience alias ──────────────────────────────────────────────

class T:
    """Shorthand access to all tokens: T.c, T.f, T.r, T.s"""

    c = Colors
    f = Fonts
    r = Radii
    s = Spacing
    src = SourceColors
