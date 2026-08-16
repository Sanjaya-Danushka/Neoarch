"""Unit tests for the shared UpdatesTable: header select-all + empty state."""

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

