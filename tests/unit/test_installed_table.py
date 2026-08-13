"""Unit tests for the Installed packages table delegate."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QStyleOptionViewItem,
    QTableWidget,
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
        InstalledTableDelegate,
        ROLE_IS_DEP,
        ROLE_HAS_UPDATE,
    )

    table = QTableWidget(4, 6)
    delegate = InstalledTableDelegate(table)
    table.setItemDelegate(delegate)
    for c in range(6):
        table.setColumnWidth(c, 140)

    for r in range(4):
        name = QTableWidgetItem(f"pkg-{r}")
        name.setData(ROLE_IS_DEP, r == 1)
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
    assert delegate.sizeHint(None, None).height() == 56


def test_paint_all_cells_no_crash(qapp):
    table, delegate = _make_table()
    table.selectRow(2)
    delegate._hover_row = 1

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
                opt.rect.setHeight(56)
                if r == 2:
                    opt.state |= QStyle.StateFlag.State_Selected
                delegate.paint(painter, opt, idx)  # should not raise
    finally:
        painter.end()


def test_dependency_and_update_roles(qapp):
    table, delegate = _make_table()
    assert bool(table.item(1, 1).data(Qt.ItemDataRole.UserRole + 1)) is True
    assert bool(table.item(0, 1).data(Qt.ItemDataRole.UserRole + 1)) is False
    assert bool(table.item(1, 4).data(Qt.ItemDataRole.UserRole + 2)) is True
    assert bool(table.item(0, 4).data(Qt.ItemDataRole.UserRole + 2)) is False


def test_hover_event_filter_tracks_rows(qapp):
    table, delegate = _make_table()
    assert delegate.hovered_row() == -1
    delegate._hover_row = 3
    assert delegate.hovered_row() == 3
