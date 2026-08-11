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
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QLinearGradient,
)

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


class _SourceTile(QWidget):
    """Rounded tile with the source color and a white letter."""

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        color = _SOURCE_COLORS.get(source, _TEXT_MUTED)
        self._c = color
        self._letter = (source or "?")[0].upper()
        self.setToolTip(source)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, self._c.lighter(115))
        grad.setColorAt(1.0, self._c.darker(110))
        path = QPainterPath()
        path.addRoundedRect(r, 7, 7)
        p.fillPath(path, grad)
        p.setFont(_small_font(9, QFont.Weight.Bold))
        p.setPen(QColor(12, 12, 14))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._letter)
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
    f.setPointSize(pt)
    f.setWeight(weight)
    return f


class PackageCard(QFrame):
    """A single package card matching the UpdatesTable design language."""

    toggled = pyqtSignal(int, bool)

    CARD_W = 268
    CARD_H = 152

    def __init__(self, pkg: dict, row: int, parent=None):
        super().__init__(parent)
        self.row = row
        self.pkg = pkg
        self._hover = False
        self.setObjectName("packageCard")
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self._apply_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(4)

        # ── top: tile + name + checkbox ────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(8)

        self.tile = _SourceTile(self.pkg.get("source", ""))
        top.addWidget(self.tile)

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

        layout.addStretch()

        # ── bottom: version stack + size + status chip ─────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.version_box = QWidget()
        vbox = QVBoxLayout(self.version_box)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(1)

        current = self.pkg.get("version") or ""
        new = self.pkg.get("new_version") or current

        self.cur_label = _SmallLabel(current or "\u2014", 8, QFont.Weight.Normal, "#5C5E66")
        vbox.addWidget(self.cur_label)

        if new and new != current:
            self.new_label = _SmallLabel(f"\u2191 {new}", 8, QFont.Weight.DemiBold, "#58CA8D")
            vbox.addWidget(self.new_label)
        else:
            self.new_label = None
        vbox.addStretch()
        bottom.addWidget(self.version_box, 1)

        self.size_label = _SmallLabel(self.pkg.get("download_size") or "",
                                      8, QFont.Weight.Normal, "#8B8D97")
        self.size_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.size_label.setVisible(bool(self.pkg.get("download_size")))
        bottom.addWidget(self.size_label)

        if new and new != current:
            status = self.pkg.get("status") or classify_update(current, new)
        elif self.pkg.get("installed") or self.pkg.get("_installed"):
            status = "Installed"
        else:
            status = "Available"
        self.status_chip = _Chip(status, _STATUS_COLORS.get(status, _TEXT_MUTED))
        bottom.addWidget(self.status_chip, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(bottom)

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#packageCard {
                background: transparent;
                border: none;
            }
        """)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        # glass surface
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor(24, 26, 31))
        grad.setColorAt(1.0, QColor(15, 16, 19))
        p.fillPath(path, grad)

        # border
        checked = self.checkbox.isChecked()
        border = QColor(0, 191, 174, 140) if checked else (
            QColor(255, 255, 255, 26) if self._hover else QColor(255, 255, 255, 14))
        p.setPen(QPen(border, 1))
        p.drawPath(path)

        # checked accent bar (like the table row)
        if checked:
            bar = QRectF(rect.left() + 2, rect.top() + 7, 3, rect.height() - 14)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(bar, 1.5, 1.5)
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(bar_path, _ACCENT)

        p.end()
        super().paintEvent(event)

    def _on_check(self, state):
        self.update()
        self.toggled.emit(self.row, state)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()


class PackagesGridView(QScrollArea):
    """Scrollable grid of package cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setVisible(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
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

    def resizeEvent(self, e):
        w = self.viewport().width() - 12
        card_w = PackageCard.CARD_W
        spacing = 14
        self._cols = max(2, (w + spacing) // (card_w + spacing))
        self._relayout()
        super().resizeEvent(e)

    def clear(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

    def add_package(self, pkg: dict, row: int):
        card = PackageCard(pkg, row)
        card.toggled.connect(self._on_card_toggled)
        self._cards.append(card)

    def _on_card_toggled(self, row: int, state: int):
        pass

    def _relayout(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.takeAt(i)
        if not self._cards:
            return
        for i, card in enumerate(self._cards):
            r, c = divmod(i, self._cols)
            self._grid.addWidget(card, r, c)

    def populate(self, packages: list[dict]):
        self.clear()
        for i, pkg in enumerate(packages):
            self.add_package(pkg, i)
        self._relayout()

    def get_checked_rows(self) -> list[int]:
        return [c.row for c in self._cards if c.is_checked()]

    def get_checked_packages(self) -> list[dict]:
        return [c.pkg for c in self._cards if c.is_checked()]
