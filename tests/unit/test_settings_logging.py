"""Smoke tests for the Logging settings page (card layout + controls)."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QComboBox, QLabel, QPushButton

from neoarch.frontend.views.settings_logging import LoggingSettingsWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeApp(QWidget):
    """Minimal app the Logging settings page talks to."""

    def __init__(self):
        super().__init__()
        self.settings = {
            "log_level": "INFO",
            "log_to_console": False,
            "log_file_path": "/tmp/neoarch.log",
            "log_max_size_mb": 5,
        }

    def update_setting(self, key, value):
        self.settings[key] = value


def _labels(widget):
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def test_widget_constructs(qapp):
    w = LoggingSettingsWidget(_FakeApp())
    assert w.layout.count() >= 4
    w.deleteLater()


def test_page_has_expected_cards(qapp):
    w = LoggingSettingsWidget(_FakeApp())
    texts = set(_labels(w))
    for expected in (
        "Logging",
        "General",
        "Log File",
        "Good Habits",
    ):
        assert expected in texts, expected
    w.deleteLater()


def test_controls_are_built(qapp):
    w = LoggingSettingsWidget(_FakeApp())
    assert len(w.findChildren(QComboBox)) == 1
    browse = [b for b in w.findChildren(QPushButton)
              if "Browse" in b.text()]
    assert len(browse) == 1
    w.deleteLater()


def test_do_dont_chips_present(qapp):
    w = LoggingSettingsWidget(_FakeApp())
    chips = _labels(w)
    assert chips.count("DO") == 1
    assert chips.count("DON'T") == 1
    w.deleteLater()