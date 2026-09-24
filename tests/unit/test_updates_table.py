"""Unit tests for the shared UpdatesTable: header select-all + empty state."""

import time

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.components.updates_table import UpdatesTable


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
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


def _click_header(header, section=0):
    x = header.sectionViewportPosition(section) + header.sectionSize(section) // 2
    ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(x, 10),
                     QPointF(x, 10), Qt.MouseButton.LeftButton,
                     Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    header.mousePressEvent(ev)


def test_header_select_all_toggles_off(qapp):
    table = _make_table()
    header = table.horizontalHeader()
    model = table.model
    _click_header(header)
    assert len(model._checked) == 4
    assert model.is_all_checked() is True
    assert header._checked is True
    _click_header(header)
    assert len(model._checked) == 0
    assert model.is_all_checked() is False
    assert header._checked is False


def test_header_indeterminate_and_clears_partial(qapp):
    table = _make_table()
    header = table.horizontalHeader()
    model = table.model
    model.setData(model.index(0, 0), Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    model.setData(model.index(1, 0), Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    assert header._indeterminate is True
    assert header._checked is False
    _click_header(header)
    assert len(model._checked) == 0
    assert header._checked is False
    assert header._indeterminate is False


def test_empty_state_wording_configurable(qapp):
    table = _make_table()
    table.set_packages([])
    assert table._empty._title.text() == "All caught up"
    assert not table._empty._hint.isHidden()
    table.set_empty_text("No installed packages",
                         "Packages installed on this system will appear here")
    assert table._empty._title.text() == "No installed packages"
    assert table._empty._sub.text() == "Packages installed on this system will appear here"
    assert table._empty._hint.isHidden()


def test_empty_state_hidden_while_loading(qapp):
    table = _make_table()
    table.set_packages([])
    table.set_loading(True)
    assert table._empty.isHidden() is False
    assert table._empty._progress.isHidden() is False
    table.set_loading(False)
    assert table._empty.isHidden() is False
    assert table._empty._progress.isHidden() is True


def test_loading_clears_stale_rows(qapp):
    table = _make_table()
    assert table.row_count() == 4
    table.set_loading(True)
    assert table.row_count() == 0
    assert table.model._checked == set()
    table.set_packages([
        {"name": "pkg-a", "id": "pkg-a", "version": "1.0",
         "new_version": "1.0", "source": "pacman"}
    ])
    assert table.row_count() == 1
    assert table._loading is False


def test_loading_state_shows_loading_text_and_message(qapp):
    table = _make_table()
    table.set_loading(True, "Loading updates\u2026")
    assert table._empty._title.text() == "Loading updates\u2026"
    assert table._empty._progress.isHidden() is False
    table.set_loading(True)
    assert table._empty._title.text() == "Loading updates\u2026"


def test_plugins_mode_hides_version_size_and_installed_columns(qapp):
    table = UpdatesTable(_FakeApp())
    table.set_plugins_mode(True)
    assert table._plugins_mode is True
    assert table._discover_mode is False
    assert table._installed_mode is False
    assert table._enrich is False
    assert table.isColumnHidden(2) is True
    assert table.isColumnHidden(3) is True
    assert table.isColumnHidden(6) is True
    header = table.horizontalHeader()
    assert header._labels == ["", "Plugin", "", "", "Source", "Status", "", ""]
    table.set_plugins_mode(False)
    assert header._labels is None
    assert table.isColumnHidden(2) is False
    assert table.isColumnHidden(3) is False
    assert table.isColumnHidden(6) is False


def test_plugins_mode_row_menu_actions(qapp):
    table = UpdatesTable(_FakeApp())
    table.set_enrich(False)
    table.set_plugins_mode(True)
    table.set_packages([
        {"name": "plug-a", "id": "plug-a", "version": "1.0",
         "new_version": "1.0", "source": "pacman", "_installed": True},
        {"name": "plug-b", "id": "plug-b", "version": "1.0",
         "new_version": "1.0", "source": "AUR", "_installed": False},
    ])
    emitted = []
    table.menu_action.connect(lambda action, pkg: emitted.append((action, pkg["id"])))

    menu_installed = table._build_row_menu(table.model.package_at(0))
    actions = [a.text() for a in menu_installed.actions()]
    assert "Launch" in actions
    assert "Uninstall" in actions
    assert "Install" not in actions
    assert "View Details" not in actions
    menu_installed.actions()[0].trigger()

    menu_available = table._build_row_menu(table.model.package_at(1))
    actions = [a.text() for a in menu_available.actions()]
    assert "Install" in actions
    assert "Launch" not in actions
    assert "Uninstall" not in actions
    menu_available.actions()[0].trigger()

    assert emitted == [("launch", "plug-a"), ("install", "plug-b")]


def test_plugins_are_cards_only_not_table_rows(qapp):
    # The plugins page is cards-only; no table-mode row mapping should exist.
    from neoarch.frontend.components.plugins_view import PluginsView
    assert not hasattr(PluginsView, "_map_plugin_row")
    assert not hasattr(PluginsView, "_plugins_table")


def test_aur_menu_group_only_for_aur_rows(qapp):
    table = UpdatesTable(_FakeApp())
    table.set_enrich(False)
    table.set_discover_mode(True)
    table.set_packages([
        {"name": "official-pkg", "id": "official-pkg", "version": "1.0",
         "new_version": None, "source": "pacman"},
        {"name": "community-pkg", "id": "community-pkg", "version": "2.0",
         "new_version": None, "source": "AUR"},
    ])
    emitted = []
    table.menu_action.connect(lambda action, pkg: emitted.append((action, pkg["id"])))

    pacman_menu = table._build_row_menu(table.model.package_at(0))
    pacman_actions = [a.text() for a in pacman_menu.actions()]
    assert "View PKGBUILD" not in pacman_actions
    assert "View Changes" not in pacman_actions
    assert "Download snapshot" not in pacman_actions

    aur_menu = table._build_row_menu(table.model.package_at(1))
    aur_actions = [a.text() for a in aur_menu.actions()]
    assert "View PKGBUILD" in aur_actions
    assert "View Changes" in aur_actions
    assert "Download snapshot" in aur_actions

    by_text = {a.text(): a for a in aur_menu.actions()}
    by_text["View PKGBUILD"].trigger()
    by_text["View Changes"].trigger()
    by_text["Download snapshot"].trigger()
    assert emitted == [
        ("pkgbuild", "community-pkg"),
        ("changes", "community-pkg"),
        ("snapshot", "community-pkg"),
    ]


def test_enrich_restarts_after_disable(qapp, monkeypatch):
    """Leaving to the Installed page disables enrichment; returning to the
    Updates page must re-enable it or pacman sizes stay blank."""
    from neoarch.frontend.components.updates_table import _EnrichWorker

    calls = []

    def fake_fetch(self):
        calls.append(len(self._packages))
        time.sleep(0.2)
        return {}

    monkeypatch.setattr(_EnrichWorker, "fetch_meta", fake_fetch)

    table = UpdatesTable(None)
    pkg = {"name": "shadow", "version": "1", "new_version": "2", "source": "pacman"}

    table.set_enrich(False)
    table.set_packages([dict(pkg)])
    assert calls == []

    table.set_enrich(True)
    table.set_packages([dict(pkg)])
    for _ in range(50):
        if calls:
            break
        qapp.processEvents()
        time.sleep(0.05)
    assert calls == [1]


def test_set_packages_stamps_repo_from_cached_map(qapp, monkeypatch):
    monkeypatch.setattr("neoarch.frontend.components.updates_table.get_repo_map",
                        lambda: {"pkg-0": "core", "pkg-2": "extra"})
    table = _make_table()
    assert table.model.package_at(0)["repo"] == "core"
    assert table.model.package_at(2)["repo"] == "extra"
    assert "repo" not in table.model.package_at(1)


def test_stamp_repos_fills_pacman_rows(qapp):
    table = _make_table()
    table.model.stamp_repos({"pkg-0": "core", "pkg-1": "extra"})
    assert table.model.package_at(0)["repo"] == "core"
    assert table.model.package_at(1)["repo"] == "extra"
    assert "repo" not in table.model.package_at(2)


def test_stamp_repos_skips_non_pacman_and_existing_repo(qapp):
    table = UpdatesTable(_FakeApp())
    table.set_enrich(False)
    table.set_packages([
        {"name": "aaa-official", "id": "aaa-official", "version": "1.0",
         "new_version": "1.0", "source": "pacman", "repo": "core"},
        {"name": "zzz-aur", "id": "zzz-aur", "version": "1.0",
         "new_version": "1.0", "source": "AUR"},
    ])
    table.model.stamp_repos({"aaa-official": "extra", "zzz-aur": "aur"})
    assert table.model.package_at(0)["repo"] == "core"
    assert "repo" not in table.model.package_at(1)


def test_stamp_repos_does_nothing_for_unknown_names(qapp):
    table = _make_table()
    table.model.stamp_repos({"nothing-here": "extra"})
    for i in range(table.row_count()):
        assert "repo" not in table.model.package_at(i)


def test_on_repos_ready_stamps_rows(qapp):
    table = _make_table()
    table._on_repos_ready({"pkg-1": "multilib"})
    assert table.model.package_at(1)["repo"] == "multilib"


def test_enrich_apply_section_captures_repository():
    from neoarch.frontend.components.updates_table import _EnrichWorker
    meta = {}
    _EnrichWorker._apply_section(
        meta,
        {"Name": "7zip", "Repository": "extra", "Description": "file archiver",
         "Download Size": "1.50 MiB"},
    )
    assert meta["7zip"]["repo"] == "extra"
    assert meta["7zip"]["description"] == "file archiver"
    assert meta["7zip"]["download_size"] == "1.50 MiB"


def test_discover_mapping_keeps_repo():
    from neoarch.frontend.mixins.views import _ViewsMixin

    class _Stub:
        def is_package_installed(self, pkg):
            return False

        def log(self, *args, **kwargs):
            pass

    out = _ViewsMixin._map_discover_pkg(
        _Stub(),
        {"name": "7zip", "id": "pacman-7zip", "version": "1.0",
         "source": "pacman", "repo": "extra"},
    )
    assert out["source"] == "pacman"
    assert out["repo"] == "extra"
    assert out["name"] == "7zip"

