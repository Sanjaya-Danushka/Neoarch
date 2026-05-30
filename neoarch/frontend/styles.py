"""Application stylesheets and theme constants.

Premium dark theme with glassmorphism, subtle transparency,
and modern rounded aesthetics inspired by Arc, Linear, and Raycast.
"""

__all__ = ["Styles", "DARK_STYLESHEET"]

# ── Premium Dark Theme ──────────────────────────────────────────────
_BG = "#0C0C0E"
_SURFACE = "rgba(22, 23, 26, 0.85)"
_CARD = "rgba(28, 30, 36, 0.75)"
_CARD_HOVER = "rgba(34, 36, 42, 0.85)"
_BORDER = "rgba(255, 255, 255, 0.06)"
_BORDER_HOVER = "rgba(255, 255, 255, 0.12)"
_ACCENT = "#00BFAE"
_ACCENT_SOFT = "rgba(0, 191, 174, 0.12)"
_TEXT = "#EDEDEF"
_TEXT_SEC = "#8B8D97"
_TEXT_MUTED = "#5C5E66"

DARK_STYLESHEET = f"""
QMainWindow {{
    background-color: transparent;
    color: {_TEXT};
}}

QWidget#appOuter {{
    background-color: transparent;
}}

QFrame#appWindow {{
    background-color: rgba(12, 12, 14, 0.75);
    border: 1px solid rgba(0, 191, 174, 0.2);
    border-radius: 14px;
}}

/* ── Title Bar ─────────────────────────────────────────────────── */
QWidget#appTitleBar {{
    background-color: transparent;
    border-bottom: 1px solid {_BORDER};
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}}

QLabel#titleBarLabel {{
    color: {_TEXT_SEC};
    font-size: 13px;
    font-weight: 500;
}}

/* ── Traffic Light Controls (macOS style) ──────────────────────── */
QPushButton#titleBarCloseBtn,
QPushButton#titleBarMinBtn,
QPushButton#titleBarMaxBtn {{
    border: none;
    border-radius: 7px;
    font-size: 11px;
    font-weight: 700;
    padding: 0;
}}

/* Close – red */
QPushButton#titleBarCloseBtn {{
    background-color: #FF5F57;
    color: transparent;
}}
QPushButton#titleBarCloseBtn:hover {{
    background-color: #FF5F57;
    color: rgba(80, 20, 20, 0.7);
}}

/* Minimize – yellow */
QPushButton#titleBarMinBtn {{
    background-color: #FEBC2E;
    color: transparent;
}}
QPushButton#titleBarMinBtn:hover {{
    background-color: #FEBC2E;
    color: rgba(120, 80, 10, 0.7);
}}

/* Maximize – green */
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
    color: {_TEXT};
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}}

/* ── Line Edit ─────────────────────────────────────────────────── */
QLineEdit {{
    background-color: rgba(18, 19, 22, 0.9);
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    selection-background-color: {_ACCENT};
}}

QLineEdit:focus {{
    background-color: rgba(20, 21, 24, 0.95);
    border: 1px solid rgba(0, 191, 174, 0.5);
}}

/* ── Push Button ────────────────────────────────────────────────── */
QPushButton {{
    background-color: {_CARD};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {_CARD_HOVER};
    border-color: {_BORDER_HOVER};
}}

QPushButton:pressed {{
    background-color: rgba(38, 40, 48, 0.9);
}}

/* ── Sidebar ────────────────────────────────────────────────────── */
QWidget#sidebar {{
    background-color: rgba(14, 14, 16, 0.95);
    border-right: 1px solid {_BORDER};
}}

QPushButton#sidebarBtn {{
    background-color: transparent;
    border: none;
    color: {_TEXT_SEC};
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
}}

QPushButton#sidebarBtn:hover {{
    background-color: rgba(255, 255, 255, 0.04);
    color: {_TEXT};
}}

QPushButton#sidebarBtn:checked {{
    background-color: rgba(0, 191, 174, 0.1);
    color: {_TEXT};
}}

QWidget#sidebarNavIcon {{
    background-color: transparent;
    font-size: 16px;
    color: {_TEXT_SEC};
}}

QLabel#sidebarLabel {{
    color: {_TEXT_SEC};
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}

QPushButton#sidebarBtn:hover QWidget#sidebarNavIcon {{
    color: {_TEXT};
}}

QPushButton#sidebarBtn:checked QWidget#sidebarNavIcon {{
    color: {_ACCENT};
}}

QLabel#sidebarSection {{
    color: {_TEXT_MUTED};
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 12px 16px 4px 16px;
}}

/* ── Sidebar brand header ───────────────────────────────────────── */
QLabel#sidebarLogo {{
    font-size: 20px;
}}

QLabel#sidebarTitle {{
    color: {_TEXT};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}

QLabel#sidebarSubtitle {{
    color: {_TEXT_SEC};
    font-size: 9px;
    font-weight: 400;
}}

/* ── Nav badge (updates count) ──────────────────────────────────── */
QLabel#navBadge {{
    background-color: {_ACCENT};
    color: #0C0C0E;
    border-radius: 8px;
    padding: 0 6px;
    font-size: 10px;
    font-weight: 700;
    min-width: 16px;
    min-height: 16px;
}}

/* ── Header ─────────────────────────────────────────────────────── */
QFrame#appHeader {{
    background-color: rgba(14, 14, 16, 0.6);
    border-bottom: 1px solid {_BORDER};
}}

QLabel#headerLabel {{
    color: {_TEXT};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#headerInfo {{
    color: {_TEXT_SEC};
    font-size: 12px;
}}

/* ── Table ──────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: rgba(18, 19, 22, 0.8);
    alternate-background-color: rgba(22, 23, 26, 0.5);
    gridline-color: {_BORDER};
    border: 1px solid {_BORDER};
    border-radius: 14px;
    selection-background-color: {_ACCENT_SOFT};
    selection-color: {_TEXT};
}}

QTableWidget::item {{
    padding: 12px 10px;
    border: none;
    border-bottom: 1px solid {_BORDER};
}}

QTableWidget::item:selected {{
    background-color: {_ACCENT_SOFT};
    color: {_TEXT};
}}

QHeaderView::section {{
    background-color: rgba(14, 14, 16, 0.8);
    color: {_TEXT_SEC};
    padding: 10px 10px;
    border: none;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid {_BORDER};
}}

/* ── Text Edit (console) ────────────────────────────────────────── */
QTextEdit {{
    background-color: rgba(14, 14, 16, 0.9);
    color: {_TEXT_SEC};
    border: 1px solid {_BORDER};
    border-radius: 12px;
    font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
}}

/* ── Labels ─────────────────────────────────────────────────────── */
QLabel {{
    color: {_TEXT};
}}

QLabel#sectionLabel {{
    color: {_TEXT_SEC};
    font-size: 10px;
    font-weight: 500;
    background: transparent;
    border: none;
}}

/* ── Frame ──────────────────────────────────────────────────────── */
QFrame {{
    background-color: transparent;
    border: none;
}}

/* ── Checkbox ───────────────────────────────────────────────────── */
QCheckBox {{
    color: {_TEXT};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {_TEXT_MUTED};
    background-color: rgba(18, 19, 22, 0.8);
}}

QCheckBox::indicator:checked {{
    background-color: {_ACCENT};
    border: 1.5px solid {_ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {_ACCENT};
}}

/* ── List ───────────────────────────────────────────────────────── */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item:hover {{
    background-color: {_ACCENT_SOFT};
    border-radius: 8px;
}}

QListWidget::item:selected {{
    background-color: rgba(0, 191, 174, 0.18);
    color: {_ACCENT};
    border-radius: 8px;
}}

/* ── Source chips ───────────────────────────────────────────────── */
QWidget#sourceChip {{
    background-color: {_ACCENT_SOFT};
    border: 1px solid rgba(0, 191, 174, 0.25);
    border-radius: 6px;
}}

QWidget#sourceChip QLabel {{
    color: {_ACCENT};
    font-size: 11px;
    padding: 0 4px;
}}

/* ── Progress Bar ───────────────────────────────────────────────── */
QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background-color: rgba(18, 19, 22, 0.8);
}}

QProgressBar::chunk {{
    background-color: {_ACCENT};
    border-radius: 4px;
}}

/* ── ScrollBar ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(60, 60, 65, 0.5);
    border-radius: 4px;
    min-height: 24px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(80, 80, 85, 0.7);
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
    background: rgba(60, 60, 65, 0.5);
    border-radius: 4px;
    min-width: 24px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(80, 80, 85, 0.7);
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


class Styles:
    """Application styling helpers with premium dark theme."""

    @staticmethod
    def get_dark_stylesheet():
        return DARK_STYLESHEET

    @staticmethod
    def get_card_stylesheet():
        return f"""
            background-color: {_CARD};
            border: 1px solid {_BORDER};
            border-radius: 16px;
        """

    @staticmethod
    def get_glass_stylesheet():
        return f"""
            background-color: rgba(22, 23, 26, 0.6);
            border: 1px solid {_BORDER};
            border-radius: 16px;
        """

    @staticmethod
    def get_header_stylesheet():
        return f"""
            QFrame#appHeader {{
                background-color: rgba(14, 14, 16, 0.6);
                border-bottom: 1px solid {_BORDER};
            }}
        """

    @staticmethod
    def get_filters_panel_stylesheet():
        return f"""
            QFrame {{
                background-color: rgba(12, 12, 14, 0.6);
                border-right: 1px solid {_BORDER};
            }}
        """

    @staticmethod
    def get_separator_stylesheet():
        return f"""
            QFrame {{
                color: {_BORDER};
                background-color: {_BORDER};
                margin: 8px 0;
                max-height: 1px;
            }}
        """

    @staticmethod
    def get_spinner_label_stylesheet():
        return f"""
            QLabel {{
                font-size: 32px;
                color: {_ACCENT};
            }}
        """

    @staticmethod
    def get_accent_button_stylesheet():
        return f"""
            QPushButton {{
                background-color: {_ACCENT};
                color: #0C0C0E;
                border: none;
                border-radius: 10px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #00D4C1;
            }}
            QPushButton:pressed {{
                background-color: #009688;
            }}
        """

    @staticmethod
    def get_ghost_button_stylesheet():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {_TEXT_SEC};
                border: 1px solid {_BORDER};
                border-radius: 10px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.04);
                border-color: {_BORDER_HOVER};
                color: {_TEXT};
            }}
        """

    @staticmethod
    def get_section_title_stylesheet():
        return f"""
            QLabel {{
                color: {_TEXT_SEC};
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.6px;
            }}
        """
