"""Tests for per-view state preservation on page navigation.

Covers the `_restore_checked` helper that keeps the user's install
selection across re-renders of the shared table. Full switch_view()
navigation is exercised by the GUI smoke tests; here we verify the
model-level restore semantics that the navigation uses.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from neoarch.backend.services.i18n import set_language
from neoarch.frontend.components.updates_table import UpdatesTable
from neoarch.frontend.mixins.views import _ViewsMixin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    set_language("en")
    return app


class _FakeApp:
    def get_source_icon(self, source, size):
        return None


def _make_table():
    table = UpdatesTable(_FakeApp())
    table.set_enrich(False)
    table.set_packages([
        {"name": f"pkg-{i}", "id": f"pkg-{i}", "version": "1.0",
         "new_version": "1.0", "source": "pacman"}
        for i in range(4)
    ])
    return table


def _mixin(table):
    obj = _ViewsMixin.__new__(_ViewsMixin)
    obj.updates_table = table
    obj.log = lambda *a, **k: None
    return obj


def test_restore_checked_rechecks_matching_rows(qapp):
    table = _make_table()
    model = table.model
    mixin = _mixin(table)

    # Simulate a selection that a table repaint wiped.
    model.setData(model.index(1, 0), Qt.CheckState.Checked,
                  Qt.ItemDataRole.CheckStateRole)
    assert len(model.checked_names()) == 1
    key = ("pkg-1", "pacman")

    model.set_packages([
        {"name": f"pkg-{i}", "id": f"pkg-{i}", "version": "1.0",
         "new_version": "1.0", "source": "pacman"}
        for i in range(4)
    ])
    assert model.checked_names() == set()

    mixin._restore_checked({key})
    assert model.checked_names() == {key}


def test_restore_checked_skips_installed_rows(qapp):
    table = _make_table()
    model = table.model
    mixin = _mixin(table)

    model.set_packages([
        {"name": "avail", "id": "avail", "version": "1.0",
         "new_version": "1.0", "source": "AUR", "_installed": True},
        {"name": "pick", "id": "pick", "version": "1.0",
         "new_version": "1.0", "source": "AUR"},
    ])
    mixin._restore_checked({("avail", "AUR"), ("pick", "AUR")})
    assert model.checked_names() == {("pick", "AUR")}


def test_restore_checked_ignores_missing_rows(qapp):
    table = _make_table()
    model = table.model
    mixin = _mixin(table)

    model.set_packages([
        {"name": "here", "id": "here", "version": "1.0",
         "new_version": "1.0", "source": "pacman"},
    ])
    mixin._restore_checked({("gone", "pacman")})
    assert model.checked_names() == set()


class _Stub(_ViewsMixin):
    """Minimal host for the shared-table mixin logic (no full window)."""

    def __init__(self):
        self.current_view = "installed"
        self.loading_context = "installed"
        self._view_mode = "table"
        self._installing = False
        self._operation_view = None
        self._installed_loading = False
        self._installed_load_id = None
        self._updates_load_id = None
        self._pending_update_all = False
        self.all_packages = []
        self.installed_all = []
        self.updates_all = []
        self._table_view_owner = ""
        self.source_card = None
        self.updates_table = UpdatesTable(_FakeApp())
        self.updates_table.set_enrich(False)
        self.package_table = UpdatesTable(_FakeApp())
        self.package_table.set_enrich(False)
        self.packages_grid = UpdatesTable(_FakeApp())
        self.packages_grid.set_enrich(False)
        self.loading_widget = _FakeWidget()
        self.log = lambda *a, **k: None


class _FakeWidget:
    def setVisible(self, *a):
        return None

    def stop_animation(self, *a):
        return None

    def isHidden(self, *a):
        return False


def _rows_of(stub):
    return [p.get("name") for p in stub.updates_table.model.packages()]


def _pkg(name, source="pacman"):
    return {"name": name, "id": name, "version": "1.0",
            "new_version": "1.0", "source": source, "repo": "core"}


def test_sync_installed_table_uses_cached_installed_dataset(qapp):
    """Installed page must render installed data, never the updates list."""
    stub = _Stub()
    stub.current_view = "installed"
    stub.all_packages = [_pkg("upd-pkg")]        # what all_packages holds now
    stub.installed_all = [_pkg("bash")]          # real installed cache
    stub.updates_table.set_packages([_pkg("upd-pkg")])
    stub._table_view_owner = "updates"

    stub._sync_installed_table(dataset=stub.installed_all)

    model = stub.updates_table.model
    names = [pkg["name"] for pkg in model.packages()]
    assert names == ["bash"], f"installed page rendered wrong data: {names}"
    assert stub._table_view_owner == "installed"
    assert stub._installed_loaded is True


def test_show_active_view_keeps_operation_page_spinner_only(qapp):
    """During an operation, nothing may re-plant the table under the spinner."""
    stub = _Stub()
    stub.current_view = "updates"
    stub._installing = True
    stub._operation_view = "updates"
    stub.updates_table.setVisible(True)

    stub._show_active_view()
    assert stub.updates_table.isHidden(), \
        "origin page must stay spinner-only during the operation"


def test_show_active_view_other_pages_unaffected(qapp):
    """The operation guard only applies to the operation's origin page."""
    stub = _Stub()
    stub.current_view = "installed"
    stub._installing = True
    stub._operation_view = "updates"
    stub._table_view_owner = "installed"
    stub._installed_loaded = True
    stub.updates_table.setVisible(True)

    stub._show_active_view()
    assert not stub.updates_table.isHidden(), \
        "non-origin pages render normally during the operation"


