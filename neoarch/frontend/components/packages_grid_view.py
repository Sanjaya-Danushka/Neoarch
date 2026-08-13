"""PackagesGridView - Card-based grid view alternative to the table.

Cards follow the same design language as the UpdatesTable: dark glass
surfaces, mint accent #00BFAE, source tiles, stacked version arrow and
colored-dot status chips.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
    QLinearGradient, QRadialGradient, QPixmap,
)

from neoarch.frontend.components.updates_table import _EmptyOverlay

# ── theme (matches updates_table.py) ──────────────────────────────────
_ACCENT = QColor(0, 191, 174)
_TEXT = QColor(238, 240, 244)
_TEXT_SEC = QColor(139, 141, 151)
_TEXT_MUTED = QColor(92, 94, 102)
_GREEN = QColor(88, 202, 143)

_SOURCE_COLORS = {
    "pacman": QColor(79, 195, 247),
    "AUR": QColor(255, 138, 101),
    "Flatpak": QColor(38, 166, 154),
    "npm": QColor(229, 57, 53),
    "Local": QColor(163, 166, 176),
    "Docker": QColor(36, 150, 237),
}

_STATUS_COLORS = {
    "Security": QColor(248, 113, 113),
    "Feature": QColor(96, 165, 250),
    "Bug Fix": QColor(93, 199, 139),
    "Maintenance": QColor(163, 166, 176),
    "Installed": QColor(93, 199, 139),
    "Available": QColor(163, 166, 176),
}


def _card_qss(checked: bool) -> str:
    """Dark black glass gradient, matching the updates table glass
    (#16171A → #0D0D0F). Rendered by Qt's style engine (safe with
    translucent colors, unlike QPainter gradient fills)."""
    if checked:
        body = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(24, 45, 45, 0.96),
        stop:0.5 rgba(17, 34, 36, 0.94),
        stop:1 rgba(12, 20, 24, 0.97));
    border: 1px solid rgba(0, 191, 174, 0.5);
    border-top: 1px solid rgba(0, 191, 174, 0.72);"""
        hover = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(29, 53, 53, 0.97),
        stop:0.5 rgba(21, 41, 43, 0.95),
        stop:1 rgba(15, 24, 29, 0.97));
    border: 1px solid rgba(0, 191, 174, 0.68);
    border-top: 1px solid rgba(0, 191, 174, 0.9);"""
    else:
        body = """
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(24, 25, 29, 0.94),
        stop:0.5 rgba(18, 19, 22, 0.92),
        stop:1 rgba(12, 13, 15, 0.96));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top: 1px solid rgba(255, 255, 255, 0.14);"""
        hover = """
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(31, 33, 38, 0.96),
        stop:0.5 rgba(23, 24, 28, 0.94),
        stop:1 rgba(15, 16, 19, 0.97));
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-top: 1px solid rgba(255, 255, 255, 0.26);"""
    return f"""
