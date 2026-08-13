"""Unit tests for the Installed packages table (HoverTableWidget + delegate)."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QStyleOptionViewItem,
    QTableWidgetItem,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_table():
    from neoarch.frontend.components.installed_table import (
        HoverTableWidget,
        InstalledRowDelegate,
        ROLE_IS_DEP,
        ROLE_HAS_UPDATE,
    )

    table = HoverTableWidget(4, 6)
    delegate = InstalledRowDelegate(table)
    table.setItemDelegate(delegate)
    for c in range(6):
        table.setColumnWidth(c, 140)

    for r in range(4):
        name = QTableWidgetItem(f"pkg-{r}")
        name.setData(ROLE_IS_DEP, r == 1)
        name.setData(Qt.ItemDataRole.UserRole, {"id": f"pkg-{r}", "description": "A test package"})
        table.setItem(r, 1, name)
        table.setItem(r, 2, QTableWidgetItem(f"1.{r}.0-1"))
        table.setItem(r, 3, QTableWidgetItem(["pacman", "AUR", "Flatpak", "pacman"][r]))
        status = QTableWidgetItem("Update available" if r % 2 else "Up to date")
        status.setData(ROLE_HAS_UPDATE, r % 2)
        table.setItem(r, 4, status)
        table.setItem(r, 5, QTableWidgetItem(["12.4 MB", "—", "1.2 GB", "3.1 kB"][r]))

    return table, delegate


def test_delegate_installs_and_size(qapp):
    table, delegate = _make_table()
    assert table.itemDelegate() is delegate
    assert isinstance(delegate, __import__("neoarch.frontend.components.updates_table", fromlist=["UpdatesRowDelegate"]).UpdatesRowDelegate)
    assert delegate.sizeHint(None, None).height() == 52


def test_paint_all_cells_no_crash(qapp):
    table, delegate = _make_table()
    table.selectRow(2)
    table.set_hover_row(1)

    pix = QPixmap(900, 600)
    pix.fill(QColor(18, 19, 22))
    painter = QPainter(pix)
    try:
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                idx = table.model().index(r, c)
                opt = QStyleOptionViewItem()
                opt.initFrom(table)
                opt.index = idx
                opt.rect = table.visualRect(idx)
                opt.rect.setHeight(52)
                if r == 2:
                    opt.state |= QStyle.StateFlag.State_Selected
                delegate.paint(painter, opt, idx)  # should not raise
    finally:
        painter.end()


def test_pkg_at_builds_package_dict(qapp):
    table, delegate = _make_table()
    pkg = delegate.pkg_at(0)
    assert pkg["name"] == "pkg-0"
    assert pkg["version"] == "1.0.0-1"
    assert pkg["source"] == "pacman"
    assert pkg["has_update"] is False
    assert pkg["download_size"] == "12.4 MB"
    dep = delegate.pkg_at(1)
    assert dep["_dependency"] is True
    assert delegate.pkg_at(99) is None


def test_dependency_and_update_roles(qapp):
    table, delegate = _make_table()
    assert bool(table.item(1, 1).data(Qt.ItemDataRole.UserRole + 1)) is True
    assert bool(table.item(0, 1).data(Qt.ItemDataRole.UserRole + 1)) is False
    assert bool(table.item(1, 4).data(Qt.ItemDataRole.UserRole + 2)) is True
    assert bool(table.item(0, 4).data(Qt.ItemDataRole.UserRole + 2)) is False


def test_hover_table_tracks_rows(qapp):
    table, delegate = _make_table()
    assert table.hovered_row() == -1
    table.set_hover_row(3)
    assert table.hovered_row() == 3
    table.set_hover_row(-1)
    assert table.hovered_row() == -1
