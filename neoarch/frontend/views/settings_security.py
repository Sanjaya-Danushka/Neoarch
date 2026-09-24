"""Security settings page — education first.

Explains what NeoArch can reach, what it runs, how it protects secrets,
and the habits that keep an Arch system healthy. NeoArch is a *warning*
oriented app: it flags risky actions but rarely blocks them, so this page
spells out the "why" behind every guardrail as a set of Do's and Don'ts.
"""

import webbrowser

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.backend.services.i18n import _
from neoarch.frontend.views._settings_kit import (
    make_card, row, sep, btn, actions_row, chip, advice)

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_BOX = (
    '<path d="M21 8l-9-5-9 5v8l9 5 9-5V8z"/><path d="M3 8l9 5 9-5"/>'
    '<path d="M12 13v8"/>'
)
_ICON_UPDATE = (
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
    '<polyline points="17 6 23 6 23 12"/>'
)
_ICON_HABITS = (
    '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/>'
    '<path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>'
)
_ICON_KEY = (
    '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 8.3-8.3"/>'
    '<path d="m15 8 3 3"/>'
)

_AMBER = Colors.ORANGE
_GREEN = Colors.GREEN


def _warned_row(title, desc):
    """Row with an amber WARNED chip — the 'flagged but not blocked' look."""
    return row(title, desc, subtitle_color=_AMBER,
               control=chip(_("WARNED"), _AMBER))


# ── Cards ───────────────────────────────────────────────────────────

def _sources_card():
    card, lay = make_card(
        _("Sources & Community Packages"), _ICON_BOX)

    lay.addWidget(row(
        _("AUR — Arch User Repository"),
        _("Community-maintained build recipes. Unlike the official repos "
          "they are not curated or reviewed by Arch — anyone can publish "
          "a recipe.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Every AUR result is badged [aur]"),
        _("The source column always shows where a package comes from, "
          "so community packages are never mistaken for official ones.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("One-at-a-time builds"),
        _("AUR updates build one package at a time; a single failure "
          "never aborts the rest of the queue.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("AUR helper: auto"),
        _("Resolved automatically to yay, paru, trizen or pikaur. "
          "Change it under General settings.")))

    return card


def _updates_card():
    card, lay = make_card(_("Updates & Review"), _ICON_UPDATE)

    lay.addWidget(_warned_row(
        _("Warned, not blocked"),
        _("NeoArch never quietly blocks an action. Risky moves get a "
          "warning and your explicit confirmation \u2014 you always hold "
          "the final say.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Full upgrades are the safe path"),
        _("Arch is a rolling release: packages expect to move forward "
          "together. Updating a selection can desync libraries from the "
          "apps that use them."),
        subtitle_color=Colors.GREEN))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Review before installing"),
        _("Package count and version changes are shown first; nothing "
          "starts until you press confirm \u2014 never silently."),
        subtitle_color=Colors.GREEN))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Optional snapshots"),
        _("Enable \u201cSnapshot before update\u201d in General settings "
          "so a bad upgrade can be reverted in one click.")))

    return card


def _advice_card():
    card, lay = make_card(
        _("Quick Reference \u2014 Do's & Don'ts"), _ICON_HABITS,
        icon_color=_AMBER)

    lay.addWidget(advice(
        "do",
        _("Update everything together"),
        _("A full system upgrade keeps libraries and applications in "
          "lockstep \u2014 the Arch-supported way to stay current.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "do",
        _("Read the PKGBUILD before installing from the AUR"),
        _("NeoArch fetches and statically scans recipes first and pauses "
          "on critical findings. Read the whole file anyway.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "do",
        _("Keep IgnorePkg minimal"),
        _("A pinned version quietly freezes the packages that depend on "
          "it. If you must pin, review it regularly.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "do",
        _("Housekeep: orphans, cache, Arch news"),
        _("Drop orphaned packages, prune the cache, and read the "
          "archlinux.org news before major upgrades.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "dont",
        _("Partial upgrades"),
        _("Mixing old and new packages desyncs libraries from the apps "
          "that link them \u2014 the classic broken-Arch setup.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "dont",
        _("Install AUR packages blindly"),
        _("Anyone can publish a recipe. Skipping the review means "
          "trusting a stranger's build script with your machine.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "dont",
        _("Ignore the full-upgrade warning"),
        _("NeoArch will let you proceed \u2014 but the warning exists "
          "because this is how systems break.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "dont",
        _("Pipe scripts into a shell"),
        _("curl \u2026 | bash runs code sight-unseen. Prefer real "
          "packages, or read what you are about to execute.")))

    return card


def _protection_card():
    card, lay = make_card(
        _("System Protection & Habits"), _ICON_KEY, icon_color=_GREEN)

    lay.addWidget(row(
        _("GUI sudo prompt (SUDO_ASKPASS)"),
        _("Passwords go straight to the privilege prompt in your session "
          "and are never written to disk."),
        subtitle_color=Colors.GREEN))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("OAuth tokens expire"),
        _("Cloud login caches tokens only until they expire \u2014 it "
          "never stores your credentials forever.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Config stays local"),
        _("Settings live in ~/.config/neoarch \u2014 no telemetry, no "
          "account, no cloud by default.")))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("AUR pre-install scan"),
        _("PKGBUILDs and .install scriptlets are statically inspected "
          "before every AUR install; critical findings demand explicit "
          "acceptance."),
        subtitle_color=Colors.GREEN))

    return card


def _link_card():
    card, lay = make_card(_("AUR Resources"), _ICON_BOX)
    lay.addWidget(row(
        _("Before installing from the AUR, review the package.")))
    btn_row = actions_row([
        btn(_("Open aur.archlinux.org \u2197"),
            on_click=lambda: webbrowser.open("https://aur.archlinux.org")),
    ])
    lay.addWidget(btn_row)
    return card


# ── Page ────────────────────────────────────────────────────────────

def _page_title():
    title = QLabel(_("Security"))
    title.setStyleSheet(
        f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
        f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
    return title


def _page_subtitle():
    subtitle = QLabel(
        _("What NeoArch can reach, what it runs, how it protects secrets, "
          "and the habits that keep an Arch system healthy"))
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet(
        f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
        " border: none; background: transparent; margin-top: 0;")
    return subtitle


class SecuritySettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)

        self.setup_ui()

    def setup_ui(self):
        self.layout.addWidget(_page_title())
        self.layout.addWidget(_page_subtitle())
        self.layout.addWidget(_sources_card())
        self.layout.addWidget(_updates_card())
        self.layout.addWidget(_advice_card())
        self.layout.addWidget(_protection_card())
        self.layout.addWidget(_link_card())
