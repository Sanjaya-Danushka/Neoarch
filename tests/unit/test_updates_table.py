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
    assert table._skeleton.isHidden() is False
    assert table._empty.isHidden() is True
    table.set_loading(False)
    assert table._skeleton.isHidden() is True
    assert table._empty.isHidden() is False


def test_skeleton_mirrors_table_columns_and_paints(qapp):
    from PyQt6.QtGui import QPixmap

    table = _make_table()
    table.resize(980, 560)
    table.show()
    table.set_loading(True)
    qapp.processEvents()

    cols = table._skeleton._columns()
    assert len(cols) == table.model.columnCount()
    assert cols[0] == (0, 46)
    assert cols[6][1] == 44

    for phase in (5, 30):
        table._skeleton._phase = phase
        pix = QPixmap(table.size())
        table.render(pix)
        assert not pix.isNull()

