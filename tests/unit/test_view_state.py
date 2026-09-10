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
        self._view_mode = "table"
        self._installing = False
        self._operation_view = None
        self.updates_table = UpdatesTable(_FakeApp())
        self.updates_table.set_enrich(False)
        self.package_table = UpdatesTable(_FakeApp())
        self.package_table.set_enrich(False)
        self.packages_grid = UpdatesTable(_FakeApp())
        self.packages_grid.set_enrich(False)
        self.log = lambda *a, **k: None


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
