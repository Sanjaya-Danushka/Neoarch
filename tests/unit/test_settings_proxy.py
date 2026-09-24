"""Smoke tests for the Proxy & Network settings page (card layout + controls)."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QComboBox, QLabel

from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.views.settings_proxy import ProxySettingsWidget
from neoarch.frontend.views._settings_kit import Stepper


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _MsgBus:
    def __init__(self):
        self.messages = []

    def emit(self, *args):
        self.messages.append(args)


class _FakeApp(QWidget):
    """Minimal app the Proxy & Network settings page talks to."""

    def __init__(self):
        super().__init__()
        self.settings = {
            "proxy_type": "none",
            "proxy_host": "",
            "proxy_port": 8080,
            "request_timeout": 30,
            "verify_ssl": True,
            "parallel_network": True,
        }
        self.show_message = _MsgBus()

    def update_setting(self, key, value):
        self.settings[key] = value


def _labels(widget):
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def test_widget_constructs(qapp):
    w = ProxySettingsWidget(_FakeApp())
    assert w.layout.count() >= 4
    w.deleteLater()


def test_page_has_expected_cards(qapp):
    w = ProxySettingsWidget(_FakeApp())
    texts = set(_labels(w))
    for expected in (
        "Proxy & Network",
        "Connection",
        "Timeouts",
        "Advanced",
    ):
        assert expected in texts, expected
    w.deleteLater()


def test_descriptive_rows(qapp):
    w = ProxySettingsWidget(_FakeApp())
    texts = set(_labels(w))
    for expected in (
        "Proxy type",
        "Host & port",
        "Request timeout",
        "Verify SSL certificates",
        "Parallel network requests",
        "Pacman ParallelDownloads",
    ):
        assert expected in texts, expected
    w.deleteLater()


def test_controls_built(qapp):
    w = ProxySettingsWidget(_FakeApp())
    assert len(w.findChildren(QComboBox)) == 1
    assert w._host.text() == ""
    assert w._port.value() == 8080  # port is a Stepper now
    assert len(w.findChildren(ToggleSwitch)) == 2
    steppers = w.findChildren(Stepper)
    assert len(steppers) == 3  # port + request timeout + ParallelDownloads
    assert any(s.value() == 30 for s in steppers)  # request timeout
    w.deleteLater()


def test_host_disabled_when_no_proxy(qapp):
    app = _FakeApp()
    w = ProxySettingsWidget(app)
    assert not w._host.isEnabled()


def test_selecting_proxy_enables_host_port(qapp):
    app = _FakeApp()
    w = ProxySettingsWidget(app)
    combo = w._type_combo
    idx = combo.findData("http")
    combo.setCurrentIndex(idx)
    assert app.settings["proxy_type"] == "http"
    assert w._host.isEnabled()
    assert w._port.isEnabled()
    w.deleteLater()