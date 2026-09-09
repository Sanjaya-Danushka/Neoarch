"""What's New dialog — shows descriptive, card-wise release notes.

Rendered from the curated ``CHANGELOG.md`` (see the release-notes service) so
installed users always see exactly what was added and fixed, even without a
git checkout or network access.

Two modes:

* ``whats_new`` — shown once after the app itself has been updated.
* ``update``   — shown when a newer GitHub release is available; includes the
  release summary and an Update button that opens the GitHub release page.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.backend.services.i18n import _
from neoarch.backend.services.release_notes import latest_release, SECTION_LABELS


def _open_url(url):
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl(url))


class WhatIsNewDialog(QDialog):
    """Modal card-based release notes dialog."""

    def __init__(self, blocks, mode="whats_new", latest=None,
                 current_version="", parent=None):
        super().__init__(parent)
        self._blocks = blocks or []
        self._mode = mode
        self._latest = latest or {}
        self._current_version = current_version
        self.setWindowTitle(_("What's New"))
        self.setMinimumWidth(620)
        self.setMaximumWidth(820)
        self.setStyleSheet(
            f"QDialog {{ background-color: rgba(22, 23, 26, 240); }}")
        self._build()

    # ── UI ────────────────────────────────────────────────────────────
    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 26, 28, 24)
        v.setSpacing(14)

        # Heading
        if self._mode == "update" and self._latest:
            title = (_("NeoArch {version} is available")
                     .format(version=self._latest.get("version", "")))
            subtitle = _("A new version of NeoArch is available")
        else:
            title = (_("What's New in NeoArch {version}")
                     .format(version=self._current_version))
            subtitle = _("Here's what's new in this update")

        v.addWidget(self._title_label(title))
        v.addWidget(self._subtitle_label(subtitle))

        # Latest-release summary body (update mode only)
        if self._mode == "update" and self._latest.get("body"):
            body = QLabel(self._latest["body"])
            body.setWordWrap(True)
            body.setStyleSheet(
                f"color: {Colors.TEXT_2}; font-size: {Fonts.MD};"
                " border: none;")
            v.addWidget(body)

        # Scrolling release blocks (cards)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 6, 0)
        cl.setSpacing(18)
        for block in self._blocks:
            cl.addWidget(self._block_card(block))
        cl.addStretch(1)
        scroll.setWidget(content)
        v.addWidget(scroll, 1)

        # Buttons
        v.addLayout(self._actions())

    def _title_label(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; border: none;")
        return lbl

    def _subtitle_label(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"font-size: {Fonts.MD}; color: {Colors.TEXT_2}; border: none;")
        return lbl

    def _block_card(self, block):
        card = QFrame()
        card.setObjectName("whatsNewCard")
        card.setStyleSheet(
            f"QFrame#whatsNewCard {{ background-color: {Colors.SURFACE};"
            f" border: 1px solid {Colors.BORDER};"
            f" border-radius: {Radii.XL}px; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 18)
        cl.setSpacing(12)

        # Version header
        version = block.get("version", "")
        if version.lower() == "unreleased":
            version_text = _("Upcoming release")
        else:
            version_text = _("Version {version}").format(version=version)
        date = block.get("date", "")
        if date:
            version_text += f"        —  {date}"
        header = QLabel(version_text)
        header.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.ACCENT}; border: none;")
        cl.addWidget(header)

        sections = block.get("sections", {})
        if sections:
            for label in SECTION_LABELS:
                items = sections.get(label)
                if not items:
                    continue
                cl.addWidget(self._section_block(label, items))

        return card

    def _section_block(self, label, items):
        box = QFrame()
        box.setStyleSheet("QFrame { background: transparent; border: none; }")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)

        head = QLabel(_(label))
        head.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; border: none;")
        bl.addWidget(head)

        for item in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("•")
            dot.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: {Fonts.BASE};"
                " border: none;")
            dot.setFixedWidth(10)
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            text = QLabel(item)
            text.setWordWrap(True)
            text.setStyleSheet(
                f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
                " border: none;")
            row.addWidget(text, 1)
            bl.addLayout(row)

        return box

    def _actions(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        if self._mode == "update" and self._latest:
            update_btn = QPushButton(_("Update"))
            update_btn.setMinimumHeight(38)
            update_btn.setStyleSheet(self._accent_qss())
            update_btn.clicked.connect(
                lambda: _open_url(self._latest.get("html_url", "")))
            row.addWidget(update_btn)

        continue_btn = QPushButton(
            _("Skip for now") if (self._mode == "update" and self._latest)
            else _("Continue"))
        continue_btn.setMinimumHeight(38)
        if self._mode == "update" and self._latest:
            continue_btn.setStyleSheet(self._outline_qss())
        else:
            continue_btn.setStyleSheet(self._accent_qss())
        continue_btn.clicked.connect(self.accept)
        row.addWidget(continue_btn)

        row.addStretch(1)
        return row

    def _accent_qss(self):
        return (f"QPushButton {{ background-color: {Colors.ACCENT};"
                " color: #08131a; border: none;"
                f" border-radius: {Radii.MD}px; font-weight: {Fonts.SEMI};"
                " padding: 0 22px; }"
                "QPushButton:hover { opacity: 0.92; }")

    def _outline_qss(self):
        return (f"QPushButton {{ background-color: transparent;"
                f" color: {Colors.TEXT}; border: 1px solid {Colors.BORDER};"
                f" border-radius: {Radii.MD}px; font-weight: {Fonts.SEMI};"
                " padding: 0 22px; }")


# Convenience entry points used by the GUI code.
def show_whats_new(parent, blocks, current_version=""):
    """Blocking What's New dialog after an update."""
    dialog = WhatIsNewDialog(blocks, mode="whats_new",
                             current_version=current_version, parent=parent)
    dialog.exec()


def show_update_available(parent, latest, blocks):
    """Blocking 'update available' dialog with the release summary."""
    dialog = WhatIsNewDialog(blocks, mode="update", latest=latest,
                             parent=parent)
    dialog.exec()


def fetch_latest_release():
    """Best-effort latest GitHub release (background-friendly)."""
    return latest_release()