WAIT_TITLE = "Waiting for the update to finish\u2026"
WAIT_SUB = "Installed packages will appear here automatically once it completes."


def test_wait_state_is_static_not_a_loading_animation(qapp):
    """The no-cache installed page during an update must show a calm waiting
    message, never a shimmery loading animation or an empty-state claim."""
    table = UpdatesTable(_FakeApp())
    table.set_enrich(False)
    table.set_empty_text(WAIT_TITLE, WAIT_SUB)
    table.set_packages([])

    assert table.model.rowCount() == 0
    assert table._loading is False, "loading overlay must be off"
    assert table._empty._progress.isHidden(), "no progress shimmer animation"
    assert table._empty._title.text() == WAIT_TITLE
    assert table._empty._sub.text() == WAIT_SUB
    assert "No installed packages" not in table._empty._title.text()


def test_no_empty_claim_from_stale_query_during_operation(qapp):
    """A stale empty installed result landing mid-operation must not replace
    the wait-state with a bogus 'no installed packages' claim, and must not
    re-own the shared table."""
    stub = _Stub()
    stub.current_view = "installed"
    stub._installing = True
    stub.all_packages = []
    stub.updates_table.set_empty_text(WAIT_TITLE, WAIT_SUB)
    stub.updates_table.set_packages([])

    stub._sync_installed_table()

    assert stub.updates_table._empty._title.text() == WAIT_TITLE
    assert "No installed packages" not in stub.updates_table._empty._title.text()
    assert getattr(stub, '_table_view_owner', None) != "installed"
    assert getattr(stub, '_installed_loaded', False) is not True


def test_installed_results_kept_when_context_clobbered_by_parallel_load(qapp):
    """A startup/auto 'updates' refresh rewrites the shared loading_context
    after the Installed page's load started. Its results must still be
    accepted (keyed by the page's load id), never stranded on an empty table
    until a manual refresh."""
    stub = _Stub()
    stub.current_view = "installed"
    stub.loading_context = "updates"       # clobbered by a parallel loader
    stub._installed_loading = True
    stub._installed_load_id = 7
    stub.updates_table.set_packages([])

    stub.on_packages_loaded([_pkg("bash"), _pkg("pacman")], 7, False)

    assert not stub._installed_loading
    assert stub.installed_all == [_pkg("bash"), _pkg("pacman")]
    assert stub._table_view_owner == "installed"
    assert _rows_of(stub) == ["bash", "pacman"]


