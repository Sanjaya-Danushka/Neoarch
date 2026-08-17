"""Application stylesheets and theme constants.

Re-exports DARK_STYLESHEET from tokens.py (which is rebuilt on theme change).
The Styles class provides convenience methods for common QSS patterns.
"""

__all__ = ["Styles", "DARK_STYLESHEET"]

from neoarch.frontend.tokens import DARK_STYLESHEET, Colors, Radii


class Styles:
    """Application styling helpers — reads live token values."""

    @staticmethod
    def get_dark_stylesheet():
        from neoarch.frontend.tokens import DARK_STYLESHEET as ds
        return ds

    @staticmethod
    def get_card_stylesheet():
        return f"""
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radii.XL}px;
        """

    @staticmethod
    def get_glass_stylesheet():
        return f"""
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radii.XL}px;
        """

    @staticmethod
    def get_header_stylesheet():
        return f"""
            QFrame#appHeader {{
                background-color: {Colors.SIDEBAR};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """

    @staticmethod
    def get_filters_panel_stylesheet():
        return f"""
            QFrame {{
                background-color: {Colors.BG};
                border-right: 1px solid {Colors.BORDER};
            }}
        """

    @staticmethod
    def get_separator_stylesheet():
        return f"""
            QFrame {{
                color: {Colors.BORDER};
                background-color: {Colors.BORDER};
                margin: 8px 0;
                max-height: 1px;
            }}
        """

    @staticmethod
    def get_spinner_label_stylesheet():
        return f"""
            QLabel {{
                font-size: 32px;
                color: {Colors.ACCENT};
            }}
        """

    @staticmethod
    def get_accent_button_stylesheet():
        return f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
                border-radius: 10px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.ACCENT_PRESSED};
            }}
        """

    @staticmethod
    def get_ghost_button_stylesheet():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_2};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                border-color: {Colors.BORDER_HOVER};
                color: {Colors.TEXT};
            }}
        """

    @staticmethod
    def get_section_title_stylesheet():
        return f"""
            QLabel {{
                color: {Colors.TEXT_2};
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.6px;
            }}
        """

    @staticmethod
    def get_load_more_button_stylesheet():
        return f"""
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
        """
