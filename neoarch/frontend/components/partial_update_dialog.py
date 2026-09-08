"""Partial-update warning dialog, matching the app's default prompt design.

Shown when the user updates a *selection* on Arch-backed sources instead of
everything. It never blocks anyone who knows what they are doing: it just
makes silent partial upgrades visible and asks for explicit confirmation.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)

from neoarch.frontend.tokens import Colors, Fonts


def count_selected(total_updates, packages_by_source):
    """Return (selected_count, available_count) for Arch-backed sources.

    Available = every update whose source is pacman/AUR in ``total_updates``.
    Selecting these acks is meaningful even if ``total_updates`` holds extra
    non-Arch rows (flatpak/npm), which a partial upgrade does not risk.
    """
    available = {
        (p.get("name") or p.get("id") or "").strip()
        for p in total_updates
        if (p.get("source") or "").upper() in ("PACMAN", "AUR")
    }
    selected = set()
    for src in ("pacman", "AUR"):
        selected.update(
            str(n).strip() for n in packages_by_source.get(src, []) if n)
    return len(selected), len(available)


def is_partial_update(total_updates, packages_by_source):
    """True when an Arch selection is smaller than the full available set."""
    selected, available = count_selected(total_updates, packages_by_source)
    if not selected or not available:
        return False
    if selected >= available:
        return False
    return True


class PartialUpdateDialog(QDialog):
    def __init__(self, total_updates, packages_by_source, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Partial Update Warning")
        self.setMinimumWidth(540)
        self.setStyleSheet(
            f"QDialog {{ background-color: rgba(22, 23, 26, 235); }}")
        self._build(total_updates, packages_by_source)

    def _build(self, total_updates, packages_by_source):
        selected, available = count_selected(total_updates, packages_by_source)

        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(24, 22, 24, 20)

        heading = QLabel("Updating a selection only")
        heading.setWordWrap(True)
        heading.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        v.addWidget(heading)

        body = QLabel(
            f"You picked {selected} of {available} available updates. "
            "On Arch, packages are built against the latest libraries \u2014 "
            "a partial upgrade can desync libraries from their apps and "
            "break your system.\n\n"
            "It\u2019s recommended to do a full system upgrade instead.")
        body.setWordWrap(True)
        body.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            f" line-height: 150%; background: transparent; border: none;")
        v.addWidget(body)

        v.addSpacing(6)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.CARD};"
            f" color: {Colors.TEXT}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: 13px; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {Colors.CARD_HOVER};"
            f" border-color: {Colors.BORDER_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.SURFACE_3}; }}")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("I understand \u2014 Update Selection")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setMinimumHeight(36)
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setMinimumWidth(170)
        self.confirm_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.WHITE};"
            f" color: {Colors.TEXT_ON_ACCENT};"
            f" border: 1px solid rgba(255, 255, 255, 0.9);"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.WHITE_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.WHITE_PRESSED}; }}")
        self.confirm_btn.clicked.connect(self.accept)
        buttons.addWidget(self.confirm_btn)

        v.addLayout(buttons)