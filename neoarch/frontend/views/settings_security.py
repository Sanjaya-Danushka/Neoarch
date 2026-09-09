from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QFrame, QGridLayout, QSizePolicy)

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.about_tab import (
    _card, _mac_icon_pixmap, _accent_btn, _open_url,
)


# ── Security page ───────────────────────────────────────────────────
#
# A safety dashboard ("warning page"): alert hero, posture status bar,
# and an aligned 3x2 grid of alert tiles with per-tile tags. Amber pulls
# attention where it matters (AUR, partial updates); green marks
# safe-by-design areas (sudo prompt). One glance = the page's posture.


# Monochrome stroke icons (24x24 viewBox)
_ICON_SHIELD = (
    '<path d="M12 2l7 3v6c0 4.97-3.13 8.94-7 10-3.87-1.06-7-5.03-7-10V5l7-3z"/>'
    '<path d="m9 12 2 2 4-4"/>'
)
_ICON_ALERT = (
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16'
    'a2 2 0 0 0 1.73-3z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'
)
_ICON_ARROW = (
    '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 3.5-3.5 3.5 3.5"/>'
    '<path d="M12 15V9"/>'
)
_ICON_LAYERS = (
    '<path d="m12 2 10 6.5L12 15 2 8.5 12 2z"/><path d="m2 12.5 10 6.5 10-6.5"/>'
)
_ICON_KEY = (
    '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 8.3-8.3"/><path d="m15 8 3 3"/>'
)
_ICON_PACKAGE = (
    '<path d="M21 8l-9-5-9 5v8l9 5 9-5V8z"/><path d="M3 8l9 5 9-5"/>'
    '<path d="M12 13v8"/>'
)

_AMBER = Colors.ORANGE
_GREEN = Colors.GREEN
_LINK = "https://aur.archlinux.org"

_TILE_QSS = (
    "QFrame#secTile {{ background-color: #17181D;"
    " border: 1px solid {border}; border-radius: {radius}px; }}"
    "QFrame#secTile:hover {{ border: 1px solid rgba(255, 159, 28, 0.32);"
    " background-color: #1A1B21; }}"
).format(border=Colors.BORDER, radius=Radii.MD)

_TILE_WARN_QSS = (
    "QFrame#secTile {{ background-color: #17181D;"
    " border: 1px solid {border}; border-left: 3px solid {amber};"
    " border-radius: {radius}px; }}"
    "QFrame#secTile:hover {{ border-color: rgba(255, 159, 28, 0.32);"
    " background-color: #1A1B21; }}"
).format(border=Colors.BORDER, amber=_AMBER, radius=Radii.MD)


class SecuritySettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)

        self.setup_ui()

    # ── Hero ───────────────────────────────────────────────────────

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
        badge.setPixmap(_mac_icon_pixmap(_ICON_SHIELD, 28, _AMBER))
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
            f"font-size: {Fonts.HERO}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        title_col.addWidget(name)
        sub = QLabel(_("What NeoArch can reach, what it runs, and what it asks before it acts"))
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " background: transparent; border: none;")
        title_col.addWidget(sub)
        hl.addLayout(title_col, 1)

        cap = QLabel(_("WARNED · NOT BLOCKED"))
        cap.setStyleSheet(
            f"font-size: {Fonts.XS}; font-weight: {Fonts.BOLD}; letter-spacing: 1.2px;"
            f" color: {_AMBER}; background-color: rgba(255, 159, 28, 0.10);"
            f" padding: 5px 10px; border-radius: {Radii.FULL}px;")
        hl.addWidget(cap, 0, Qt.AlignmentFlag.AlignTop)

        return hero

    # ── Status bar ─────────────────────────────────────────────────

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
            dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
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

    # ── Alert tile ─────────────────────────────────────────────────

    def _tile(self, icon, accent, title, tag, lines, warn=False):
        cell = QFrame()
        cell.setObjectName("secTile")
        cell.setStyleSheet(_TILE_WARN_QSS if warn else _TILE_QSS)
        cell.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        cl = QVBoxLayout(cell)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)

        ic = QLabel()
        ic.setPixmap(_mac_icon_pixmap(icon, 16, accent))
        ic.setFixedSize(16, 16)
        head.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)

        t = QLabel(title)
        t.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        head.addWidget(t, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch()

        pill = QLabel(tag)
        pill.setStyleSheet(
            f"font-size: {Fonts.XS}; font-weight: {Fonts.BOLD};"
            f" letter-spacing: 0.8px; color: {accent};"
            f" background-color: rgba(255, 255, 255, 0.05);"
            f" padding: 2px 8px; border-radius: {Radii.FULL}px;")
        head.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)

        cl.addLayout(head)

        for line in lines:
            if isinstance(line, tuple):
                text, line_color = line
            else:
                text, line_color = line, Colors.TEXT_2
            row = QHBoxLayout()
            row.setSpacing(8)
            l = QLabel(text)
            l.setWordWrap(True)
            l.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {line_color};"
                " background: transparent; border: none; line-height: 150%;")
            row.addWidget(l, 1, Qt.AlignmentFlag.AlignTop)
            cl.addLayout(row)

        return cell

    # ── Page ───────────────────────────────────────────────────────

    def setup_ui(self):
        self.layout.addWidget(self._hero())
        self.layout.addWidget(self._status_bar())

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._tile(
            _ICON_PACKAGE, _AMBER, _("AUR — Arch User Repository"), _("COMMUNITY"), [
                (_("Community-maintained recipes — not curated or reviewed by Arch."), Colors.TEXT),
                (_("Every result is badged [aur] \u2014 never confused with official."), Colors.TEXT_2),
                (_("Updates build one at a time; a failure never aborts the rest."), Colors.TEXT_2),
                (_("Helper: auto \u2014 yay, paru, trizen, pikaur (General)."), Colors.TEXT_2),
            ]), 0, 0)

        grid.addWidget(self._tile(
            _ICON_ALERT, _AMBER, _("Partial upgrades"), _("WARNING"), [
                (_("Rolling release \u2014 packages expect to update together."), Colors.TEXT_2),
                (_("Updating a selection can desync libraries from their apps."), Colors.TEXT_2),
                (_("NeoArch warns \u201cfull system upgrade recommended\u201d, then lets you proceed."), _AMBER),
            ], warn=True), 0, 1)

        grid.addWidget(self._tile(
            _ICON_ARROW, _GREEN, _("Update review"), _("SAFE"), [
                (_("Package count and version changes are shown first."), Colors.TEXT_2),
                (_("Nothing starts until you confirm \u2014 never silently."), Colors.GREEN),
            ]), 1, 0)

        grid.addWidget(self._tile(
            _ICON_LAYERS, _AMBER, _("Package sources"), _("SOURCES"), [
                (_("Official: core / extra / multilib via pacman."), Colors.TEXT_2),
                (_("Chaotic-AUR: automatic through pacman.conf."), Colors.TEAL),
                (_("Flatpak sandboxed \u00b7 npm user mode."), Colors.TEXT_2),
            ]), 1, 1)

        grid.addWidget(self._tile(
            _ICON_KEY, _GREEN, _("Credentials & sudo"), _("PROTECTED"), [
                (_("GUI sudo prompt (SUDO_ASKPASS) \u2014 never stored."), Colors.GREEN),
                (_("OAuth tokens cached with an expiry."), Colors.TEXT_2),
                (_("Config in ~/.config/neoarch."), Colors.TEXT_2),
            ]), 2, 0)

        grid.addWidget(self._tile(
            _ICON_SHIELD, _AMBER, _("Healthy-system checklist"), _("HABITS"), [
                (_("Prefer official repos over AUR when both exist."), Colors.TEXT_2),
                (_("Read PKGBUILDs before installing AUR packages."), Colors.TEXT_2),
                (_("Prefer full upgrades \u2014 keep IgnorePkg minimal."), Colors.TEXT_2),
                (_("Clean orphans, cache, and read Arch news."), Colors.TEXT_2),
            ]), 2, 1)

        self.layout.addLayout(grid)

        link_card = _card()
        link_card.setStyleSheet(
            "QFrame { background-color: #17181D;"
            f" border: 1px solid {Colors.BORDER};"
            f" border-radius: {Radii.MD}px; }}")
        ll = QHBoxLayout(link_card)
        ll.setContentsMargins(16, 12, 16, 12)
        ll.setSpacing(12)

        lab = QLabel(_("Before installing from the AUR, review the PKGBUILD."))
        lab.setStyleSheet(
            f"font-size: {Fonts.MD}; color: {Colors.TEXT};"
            " background: transparent; border: none;")
        ll.addWidget(lab, 1)

        ll.addWidget(_accent_btn(_("Open aur.archlinux.org \u2197"),
                                 lambda: _open_url(_LINK)))

        self.layout.addWidget(link_card)
        self.layout.addStretch()