def test_updates_results_kept_when_context_clobbered_by_parallel_load(qapp):
    """Mirror-case: an Installed load starting while an updates refresh is in
    flight flips loading_context to 'installed'; the updates results must not
    be dropped either."""
    stub = _Stub()
    stub.current_view = "updates"
    stub.loading_context = "installed"
    stub._updates_load_id = 3
    recorded = []

    def _fake_sync(dataset=None):
        recorded.append(dataset if dataset is not None
                         else (stub.updates_all or stub.all_packages))

    stub._sync_updates_table = _fake_sync

    stub.on_packages_loaded([_pkg("linux", "pacman")], 3, False)

    assert stub.updates_all == [_pkg("linux", "pacman")]
    assert recorded == [[_pkg("linux", "pacman")]], \
        "updates results were dropped by the context clobber"


def test_superseded_load_still_rejected(qapp):
    """Ownership is now per-page by load id: a load that belongs to a page the
    user left must still be rejected (the loading indicator stays intact)."""
    stub = _Stub()
    stub.current_view = "installed"
    stub.loading_context = "installed"
    stub._installed_loading = True
    stub._installed_load_id = 5
    stub.installed_all = [_pkg("kept")]

    stub.on_packages_loaded([_pkg("stale")], 4, True)

    assert stub.installed_all == [_pkg("kept")], "superseded load leaked in"
    assert _rows_of(stub) == [], "stale results must not paint the table"


def test_recover_stuck_installed_requeries_when_still_loading(qapp):
    stub = _Stub()
    stub.current_view = "installed"
    stub._installed_loading = True
    calls = []
    stub.load_installed_packages = lambda: calls.append("reload")

    stub._recover_stuck_installed_load()

    assert calls == ["reload"]


def test_recover_stuck_installed_noop_when_loaded(qapp):
    stub = _Stub()
    stub.current_view = "installed"
    stub._installed_loading = False
    calls = []
    stub.load_installed_packages = lambda: calls.append("reload")

    stub._recover_stuck_installed_load()

    assert calls == []


def test_recover_stuck_installed_noop_during_operation(qapp):
    stub = _Stub()
    stub.current_view = "installed"
    stub._installed_loading = True
    stub._installing = True
    calls = []
    stub.load_installed_packages = lambda: calls.append("reload")

    stub._recover_stuck_installed_load()

    assert calls == []


def test_pending_update_all_ignores_installed_result_on_updates_page(qapp):
    """While an update-all is pending, an Installed loader result arriving on
    the Updates page must be rejected — it is not the updates dataset (this
    used to leak the installed rows/count onto the Updates page)."""
    stub = _Stub()
    stub.current_view = "updates"
    stub._pending_update_all = True
    stub._installed_load_id = 7
    stub._updates_load_id = 9
    calls = []
    stub._do_update_all = lambda: calls.append("update-all")

    stub.on_packages_loaded([_pkg("bash"), _pkg("pacman")], 7, True)

    assert stub.updates_all == [], "installed result leaked into updates_all"
    assert stub._pending_update_all is True, "pending flag must survive"
    assert calls == [], "update-all must not start from installed data"
    assert _rows_of(stub) == [], "installed rows must not paint the table"


def test_pending_update_all_on_installed_page_paints_nothing(qapp):
    """The updates loader's final result while on the Installed page must
    trigger the pending update-all but must NOT replace the Installed table
    or installed_all with the updates dataset."""
    stub = _Stub()
    stub.current_view = "installed"
    stub._pending_update_all = True
    stub._installed_load_id = 7
    stub._updates_load_id = 9
    stub.installed_all = [_pkg("kept-installed")]
    stub.updates_table.set_packages([_pkg("kept-installed")])
    calls = []
    stub._do_update_all = lambda: calls.append("update-all")

    stub.on_packages_loaded([_pkg("linux"), _pkg("glibc")], 9, True)

    assert calls == ["update-all"], "pending update-all did not start"
    assert stub._pending_update_all is False
    assert stub.updates_all == [_pkg("linux"), _pkg("glibc")]
    assert stub.installed_all == [_pkg("kept-installed")], \
        "installed_all was clobbered by the updates dataset"
    assert _rows_of(stub) == ["kept-installed"], \
        "installed table was repainted with updates rows"


