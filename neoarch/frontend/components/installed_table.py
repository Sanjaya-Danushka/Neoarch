"""Installed packages table, reusing the Updates table's premium row design.

The Installed page keeps its QTableWidget (checkbox widgets synced to row
selection, pagination, context menu, sort menu, detail card) but its rows
are painted by a delegate that subclasses the Updates table's row delegate.
That means the exact same paint code draws both tables: dark glass hover /
selected bands with an accent bar, package tile, two-line package cell,
single-line version, source label, status chip and right-aligned size.
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QTableWidget

from neoarch.frontend.components.updates_table import (
    UpdatesRowDelegate,
    _GREEN,
    _SOURCE_COLORS,
    _TEXT_SEC,
    _make_fallback_pixmap,
)

ROLE_IS_DEP = int(Qt.ItemDataRole.UserRole) + 1
ROLE_HAS_UPDATE = int(Qt.ItemDataRole.UserRole) + 2

_UPDATE_ORANGE = QColor(248, 165, 90)
_STATUS_COLORS = {
    "Update available": _UPDATE_ORANGE,
    "Up to date": _GREEN,
}


class HoverTableWidget(QTableWidget):
    """QTableWidget that tracks the hovered row for custom row painting.

    Uses event overrides (mouseMoveEvent / leaveEvent) instead of an event
    filter so hover tracking is safe at app shutdown - event filters get
    invoked for every event, including internal ones during widget
    destruction, which can abort a PyQt app at exit.
    """

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self._hover_row = -1
        self.setMouseTracking(True)

    def hovered_row(self):
        return self._hover_row

    def set_hover_row(self, row):
        if row != self._hover_row:
            self._hover_row = row
            viewport = self.viewport()
            if viewport is not None:
                viewport.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        self.set_hover_row(self.indexAt(pos).row())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.set_hover_row(-1)
        super().leaveEvent(event)

    def source_pixmap(self, source, size=16):
        """Same API as UpdatesTable.source_pixmap so the shared row paint
        code can draw the package tile regardless of table class."""
        delegate = self.itemDelegate()
        if delegate is not None and hasattr(delegate, "source_pixmap"):
            return delegate.source_pixmap(source, size)
        return _make_fallback_pixmap(size, _SOURCE_COLORS.get(source or "", _TEXT_SEC))


class InstalledRowDelegate(UpdatesRowDelegate):
    """Paints Installed rows with the shared Updates row paint code."""

    def __init__(self, table, app=None):
        super().__init__(table)
        self._app = app
        self._pix_cache = {}

    # ── per-row package data (built from the QTableWidget items) ──────
    def pkg_at(self, row):
        table = self._table

        def item(col):
            try:
                return table.item(row, col)
            except Exception:
                return None

        name_item = item(1)
        if name_item is None:
            return None
        name = name_item.text() or ""
        stored = {}
        try:
            stored = name_item.data(Qt.ItemDataRole.UserRole) or {}
        except Exception:
            stored = {}

        source_item = item(3)
        source = source_item.text() if source_item else ""

        status_item = item(4)
        has_update = False
        if status_item is not None:
            try:
                has_update = bool(status_item.data(ROLE_HAS_UPDATE))
            except Exception:
                has_update = False

        is_dep = False
        try:
            is_dep = bool(name_item.data(ROLE_IS_DEP))
        except Exception:
            is_dep = False

        version_item = item(2)
        size_item = item(5)
        pkg = {
            "name": name,
            "id": stored.get("id", name),
            "version": version_item.text() if version_item else "",
            "source": source,
            "description": stored.get("description", ""),
            "has_update": has_update,
            "download_size": size_item.text() if size_item else "",
        }
        if is_dep:
            pkg["_dependency"] = True
        return pkg

    # ── icons (same provider chain as UpdatesTable.source_pixmap) ─────
    def source_pixmap(self, source, size=16):
        key = ("src", source, size)
        if key in self._pix_cache:
            return self._pix_cache[key]
        pm = None
        if self._app is not None:
            try:
                icon = self._app.get_source_icon(source, size)
                if icon and not icon.isNull():
                    pm = icon.pixmap(size, size)
            except Exception:
                pm = None
        if pm is None or pm.isNull():
            pm = _make_fallback_pixmap(size, _SOURCE_COLORS.get(source or "", _TEXT_SEC))
        self._pix_cache[key] = pm
        return pm

    # ── paint (reuses the Updates delegate's paint methods) ───────────
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect = QRectF(option.rect)
        row = index.row()
        col = index.column()
        row_rect = self._row_rect(option)

        self._paint_row_background(painter, row_rect, option, row)

        pkg = self.pkg_at(row)
        if pkg is None:
            painter.restore()
            return

        # Clip all cell content to its own column so nothing overlaps neighbors
        painter.save()
        painter.setClipRect(rect)

        if col == 1:
            self._paint_package(painter, rect, option, pkg)
        elif col == 2:
            self._paint_version(painter, rect, pkg, row)
        elif col == 3:
            self._paint_label(painter, rect, pkg.get("source", ""), _TEXT_SEC)
        elif col == 4:
            self._paint_status(painter, rect, pkg)
        elif col == 5:
            self._paint_size(painter, rect, pkg)
        painter.restore()
        painter.restore()

    def _paint_package(self, painter, rect, option, pkg):
        if pkg.get("_dependency"):
            pkg = dict(pkg)
            pkg["description"] = "Dependency"
        super()._paint_package(painter, rect, option, pkg)

    def _paint_status(self, painter, rect, pkg):
        text = "Update available" if pkg.get("has_update") else "Up to date"
        self._paint_chip(painter, rect, text, _STATUS_COLORS.get(text, _TEXT_SEC))
