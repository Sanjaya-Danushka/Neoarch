"""Unit tests for the shared hover-tracking table widget (HoverTableWidget)."""

import pytest
from PyQt6.QtWidgets import QApplication, QTableWidgetItem

from neoarch.frontend.components.installed_table import HoverTableWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_table():
    table = HoverTableWidget(4, 6)
    for c in range(6):
        table.setColumnWidth(c, 140)
    for r in range(4):
        table.setItem(r, 1, QTableWidgetItem(f"pkg-{r}"))
        table.setItem(r, 2, QTableWidgetItem(f"1.{r}.0-1"))
    return table


def test_hover_table_tracks_rows(qapp):
    table = _make_table()
    assert table.hovered_row() == -1
    table.set_hover_row(3)
    assert table.hovered_row() == 3
    table.set_hover_row(-1)
    assert table.hovered_row() == -1


def test_loading_toggle(qapp):
    table = _make_table()
    assert table._loading is False
    table.set_loading(True)
    assert table._loading is True
    table.set_loading(False)
    assert table._loading is False


def test_source_pixmap_fallback(qapp):
    table = _make_table()
    pm = table.source_pixmap("pacman", 16)
    assert not pm.isNull()
