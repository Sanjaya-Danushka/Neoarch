"""Smoke tests for the Repositories settings widget (GUI-only pieces)."""

import time

import pytest
from PyQt6.QtWidgets import QApplication, QFrame, QPushButton

from neoarch.frontend.components.source_item import ToggleSwitch
from neoarch.frontend.views.settings_repos import RepositoriesSettingsWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def _fake_list_repos(monkeypatch):
    """Keep the widget's async list_repos slot consistent with our samples."""
    from neoarch.backend.services import repo_manager

    monkeypatch.setattr(repo_manager, "list_repos", _sample_repos)


def _sample_repos():
    return [
        {"name": "core", "enabled": True, "include": "/etc/pacman.d/mirrorlist",
         "servers": [], "managed": False, "system": True},
        {"name": "extra", "enabled": True, "include": "/etc/pacman.d/mirrorlist",
         "servers": [], "managed": False, "system": True},
        {"name": "chaotic-aur", "enabled": True,
         "include": "/etc/pacman.d/chaotic-mirrorlist",
         "servers": [], "managed": True, "system": False},
        {"name": "myrepo", "enabled": False, "include": "",
         "servers": ["https://x.example"], "managed": False, "system": False},
    ]


def _pump(qapp, until, timeout=3.0):
    """Process Qt events until `until()` is truthy or we time out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if until():
            return True
        time.sleep(0.02)
    return until()


def _make_ready_widget(qapp):
    w = RepositoriesSettingsWidget()
    w._on_repos_ready({"ok": True, "repos": _sample_repos()})
    qapp.processEvents()
    return w


def _rows(w):
    for i in range(w._rows_host.count()):
        row = w._rows_host.itemAt(i).widget()
        if row is None or isinstance(row, QFrame) or row.layout() is None:
            continue
        control = row.layout().itemAt(row.layout().count() - 1).widget()
        yield control


def _toggles(w):
    """All repo ToggleSwitches, in row order (chaotic-aur, then myrepo)."""
    out = []
    for control in _rows(w):
        if control is None:
            continue
        h = control.layout()
        for j in range(h.count()):
            widget = h.itemAt(j).widget()
            if isinstance(widget, ToggleSwitch):
                out.append(widget)
    return out


def test_widget_constructs(qapp):
    w = RepositoriesSettingsWidget()
    assert w.layout.count() > 0
    w.deleteLater()


def test_system_repos_get_no_control(qapp):
    w = _make_ready_widget(qapp)
    controls = list(_rows(w))
    # core + extra render plain rows (control is None), chaotic-aur gets a
    # toggle + Remove, myrepo gets a toggle (disabled state).
    assert controls[0] is None
    assert controls[1] is None
    assert controls[2] is not None
    assert controls[3] is not None
    w.deleteLater()


def test_managed_repo_has_remove_button(qapp):
    w = _make_ready_widget(qapp)
    found = False
    for control in _rows(w):
        if control is None:
            continue
        for j in range(control.layout().count()):
            widget = control.layout().itemAt(j).widget()
            if isinstance(widget, QPushButton) and widget.text() == "Remove":
                found = True
    assert found is True
    w.deleteLater()


def test_enable_toggle_runs_repo_op(qapp, monkeypatch):
    from neoarch.backend.services import repo_manager

    w = _make_ready_widget(qapp)
    monkeypatch.setattr(w, "_auth", lambda: True)
    calls = []
    monkeypatch.setattr(repo_manager, "set_repo_enabled",
                        lambda name, enabled, sync=False: (
                            calls.append((name, enabled)), (True, "toggled"))[1])
    toggle = _toggles(w)[-1]  # myrepo (disabled)
    assert toggle is not None
    assert toggle.isChecked() is False

    toggle.setChecked(True)  # clicks through the same signal path as a mouse click

    assert _pump(qapp, lambda: w._status.text() == "toggled")
    assert calls == [("myrepo", True)]
    assert w._generic_btn.isEnabled() is True  # busy flag cleared
    w.deleteLater()


def test_chaotic_button_runs_preset(qapp, monkeypatch):
    from neoarch.backend.services import repo_manager

    w = RepositoriesSettingsWidget()
    monkeypatch.setattr(w, "_auth", lambda: True)
    monkeypatch.setattr("neoarch.frontend.components.dark_dialogs.dark_confirm",
                        lambda parent, title, message, danger=False: True)
    calls = []
    monkeypatch.setattr(repo_manager, "add_chaotic_aur",
                        lambda sync=True: (calls.append(sync), (True, "chaotic ok"))[1])

    w._chaotic_btn.click()

    assert _pump(qapp, lambda: w._status.text() == "chaotic ok")
    assert calls == [True]
    assert w._pin_status is True
    w.deleteLater()


def test_chaotic_button_surfaces_manjaro_warning(qapp, monkeypatch):
    from neoarch.backend.services import repo_manager

    w = RepositoriesSettingsWidget()
    monkeypatch.setattr(w, "_auth", lambda: True)
    seen = {}
    monkeypatch.setattr("neoarch.frontend.components.dark_dialogs.dark_confirm",
                        lambda parent, title, message, danger=False: seen.update(
                            {"message": message, "danger": danger}) or True)
    monkeypatch.setattr(repo_manager, "chaotic_preflight",
                        lambda: "Chaotic AUR warning for stable branch")
    monkeypatch.setattr(repo_manager, "add_chaotic_aur",
                        lambda sync=True: (True, "chaotic ok"))

    w._chaotic_btn.click()

    assert _pump(qapp, lambda: w._status.text() == "chaotic ok")
    assert "Chaotic AUR warning for stable branch" in seen.get("message", "")
    assert seen.get("danger") is True
    w.deleteLater()


def test_op_failure_pins_error_and_reloads(qapp, monkeypatch):
    from neoarch.backend.services import repo_manager

    w = RepositoriesSettingsWidget()
    monkeypatch.setattr(w, "_auth", lambda: True)
    monkeypatch.setattr(repo_manager, "add_chaotic_aur",
                        lambda sync=True: (False, "keyring failed"))

    w._on_op_finished(False, "keyring failed")
    assert w._status.text() == "keyring failed"
    assert w._pin_status is True
    qapp.processEvents()
    w.deleteLater()