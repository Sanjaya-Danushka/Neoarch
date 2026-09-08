import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QLabel

from neoarch.frontend.components.partial_update_dialog import (
    PartialUpdateDialog, count_selected, is_partial_update,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _total_updates():
    return [
        {"name": "firefox", "version": "128.0", "new_version": "129.0",
         "source": "pacman"},
        {"name": "yay", "version": "12.4.0", "new_version": "12.4.1",
         "source": "AUR"},
        {"name": "kernel", "version": "6.10", "new_version": "6.11",
         "source": "pacman"},
        {"name": "flatpak-app", "version": "1.0", "new_version": "1.1",
         "source": "Flatpak"},
    ]


def test_is_partial_update_logic():
    # A subset of the Arch updates = partial
    assert is_partial_update(
        _total_updates(), {"pacman": ["firefox"]}) is True
    # All Arch updates selected = full, no warning
    assert is_partial_update(
        _total_updates(), {"pacman": ["firefox", "kernel"], "AUR": ["yay"]}) is False
    # No Arch packages at all = never partial
    assert is_partial_update(
        _total_updates(), {"Flatpak": ["flatpak-app"]}) is False
    # Flatpak-only totals + arch selection => no warning (unknown set)
    assert is_partial_update(
        [{"name": "a", "source": "Flatpak"}], {"pacman": ["firefox"]}) is False
    # Empty updates => no warning (cannot judge)
    assert is_partial_update([], {"pacman": ["firefox"]}) is False


def test_count_selected():
    sel, avail = count_selected(
        _total_updates(), {"pacman": ["firefox", "kernel"]})
    assert (sel, avail) == (2, 3)


def test_partial_update_dialog_wording(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.show()
    texts = [l.text() for l in dlg.findChildren(QLabel)]
    assert any("Updating a selection only" == t for t in texts)
    assert any("1 of 3" in t for t in texts)
    assert dlg.confirm_btn.text() == "I understand \u2014 Update Selection"


def test_partial_update_dialog_accept_reject(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    dlg.reject()
    assert dlg.result() == QDialog.DialogCode.Rejected