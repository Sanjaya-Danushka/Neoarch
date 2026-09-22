"""Unit tests for the Plugins page: new-style plugin cards and row mapping."""

import pytest
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication

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


def test_plain_pkg_strips_source_prefixes(qapp):
    from neoarch.frontend.components.plugins_view import _plain_pkg
    assert _plain_pkg("aur/yay") == "yay"
    assert _plain_pkg("npm-typescript") == "typescript"
    assert _plain_pkg("brew-fd") == "fd"
    assert _plain_pkg("org.gnome.Evolution.flatpak") == "org.gnome.Evolution"
    assert _plain_pkg("pandoc") == "pandoc"
    assert _plain_pkg("") == ""


def test_prewarm_installed_cache_detects_meta_package_via_cmd(qapp, monkeypatch):
    """A plugin whose pkg is a meta package (e.g. QEMU's 'qemu-full') must
    still be marked installed when the launcher binary exists, even if the
    meta package name is missing from `pacman -Qq` (split package install)."""
    import neoarch.frontend.components.plugins_view as pv_mod
    specs = [
        {"id": "qemu", "name": "QEMU", "pkg": "qemu-full", "cmd": "qemu-system-x86_64"},
        {"id": "optipng", "name": "Image Optimizer", "pkg": "optipng", "cmd": "optipng"},
    ]
    monkeypatch.setattr(pv_mod, "get_plugins_data", lambda: specs)
    monkeypatch.setattr("neoarch.resources.plugin_data.get_all_plugins_data", lambda: specs)

    import subprocess
    called = []

    def fake_run(cmd, capture_output=True, text=True, timeout=5, check=False):
        called.append(cmd)
        return type("R", (), {"returncode": 0, "stdout": "optipng\n"})()  # no qemu-full

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(pv_mod.shutil, "which",
                        lambda name: "/usr/bin/" + name if name == "qemu-system-x86_64" else None)

    view = PluginsView.__new__(PluginsView)
    view._installed_cache = {}
    view._prewarm_installed_cache()

    assert view._installed_cache == {"qemu": True, "optipng": True}
    assert any(a == "pacman" or "-Qq" in a for a in called)


def test_is_installed_strips_aur_prefix_before_pacman_qi(qapp, monkeypatch):
    """is_installed must query the plain package name, not the 'aur/' prefixed
    pkg string, or an installed AUR package is reported as missing."""
    import neoarch.frontend.components.plugins_view as pv_mod
    import subprocess
    seen = []
    monkeypatch.setattr(pv_mod.shutil, "which", lambda name: None)

    def fake_run(cmd, capture_output=True, text=True, timeout=5, check=False):
        seen.append(cmd)
        return type("R", (), {"returncode": 0, "stdout": ""})()

    monkeypatch.setattr(subprocess, "run", fake_run)

    view = PluginsView.__new__(PluginsView)
    view._installed_cache = {}
    assert view.is_installed({"id": "aur-yay", "pkg": "aur/yay", "cmd": None}) is True
    assert "-Qi" in seen[0] and seen[0][-1] == "yay"


def test_get_plugin_resolves_live_search_specs(qapp):
    """Cards created from pacman/AUR live-search results carry prefixed ids
    ('pacman-pandoc'); get_plugin must resolve them so batch installs no longer
    collapse into the misleading 'Nothing to install' path."""
    view = PluginsView.__new__(PluginsView)
    view.plugins = []
    spec = {"id": "pacman-pandoc", "name": "pandoc", "pkg": "pandoc", "cmd": None}
    view._dynamic_specs = {"pacman-pandoc": spec}
    assert view.get_plugin("pacman-pandoc") is spec
    assert view.get_plugin("pacman-missing") is None


def test_live_search_ready_stores_dynamic_specs(qapp, monkeypatch):
    """_on_live_search_ready must record non-curated specs so get_plugin can
    find them later (install/extend via Batch install)."""
    import neoarch.frontend.components.plugins_view as pv_mod
    monkeypatch.setattr(pv_mod.PluginsView, "is_installed", lambda self, spec: False)
    monkeypatch.setattr(pv_mod.PluginsView, "create_app_card",
                        lambda self, spec, parent, installed: None)
    monkeypatch.setattr(pv_mod.PluginsView, "_sort_cards", lambda self, cards: cards)
    monkeypatch.setattr(pv_mod.PluginsView, "_refresh_content", lambda self: None)
    view = PluginsView(None, lambda *a: None)
    view._dynamic_specs.clear()
    view._pending_live_query = "pandoc"
    spec = {"id": "pacman-pandoc", "name": "pandoc", "pkg": "pandoc"}
    view._on_live_search_ready(("pandoc", [spec]))
    resolved = view.get_plugin("pacman-pandoc")
    assert resolved is not None and resolved["id"] == "pacman-pandoc" and resolved["pkg"] == "pandoc"


