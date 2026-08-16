"""Unit tests for the Plugins page: new-style plugin cards and row mapping."""

import pytest
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QPushButton

from neoarch.frontend.components.packages_grid_view import PackageCard
from neoarch.frontend.components.plugins_view import PluginsView, _PluginPackageCard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _spec(pid="alacritty", pkg="alacritty", **extra):
    spec = {"id": pid, "name": pid.capitalize(), "pkg": pkg, "desc": "A thing"}
    spec.update(extra)
    return spec


def test_plugin_card_uses_new_design_language(qapp):
    card = _PluginPackageCard(_spec(), False, None)
    assert isinstance(card, PackageCard)
    assert card.objectName() == "packageCard"
    assert card.width() == 280
    assert card.height() == 150
    assert hasattr(card, "logo")
    assert hasattr(card, "status_chip")
    assert hasattr(card, "checkbox")


def test_plugin_card_actions_reflect_installed_state(qapp):
    avail = _PluginPackageCard(_spec(), False, None)
    assert [b.text() for b in avail._action_buttons] == ["Install"]
    assert avail.status_chip._text == "Available"

    inst = _PluginPackageCard(_spec(), True, None)
    assert [b.text() for b in inst._action_buttons] == ["Open", "Uninstall"]
    assert inst.status_chip._text == "Installed"


def test_plugin_card_set_installing_swaps_text(qapp):
    inst = _PluginPackageCard(_spec(), True, None)
    inst.set_installing(True)
    assert [b.text() for b in inst._action_buttons] == ["Installing\u2026", "Uninstalling\u2026"]
    assert all(not b.isEnabled() for b in inst._action_buttons)
    inst.set_installing(False)
    assert [b.text() for b in inst._action_buttons] == ["Open", "Uninstall"]

    avail = _PluginPackageCard(_spec(), False, None)
    avail.set_installing(True)
    assert avail._action_buttons[0].text() == "Installing\u2026"
    avail.set_installing(False)
    assert avail._action_buttons[0].text() == "Install"


def test_plugin_card_button_signals_emit_plugin_id(qapp):
    emitted = []

    avail = _PluginPackageCard(_spec(pid="bob"), False, None)
    avail.install_clicked.connect(lambda pid: emitted.append(("install", pid)))
    avail._action_buttons[0].click()

    inst = _PluginPackageCard(_spec(pid="htop"), True, None)
    inst.launch_clicked.connect(lambda pid: emitted.append(("launch", pid)))
    inst.uninstall_clicked.connect(lambda pid: emitted.append(("uninstall", pid)))
    inst._action_buttons[0].click()
    inst._action_buttons[1].click()

    assert emitted == [("install", "bob"), ("launch", "htop"), ("uninstall", "htop")]


class _StubView(QObject):
    install_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)
    uninstall_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.main_app = None


def test_create_app_card_wires_view_signals(qapp):
    view = _StubView()
    emitted = []
    view.install_requested.connect(lambda pid: emitted.append(("install", pid)))
    view.launch_requested.connect(lambda pid: emitted.append(("launch", pid)))
    view.uninstall_requested.connect(lambda pid: emitted.append(("uninstall", pid)))

    avail = PluginsView.create_app_card(view, _spec(pid="bob"), None, False)
    assert isinstance(avail, _PluginPackageCard)
    avail._action_buttons[0].click()

    inst = PluginsView.create_app_card(view, _spec(pid="htop"), None, True)
    inst._action_buttons[0].click()
    inst._action_buttons[1].click()

    assert emitted == [("install", "bob"), ("launch", "htop"), ("uninstall", "htop")]


def test_package_source_resolution_for_cards(qapp):
    assert PluginsView._get_package_source(_spec(pid="yay", pkg="aur/yay")) == "aur"
    assert PluginsView._get_package_source(_spec(pid="spot", pkg="spot.flatpak")) == "flatpak"
    assert PluginsView._get_package_source(_spec(pid="ts", pkg="npm-typescript")) == "npm"
    assert PluginsView._get_package_source(_spec(pid="vim", pkg="vim")) == "pacman"
    from neoarch.frontend.components.plugins_view import _canonical_source
    assert _canonical_source("aur") == "AUR"
    assert _canonical_source("flatpak") == "Flatpak"


