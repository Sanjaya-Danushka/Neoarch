"""Partial-update warning dialog, matching the app's default prompt design.

Shown when the user updates a *selection* of official pacman packages
instead of everything available. AUR packages are intentionally not part
of the check: they build from source against the current system, so they
don't create the library-desync risk a partial official-repo upgrade
does. The dialog never blocks anyone who knows what they are doing — it
makes silent partial upgrades visible, turns the risky choice red, and
offers the recommended full upgrade in one click.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.backend.services.i18n import _
from neoarch.frontend.styles import Styles
from neoarch.frontend.views._settings_kit import btn, icon_pixmap

_ICON_SHIELD = (
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    '<path d="M12 8v4"/><path d="M12 16h.01"/>'
)


def _canonical_name(pkg):
    return (pkg.get("name") or pkg.get("id") or "").strip()


def _selected_official(names):
    """Official (pacman) package names from a packages-by-source map."""
    selected = set()
    for src, pkgs in names.items():
        if (src or "").lower() != "pacman":
            continue
        selected.update(str(n).strip() for n in pkgs if n)
    return selected


def count_selected(total_updates, packages_by_source):
    """Return (selected_count, available_count) for official pacman only.

    Available = every update whose source is the official repos in
    ``total_updates``. AUR rows are excluded because they cannot cause the
    partial-upgrade library desync; they only inflate the numbers.
    """
    available = {
        _canonical_name(p) for p in total_updates
        if (p.get("source") or "").upper() == "PACMAN"
    }
    return len(_selected_official(packages_by_source)), len(available)


def is_partial_update(total_updates, packages_by_source):
    """True when an official pacman selection is smaller than what's left."""
    selected, available = count_selected(total_updates, packages_by_source)
    if not selected or not available:
        return False
    if selected >= available:
        return False
    return True


class PartialUpdateDialog(QDialog):
    """Three-way partial-update prompt: cancel / update all / selection.

    When ``blocked`` is True the "Update Selection" choice is disabled and a
    warning links the user to Settings \u2192 Security, where the guard can be
    turned off. ``on_open_settings`` is invoked when that link is clicked.
    """
    def __init__(self, total_updates, packages_by_source, parent=None,
                 blocked=False, on_open_settings=None):
        super().__init__(parent)
        self.setWindowTitle(_("Partial Update Warning"))
        self.setMinimumWidth(560)
        self.setStyleSheet(
            "QDialog { background-color: rgba(22, 23, 26, 235); }")
        self.choice = None
        self.blocked = blocked
        self.settings_btn = None
        self._on_open_settings = on_open_settings
        self._build(total_updates, packages_by_source)

    def result_choice(self):
        """One of "selection", "all", or None (cancelled)."""
        return self.choice

    def open_settings(self):
        """Close the dialog and hand off to the Security settings page."""
        self.choice = None
        self.reject()
        if self._on_open_settings is not None:
            try:
                self._on_open_settings()
            except Exception:
                pass

    def _build(self, total_updates, packages_by_source):
        selected, available = count_selected(
            total_updates, packages_by_source)
        total_all = len(total_updates)

        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(24, 22, 24, 20)

        heading = QLabel(_("Updating a selection only"))
        heading.setWordWrap(True)
        heading.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        v.addWidget(heading)

        body = QLabel(
            _("You picked {selected} of {available} available updates. On "
              "Arch, packages are built against the latest libraries \u2014 "
              "a partial upgrade can desync libraries from their apps and "
              "break your system.\n\n"
              "It\u2019s recommended to do a full system upgrade instead."
              ).format(selected=selected, available=available))
        body.setWordWrap(True)
        body.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            f" line-height: 150%; background: transparent; border: none;")
        v.addWidget(body)

        if self.blocked:
            v.addWidget(self._block_notice())

        v.addSpacing(6)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()

        cancel_btn = QPushButton(_("Cancel"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.CARD};"
            f" color: {Colors.TEXT}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: {Fonts.BASE}; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {Colors.CARD_HOVER};"
            f" border-color: {Colors.BORDER_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.SURFACE_3}; }}")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        # Uses the existing catalogs across all bundled languages.
        self.selection_btn = QPushButton(
            _("I understand \u2014 Update Selection"))
        self.selection_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.selection_btn.setMinimumHeight(36)
        self.selection_btn.setStyleSheet(Styles.btn_danger())
        if self.blocked:
            self.selection_btn.setEnabled(False)
            self.selection_btn.setToolTip(_(
                "Blocked in Settings \u2192 Security. Turn off "
                "\u201cBlock partial updates\u201d to allow selection-only "
                "upgrades."))

        def _on_selection():
            self.choice = "selection"
            self.accept()
        self.selection_btn.clicked.connect(_on_selection)
        buttons.addWidget(self.selection_btn)

        # Count-only suffix: "Update All (4)" needs no translation, so the
        # button stays translated in every bundled language.
        self.update_all_btn = QPushButton(
            _("Update All") + " ({total})".format(total=total_all))
        self.update_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_all_btn.setMinimumHeight(36)
        self.update_all_btn.setDefault(True)
        self.update_all_btn.setStyleSheet(Styles.btn_white(
            padding="8px 18px", size=Fonts.BASE, radius=10))

        def _on_all():
            self.choice = "all"
            self.accept()
        self.update_all_btn.clicked.connect(_on_all)
        buttons.addWidget(self.update_all_btn)

        v.addLayout(buttons)

    def _block_notice(self):
        """Polished amber callout shown when selection-only updates are blocked."""
        notice = QFrame()
        notice.setObjectName("blockNotice")
        notice.setStyleSheet(
            "QFrame#blockNotice {"
            " background-color: rgba(255, 159, 28, 0.07);"
            " border: 1px solid rgba(255, 159, 28, 0.25);"
            " border-radius: 12px; }")
        h = QHBoxLayout(notice)
        h.setContentsMargins(14, 13, 14, 13)
        h.setSpacing(12)

        badge = QLabel()
        badge.setFixedSize(30, 30)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background: rgba(255, 159, 28, 0.14); border: none;"
            " border-radius: 9px;")
        badge.setPixmap(icon_pixmap(_ICON_SHIELD, 16, color=Colors.ORANGE))
        h.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)

        title = QLabel(_("Partial updates are blocked"))
        title.setStyleSheet(
            f"color: {Colors.ORANGE}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.SEMI}; background: transparent;"
            " border: none;")
        col.addWidget(title)

        body = QLabel(
            _("A selection-only upgrade can desync libraries and break your "
              "system. Turn off \u201cBlock partial updates\u201d in Settings "
              "\u2192 Security to allow it, or use Update All."))
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        col.addWidget(body)

        action = QHBoxLayout()
        action.setContentsMargins(0, 6, 0, 0)
        self.settings_btn = btn(
            _("Open Security settings"), on_click=self.open_settings)
        self.settings_btn.setMaximumWidth(210)
        action.addWidget(self.settings_btn)
        action.addStretch()
        col.addLayout(action)

        h.addLayout(col, 1)
        return notice
