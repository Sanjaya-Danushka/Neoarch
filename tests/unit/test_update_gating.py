import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.mixins.operations import _OperationsMixin


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _Model:
    def __init__(self, pkgs):
        self._pkgs = pkgs

    def packages(self):
        return self._pkgs


class _Tbl:
    def __init__(self, pkgs):
        self.model = _Model(pkgs)


class _Fake:
    def __init__(self, updates_all=None, table_pkgs=None):
        self.updates_all = updates_all
        self.updates_table = _Tbl(table_pkgs or [])


def test_available_prefers_updates_all(qapp):
    fake = _Fake(
        updates_all=[
            {"name": "a", "source": "pacman", "new_version": "2"},
            {"name": "b", "source": "AUR", "new_version": "2"},
            {"name": "c", "source": "Flatpak", "new_version": "2"},
        ])
    out = _OperationsMixin._available_arch_updates(fake)
    names = {p["name"] for p in out}
    assert names == {"a"}


def test_available_falls_back_to_table_rows(qapp):
    fake = _Fake(
        updates_all=None,
        table_pkgs=[
            {"name": "a", "source": "pacman", "version": "1",
             "new_version": "2"},
            {"name": "b", "source": "AUR", "version": "1",
             "new_version": "2"},
            {"name": "c", "source": "pacman", "version": "1",
             "new_version": "1"},
            {"name": "d", "source": "Flatpak", "version": "1",
             "new_version": "2"},
        ])
    out = _OperationsMixin._available_arch_updates(fake)
    names = {p["name"] for p in out}
    assert names == {"a"}


def test_available_none_when_nothing_loaded(qapp):
    fake = _Fake()
    assert _OperationsMixin._available_arch_updates(fake) == []

class _SelectionTable:
    def __init__(self, pkgs):
        self._pkgs = pkgs

    def selected_packages(self):
        return self._pkgs


class _Progress:
    def __init__(self):
        self.emitted = []

    def emit(self, *args):
        self.emitted.append(args)


class _SelectionApp:
    """Stub host for the multi-row update action."""

    def __init__(self, pkgs, confirm=True, locked=True, authed=True):
        self.updates_table = _SelectionTable(pkgs)
        self.installation_progress = _Progress()
        self.confirmed = None
        self.locked = locked
        self.authed = authed
        self._confirm_result = confirm
        self.logs = []

    def log(self, *args, **kwargs):
        self.logs.append(args)

    def _confirm_partial_update(self, packages_by_source):
        self.confirmed = packages_by_source
        return self._confirm_result

    def _db_lock_preflight(self, operation=""):
        return self.locked

    def ensure_session_auth(self):
        return self.authed


def _captured_updates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "neoarch.frontend.mixins.operations.update_service.update_packages",
        lambda app, packages_by_source: calls.append(packages_by_source))
    return calls


def test_multi_row_action_groups_selected_rows_by_source(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _SelectionApp([
        {"name": "bash", "source": "pacman"},
        {"name": "curl", "source": "pacman"},
        {"name": "yay", "source": "AUR"},
        {"name": "code", "source": "Flatpak"},
        {"name": "", "source": "pacman"},
    ])

    _OperationsMixin.update_selected_from_selection(fake)

    expected = {"pacman": ["bash", "curl"], "AUR": ["yay"], "Flatpak": ["code"]}
    assert fake.confirmed == expected
    assert calls == [expected]
    assert fake.installation_progress.emitted == [("start", True)]


def test_multi_row_action_stops_when_confirmation_declined(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _SelectionApp([{"name": "bash", "source": "pacman"}], confirm=False)

    _OperationsMixin.update_selected_from_selection(fake)

    assert calls == []
    assert fake.installation_progress.emitted == []


def test_multi_row_action_respects_db_lock_and_auth(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    locked = _SelectionApp([{"name": "bash", "source": "pacman"}], locked=False)
    _OperationsMixin.update_selected_from_selection(locked)
    assert calls == []

    unauthed = _SelectionApp([{"name": "bash", "source": "pacman"}], authed=False)
    _OperationsMixin.update_selected_from_selection(unauthed)
    assert calls == []
    assert unauthed.installation_progress.emitted == []


def test_multi_row_action_noop_without_selection(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _SelectionApp([])

    _OperationsMixin.update_selected_from_selection(fake)

    assert calls == []
    assert fake.confirmed is None
    assert fake.logs
