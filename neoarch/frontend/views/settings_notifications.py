from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QCheckBox, QSpinBox)

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


class NotificationsSettingsWidget(QWidget):
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
        title = QLabel("Notifications")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Control which events show notifications and alerts")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Channels Card ──
        channel_card, channel_layout = self._make_card("Notification Channels")

        self.cb_desktop = QCheckBox("Desktop notifications (system tray)")
        self.cb_desktop.setStyleSheet(_CHECKBOX)
        self.cb_desktop.setChecked(bool(self.app.settings.get('notify_desktop', True)))
        self.cb_desktop.toggled.connect(lambda v: self.app.update_setting('notify_desktop', v))
        channel_layout.addWidget(self.cb_desktop)

        self.cb_inapp = QCheckBox("In-app toast messages")
        self.cb_inapp.setStyleSheet(_CHECKBOX)
        self.cb_inapp.setChecked(bool(self.app.settings.get('notify_inapp', True)))
        self.cb_inapp.toggled.connect(lambda v: self.app.update_setting('notify_inapp', v))
        channel_layout.addWidget(self.cb_inapp)

        self.cb_sound = QCheckBox("Play sound on events")
        self.cb_sound.setStyleSheet(_CHECKBOX)
        self.cb_sound.setChecked(bool(self.app.settings.get('notify_sound', False)))
        self.cb_sound.toggled.connect(lambda v: self.app.update_setting('notify_sound', v))
        channel_layout.addWidget(self.cb_sound)

        self.layout.addWidget(channel_card)

        # ── Events Card ──
        event_card, event_layout = self._make_card("Events")

        self.cb_install = QCheckBox("Package install / uninstall complete")
        self.cb_install.setStyleSheet(_CHECKBOX)
        self.cb_install.setChecked(bool(self.app.settings.get('notify_on_install', True)))
        self.cb_install.toggled.connect(lambda v: self.app.update_setting('notify_on_install', v))
        event_layout.addWidget(self.cb_install)

        self.cb_updates = QCheckBox("Updates available")
        self.cb_updates.setStyleSheet(_CHECKBOX)
        self.cb_updates.setChecked(bool(self.app.settings.get('notify_on_updates', True)))
        self.cb_updates.toggled.connect(lambda v: self.app.update_setting('notify_on_updates', v))
        event_layout.addWidget(self.cb_updates)

        self.cb_errors = QCheckBox("Errors and warnings")
        self.cb_errors.setStyleSheet(_CHECKBOX)
        self.cb_errors.setChecked(bool(self.app.settings.get('notify_on_errors', True)))
        self.cb_errors.toggled.connect(lambda v: self.app.update_setting('notify_on_errors', v))
        event_layout.addWidget(self.cb_errors)

        self.layout.addWidget(event_card)

        # ── Rate Limiting Card ──
        rate_card, rate_layout = self._make_card("Rate Limiting")

        rate_row = QHBoxLayout()
        rate_row.setSpacing(12)
        rate_label = QLabel("Cooldown between notifications (seconds):")
        rate_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        rate_row.addWidget(rate_label)

        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setStyleSheet(_SPINBOX)
        self.cooldown_spin.setRange(0, 300)
        self.cooldown_spin.setSingleStep(5)
        self.cooldown_spin.setValue(int(self.app.settings.get('notify_cooldown', 10)))
        self.cooldown_spin.valueChanged.connect(lambda v: self.app.update_setting('notify_cooldown', v))
        rate_row.addWidget(self.cooldown_spin)

        rate_unit = QLabel("sec")
        rate_unit.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        rate_row.addWidget(rate_unit)
        rate_row.addStretch()

        rate_layout.addLayout(rate_row)
        self.layout.addWidget(rate_card)
