from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.views._settings_kit import make_card, row, sep, Stepper

_ICON_BELL = (
    '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
    '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'
)
_ICON_BELL_RING = (
    '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
    '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'
    '<path d="M4 2a10.2 10.2 0 0 0-2 5.5"/>'
    '<path d="M22 2a10.2 10.2 0 0 1 2 5.5"/>'
)
_ICON_TIMER = (
    '<line x1="10" x2="14" y1="2" y2="2"/>'
    '<line x1="12" x2="15" y1="14" y2="11"/>'
    '<circle cx="12" cy="14" r="8"/>'
)


class NotificationsSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)

        self.setup_ui()

    def setup_ui(self):
        title = QLabel(_("Notifications"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Control which events show notifications and alerts"))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        self.layout.addWidget(subtitle)

        self.setup_channels()
        self.layout.addWidget(self.channel_card)

        self.setup_events()
        self.layout.addWidget(self.event_card)

        self.setup_rate_limiting()
        self.layout.addWidget(self.rate_card)

    def _toggle(self, key, default, name):
        toggle = ToggleSwitch(self, name)
        toggle.setChecked(
            bool(self.app.settings.get(key, default)), animate=False)
        toggle.toggled.connect(
            lambda v: self.app.update_setting(key, v))
        return toggle

    def setup_channels(self):
        self.channel_card, lay = make_card(
            _("Notification Channels"), _ICON_BELL)

        self.sw_desktop = self._toggle(
            'notify_desktop', True, _("Desktop notifications"))
        lay.addWidget(row(
            _("Desktop notifications"),
            _("Show a pop-up notification from the system tray "
              "when a task completes."),
            control=self.sw_desktop))
        lay.addWidget(sep())

        self.sw_inapp = self._toggle(
            'notify_inapp', True, _("In-app toast messages"))
        lay.addWidget(row(
            _("In-app toast messages"),
            _("Show a message banner inside the app when a task completes."),
            control=self.sw_inapp))
        lay.addWidget(sep())

        self.sw_sound = self._toggle(
            'notify_sound', False, _("Play sound on events"))
        lay.addWidget(row(
            _("Play sound on events"),
            _("Play a short alert sound together with each notification."),
            control=self.sw_sound))

    def setup_events(self):
        self.event_card, lay = make_card(_("Events"), _ICON_BELL_RING)

        self.sw_install = self._toggle(
            'notify_on_install', True, _("Package install / uninstall complete"))
        lay.addWidget(row(
            _("Package install / uninstall complete"),
            _("When a package installation or removal finishes."),
            control=self.sw_install))
        lay.addWidget(sep())

        self.sw_updates = self._toggle(
            'notify_on_updates', True, _("Updates available"))
        lay.addWidget(row(
            _("Updates available"),
            _("When new system and package updates are ready."),
            control=self.sw_updates))
        lay.addWidget(sep())

        self.sw_errors = self._toggle(
            'notify_on_errors', True, _("Errors and warnings"))
        lay.addWidget(row(
            _("Errors and warnings"),
            _("When an operation fails or emits warnings."),
            control=self.sw_errors))

    def setup_rate_limiting(self):
        self.rate_card, lay = make_card(_("Rate Limiting"), _ICON_TIMER)

        self.cooldown_stepper = Stepper(
            0, 300, step=5, suffix=_(" s"), on_text=_("No cooldown"))
        self.cooldown_stepper.setValue(
            int(self.app.settings.get('notify_cooldown', 10)))
        self.cooldown_stepper.valueChanged.connect(
            lambda v: self.app.update_setting('notify_cooldown', v))

        lay.addWidget(row(
            _("Cooldown between notifications (seconds):"),
            _("Seconds to wait before repeating the same notification."),
            control=self.cooldown_stepper))