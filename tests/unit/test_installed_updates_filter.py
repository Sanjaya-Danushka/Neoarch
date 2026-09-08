"""Unit tests for the Installed-page 'Updates available' source-panel toggle."""

import pytest
from PyQt6.QtWidgets import QApplication, QVBoxLayout


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _SourceCardStub:
    def get_selected_sources(self):
        return {}

    def get_sort(self):
        return "name"

    def get_sort_asc(self):
        return True


class _SearchBox:
    def text(self):
        return ""


class _Table:
    def setRowCount(self, n):
        pass


class _FakeApp:
    def __init__(self, pkgs):
        self.current_view = "installed"
        self.installed_all = list(pkgs)
        self.source_card = _SourceCardStub()
        self._installed_filter_states = {"Updates available": False}
        self.search_input = _SearchBox()
        self.package_table = _Table()
        self.all_packages = []
        self.current_page = 0
        self._view_mode = "table"
        self._installed_sizes = {}
        self.sync_called = []

    def _sync_installed_table(self):
        self.sync_called.append(True)


def _pkgs():
    return [
        {"name": "firefox", "source": "pacman", "has_update": True},
        {"name": "linux", "source": "pacman", "has_update": False},
        {"name": "node", "source": "npm", "has_update": True},
    ]


def test_apply_filters_all_views(qapp):
    from neoarch.backend.services.filter import apply_filters

    app = _FakeApp(_pkgs())
    apply_filters(app)
    assert {p["name"] for p in app.all_packages} == {"firefox", "linux", "node"}


def test_apply_filters_updates_only(qapp):
    from neoarch.backend.services.filter import apply_filters

    app = _FakeApp(_pkgs())
    app._installed_filter_states = {"Updates available": True}
    apply_filters(app)
    assert {p["name"] for p in app.all_packages} == {"firefox", "node"}


def test_installed_sources_toggle_wires_into_app(qapp):
    from neoarch.frontend.mixins.filters import _FiltersMixin

    view = object.__new__(_FiltersMixin)
    view._installed_filter_states = {"Updates available": False}
    calls = []
    view.apply_filters = lambda: calls.append("apply")
    _FiltersMixin.on_installed_updates_filter_changed(view, True)
    assert view._installed_filter_states == {"Updates available": True}
    assert calls == ["apply"]


def test_build_installed_panel_shows_updates_filter(qapp):
    from PyQt6.QtWidgets import QMainWindow
    from neoarch.frontend.mixins.filters import _FiltersMixin

    app = QMainWindow()
    app.sources_layout = QVBoxLayout()
    app.source_card = None
    app.current_view = "installed"
    app._installed_filter_states = {"Updates available": False}
    app._apply_called = []
    app._installed_sizes = {}
    app.all_packages = []
    app.apply_filters = lambda *a, **k: app._apply_called.append(1)
    app.on_installed_source_changed = lambda *a, **k: None
    app.on_installed_health_action = lambda *a, **k: None
    app.on_installed_maintenance_action = lambda *a, **k: None
    app.on_installed_updates_filter_changed = (
        lambda checked: _FiltersMixin.on_installed_updates_filter_changed(app, checked))
    app._refresh_installed_sources = lambda *a, **k: None
    app._refresh_installed_health_async = lambda *a, **k: None
    app.log = lambda *a, **k: None
    app.ensure_session_auth = lambda *a, **k: True
    _FiltersMixin.update_installed_sources(app)

    assert app.source_card is not None
    app.show()
    assert app.source_card.updates_filter_widget.isVisible() is True

    emitted = []
    app.source_card.update_status_changed.connect(emitted.append)
    app.source_card.set_updates_available_filter(True, emit=True)
    assert emitted == [True]
    assert app._installed_filter_states == {"Updates available": True}
    assert app._apply_called == [1]