def test_pending_update_all_updates_page_paints_and_triggers(qapp):
    """On the Updates page itself the pending update-all still paints the real
    updates list and then starts."""
    stub = _Stub()
    stub.current_view = "updates"
    stub._pending_update_all = True
    stub._updates_load_id = 9
    calls = []
    stub._do_update_all = lambda: calls.append("update-all")
    stub.update_updates_header_counts = lambda: None
    stub.package_table = _FakeLegacy()

    stub.on_packages_loaded([_pkg("linux"), _pkg("glibc")], 9, True)

    assert calls == ["update-all"], "update-all did not start"
    assert stub._pending_update_all is False
    assert stub.updates_all == [_pkg("linux"), _pkg("glibc")]
    assert sorted(_rows_of(stub)) == ["glibc", "linux"], "updates list was not painted"


class _FakeLegacy:
    def __init__(self):
        self.rows = 0

    def setRowCount(self, n):
        self.rows = n

    def rowCount(self):
        return self.rows

    def setVisible(self, *a):
        return None


def test_sync_updates_table_empty_before_first_load_leaves_clean_slate(qapp):
    """A filter-panel rebuild before the Updates loader delivered anything
    must not paint a bogus 'All caught up', claim the shared table, or make
    switch_view's restore skip the real load."""
    stub = _Stub()
    stub.current_view = "updates"
    stub.updates_all = []
    stub.updates_table.set_packages([])

    stub._sync_updates_table()

    assert getattr(stub, '_table_view_owner', "") != "updates"
    assert getattr(stub, '_updates_loaded', False) is False
    assert _rows_of(stub) == [], "empty state must not be painted early"


def test_sync_updates_table_empty_after_real_load_shows_all_caught_up(qapp):
    """Once real updates data arrived (even as an empty list), the legit
    'All caught up' paint is allowed and owns the table as before."""
    stub = _Stub()
    stub.current_view = "updates"
    stub._updates_loaded = True
    stub.updates_all = []

    stub._sync_updates_table()

    assert stub._table_view_owner == "updates"
    assert stub._updates_loaded is True
    assert _rows_of(stub) == []


def test_on_packages_loaded_marks_updates_received(qapp):
    """An accepted Updates loader result flags the dataset as received so a
    later genuine empty paint ('All caught up') is not mistaken for a pre-load
    rebuild."""
    stub = _Stub()
    stub.current_view = "updates"
    stub._updates_load_id = 3

    stub.on_packages_loaded([_pkg("linux")], 3, False)

    assert stub._updates_loaded is True
    assert stub._updates_loading is False


class _FakePluginsView:
    """Minimal PluginsView stand-in with the real filtered-card accessor."""

    def __init__(self):
        self._sort_mode = "name_asc"

    def set_sort(self, mode):
        self._sort_mode = mode or "name_asc"

    def selected_installable_ids(self):
        return []

    def _get_filtered_plugins(self):
        cards = [
            {"plugin": {"id": "bleachbit", "name": "BleachBit",
                        "version": "1.0", "desc": "Cleaner", "pkg": "bleachbit"},
             "installed": True},
            {"plugin": {"id": "timeshift", "name": "Timeshift",
                        "version": "2.0", "desc": "Snapshots", "pkg": "timeshift"},
             "installed": False},
        ]
        reverse = self._sort_mode == "name_desc"
        sort_key = lambda c: (c['plugin'].get('name') or c['plugin'].get('id') or '').lower()
        return sorted(cards, key=sort_key, reverse=reverse)

    @classmethod
    def _get_package_source(cls, plugin):
        return "AUR" if plugin.get("id") == "timeshift" else "pacman"


def test_sync_plugins_table_populates_list_view(qapp):
    """Switching the Plugins page to list view must fill the shared table with
    the plugin catalog. Guards against the typo'd accessor name that made
    _sync_plugins_table bail out and leave the updates table empty/stale."""
    stub = _Stub()
    stub.plugins_view = _FakePluginsView()

    stub._sync_plugins_table()

    rows = stub.updates_table.model.packages()
    assert [p.get("name") for p in rows] == ["BleachBit", "Timeshift"]
    assert rows[0].get("source") == "pacman"
    assert rows[1].get("source") == "AUR"
    assert rows[0].get("status") == "Installed"
    assert rows[1].get("status") == "Available"
    assert rows[0].get("_installed") is True


