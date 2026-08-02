from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton)
from PyQt6.QtCore import Qt

_CARD = """
    QFrame#settingsCard {
        background-color: rgba(28, 30, 36, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
    }
"""

_BTN_OUTLINE = """
    QPushButton {
        background-color: transparent;
        color: #00BFAE;
        border: 1px solid rgba(0, 191, 174, 0.35);
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: rgba(0, 191, 174, 0.12);
        border-color: #00BFAE;
    }
"""

_HINT = "color: #8B8D97; font-size: 12px; border: none;"


class MaintenanceSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.setup_ui()

    def _make_card(self, title_text):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(_CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #EDEDEF; border: none;")
        card_layout.addWidget(title)
        return card, card_layout

    def _row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        return row

    def setup_ui(self):
        title = QLabel("Maintenance")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Keep your system tidy: orphans, leftover configs, and news")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Orphans ──
        card, card_layout = self._make_card("Orphaned Packages")
        hint = QLabel("Packages installed as dependencies that nothing needs anymore.")
        hint.setStyleSheet(_HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton("Remove Orphans")
        btn.setStyleSheet(_BTN_OUTLINE)
        btn.clicked.connect(self.app.cleanup_orphans)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)

        # ── .pacnew files ──
        card, card_layout = self._make_card("Config Files (.pacnew)")
        hint = QLabel("When packages ship new configs, the old one is kept as .pacnew.")
        hint.setStyleSheet(_HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton("Manage .pacnew")
        btn.setStyleSheet(_BTN_OUTLINE)
        btn.clicked.connect(self.app.manage_pacnew)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)

        # ── Arch News ──
        card, card_layout = self._make_card("Arch Linux News")
        hint = QLabel("Stay informed about important announcements before updating.")
        hint.setStyleSheet(_HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton("Show News")
        btn.setStyleSheet(_BTN_OUTLINE)
        btn.clicked.connect(self.app.show_arch_news)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)