QFrame#packageCard {{
{body}
    border-radius: 18px;
}}
QFrame#packageCard:hover {{
{hover}
    border-radius: 18px;
}}
"""


def _make_glow_pixmap(size: QSize) -> QPixmap:
    """Soft blue ambient glow from the upper-left corner, pre-rendered so the
    live paint path only ever blits a pixmap (avoids the translucent-gradient
    QPainter fill crash seen with custom paintEvent fills)."""
    pm = QPixmap(size.width(), size.height())
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = size.width(), size.height()
    g = QRadialGradient(w * 0.08, h * 0.06, max(w, h) * 0.7)
    g.setColorAt(0.0, QColor(59, 130, 246, 42))
    g.setColorAt(0.5, QColor(59, 130, 246, 8))
    g.setColorAt(1.0, QColor(59, 130, 246, 0))
    p.fillRect(0, 0, w, h, g)
    p.end()
    return pm


def _fallback_description(pkg):
    source = pkg.get("source", "")
    return {
        "pacman": "Official repository package",
        "AUR": "Arch User Repository package",
        "Flatpak": "Flatpak application",
        "npm": "Global npm package",
        "Local": "Local package",
    }.get(source, "Package")


def classify_update(current, new):
    """Best-effort classification (mirrors updates_table.classify_update)."""
    import re

    def parse(v):
        return [int(m.group()) for m in re.finditer(r"\d+", str(v))] or [0]

    cur, newv = parse(current), parse(new)
    if not cur or not newv:
        return "Maintenance"
    for i in range(min(len(cur), len(newv))):
        if newv[i] > cur[i]:
            if i == 0:
                return "Security"
            if i == 1:
                return "Feature"
            return "Bug Fix"
    if len(newv) > len(cur) and newv[len(cur)] > 0:
        return "Bug Fix"
    return "Maintenance"


class _CheckBox(QWidget):
    """Custom checkbox painted exactly like the UpdatesTable row checkbox."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)

    def toggle(self):
        self.setChecked(not self._checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        csize = 18
        r = QRectF((self.width() - csize) / 2, (self.height() - csize) / 2, csize, csize)
        path = QPainterPath()
        path.addRoundedRect(r, 5, 5)
        if self._checked:
            p.fillPath(path, _ACCENT)
            pen = QPen(QColor(255, 255, 255), 1.9)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(r.left() + 4, r.center().y()), QPointF(r.center().x() - 1, r.bottom() - 4))
            p.drawLine(QPointF(r.center().x() - 1, r.bottom() - 4), QPointF(r.right() - 3, r.top() + 4))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            p.fillPath(path, QColor(255, 255, 255, 14))
            p.drawPath(path)
        p.end()


class _SourceLogo(QWidget):
    """Real source logo (pacman/AUR/flatpak/npm SVG) with letter fallback."""

    def __init__(self, app, source, size=30, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._app = app
        self._source = source
        self._size = size
        self._pm = None
        if app is not None:
            try:
                icon = app.get_source_icon(source, size)
                if icon and not icon.isNull():
                    self._pm = icon.pixmap(size, size)
            except Exception:
                self._pm = None
        self.setToolTip(source)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._pm is not None and not self._pm.isNull():
            p.drawPixmap((self.width() - self._pm.width()) // 2,
                         (self.height() - self._pm.height()) // 2, self._pm)
            p.end()
            return
        r = QRectF(self.rect())
        c = _SOURCE_COLORS.get(self._source, _TEXT_MUTED)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, c.lighter(115))
        grad.setColorAt(1.0, c.darker(110))
        path = QPainterPath()
        path.addRoundedRect(r, r.width() / 4, r.width() / 4)
        p.fillPath(path, grad)
        p.setFont(_small_font(int(self._size / 2.6), QFont.Weight.Bold))
        p.setPen(QColor(12, 12, 14))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, (self._source or "?")[0].upper())
        p.end()


