"""Application stylesheets and theme constants.

Re-exports DARK_STYLESHEET from tokens.py (which is rebuilt on theme change).
"""

__all__ = ["Styles", "DARK_STYLESHEET"]

from neoarch.frontend.tokens import DARK_STYLESHEET


class Styles:
    """Application styling helpers — reads live token values."""

    @staticmethod
    def get_dark_stylesheet():
        from neoarch.frontend.tokens import DARK_STYLESHEET as ds
        return ds
