"""Premium installed-packages table delegate.

Custom QStyledItemDelegate for the Installed page's QTableWidget. It gives
rows the same premium treatment as the Updates table: rounded hover/selected
bands with an accent bar, a source-colored package tile, a dependency
subtitle, a source dot, a status chip, and right-aligned sizes.

The delegate is only installed while the Installed view is active; other
views reuse the default QTableWidget rendering.
"""

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QTableWidget

# theme constants shared with the updates table design
from neoarch.frontend.components.updates_table import (
    _ACCENT,
    _TEXT,
    _TEXT_SEC,
    _SOURCE_COLORS,
    _ROW_HOVER,
    _ROW_SELECTED,
    _SEPARATOR,
    _GREEN,
)

ROW_HEIGHT = 56

ROLE_IS_DEP = int(Qt.ItemDataRole.UserRole) + 1
ROLE_HAS_UPDATE = int(Qt.ItemDataRole.UserRole) + 2

_FALLBACK_SOURCE = QColor(163, 166, 176)


def _source_color(source):
    try:
        return _SOURCE_COLORS.get(source or "", _FALLBACK_SOURCE)
    except Exception:
        return _FALLBACK_SOURCE


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

    def hover_row(self):
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


class InstalledTableDelegate(QStyledItemDelegate):
    """Paints the Installed page rows in the app's premium row language."""

    def __init__(self, table):
        super().__init__(table)
        self._table = table

        self._name_font = QFont()
        self._name_font.setPointSize(10)
        self._name_font.setWeight(QFont.Weight.DemiBold)

        self._sub_font = QFont()
        self._sub_font.setPointSize(8)

        self._ver_font = QFont()
        self._ver_font.setPointSize(9)

        self._chip_font = QFont()
        self._chip_font.setPointSize(8)
        self._chip_font.setWeight(QFont.Weight.DemiBold)

    def _table_hover_row(self):
        try:
            hover_row = self._table.hover_row()
        except AttributeError:
            return -1
        return hover_row

    def sizeHint(self, option, index):
        return QSize(0, ROW_HEIGHT)

    def _row_rect(self, option):
        table = self._table
        try:
            left = table.columnViewportPosition(0)
            right = table.columnViewportPosition(table.columnCount() - 1) + table.columnWidth(table.columnCount() - 1)
        except Exception:
            return QRectF(option.rect)
        top = option.rect.top()
        height = max(option.rect.height(), table.verticalHeader().sectionSize(0))
        return QRectF(left, top, max(1, right - left), height)

    # ── paint ─────────────────────────────────────────────────────────
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        table = self._table
        row = index.row()
        col = index.column()
        rect = QRectF(option.rect)

        self._paint_row_band(painter, self._row_rect(option), option)

        painter.save()
        painter.setClipRect(rect)
        if col == 1:
            self._paint_name(painter, rect, table, row)
        elif col == 2:
            self._paint_version(painter, rect, table, row)
        elif col == 3:
            self._paint_source(painter, rect, table, row)
        elif col == 4:
            self._paint_status(painter, rect, table, row)
        elif col == 5:
            self._paint_size(painter, rect, table, row)
        painter.restore()
        painter.restore()

    def _paint_row_band(self, painter, rect, option):
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = self._table_hover_row() == option.index.row()

        if selected:
            band = QRectF(rect.left() + 2, rect.top() + 1, rect.width() - 4, rect.height() - 2)
            path = QPainterPath()
            path.addRoundedRect(band, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, _ROW_SELECTED)
            bar = QRectF(rect.left() + 2, band.top() + 7, 3, band.height() - 14)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(bar, 2, 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_ACCENT)
            painter.drawPath(bar_path)
        elif hovered:
            band = QRectF(rect.left() + 2, rect.top() + 1, rect.width() - 4, rect.height() - 2)
            path = QPainterPath()
            path.addRoundedRect(band, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, _ROW_HOVER)

        if not selected:
            pen = QPen(_SEPARATOR)
            pen.setWidthF(1)
            painter.setPen(pen)
            painter.drawLine(QPointF(rect.left() + 14, rect.bottom()), QPointF(rect.right() - 14, rect.bottom()))

    def _item(self, table, row, col):
        try:
            return table.item(row, col)
        except Exception:
            return None

    def _paint_name(self, painter, rect, table, row):
        name_item = self._item(table, row, 1)
        if name_item is None:
            return
        name = name_item.text() or ""
        source_item = self._item(table, row, 3)
        source = source_item.text() if source_item else ""
        color = _source_color(source)

        tile = 20
        ix = rect.left() + 12
        iy = rect.top() + (rect.height() - tile) / 2
        tile_rect = QRectF(ix, iy, tile, tile)
        path = QPainterPath()
        path.addRoundedRect(tile_rect, 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(path, color)

        letter = name[0].upper() if name else "?"
        painter.setFont(self._sub_font)
        painter.setPen(_TEXT)
        painter.drawText(tile_rect, Qt.AlignmentFlag.AlignCenter, letter)

        text_left = ix + tile + 10
        avail_w = max(20, rect.right() - text_left - 4)
        is_dep = bool(name_item.data(ROLE_IS_DEP))

        if is_dep:
            name_fm = QFontMetrics(self._name_font)
            name_el = name_fm.elidedText(name, Qt.TextElideMode.ElideRight, int(avail_w))
            painter.setFont(self._name_font)
            painter.setPen(_TEXT)
            painter.drawText(QRectF(text_left, rect.top() + 7, avail_w, 16),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                             name_el)
            painter.setFont(self._sub_font)
            painter.setPen(_TEXT_SEC)
            painter.drawText(QRectF(text_left, rect.top() + 26, avail_w, 14),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                             "Dependency")
        else:
            name_fm = QFontMetrics(self._name_font)
            name_el = name_fm.elidedText(name, Qt.TextElideMode.ElideRight, int(avail_w))
            painter.setFont(self._name_font)
            painter.setPen(_TEXT)
            painter.drawText(QRectF(text_left, rect.top(), avail_w, rect.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                             name_el)

    def _paint_version(self, painter, rect, table, row):
        ver_item = self._item(table, row, 2)
        text = ver_item.text() if ver_item else ""
        if text.startswith("v"):
            text = text[1:]
        fm = QFontMetrics(self._ver_font)
        el = fm.elidedText(text or "—", Qt.TextElideMode.ElideMiddle, int(max(20, rect.width() - 12)))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 6, rect.top(), rect.width() - 12, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         el)

    def _paint_source(self, painter, rect, table, row):
        src_item = self._item(table, row, 3)
        text = src_item.text() if src_item else ""
        color = _source_color(text)
        fm = QFontMetrics(self._chip_font)
        avail = max(10, rect.width() - 20)
        el = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(avail))
        dot = 6
        x = rect.left() + 10
        cy = rect.top() + (rect.height() - dot) / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(x + dot / 2, cy + dot / 2), dot / 2, dot / 2)
        painter.setFont(self._chip_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(x + dot + 8, rect.top(), avail, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         el)

    def _paint_status(self, painter, rect, table, row):
        status_item = self._item(table, row, 4)
        if status_item is None:
            return
        has_update = bool(status_item.data(ROLE_HAS_UPDATE))
        text = status_item.text() or ("Update available" if has_update else "Up to date")
        color = QColor(248, 165, 90) if has_update else _GREEN

        fm = QFontMetrics(self._chip_font)
        avail = max(24, rect.width() - 12)
        dot = 6
        tw = fm.horizontalAdvance(text)
        max_tw = max(10, avail - 26 - dot - 6)
        if tw > max_tw:
            text = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(max_tw))
            tw = fm.horizontalAdvance(text)
        total = 26 + dot + 6 + tw
        x = rect.left() + max(4, (rect.width() - total) / 2)
        cy = rect.top() + (rect.height() - 24) / 2
        chip = QRectF(x, cy, total, 24)
        path = QPainterPath()
        path.addRoundedRect(chip, 12, 12)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.fillPath(path, QColor(255, 255, 255, 10))
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(chip.left() + 13, chip.center().y()), dot / 2, dot / 2)
        painter.setFont(self._chip_font)
        painter.setPen(_TEXT)
        painter.drawText(QRectF(chip.left() + 13 + dot + 6, chip.top(), tw, chip.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         text)

    def _paint_size(self, painter, rect, table, row):
        size_item = self._item(table, row, 5)
        text = size_item.text() if size_item else "—"
        fm = QFontMetrics(self._ver_font)
        el = fm.elidedText(text, Qt.TextElideMode.ElideLeft, int(max(12, rect.width() - 14)))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 4, rect.top(), rect.width() - 14, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextSingleLine,
                         el)
