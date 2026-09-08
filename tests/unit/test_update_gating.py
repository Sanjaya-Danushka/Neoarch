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
    assert names == {"a", "b"}


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
    assert names == {"a", "b"}


def test_available_none_when_nothing_loaded(qapp):
    fake = _Fake()
    assert _OperationsMixin._available_arch_updates(fake) == []