def _plugins_row_click(stub, pkg):
    """Drive the shared-table row-selected dispatch exactly as a click does."""
    stub.current_view = "plugins"
    stub._on_updates_table_row_selected(pkg)


def test_plugin_list_detail_shows_install_not_update(qapp):
    """Clicking an available plugin row must open the detail card with the
    Install action — never the Updates page's 'Update Package' button."""
    from neoarch.frontend.components.package_detail_card import PackageDetailCard
    stub = _Stub()
    stub.current_view = "plugins"
    stub.package_detail_card = PackageDetailCard()
    pkg = {"name": "Timeshift", "id": "timeshift", "version": "2.0",
           "source": "AUR", "_installed": False,
           "description": "Snapshots", "_src": {"desc": "Snapshots"}}

    _plugins_row_click(stub, pkg)

    assert stub.package_detail_card.install_btn.isVisible() is True
    assert stub.package_detail_card.update_btn.isVisible() is False
    assert stub.package_detail_card.uninstall_btn.isVisible() is False
    assert stub.package_detail_card.launch_btn.isVisible() is False


def test_plugin_list_detail_shows_launch_and_uninstall_when_installed(qapp):
    """An installed plugin's detail card offers Launch + Uninstall together,
    exactly the actions the grid cards expose."""
    from neoarch.frontend.components.package_detail_card import PackageDetailCard
    stub = _Stub()
    stub.current_view = "plugins"
    stub.package_detail_card = PackageDetailCard()
    pkg = {"name": "BleachBit", "id": "bleachbit", "version": "1.0",
           "source": "pacman", "_installed": True,
           "description": "Cleaner", "_src": {"desc": "Cleaner"}}

    _plugins_row_click(stub, pkg)

    assert stub.package_detail_card.install_btn.isVisible() is False
    assert stub.package_detail_card.update_btn.isVisible() is False
    assert stub.package_detail_card.launch_btn.isVisible() is True
    assert stub.package_detail_card.uninstall_btn.isVisible() is True


class _RecordingPluginsManager:
    def __init__(self, calls):
        self._calls = calls

    def install_by_id(self, view, plugin_id):
        self._calls.append(("install", plugin_id))

    def uninstall_by_id(self, view, plugin_id):
        self._calls.append(("uninstall", plugin_id))

    def launch_by_id(self, view, plugin_id):
        self._calls.append(("launch", plugin_id))

    def install_many_by_id(self, view, plugin_ids):
        self._calls.append(("install_many", list(plugin_ids)))


def test_toggle_check_selects_installed_rows(qapp):
    """Clicking an installed plugin row must select it (opening the detail
    card) instead of being a silent no-op. Only batch-install checking is
    forbidden for installed rows."""
    stub = _Stub()
    stub.current_view = "plugins"
    stub._view_mode = "table"
    stub.plugins_view = _FakePluginsView()
    stub._sync_plugins_table()
    stub.updates_table.set_packages(stub.updates_table.model.packages())
    table = stub.updates_table

    selected = []
    table.row_selected.connect(lambda pkg: selected.append(pkg))

    table._toggle_check(0, None)

    assert selected, "an installed row click must emit row_selected"
    assert selected[0].get("_installed") is True

    checked = table.model.checked_names()
    assert not checked, "installed rows must not enter the batch-install selection"


def test_plugin_detail_install_routes_through_plugins_manager(qapp):
    """The detail card's Install button on a plugin row must install via the
    plugins manager (lifecycle-aware), never the generic package installer."""
    from neoarch.frontend.components.package_detail_card import PackageDetailCard
    from neoarch.frontend.mixins.operations import _OperationsMixin
    stub = _Stub()
    stub.package_detail_card = PackageDetailCard()
    stub.package_detail_card._pkg_data = {
        "_view": "plugins", "id": "timeshift", "name": "Timeshift", "source": "AUR"}
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)
    stub.plugins_view = object()

    stub.install_from_detail = _OperationsMixin.install_from_detail.__get__(stub, _Stub)

    stub.install_from_detail()

    assert calls == [("install", "timeshift")]


