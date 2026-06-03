from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QCheckBox, QSpinBox, QPushButton)
from PyQt6.QtCore import Qt

_CARD = """
    QFrame#settingsCard {
        background-color: rgba(28, 30, 36, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
    }
"""

_CHECKBOX = """
    QCheckBox {
        color: #EDEDEF;
        font-size: 13px;
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1.5px solid #5C5E66;
        background-color: rgba(18, 19, 22, 0.8);
    }
    QCheckBox::indicator:hover {
        border-color: #00BFAE;
    }
    QCheckBox::indicator:checked {
        background-color: #00BFAE;
        border: 1.5px solid #00BFAE;
    }
"""

_SPINBOX = """
    QSpinBox {
        background-color: rgba(18, 19, 22, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 8px 12px;
        color: #EDEDEF;
        font-size: 13px;
        min-width: 80px;
    }
    QSpinBox:focus {
        border-color: #00BFAE;
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


class AutoUpdateSettingsWidget(QWidget):
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

    def setup_ui(self):
        title = QLabel("Auto Update")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Manage automatic updates and system snapshots")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Auto Update Card ──
        update_card, update_layout = self._make_card("Auto Update")

        self.cb_auto_update = QCheckBox("Enable automatic updates")
        self.cb_auto_update.setStyleSheet(_CHECKBOX)
        self.cb_auto_update.setChecked(bool(self.app.settings.get('auto_update_enabled', False)))
        self.cb_auto_update.toggled.connect(lambda v: self.app.update_setting('auto_update_enabled', v))
        update_layout.addWidget(self.cb_auto_update)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(12)
        interval_label = QLabel("Update interval (days):")
        interval_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        interval_row.addWidget(interval_label)

        self.interval_spin = QSpinBox()
        self.interval_spin.setStyleSheet(_SPINBOX)
        self.interval_spin.setRange(1, 30)
        self.interval_spin.setValue(int(self.app.settings.get('auto_update_interval_days', 1)))
        self.interval_spin.valueChanged.connect(lambda v: self.app.update_setting('auto_update_interval_days', v))
        interval_row.addWidget(self.interval_spin)
        interval_row.addStretch()

        update_layout.addLayout(interval_row)
        self.layout.addWidget(update_card)

        # ── Snapshots Card ──
        snap_card, snap_layout = self._make_card("Snapshots")

        self.cb_snapshot = QCheckBox("Create snapshot before updates")
        self.cb_snapshot.setStyleSheet(_CHECKBOX)
        self.cb_snapshot.setChecked(bool(self.app.settings.get('snapshot_before_update', False)))
        self.cb_snapshot.toggled.connect(lambda v: self.app.update_setting('snapshot_before_update', v))
        snap_layout.addWidget(self.cb_snapshot)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.setStyleSheet(_BTN_OUTLINE)
        create_snap_btn.clicked.connect(self.app.create_snapshot)
        btn_row.addWidget(create_snap_btn)

        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.setStyleSheet(_BTN_OUTLINE)
        revert_snap_btn.clicked.connect(self.app.revert_to_snapshot)
        btn_row.addWidget(revert_snap_btn)

        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.setStyleSheet(_BTN_OUTLINE)
        delete_snap_btn.clicked.connect(self.app.delete_snapshots)
        btn_row.addWidget(delete_snap_btn)

        btn_row.addStretch()
        snap_layout.addLayout(btn_row)

        self.layout.addWidget(snap_card)
