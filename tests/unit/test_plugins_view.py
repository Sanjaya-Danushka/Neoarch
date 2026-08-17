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


def test_plugin_card_uninstall_hidden_until_hover(qapp):
    """The Uninstall button must be hidden by default and only appear while
    hovering (double-click launches; uninstall is an explicit secondary action)."""
    inst = _PluginPackageCard(_spec(), True, None)
    assert inst._action_buttons[1].isHidden()
    inst._hover = True
    inst._sync_uninstall_visibility()
    assert not inst._action_buttons[1].isHidden()
    inst._hover = False
    inst._sync_uninstall_visibility()
    assert inst._action_buttons[1].isHidden()


def test_plugin_card_set_installed_swaps_actions_in_place(qapp):
    """After an install/uninstall completes the card's action row must flip
    (Install -> Open + hover Uninstall) without recreating the card."""
    card = _PluginPackageCard(_spec(pid="bob"), False, None)
    assert [b.text() for b in card._action_buttons] == ["Install"]
    assert card.status_chip._text == "Available"

    card.set_installed(True)
    assert [b.text() for b in card._action_buttons] == ["Open", "Uninstall"]
    assert card.status_chip._text == "Installed"
    assert card._action_buttons[1].isHidden()

    card.set_installed(False)
    assert [b.text() for b in card._action_buttons] == ["Install"]
    assert card.status_chip._text == "Available"

    # Idempotent: same state leaves the card untouched.
    card.set_installed(False)
    assert [b.text() for b in card._action_buttons] == ["Install"]


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


def test_toolbar_plugins_view_has_no_install_plugin_button(qapp):
    """The 'Install Plugin (.py file)' button must not appear in the toolbar
    for the plugins page — it was redundant since install is done from the
    cards directly."""
    import inspect
    from neoarch.frontend.mixins import views as views_module
    src = inspect.getsource(views_module._ViewsMixin.update_toolbar)
    assert "_install_plugin_btn" not in src
    assert "Install Plugin (.py file)" not in src


def _make_view(qapp, specs, monkeypatch):
    import neoarch.frontend.components.plugins_view as pv_mod
    from neoarch.frontend.components.plugins_view import PluginsView
    monkeypatch.setattr(pv_mod, "get_all_plugins_data", lambda: specs)
    monkeypatch.setattr(pv_mod, "get_plugins_data", lambda: specs)
    monkeypatch.setattr(pv_mod.PluginsView, "is_installed", lambda self, spec: False)
    view = PluginsView(None, lambda *a: None)
    view.resize(1000, 700)
    view.show()
    qapp.processEvents()
    view._transition_from_spinner()
    qapp.processEvents()
    return view


def test_search_cards_align_to_top_not_vertically_centered(qapp, monkeypatch):
    """Search results must be top-aligned. The grid container used to expand
    to the full viewport height, so the fixed-height cards were vertically
    centered in the middle of the page (their y was ~(viewport - card)/2)."""
    specs = [
        {"id": pid, "name": pid.capitalize(), "pkg": pid, "desc": "x", "cmd": pid}
        for pid in ("alpha", "beta", "gamma", "delta", "epsilon")
    ]
    view = _make_view(qapp, specs, monkeypatch)

    view.set_filter("ep", False, None)
    qapp.processEvents()

    cards = list(view._all_filtered_search_cards or [])
    assert len(cards) == 1
    assert cards[0]["widget"].y() == 0
    assert view.grid_layout.parentWidget().height() == 150


def test_selection_emits_signal_and_batch_installs(qapp, monkeypatch):
    """Checking multiple cards emits selection_changed with count and
    install_many_requested fires with exactly the checked installable ids."""
    specs = [
        {"id": pid, "name": pid.capitalize(), "pkg": pid, "desc": "x", "cmd": pid}
        for pid in ("alpha", "beta", "gamma")
    ]
    view = _make_view(qapp, specs, monkeypatch)
    view.refresh_all()
    qapp.processEvents()

    counts = []
    view.selection_changed.connect(lambda n: counts.append(n))

    install_emitted = []
    view.install_many_requested.connect(lambda ids: install_emitted.append(list(ids)))

    for d in view._all_cards:
        if d["plugin"]["id"] in ("alpha", "beta"):
            d["widget"].set_checked(True)
    qapp.processEvents()

    assert counts[-1] == 2
    assert len(view.selected_installable_ids()) == 2

    view.clear_selection()
    assert counts[-1] == 0
    assert all(not d["widget"].is_checked() for d in view._all_cards)


def test_plugins_view_set_installed_updates_card_data(qapp, monkeypatch):
    specs = [{"id": "alpha", "name": "Alpha", "pkg": "alpha", "desc": "x", "cmd": "alpha"}]
    view = _make_view(qapp, specs, monkeypatch)
    view.refresh_all()
    qapp.processEvents()

    view.set_installed("alpha", True)
    data = next(d for d in view._all_cards if d["plugin"]["id"] == "alpha")
    assert data["installed"] is True
    assert [b.text() for b in data["widget"]._action_buttons] == ["Open", "Uninstall"]


def test_install_many_batches_into_single_operation(qapp, monkeypatch):
    """install_many_by_id merges all packages per source into one install call
    and flips every card to its real installed state on success."""
    from PyQt6.QtCore import QObject, pyqtSignal
    import neoarch.managers.plugin_manager as pm_mod
    from neoarch.managers.plugin_manager import PluginsManager

    specs = {
        "alpha": _spec("alpha", "alpha"),
        "beta": _spec("beta", "beta"),
        "ts": _spec("ts", "npm-typescript"),
    }
    calls = []
    monkeypatch.setattr(pm_mod.install_service, "install_packages",
                        lambda app, pkgs: calls.append(dict(pkgs)))

    class _RecordingView:
        def __init__(self):
            self.installing = []
            self.installed = []
            self.refresh_forced = False

        def get_plugin(self, pid):
            return specs.get(pid)

        def is_installed(self, spec):
            return False

        def set_installing(self, pid, state):
            self.installing.append((pid, state))

        def set_installed(self, pid, state):
            self.installed.append((pid, state))

        def refresh_all(self, force=False):
            self.refresh_forced = bool(force)

    class _App(QObject):
        installation_progress = pyqtSignal(str, bool)
        log_signal = pyqtSignal(str)
        show_message = pyqtSignal(str, str)

        def __init__(self):
            super().__init__()
            self.ensure_session_auth = lambda: True
            self.force_sudo_install = False
            self._pending_install_packages = {}

    app = _App()
    view = _RecordingView()
    manager = PluginsManager(app)

    manager.install_many_by_id(view, ["alpha", "beta", "ts"])
    assert app._pending_install_packages == {"pacman": ["alpha", "beta"], "npm": ["typescript"]}
    assert calls == [{"pacman": ["alpha", "beta"], "npm": ["typescript"]}]

    app.installation_progress.emit("success", False)
    qapp.processEvents()
    qapp.processEvents()

    assert ("alpha", True) in view.installing and ("alpha", False) in view.installing
    assert set(view.installed) == {("alpha", True), ("beta", True), ("ts", True)}

    from PyQt6.QtTest import QTest
    QTest.qWait(300)
    assert view.refresh_forced is True


