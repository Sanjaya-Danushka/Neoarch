"""Smoke tests for the Security settings page (educational card layout)."""

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from neoarch.frontend.views.settings_security import SecuritySettingsWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_widget_constructs(qapp):
    w = SecuritySettingsWidget()
    assert w.layout.count() >= 5
    w.deleteLater()


def test_page_has_expected_cards(qapp):
    w = SecuritySettingsWidget()
    titles = {lbl.text() for lbl in w.findChildren(QLabel)
              if not lbl.text().startswith("http")}
    for expected in (
        "Security",
        "Sources & Community Packages",
        "Updates & Review",
        "Quick Reference \u2014 Do's & Don'ts",
        "System Protection & Habits",
        "AUR Resources",
    ):
        assert expected in titles, expected
    w.deleteLater()


def test_do_and_dont_chips_present(qapp):
    w = SecuritySettingsWidget()
    chips = [lbl.text() for lbl in w.findChildren(QLabel)]
    assert chips.count("DO") >= 4
    assert chips.count("DON'T") >= 4
    assert "WARNED" in chips
    w.deleteLater()


def test_advice_targets_exist(qapp):
    w = SecuritySettingsWidget()
    text = {lbl.text() for lbl in w.findChildren(QLabel)}
    for expected in (
        "Partial upgrades",
        "Install AUR packages blindly",
        "Ignore the full-upgrade warning",
        "Pipe scripts into a shell",
        "Read the PKGBUILD before installing from the AUR",
        "Update everything together",
    ):
        assert expected in text, expected
    w.deleteLater()


def test_aur_link_button_present(qapp):
    w = SecuritySettingsWidget()
    buttons = [b for b in w.findChildren(QPushButton)
               if "aur.archlinux.org" in b.text()]
    assert len(buttons) == 1
    w.deleteLater()