class _Chip(QWidget):
    """Pill chip with a colored status dot — matches the table's status chip."""

    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        self._text = text
        self._color = color
        fm = QFontMetrics(_small_font(8, QFont.Weight.DemiBold))
        tw = fm.horizontalAdvance(text)
        self.setFixedSize(26 + 6 + 6 + tw, 22)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        chip = QRectF(0, (self.height() - 22) / 2, self.width(), 22)
        path = QPainterPath()
        path.addRoundedRect(chip, 11, 11)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.fillPath(path, QColor(255, 255, 255, 10))
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QPointF(chip.left() + 13, chip.center().y()), 3, 3)
        p.setFont(_small_font(8, QFont.Weight.DemiBold))
        p.setPen(_TEXT)
        p.drawText(QRectF(chip.left() + 13 + 6 + 6, chip.top(), self.width() - 25, chip.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._text)
        p.end()


class _SmallLabel(QLabel):
    """Eliding label with a fixed font weight/size."""

    def __init__(self, text, pt, weight, color, parent=None):
        super().__init__(text, parent)
        f = _small_font(pt, weight)
        self.setFont(f)
        self._color = QColor(color)
        self.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setWordWrap(False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self.font())
        p.setPen(self._color)
        fm = QFontMetrics(self.font())
        text = fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.end()


def _small_font(pt, weight):
    f = QFont()
    f.setPointSizeF(pt)
    f.setWeight(weight)
    return f


class PackageCard(QFrame):
    """A single package card matching the UpdatesTable design language."""

    toggled = pyqtSignal(int, bool)
    clicked = pyqtSignal(int, object)

    CARD_W = 268
    CARD_H = 148

    def __init__(self, pkg: dict, row: int, app=None, parent=None):
        super().__init__(parent)
        self.row = row
        self.pkg = pkg
        self._app = app
        self._glow = None
        self.setObjectName("packageCard")
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self._apply_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 9)
        layout.setSpacing(3)

        # ── top: logo + name + checkbox ────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(9)

        self.logo = _SourceLogo(self._app, self.pkg.get("source", ""), 26)
        top.addWidget(self.logo)

        self.name_label = _SmallLabel(
            self.pkg.get("name") or self.pkg.get("id") or "",
            11, QFont.Weight.Bold, "#EEF0F4")
        self.name_label.setToolTip(self.pkg.get("name") or self.pkg.get("id") or "")
        top.addWidget(self.name_label, 1)

        self.checkbox = _CheckBox()
        self.checkbox.toggled.connect(self._on_check)
        top.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top)

        # ── description ────────────────────────────────────────────────
        desc = self.pkg.get("description") or _fallback_description(self.pkg)
        self.desc_label = _SmallLabel(desc, 8, QFont.Weight.Normal, "#8B8D97")
        self.desc_label.setToolTip(desc)
        layout.addWidget(self.desc_label)

        # ── extra detail: tags (AUR keywords) ──────────────────────────
        tags = self.pkg.get("tags") or ""
        self.tags_label = None
        if tags:
            self.tags_label = _SmallLabel(tags, 7, QFont.Weight.Normal, "#5C5E66")
            self.tags_label.setToolTip(tags)
            layout.addWidget(self.tags_label)

        layout.addStretch()

        # ── bottom: version transition + size + status chip ────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(7)

        current = self.pkg.get("version") or ""
        new = self.pkg.get("new_version") or current
        has_update = bool(new) and new != current

        self.cur_label = _SmallLabel(current or "\u2014", 8.5, QFont.Weight.Normal, "#9AA0AB")
        bottom.addWidget(self.cur_label)

        self.arrow_label = None
        self.new_label = None
        if has_update:
            self.arrow_label = _SmallLabel("\u2192", 8.5, QFont.Weight.Normal, "#5C5E66")
            bottom.addWidget(self.arrow_label)
            self.new_label = _SmallLabel(new, 8.5, QFont.Weight.DemiBold, "#58CA8D")
            self.new_label.setToolTip(new)
            bottom.addWidget(self.new_label)
        else:
            self.new_label = None

        bottom.addStretch(1)

        self.size_label = _SmallLabel(self.pkg.get("download_size") or "",
                                      8, QFont.Weight.Normal, "#8B8D97")
        self.size_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.size_label.setVisible(bool(self.pkg.get("download_size")))
        bottom.addWidget(self.size_label)

        if self.pkg.get("has_update"):
            status = "Update"
        elif has_update:
            status = self.pkg.get("status") or classify_update(current, new)
        elif self.pkg.get("installed") or self.pkg.get("_installed"):
            status = "Installed"
        else:
            status = "Available"
        self.status_chip = _Chip(status, _STATUS_COLORS.get(status, _TEXT_MUTED))
        bottom.addWidget(self.status_chip, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(bottom)

    def _apply_style(self):
        self.setStyleSheet(_card_qss(False))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # pre-rendered ambient glow (pixmap blit is safe)
        if self._glow is None or self._glow.size() != self.size():
            self._glow = _make_glow_pixmap(self.size())
        p.drawPixmap(0, 0, self._glow)

        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        # glass top reflection, clipped to the rounded card
        p.save()
        card_path = QPainterPath()
        card_path.addRoundedRect(rect, 18, 18)
        reflect = QPainterPath()
        reflect.addRect(QRectF(rect.left(), rect.top(), rect.width(), 9))
        p.setClipPath(card_path.intersected(reflect))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawLine(QPointF(rect.left() + 16, rect.top() + 1),
                   QPointF(rect.right() - 16, rect.top() + 1))
        p.restore()

        # selected: accent bar like the table's selected row
        if self.checkbox.isChecked():
            bar = QRectF(rect.left() + 2, rect.top() + 7, 3, rect.height() - 14)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(bar, 1.5, 1.5)
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(bar_path, _ACCENT)

        p.end()

    def _on_check(self, state):
        self.setStyleSheet(_card_qss(bool(state)))
        self.update()
        self.toggled.emit(self.row, state)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            self.clicked.emit(self.row, self.pkg)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()


class PackagesGridView(QScrollArea):
    """Scrollable grid of package cards."""

    card_selected = pyqtSignal(object)
    card_cleared = pyqtSignal()
    load_more_requested = pyqtSignal()

    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self._app = app
        self._selected_row = -1
        self.setWidgetResizable(True)
        self.setVisible(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._loading_more = False
        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.03);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(10, 10, 10, 10)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self._container)

        self._cards: list[PackageCard] = []
        self._cols = 3

        # "All caught up" empty state, same overlay as the updates table
        self._empty = _EmptyOverlay(self.viewport())
        self._empty.setGeometry(self.viewport().rect())
        self._empty.setVisible(False)

    def resizeEvent(self, e):
        self._relayout()
        self._sync_empty()
        super().resizeEvent(e)

    def _on_scroll(self, value):
        bar = self.verticalScrollBar()
        if bar.maximum() > 0 and value >= bar.maximum() - 10:
            if not self._loading_more:
                self._loading_more = True
                self.load_more_requested.emit()

    def set_loading_more(self, loading: bool):
        self._loading_more = loading

    def clear(self):
        self._selected_row = -1
        self._loading_more = False
        self.card_cleared.emit()
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self._sync_empty()

    def add_package(self, pkg: dict, row: int):
        card = PackageCard(pkg, row, self._app)
        card.toggled.connect(self._on_card_toggled)
        card.clicked.connect(self._on_card_clicked)
        self._cards.append(card)

    def _on_card_toggled(self, row: int, state: int):
        pass

    def _on_card_clicked(self, row: int, pkg: dict):
        if row == self._selected_row:
            self._selected_row = -1
            self.card_cleared.emit()
        else:
            self._selected_row = row
            self.card_selected.emit(pkg)

    def _relayout(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
        n = len(self._cards)
        if not n:
            return
        vw = self.viewport().width() - 20
        spacing = self._grid.spacing()
        min_w = 210
        self._cols = 3
        while self._cols > 1 and vw < self._cols * min_w + (self._cols - 1) * spacing:
            self._cols -= 1
        avail = max(1, vw - (self._cols - 1) * spacing)
        card_w = max(min_w, avail // self._cols)
        for i, card in enumerate(self._cards):
            card.setFixedWidth(card_w)
            r, c = divmod(i, self._cols)
            self._grid.addWidget(card, r, c)

    def populate(self, packages: list[dict]):
        self.clear()
        for i, pkg in enumerate(packages):
            self.add_package(pkg, i)
        self._relayout()
        self._sync_empty()

    def _sync_empty(self):
        if not hasattr(self, "_empty"):
            return
        self._empty.setGeometry(self.viewport().rect())
        self._empty.setVisible(len(self._cards) == 0)

    def get_checked_rows(self) -> list[int]:
        return [c.row for c in self._cards if c.is_checked()]

    def get_checked_packages(self) -> list[dict]:
        return [c.pkg for c in self._cards if c.is_checked()]
