"""Tests for the Notifications settings page and notification dispatch gating."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.views.settings_notifications import NotificationsSettingsWidget
from neoarch.frontend.mixins.views import _ViewsMixin


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


_DEFAULTS = {
    "notify_desktop": True,
    "notify_inapp": True,
    "notify_sound": False,
    "notify_on_install": True,
    "notify_on_updates": True,
    "notify_on_errors": True,
    "notify_on_connection": True,
    "notify_cooldown": 0,
}


class _FakeApp(QWidget):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = dict(_DEFAULTS)
        if settings:
            self.settings.update(settings)
        self.updates = []

    def update_setting(self, key, value):
        self.settings[key] = value
        self.updates.append((key, value))


def test_widget_constructs_and_lists_all_toggles(qapp):
    w = NotificationsSettingsWidget(_FakeApp())
    toggles = w.findChildren(ToggleSwitch)
    assert len(toggles) == 7
    w.deleteLater()


def test_toggles_reflect_settings(qapp):
    app = _FakeApp({"notify_desktop": False, "notify_on_connection": False})
    w = NotificationsSettingsWidget(app)
    assert w.sw_desktop.isChecked() is False
    assert w.sw_connection.isChecked() is False
    assert w.sw_inapp.isChecked() is True
    w.deleteLater()


def test_connection_toggle_persists(qapp):
    app = _FakeApp()
    w = NotificationsSettingsWidget(app)
    assert w.sw_connection.isChecked() is True
    w.sw_connection.setChecked(False)
    assert ("notify_on_connection", False) in app.updates
    assert app.settings["notify_on_connection"] is False
    w.deleteLater()


def test_every_toggle_writes_its_setting(qapp):
    app = _FakeApp()
    w = NotificationsSettingsWidget(app)
    for toggle, key in (
        (w.sw_desktop, "notify_desktop"),
        (w.sw_inapp, "notify_inapp"),
        (w.sw_sound, "notify_sound"),
        (w.sw_install, "notify_on_install"),
        (w.sw_updates, "notify_on_updates"),
        (w.sw_errors, "notify_on_errors"),
        (w.sw_connection, "notify_on_connection"),
    ):
        before = toggle.isChecked()
        toggle.setChecked(not before)
        assert (key, not before) in app.updates, key
    w.deleteLater()


class _Notifier(_ViewsMixin):
    def __init__(self, settings):
        self.settings = settings
        self.calls = []
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)

    def _desktop_notify(self, title, text):
        self.calls.append(("desktop", title))

    def _toast_notify(self, text, level="info"):
        self.calls.append(("toast", level))


def test_connection_notify_gated_off():
    n = _Notifier({**_DEFAULTS, "notify_on_connection": False})
    n._on_no_signal()
    n._on_connection_restored()
    assert n.calls == []


def test_connection_notify_dispatches_both_channels():
    n = _Notifier({**_DEFAULTS})
    n._on_no_signal()
    n._on_connection_restored()
    assert ("desktop", "No internet connection") in n.calls
    assert ("toast", "warning") in n.calls
    assert ("desktop", "Connection restored") in n.calls
    assert ("toast", "success") in n.calls


def test_channels_independent():
    n = _Notifier({**_DEFAULTS, "notify_desktop": False})
    n._on_no_signal()
    assert all(kind != "desktop" for kind, _ in n.calls)
    assert ("toast", "warning") in n.calls


def test_errors_toggle_no_longer_gates_connection():
    # A regression guard: connection events must follow notify_on_connection,
    # not notify_on_errors / notify_on_updates.
    n = _Notifier({**_DEFAULTS, "notify_on_errors": False, "notify_on_updates": False})
    n._on_no_signal()
    n._on_connection_restored()
    assert ("desktop", "No internet connection") in n.calls
    assert ("desktop", "Connection restored") in n.calls
