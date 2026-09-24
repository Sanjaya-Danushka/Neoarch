import pytest
from PyQt6.QtWidgets import QApplication, QLabel

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


def test_is_partial_update_official_only():
    # A subset of the official updates = partial
    assert is_partial_update(
        _total_updates(), {"pacman": ["firefox"]}) is True
    # All official updates selected = full, no warning (AUR ignored)
    assert is_partial_update(
        _total_updates(), {"pacman": ["firefox", "kernel"]}) is False
    # Official + AUR selected still counts as full for official
    assert is_partial_update(
        _total_updates(),
        {"pacman": ["firefox", "kernel"], "AUR": ["yay"]}) is False
    # AUR-only selection never trips the warning
    assert is_partial_update(
        _total_updates(), {"AUR": ["yay"]}) is False
    # No official packages at all = never partial
    assert is_partial_update(
        _total_updates(), {"Flatpak": ["flatpak-app"]}) is False
    # Flatpak-only totals + official selection => no warning (unknown set)
    assert is_partial_update(
        [{"name": "a", "source": "Flatpak"}], {"pacman": ["firefox"]}) is False
    # Empty updates => no warning (cannot judge)
    assert is_partial_update([], {"pacman": ["firefox"]}) is False


def test_count_selected_official_only():
    sel, avail = count_selected(
        _total_updates(), {"pacman": ["firefox", "kernel"]})
    assert (sel, avail) == (2, 2)


def test_count_selected_ignores_aur():
    sel, avail = count_selected(
        _total_updates(), {"AUR": ["yay"]})
    assert (sel, avail) == (0, 2)


def test_partial_update_dialog_wording(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.show()
    texts = [l.text() for l in dlg.findChildren(QLabel)]
    assert any("Updating a selection only" == t for t in texts)
    assert any("1 of 2" in t for t in texts)
    # Reuses fully-translated msgids from every bundled catalog.
    assert dlg.selection_btn.text() == "I understand \u2014 Update Selection"
    assert dlg.update_all_btn.text() == "Update All (4)"


def test_update_all_choice(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.update_all_btn.click()
    assert dlg.result() == 1
    assert dlg.result_choice() == "all"


def test_selection_choice(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.selection_btn.click()
    assert dlg.result() == 1
    assert dlg.result_choice() == "selection"


def test_cancel_choice(qapp):
    dlg = PartialUpdateDialog(_total_updates(), {"pacman": ["firefox"]})
    dlg.reject()
    assert dlg.result() == 0
    assert dlg.result_choice() is None