def test_plugin_detail_uninstall_routes_through_plugins_manager(qapp):
    from neoarch.frontend.components.package_detail_card import PackageDetailCard
    from neoarch.frontend.mixins.operations import _OperationsMixin
    stub = _Stub()
    stub.package_detail_card = PackageDetailCard()
    stub.package_detail_card._pkg_data = {
        "_view": "plugins", "id": "bleachbit", "name": "BleachBit", "source": "pacman"}
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)
    stub.plugins_view = object()

    stub.uninstall_from_detail = _OperationsMixin.uninstall_from_detail.__get__(stub, _Stub)

    stub.uninstall_from_detail()

    assert calls == [("uninstall", "bleachbit")]


def test_plugin_detail_launch_routes_through_plugins_manager(qapp):
    """The plugin detail card's Launch button must run the plugin through the
    plugins manager (as the ⋯ menu and grid cards do)."""
    from neoarch.frontend.components.package_detail_card import PackageDetailCard
    from neoarch.frontend.mixins.operations import _OperationsMixin
    stub = _Stub()
    stub.package_detail_card = PackageDetailCard()
    stub.package_detail_card._pkg_data = {
        "_view": "plugins", "id": "bleachbit", "name": "BleachBit", "source": "pacman"}
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)
    stub.plugins_view = object()

    stub.launch_from_detail = _OperationsMixin.launch_from_detail.__get__(stub, _Stub)

    stub.launch_from_detail()

    assert calls == [("launch", "bleachbit")]


class _FilteredFakePluginsView(_FakePluginsView):
    """Simulates the source-panel filters already applied on the grid."""

    def _get_filtered_plugins(self):
        return [card for card in super()._get_filtered_plugins()
                if card.get("installed") is False]


def test_sync_plugins_table_respects_source_panel_filters(qapp):
    """Source/status/category filters must narrow the list view too: the
    table is re-mapped from the grid's filtered card set, not the full
    catalog."""
    stub = _Stub()
    stub.plugins_view = _FilteredFakePluginsView()   # Available-only filter

    stub._sync_plugins_table()

    rows = stub.updates_table.model.packages()
    assert [p.get("name") for p in rows] == ["Timeshift"]
    assert rows[0].get("status") == "Available"


def test_plugins_row_menu_install_routes_through_plugins_manager(qapp):
    """The list-view ⋯ menu's Install on an available plugin must go through
    the plugins manager, matching the grid cards and detail card."""
    stub = _Stub()
    stub.current_view = "plugins"
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)
    stub.plugins_view = object()
    pkg = {"name": "Timeshift", "id": "timeshift", "source": "AUR"}

    stub._on_updates_table_menu("install", pkg)

    assert calls == [("install", "timeshift")]


def test_plugins_row_menu_uninstall_routes_through_plugins_manager(qapp):
    stub = _Stub()
    stub.current_view = "plugins"
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)
    stub.plugins_view = object()
    pkg = {"name": "BleachBit", "id": "bleachbit", "source": "pacman"}

    stub._on_updates_table_menu("uninstall", pkg)

    assert calls == [("uninstall", "bleachbit")]


class _FakeButton:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, state):
        self.enabled = bool(state)


class _FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _ToolbarPluginsView:
    """Configurable plugins_view stand-in for toolbar selection-state tests."""

    def __init__(self, installable_ids=()):
        self.installable_ids = list(installable_ids)

    def selected_installable_ids(self):
        return list(self.installable_ids)


def _plugins_toolbar_stub(plugins_view=None):
    stub = _Stub()
    stub.current_view = "plugins"
    stub._view_mode = "grid"
    stub.plugins_view = plugins_view or _ToolbarPluginsView()
    stub._plugins_install_btn = _FakeButton()
    stub._plugins_clear_btn = _FakeButton()
    stub._plugins_selection_label = _FakeLabel()
    stub.updates_table.checks_changed.connect(stub._on_table_checks_changed)
    return stub


