import os
import webbrowser
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QFrame)

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.backend.services.i18n import _
from neoarch.frontend.views._settings_kit import make_card, row, sep, btn

_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_LOGO_SVG = os.path.normpath(os.path.join(_BASE, "assets", "icons", "toolbar", "security.svg"))

_ICON_SHIELD = (
    '<path d="M12 2l7 3v6c0 4.97-3.13 8.94-7 10-3.87-1.06-7-5.03-7-10V5l7-3z"/>'
    '<path d="m9 12 2 2 4-4"/>'
)


def _logo_pixmap(size=28):
    try:
        r = QSvgRenderer(_LOGO_SVG)
        if not r.isValid():
            raise RuntimeError
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r.render(p, QRectF(0, 0, size, size))
        p.end()
        return pm
    except Exception:
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        return pm

_ICON_SHIELD = (
    '<path d="M12 2l7 3v6c0 4.97-3.13 8.94-7 10-3.87-1.06-7-5.03-7-10V5l7-3z"/>'
    '<path d="m9 12 2 2 4-4"/>'
)
_ICON_ARROW = (
    '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 3.5-3.5 3.5 3.5"/>'
    '<path d="M12 15V9"/>'
)
_ICON_KEY = (
    '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 8.3-8.3"/>'
    '<path d="m15 8 3 3"/>'
)
_ICON_PACKAGE = (
    '<path d="M21 8l-9-5-9 5v8l9 5 9-5V8z"/><path d="M3 8l9 5 9-5"/>'
    '<path d="M12 13v8"/>'
)

_AMBER = Colors.ORANGE
_GREEN = Colors.GREEN
_LINK = "https://aur.archlinux.org"


class SecuritySettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)

        self.setup_ui()

    # ── Hero (amber warning banner) ─────────────────────────────────

    def _hero(self):
        hero = QFrame()
        hero.setStyleSheet(
            f"background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 #1C1613, stop:0.55 #121013, stop:1 #101014);"
            f" border: 1px solid rgba(255, 159, 28, 0.22);"
            f" border-radius: {Radii.LG}px;")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.setSpacing(18)

        badge = QLabel()
        badge.setFixedSize(54, 54)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background-color: rgba(255, 159, 28, 0.12);"
            f" border: 1px solid rgba(255, 159, 28, 0.35);"
            f" border-radius: {Radii.LG}px;")
        badge.setPixmap(_logo_pixmap(36))
        hl.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        micro = QLabel(_("SAFETY OVERVIEW"))
        micro.setStyleSheet(
            f"font-size: {Fonts.XS}; font-weight: {Fonts.BOLD};"
            f" letter-spacing: 2px; color: {_AMBER};"
            " background: transparent; border: none;")
        title_col.addWidget(micro)
        name = QLabel(_("Security"))
        name.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        title_col.addWidget(name)
        hl.addLayout(title_col, 1)

        cap = QLabel(_("WARNED · NOT BLOCKED"))
        cap.setStyleSheet(
            f"font-size: {Fonts.XS}; font-weight: {Fonts.BOLD};"
            f" letter-spacing: 1.2px; color: {_AMBER};"
            f" background-color: rgba(255, 159, 28, 0.10);"
            f" padding: 5px 10px; border-radius: {Radii.FULL}px;")
        hl.addWidget(cap, 0, Qt.AlignmentFlag.AlignTop)

        return hero

    # ── Status bar (horizontal chips) ───────────────────────────────

    def _status_bar(self):
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)

        chips = [
            ("AUR", _("Community recipes"), _AMBER),
            ("Partial updates", _("Warned, not blocked"), _AMBER),
            ("Sudo", _("Prompt only, never stored"), _GREEN),
        ]
        for value, sub, color in chips:
            chip = QFrame()
            chip.setStyleSheet(
                f"QFrame {{ background-color: #17181D;"
                f" border: 1px solid {Colors.BORDER};"
                f" border-radius: {Radii.MD}px; }}")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(10)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background-color: {color}; border-radius: 4px;")
            cl.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(1)
            v = QLabel(value)
            v.setStyleSheet(
                f"font-size: {Fonts.MD}; font-weight: {Fonts.SEMI};"
                f" color: {Colors.TEXT}; background: transparent; border: none;")
            col.addWidget(v)
            s = QLabel(sub)
            s.setStyleSheet(
                f"font-size: {Fonts.XS}; color: {Colors.TEXT_3};"
                " background: transparent; border: none;")
            col.addWidget(s)
            cl.addLayout(col, 1)
            bl.addWidget(chip, 1)

        return bar

    # ── Sources & Community card ─────────────────────────────────────

    def _sources_card(self):
        card, lay = make_card(
            _("Sources & Community Packages"), _ICON_PACKAGE)

        aur_row = row(_("AUR — Arch User Repository"),
                      _("Community-maintained recipes — not curated or reviewed by Arch."),
                      subtitle_color=Colors.TEXT)
        lay.addWidget(aur_row)
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Every result is badged [aur] \u2014 never confused with official.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Updates build one at a time;"
              " a failure never aborts the rest.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Helper: auto \u2014 yay, paru, trizen, pikaur (General).")))

        return card

    # ── Updates card ─────────────────────────────────────────────────

    def _updates_card(self):
        card, lay = make_card(_("Updates & Review"), _ICON_ARROW)

        partial_row = row(_("Partial upgrades"),
                          _("Rolling release — packages expect to update together."))
        lay.addWidget(partial_row)
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Updating a selection can desync libraries from their apps."),
            subtitle_color=_AMBER))
        lay.addWidget(sep())
        lay.addWidget(row(
            _('NeoArch warns \u201cfull system upgrade recommended\u201d,'
              ' then lets you proceed.'),
            subtitle_color=_AMBER))
        lay.addWidget(sep())

        review_row = row(_("Update review"),
                         _("Package count and version changes are shown first."))
        lay.addWidget(review_row)
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Nothing starts until you confirm \u2014 never silently."),
            subtitle_color=Colors.GREEN))

        return card

    # ── System protection card ───────────────────────────────────────

    def _protection_card(self):
        card, lay = make_card(
            _("System Protection & Habits"), _ICON_KEY, icon_color=_GREEN)

        lay.addWidget(row(
            _("GUI sudo prompt (SUDO_ASKPASS) \u2014 never stored."),
            subtitle_color=Colors.GREEN))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("OAuth tokens cached with an expiry.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Config in ~/.config/neoarch.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Read PKGBUILDs before installing AUR packages.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Prefer full upgrades \u2014 keep IgnorePkg minimal.")))
        lay.addWidget(sep())
        lay.addWidget(row(
            _("Clean orphans, cache, and read Arch news.")))

        return card

    # ── Link card ────────────────────────────────────────────────────

    def _link_card(self):
        card, lay = make_card(_("AUR Resources"), _ICON_PACKAGE)
        lay.addWidget(row(
            _("Before installing from the AUR, review the PKGBUILD.")))
        open_btn = btn(
            _("Open aur.archlinux.org \u2197"),
            on_click=lambda: webbrowser.open(_LINK))
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 6, 0, 0)
        btn_lay.addWidget(open_btn)
        btn_lay.addStretch()
        lay.addWidget(btn_row)
        return card

    # ── Page ─────────────────────────────────────────────────────────

    def setup_ui(self):
        title = QLabel(_("Security"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(
            _("What NeoArch can reach, what it runs,"
              " and what it asks before it acts"))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        self.layout.addWidget(subtitle)

        self.layout.addWidget(self._hero())
        self.layout.addWidget(self._status_bar())
        self.layout.addWidget(self._sources_card())
        self.layout.addWidget(self._updates_card())
        self.layout.addWidget(self._protection_card())
        self.layout.addWidget(self._link_card())