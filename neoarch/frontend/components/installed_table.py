"""Hover-tracking table widget used by the Discover / Bundles / Updates tables.

The Installed page renders through the shared `UpdatesTable` component, so
this module only provides `HoverTableWidget` - a QTableWidget that tracks
the hovered row for custom row painting.

Hover tracking uses event overrides (mouseMoveEvent / leaveEvent) instead of
an event filter so it stays safe at app shutdown - event filters get invoked
for every event, including internal ones during widget destruction, which can
abort a PyQt app at exit.
"""

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QTableWidget

from neoarch.frontend.components.updates_table import (
    _SOURCE_COLORS,
    _TEXT_SEC,
    _SkeletonOverlay,
    _make_fallback_pixmap,
)


class HoverTableWidget(QTableWidget):
    """QTableWidget that tracks the hovered row for custom row painting."""

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self._hover_row = -1
        self.setMouseTracking(True)
        self._skeleton = _SkeletonOverlay(self)
        self._skeleton.setVisible(False)
        self._loading = False

    def set_loading(self, loading):
        self._loading = bool(loading)
        self._sync_skeleton()

    def _sync_skeleton(self):
        viewport = self.viewport()
        geom = viewport.geometry() if viewport is not None else QRect()
        self._skeleton.setGeometry(geom)
        self._skeleton.setVisible(self._loading)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._loading:
            self._sync_skeleton()

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
