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

class _Progress:
    def __init__(self):
        self.emitted = []

    def emit(self, *args):
        self.emitted.append(args)


class _CheckedApp:
    """Stub host for the checkbox-driven batch update path."""

    def __init__(self, pkgs, confirm=True, authed=True, view="updates"):
        self.installation_progress = _Progress()
        self.current_view = view
        self._pkgs = pkgs
        self.confirmed = None
        self.authed = authed
        self._confirm_result = confirm
        self.logs = []

    def get_checked_packages_for_view(self):
        return list(self._pkgs)

    def log(self, *args, **kwargs):
        self.logs.append(args)

    def _confirm_partial_update(self, packages_by_source):
        self.confirmed = packages_by_source
        return self._confirm_result

    def ensure_session_auth(self):
        return self.authed


def _captured_updates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "neoarch.frontend.mixins.operations.update_service.update_packages",
        lambda app, packages_by_source: calls.append(packages_by_source))
    return calls


def test_checkbox_update_groups_by_source(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _CheckedApp([
        {"name": "bash", "source": "pacman"},
        {"name": "curl", "source": "pacman"},
        {"name": "yay", "source": "AUR"},
        {"name": "code", "source": "Flatpak"},
        {"name": "", "source": "pacman"},
    ])

    _OperationsMixin._update_selected_updates_table(fake)

    expected = {"pacman": ["bash", "curl"], "AUR": ["yay"], "Flatpak": ["code"]}
    assert fake.confirmed == expected
    assert calls == [expected]
    assert fake.installation_progress.emitted == [("start", True)]


def test_checkbox_update_stops_when_confirmation_declined(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _CheckedApp([{"name": "bash", "source": "pacman"}], confirm=False)

    _OperationsMixin._update_selected_updates_table(fake)

    assert calls == []
    assert fake.installation_progress.emitted == []


def test_checkbox_update_stops_without_auth(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _CheckedApp([{"name": "bash", "source": "pacman"}], authed=False)

    _OperationsMixin._update_selected_updates_table(fake)

    assert calls == []
    assert fake.installation_progress.emitted == []


def test_checkbox_update_noop_without_checked_rows(qapp, monkeypatch):
    calls = _captured_updates(monkeypatch)
    fake = _CheckedApp([])

    _OperationsMixin._update_selected_updates_table(fake)

    assert calls == []
    assert fake.confirmed is None
    assert fake.logs