def test_plugin_card_double_click_launches_when_installed(qapp):
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QEvent

    launched = []
    inst = _PluginPackageCard(_spec(pid="htop"), True, None)
    inst.launch_clicked.connect(lambda pid: launched.append(pid))
    inst.mouseDoubleClickEvent(QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(10, 10), Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert launched == ["htop"]

    launched.clear()
    avail = _PluginPackageCard(_spec(pid="bob"), False, None)
    avail.launch_clicked.connect(lambda pid: launched.append(pid))
    avail.mouseDoubleClickEvent(QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(10, 10), Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert launched == []


def _card_spec(pid, installed=False, category="", source="pacman"):
    return {"plugin": {"id": pid, "name": pid.capitalize(), "category": category, "pkg": source},
            "installed": installed, "widget": None}


def test_plugins_view_sort_cards_orders_by_mode(qapp):
    cards = [
        _card_spec("b", installed=False, category="System"),
        _card_spec("a", installed=True, category="Games"),
        _card_spec("c", installed=False, category="System"),
    ]
    view = PluginsView.__new__(PluginsView)
    view._sort_mode = "name_asc"
    view._get_package_source = PluginsView._get_package_source
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]
    view._sort_mode = "name_desc"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["c", "b", "a"]
    view._sort_mode = "installed"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]
    view._sort_mode = "category"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]


class _FakeLegacyWidget:
    def __init__(self, name):
        self.name = name
        self._vis = True

    def setVisible(self, v):
        self._vis = bool(v)

    def isVisible(self):
        return self._vis

    def clear(self):
        pass

    def _relayout(self):
        pass


class _DummyApp:
    def __init__(self, view, mode):
        self.current_view = view
        self._view_mode = mode
        self.packages_grid = _FakeLegacyWidget("grid")
        self.package_table = _FakeLegacyWidget("table")
        self.updates_table = _FakeLegacyWidget("updates-table")
        self.called_populate = False
        self.all_packages = []
        self.search_results = []
        self.current_page = 0
        self.packages_per_page = 10

    def _populate_grid(self):
        self.called_populate = True


def test_show_active_view_never_reshows_legacy_widgets_on_self_contained_pages(qapp):
    """Background callbacks (_show_active_view) must not re-show the shared
    package table/grid while a self-contained page (plugins, appimage, git,
    docker, settings) is active."""
    from neoarch.frontend.mixins.views import _SELF_CONTAINED_VIEWS, _ViewsMixin
    for view in _SELF_CONTAINED_VIEWS:
        app = _DummyApp(view, "grid")
        _ViewsMixin._show_active_view(app)
        visible = [w.name for w in (app.packages_grid, app.package_table, app.updates_table)
                   if w.isVisible()]
        assert visible == [], f"{view} leaked legacy widgets: {visible}"
        assert not app.called_populate, f"{view} populated the legacy grid"


def test_show_active_view_still_manages_legacy_views(qapp):
    from neoarch.frontend.mixins.views import _ViewsMixin
    for view in ("updates", "installed", "discover"):
        app = _DummyApp(view, "table")
        _ViewsMixin._show_active_view(app)
        assert app.updates_table.isVisible()
        assert not app.package_table.isVisible()
        assert not app.packages_grid.isVisible()
        assert not app.called_populate

    app = _DummyApp("discover", "grid")
    _ViewsMixin._show_active_view(app)
    assert app.packages_grid.isVisible()
    assert app.called_populate


def test_populate_grid_guarded_on_self_contained_pages(qapp):
    from neoarch.frontend.mixins.views import _SELF_CONTAINED_VIEWS
    from neoarch.frontend.mixins.search import _SearchMixin
    for view in _SELF_CONTAINED_VIEWS:
        app = _DummyApp(view, "grid")
        _SearchMixin._populate_grid(app)
        assert not app.called_populate, f"{view} populated the legacy grid"
    app = _DummyApp("discover", "grid")
    _SearchMixin._populate_grid(app)
    assert app.packages_grid._vis


class _NavApp:
    def __init__(self):
        self.current_view = "updates"
        self._user_has_navigated = False
        self.loaded_updates = False

    def load_updates(self):
        self.loaded_updates = True


def test_startup_updates_load_skips_after_user_navigation(qapp):
    """Background auto-check must load updates data, never re-navigate."""
    from neoarch.frontend.mixins.views import _ViewsMixin

    app = _NavApp()
    # Startup case: no navigation yet, still on the default updates page.
    _ViewsMixin._startup_updates_load(app)
    assert app.loaded_updates

    app.loaded_updates = False
    app._user_has_navigated = True
    _ViewsMixin._startup_updates_load(app)
    assert not app.loaded_updates, "hijacked navigation after user left the page"

    app._user_has_navigated = False
    app.current_view = "discover"
    _ViewsMixin._startup_updates_load(app)
    assert not app.loaded_updates, "must not touch a non-updates view"


def test_toolbar_install_plugin_button_reset_per_view(qapp):
    """The plugins install button must be recreated like every other per-view
    toolbar button. Keeping a stale reference after the toolbar is cleared
    (deleteLater) re-adds a deleted widget, which raises inside update_toolbar
    and aborts switch_view — leaving the previous page (Discover) visible or a
    blank page, with the navbar install button missing."""
    import inspect
    from neoarch.frontend.mixins import views as views_module
    src = inspect.getsource(views_module._ViewsMixin.update_toolbar)
    assert "self._install_plugin_btn = None" in src