def test_plugins_grid_installed_selection_enables_clear_only(qapp):
    """Selecting an installed card must show the Clear button (total selection
    counted) while Install Selected stays disabled — the old code counted only
    installable cards, so checking an installed row left the toolbar dead."""
    stub = _plugins_toolbar_stub(_ToolbarPluginsView([]))
    stub._plugins_install_btn.setEnabled(False)
    stub._plugins_clear_btn.setEnabled(False)

    stub._on_plugins_selection_changed(1)   # installed card checked

    assert stub._plugins_clear_btn.enabled is True
    assert stub._plugins_install_btn.enabled is False
    assert stub._plugins_selection_label.text == "1 plugin selected"


def test_plugins_grid_available_selection_enables_install_and_clear(qapp):
    """Available cards drive the full toolbar: Install Selected + Clear active
    and the label showing the count."""
    stub = _plugins_toolbar_stub(_ToolbarPluginsView(["timeshift"]))

    stub._on_plugins_selection_changed(2)

    assert stub._plugins_install_btn.enabled is True
    assert stub._plugins_clear_btn.enabled is True
    assert stub._plugins_selection_label.text == "2 plugins selected"


def test_plugins_list_selection_toolbar_install_and_clear(qapp):
    """List view: checking an available row must update the shared toolbar,
    Install Selected must install exactly the checked non-installed rows, and
    Clear must reset the table selection."""
    stub = _plugins_toolbar_stub(_FakePluginsView())
    stub._view_mode = "table"
    stub._sync_plugins_table()
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)

    table = stub.updates_table
    rows = table.model.packages()
    ts_row = next(i for i, p in enumerate(rows) if p.get("id") == "timeshift")
    table._toggle_check(ts_row, None)
    qapp.processEvents()

    assert stub._plugins_install_btn.enabled is True
    assert stub._plugins_clear_btn.enabled is True
    assert stub._plugins_selection_label.text == "1 plugin selected"

    stub._on_plugins_install_selected()

    assert ("install_many", ["timeshift"]) in calls

    stub._on_plugins_clear_selection()

    assert not table.model.checked_names()
    assert stub._plugins_selection_label.text == ""
    assert stub._plugins_install_btn.enabled is False
    assert stub._plugins_clear_btn.enabled is False


def test_plugins_list_rerenders_on_sort_change(qapp):
    """The list view must follow the source panel's Sort by menu like the
    grid does."""
    stub = _Stub()
    stub.current_view = "plugins"
    stub._view_mode = "table"
    stub.plugins_view = _FakePluginsView()
    stub._sync_plugins_table()

    assert [p["name"] for p in stub.updates_table.model.packages()] == ["BleachBit", "Timeshift"]

    stub.on_plugins_sort_changed("name_desc")

    assert [p["name"] for p in stub.updates_table.model.packages()] == ["Timeshift", "BleachBit"]


def test_plugins_list_installed_row_selects_enables_clear_only(qapp):
    """Toggling an installed row in list view must surface the toolbar's Clear
    button (like the grid cards) while Install Selected stays disabled and
    never targets the installed plugin."""
    stub = _plugins_toolbar_stub(_FakePluginsView())
    stub._view_mode = "table"
    stub._sync_plugins_table()
    calls = []
    stub.plugins_manager = _RecordingPluginsManager(calls)

    table = stub.updates_table
    rows = table.model.packages()
    bb_row = next(i for i, p in enumerate(rows) if p.get("id") == "bleachbit")
    assert rows[bb_row].get("_installed") is True

    table._toggle_check(bb_row, None)
    qapp.processEvents()

    assert table.model.is_installed_selected(rows[bb_row]) is True
    assert not table.model.checked_packages()
    assert stub._plugins_install_btn.enabled is False
    assert stub._plugins_clear_btn.enabled is True
    assert stub._plugins_selection_label.text == "1 plugin selected"

    stub._on_plugins_install_selected()
    assert not calls, "installed plugins must never be batch-installed"

    stub._on_plugins_clear_selection()
    qapp.processEvents()

    assert table.model.is_installed_selected(rows[bb_row]) is False
    assert stub._plugins_clear_btn.enabled is False