def test_plugin_card_double_click_launches_when_installed(qapp):
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QEvent

    launched = []
    inst = _PluginPackageCard(_spec(pid="htop"), True, None)
    inst.launch_clicked.connect(launched.append)
    inst.mouseDoubleClickEvent(QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(10, 10), Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert launched == ["htop"]

    launched.clear()
    avail = _PluginPackageCard(_spec(pid="bob"), False, None)
    avail.launch_clicked.connect(launched.append)
    avail.mouseDoubleClickEvent(QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(10, 10), Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert launched == []


def _card_spec(pid, installed=False, category="", source="pacman"):
    return {"plugin": {"id": pid, "name": pid.capitalize(), "category": category, "pkg": source},
            "installed": installed, "widget": None}


def _card_by_id(view, pid):
    for entry in view._all_cards:
        if entry["plugin"]["id"] == pid:
            return entry
    return None


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
        self._cleared = False
        self._relaid_out = False

    def setVisible(self, v):
        self._vis = bool(v)

    def isVisible(self):
        return self._vis

    def clear(self):
        self._cleared = True

    def _relayout(self):
        self._relaid_out = True


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
    monkeypatch.setattr(pv_mod, "get_all_plugins_data", lambda: specs)
    monkeypatch.setattr(pv_mod, "get_plugins_data", lambda: specs)
    monkeypatch.setattr(pv_mod.PluginsView, "is_installed", lambda self, spec: False)
    view = PluginsView(None, lambda *a: None)
    view.resize(1000, 700)
    view.show()
    qapp.processEvents()
    view._transition_from_loading()
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
    view.selection_changed.connect(counts.append)

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


def test_installed_card_selection_counts_for_clear(qapp, monkeypatch):
    """Ticking an installed card's checkbox must surface in the selection count
    (so the toolbar's Clear button appears). Batch install must still ignore
    it — only non-installed checks are installable."""
    specs = [
        {"id": pid, "name": pid.capitalize(), "pkg": pid, "desc": "x", "cmd": pid}
        for pid in ("alpha", "beta")
    ]
    view = _make_view(qapp, specs, monkeypatch)
    view.refresh_all()
    qapp.processEvents()

    counts = []
    view.selection_changed.connect(counts.append)

    alpha = _card_by_id(view, "alpha")
    assert alpha is not None
    alpha["installed"] = True          # simulate an installed plugin card
    alpha["widget"].set_installed(True)
    alpha["widget"].set_checked(True)
    qapp.processEvents()

    assert counts[-1] == 1
    assert len(view.selected_installable_ids()) == 0

    view.clear_selection()
    assert counts[-1] == 0


def test_get_filtered_plugins_fallback_respects_sort(qapp, monkeypatch):
    """With no active filters, the plugins list/grid must still honor the
    source panel's Sort by setting (the previous fallback returned the raw
    catalog order, breaking the list view's sort menu)."""
    specs = [
        {"id": pid, "name": pid.capitalize(), "pkg": pid, "desc": "x", "cmd": pid}
        for pid in ("gamma", "alpha", "beta")
    ]
    view = _make_view(qapp, specs, monkeypatch)
    view.refresh_all()                 # populate the catalog
    view._current_filter_states = {}
    view._all_filtered_cards = None
    view._all_filtered_search_cards = None

    view._sort_mode = "name_desc"
    cards = view._get_filtered_plugins()
    assert [c["plugin"]["id"] for c in cards] == ["gamma", "beta", "alpha"]

    view._sort_mode = "name_asc"
    cards = view._get_filtered_plugins()
    assert [c["plugin"]["id"] for c in cards] == ["alpha", "beta", "gamma"]


def test_plugins_view_set_installed_updates_card_data(qapp, monkeypatch):
    specs = [{"id": "alpha", "name": "Alpha", "pkg": "alpha", "desc": "x", "cmd": "alpha"}]
    view = _make_view(qapp, specs, monkeypatch)
    view.refresh_all()
    qapp.processEvents()

    view.set_installed("alpha", True)
    data = _card_by_id(view, "alpha")
    assert data is not None
    assert data["installed"] is True
    assert [b.text() for b in data["widget"]._action_buttons] == ["Open", "Uninstall"]


def test_install_many_batches_into_single_operation(qapp, monkeypatch):
    """install_many_by_id merges all packages per source into one install call
    and flips every card to its real installed state on success."""
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

        @staticmethod
        def get_plugin(pid):
            return specs.get(pid)

        @staticmethod
        def is_installed(spec):
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

        def set_pending_install(self, packages_by_source):
            self._pending_install_packages = packages_by_source

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


