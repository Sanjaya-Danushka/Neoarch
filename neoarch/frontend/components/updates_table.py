"""Premium package updates table.

A fully custom QTableView replacement for the Updates page: dark, high
row-density, rounded hover/selected rows, package tiles, animated version
arrow, source and status badges, per-row overflow menu, sorting, zebra
stripes, multi-select checkboxes, sticky header with select-all checkbox,
a loading indicator and an empty state overlay.

Design follows the app theme (styles.py): accent #00BFAE, near-black
surfaces and muted secondary text. The widget owns its data model and
delegate, and talks to the rest of the app through signals.
"""

import json
import re
import subprocess
from datetime import datetime
from threading import Thread

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QProgressBar,
    QStyle,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

# ── theme (mint accent, matching the app's design language) ────────
_ACCENT = QColor(0, 191, 174)              # app accent #00BFAE
_TEXT = QColor(238, 240, 244)
_TEXT_SEC = QColor(139, 141, 151)           # app _TEXT_SEC #8B8D97
_TEXT_MUTED = QColor(92, 94, 102)           # app _TEXT_MUTED #5C5E66
_DEFAULT_LOADING_MESSAGE = "Loading\u2026"

_SOURCE_COLORS = {
    "pacman": QColor(79, 195, 247),
    "AUR": QColor(255, 138, 101),
    "Flatpak": QColor(38, 166, 154),
    "npm": QColor(229, 57, 53),
    "Local": QColor(163, 166, 176),
    "Docker": QColor(36, 150, 237),
}
_GREEN = QColor(88, 202, 143)

_PANEL_RADIUS = 14

_VIEWPORT_GLASS = """
QWidget {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0    rgba(22, 23, 26, 150),
        stop:0.06 rgba(20, 21, 24, 165),
        stop:0.6  rgba(16, 17, 20, 180),
        stop:1    rgba(12, 12, 14, 190));
    border: none;
}
"""

_ROW_HOVER = QColor(255, 255, 255, 22)
_ROW_SELECTED = QColor(0, 191, 174, 31)
_SEPARATOR = QColor(255, 255, 255, 16)

_HEADER_TEXT = QColor(139, 141, 151)        # app _TEXT_SEC #8B8D97
_HEADER_BORDER = QColor(255, 255, 255, 15)  # app _BORDER rgba(255,255,255,0.06)

_STATUS_COLORS = {
    "Security": QColor(248, 113, 113),
    "Feature": QColor(96, 165, 250),
    "Bug Fix": QColor(93, 199, 139),
    "Maintenance": QColor(163, 166, 176),
    "Downloading": QColor(251, 191, 36),
    "Installed": QColor(93, 199, 139),
    "Update": QColor(255, 179, 71),
}

_HEADERS = ["", "Package", "Version", "Size", "Source", "Status", "Installed", ""]


def _parse_version(value):
    """Best-effort numeric parse of a version string for comparisons."""
    tokens = []
    for m in re.finditer(r"\d+", str(value)):
        tokens.append(int(m.group()))
    return tokens or [0]


def classify_update(current, new):
    """Classify an update as Security / Feature / Bug Fix / Maintenance."""
    cur = _parse_version(current)
    newv = _parse_version(new)
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


def _parse_size(text):
    """Parse a human size string (e.g. '12.3 MiB') into bytes."""
    m = re.search(r"([\d.]+)\s*([KMGT]?)i?B", str(text), re.IGNORECASE)
    if not m:
        return 0
    num = float(m.group(1))
    mult = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    return int(num * mult.get(m.group(2).upper(), 1))


def _fmt_date(ts):
    """Format an install timestamp as a short date (or a dash when unknown)."""
    if not ts:
        return "\u2014"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "\u2014"


class _EnrichWorker(QObject):
    """Fetches descriptions / download sizes in a background thread."""

    finished = pyqtSignal(dict)

    def __init__(self, packages, parent=None):
        super().__init__(parent)
        self._packages = packages

    def fetch_meta(self):
        meta = {}

        pacman_names = [p.get("name", "") for p in self._packages if p.get("source") == "pacman"]
        if pacman_names:
            try:
                r = subprocess.run(
                    ["pacman", "-Si"] + pacman_names,
                    capture_output=True, text=True, timeout=120,
                )
                if r.stdout:
                    section = {}
                    for line in r.stdout.splitlines():
                        if line.strip().startswith("Repository"):
                            if section:
                                self._apply_section(meta, section)
                            section = {}
                        elif ":" in line:
                            key, _, val = line.partition(":")
                            section[key.strip()] = val.strip()
                    if section:
                        self._apply_section(meta, section)
            except Exception:
                pass

        flatpak_names = [p.get("name", "") for p in self._packages if p.get("source") == "Flatpak"]
        if flatpak_names:
            try:
                r = subprocess.run(
                    ["flatpak", "list", "--columns=application,description"],
                    capture_output=True, text=True, timeout=60,
                )
                if r.returncode == 0 and r.stdout:
                    for ln in r.stdout.splitlines():
                        parts = ln.split("\t")
                        if len(parts) >= 2:
                            meta.setdefault(parts[0].strip(), {})["description"] = parts[1].strip()
            except Exception:
                pass

        npm_names = [p.get("name", "") for p in self._packages if p.get("source") == "npm"]
        if npm_names:
            try:
                r = subprocess.run(
                    ["npm", "view"] + npm_names + ["dist.unpackedSize", "--json"],
                    capture_output=True, text=True, timeout=120,
                )
                if r.returncode == 0 and r.stdout.strip():
                    data = json.loads(r.stdout)
                    entries = data.items() if isinstance(data, dict) else []
                    for name, val in entries:
                        if isinstance(val, (str, int, float)):
                            try:
                                meta.setdefault(name, {})["download_size"] = f"{int(float(val))} B"
                            except (TypeError, ValueError):
                                pass
            except Exception:
                pass

        return meta

    @staticmethod
    def _apply_section(meta, section):
        name = section.get("Name", "")
        if not name:
            return
        entry = meta.setdefault(name, {})
        desc = section.get("Description", "").strip()
        if desc and desc != "None":
            entry["description"] = desc
        size = section.get("Download Size", "").strip()
        if size and size != "None":
            entry["download_size"] = size


class UpdatesModel(QAbstractTableModel):
    """Flat model over a list of update package dicts."""

    COLUMNS = 8
    checked_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pkgs = []
        self._checked = set()
        self._sort_col = 1
        self._sort_asc = True

    # ── helpers ───────────────────────────────────────────────────────
    def set_packages(self, packages):
        self.beginResetModel()
        self._pkgs = [dict(p) for p in packages]
        self._checked = set()
        self.endResetModel()
        self._apply_sort()
        self.checked_changed.emit(0, len(self._pkgs))

    def package_at(self, row):
        if 0 <= row < len(self._pkgs):
            return self._pkgs[row]
        return None

    def checked_packages(self):
        return [p for p in self._pkgs if p.get("name") in self._checked]

    def is_all_checked(self):
        return bool(self._pkgs) and len(self._checked) >= len(self._pkgs)

    def set_all_checked(self, state):
        if not self._pkgs:
            return
        self._checked = set(p.get("name") for p in self._pkgs) if state else set()
        if self.rowCount():
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, 0),
                [Qt.ItemDataRole.CheckStateRole],
            )
        self.checked_changed.emit(len(self._checked), len(self._pkgs))

    def set_metadata(self, meta):
        for row, pkg in enumerate(self._pkgs):
            entry = meta.get(pkg.get("name")) or meta.get(pkg.get("id"))
            if not entry:
                continue
            changed = False
            if entry.get("description"):
                pkg["description"] = entry["description"]
                changed = True
            if entry.get("download_size"):
                pkg["download_size"] = entry["download_size"]
                changed = True
            if changed:
                self.dataChanged.emit(self.index(row, 1), self.index(row, 3))

    def _sort_key(self, pkg, col):
        if col == 1:
            return (pkg.get("name") or "").lower()
        if col == 2:
            return (_parse_version(pkg.get("version")), _parse_version(pkg.get("new_version")))
        if col == 3:
            return _parse_size(pkg.get("download_size") or "0 B")
        if col == 4:
            return (pkg.get("source") or "").lower()
        if col == 5:
            status = pkg.get("status")
            if status:
                return status
            return classify_update(pkg.get("version"), pkg.get("new_version"))
        if col == 6:
            return pkg.get("installed_date") or 0
        return (pkg.get("name") or "").lower()

    def _apply_sort(self):
        if self._sort_col in (0, 7):
            return
        self._pkgs.sort(key=lambda p: self._sort_key(p, self._sort_col), reverse=not self._sort_asc)
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    # ── QAbstractTableModel ───────────────────────────────────────────
    def rowCount(self, parent=QModelIndex()):
        return len(self._pkgs)

    def columnCount(self, parent=QModelIndex()):
        return self.COLUMNS

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        fl = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            fl |= Qt.ItemFlag.ItemIsUserCheckable
        return fl

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        pkg = self.package_at(index.row())
        if pkg is None:
            return None
        col = index.column()
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if pkg.get("name") in self._checked else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.UserRole:
            return pkg
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole and index.isValid():
            pkg = self.package_at(index.row())
            if pkg is None:
                return False
            name = pkg.get("name")
            if value in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked) or value is True:
                self._checked.add(name)
            else:
                self._checked.discard(name)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            self.checked_changed.emit(len(self._checked), len(self._pkgs))
            return True
        return False

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        self._sort_col = column
        self._sort_asc = order == Qt.SortOrder.AscendingOrder
        self._apply_sort()

    def header_labels(self):
        return list(_HEADERS)


class _UpdatesHeader(QHeaderView):
    """Sticky header with select-all checkbox and sort indicator."""

    select_all_changed = pyqtSignal(bool)
    sort_requested = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._checked = False
        self._indeterminate = False
        self._sort_col = -1
        self._sort_asc = True
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setMinimumHeight(44)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._font = QFont()
        self._font.setPointSize(9)
        self._font.setWeight(QFont.Weight.DemiBold)
        self._font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
        self._section_rects = []
        self.sectionResized.connect(self._refresh_section_rects)
        self.sectionMoved.connect(self._refresh_section_rects)
        self.sectionCountChanged.connect(self._refresh_section_rects)

    def _refresh_section_rects(self, *args):
        try:
            self._section_rects = [QRect(self.sectionViewportPosition(s), 0, self.sectionSize(s), self.height())
                                   for s in range(self.count())]
        except Exception:
            self._section_rects = []

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_section_rects()

    def set_select_all_state(self, checked, indeterminate):
        self._checked = checked
        self._indeterminate = indeterminate
        self.viewport().update()

    def set_sort(self, col, asc=True):
        self._sort_col = col
        self._sort_asc = asc
        self.viewport().update()

    def _hit_section(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        return self.logicalIndexAt(pos)

    def mousePressEvent(self, event):
        section = self._hit_section(event)
        if section == 0:
            new_state = not (self._checked or self._indeterminate)
            self._checked = new_state
            self._indeterminate = False
            self.viewport().update()
            self.select_all_changed.emit(new_state)
            return
        if section >= 1:
            new_asc = not self._sort_asc if section == self._sort_col else True
            self.sort_requested.emit(section, new_asc)
            return

    def mouseReleaseEvent(self, event):
        return

    def paintSection(self, painter, rect, section):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label = (_HEADERS[section] if 0 <= section < len(_HEADERS) else "").upper()

        # QHeaderView can hand us a section rect that is offset/shrunk by its
        # style's section padding, which misaligns the header labels with the
        # cells below. Use the rect cached from the header's own geometry
        # (refreshed on resize/section changes, never read during paint).
        if 0 <= section < len(self._section_rects):
            rect = self._section_rects[section]

        # frosted glass panel (top corners rounded to match the table frame)
        glass = QLinearGradient(0, rect.top(), 0, rect.bottom())
        glass.setColorAt(0.0, QColor(19, 20, 23, 200))
        glass.setColorAt(1.0, QColor(12, 12, 14, 215))
        is_first = section == 0
        is_last = section == self.count() - 1
        if is_first or is_last:
            path = QPainterPath()
            r = QRectF(rect)
            rad = _PANEL_RADIUS
            if is_first and is_last:
                path.addRoundedRect(r, rad, rad)
            elif is_first:
                path.moveTo(r.right(), r.top())
                path.lineTo(r.right(), r.bottom())
                path.lineTo(r.left(), r.bottom())
                path.lineTo(r.left(), r.top() + rad)
                path.quadTo(r.left(), r.top(), r.left() + rad, r.top())
            else:
                path.moveTo(r.left(), r.bottom())
                path.lineTo(r.left(), r.top() + rad)
                path.quadTo(r.left(), r.top(), r.left() + rad, r.top())
                path.lineTo(r.right() - rad, r.top())
                path.quadTo(r.right(), r.top(), r.right(), r.top() + rad)
                path.lineTo(r.right(), r.bottom())
            path.closeSubpath()
            painter.fillPath(path, glass)
        else:
            painter.fillRect(QRectF(rect), glass)

        text_rect = QRectF(rect)

        if section == 0:
            # select-all checkbox
            csize = 18
            cx = rect.left() + (rect.width() - csize) / 2
            cy = rect.top() + (rect.height() - csize) / 2
            self._draw_check(painter, QRectF(cx, cy, csize, csize), self._checked, self._indeterminate)
            painter.restore()
            return

        pad = 12 if section == 1 else 6
        right_align = section == 3  # size column is right-aligned like its contents
        center_align = section == 5  # status column centers its chip, so center the label too
        text_rect = QRectF(rect)
        if right_align:
            text_rect.setRight(rect.right() - pad)
        elif not center_align:
            text_rect.setLeft(rect.left() + pad)

        if section == self._sort_col and self._sort_col >= 1:
            fm = QFontMetrics(self._font)
            tw = fm.horizontalAdvance(label)
            if center_align:
                arrow_x = text_rect.center().x() + tw / 2 + 6
            elif right_align:
                arrow_x = text_rect.right() - tw - 14
            else:
                arrow_x = text_rect.left() + tw + 6
            arrow_w = 8
            arrow_y = rect.center().y()
            tri = QPolygonF()
            if self._sort_asc:
                tri << QPointF(arrow_x, arrow_y + 3) << QPointF(arrow_x + arrow_w, arrow_y + 3) << QPointF(arrow_x + arrow_w / 2, arrow_y - 2)
            else:
                tri << QPointF(arrow_x, arrow_y - 3) << QPointF(arrow_x + arrow_w, arrow_y - 3) << QPointF(arrow_x + arrow_w / 2, arrow_y + 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_ACCENT)
            painter.drawPolygon(tri)

        painter.setFont(self._font)
        painter.setPen(_HEADER_TEXT)
        if right_align:
            align = Qt.AlignmentFlag.AlignRight
        elif center_align:
            align = Qt.AlignmentFlag.AlignHCenter
        else:
            align = Qt.AlignmentFlag.AlignLeft
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | align | Qt.TextFlag.TextSingleLine, label)

        # bottom hairline
        line_pen = QPen(_HEADER_BORDER)
        line_pen.setWidthF(1)
        painter.setPen(line_pen)
        painter.drawLine(int(rect.left()), int(rect.bottom()) - 1, int(rect.right()), int(rect.bottom()) - 1)
        painter.restore()

    def _draw_check(self, painter, r, checked, indeterminate):
        path = QPainterPath()
        path.addRoundedRect(r, 5, 5)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if checked or indeterminate:
            painter.fillPath(path, _ACCENT)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            painter.fillPath(path, QColor(255, 255, 255, 14))
            painter.drawPath(path)
        if indeterminate:
            painter.setPen(QPen(QColor(255, 255, 255), 1.8))
            painter.drawLine(QPointF(r.center().x() - 3, r.center().y()), QPointF(r.center().x() + 3, r.center().y()))
        elif checked:
            pen = QPen(QColor(255, 255, 255), 1.9)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(r.left() + 4, r.center().y()), QPointF(r.center().x() - 1, r.bottom() - 4))
            painter.drawLine(QPointF(r.center().x() - 1, r.bottom() - 4), QPointF(r.right() - 3, r.top() + 4))


class _ArrowAnimator(QObject):
    """Animates the version arrow when a row is hovered."""

    def __init__(self, table, parent=None):
        super().__init__(parent)
        self._table = table
        self._row = -1
        self._progress = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_value)

    def set_hover(self, row):
        if row == self._row:
            return
        self._row = row
        self._anim.stop()
        self._anim.setStartValue(self._progress if self._row >= 0 else 0.0)
        self._anim.setEndValue(1.0 if self._row >= 0 else 0.0)
        self._anim.start()

    def _on_value(self, v):
        self._progress = float(v)
        self._table.viewport().update()

    def progress_for(self, row):
        return self._progress if row == self._row else 0.0


class UpdatesTable(QTableView):
    """Main redesigned updates widget."""

    row_selected = pyqtSignal(object)
    row_cleared = pyqtSignal()
    menu_action = pyqtSignal(str, object)
    checks_changed = pyqtSignal(int, int)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.setObjectName("updatesTable")
        self._app = app
        self._hover_row = -1
        self._menu_hover_row = -1
        self._loading = False
        self._loading_enrich = False
        self._enrich = True
        self._installed_mode = False
        self._loading_message = _DEFAULT_LOADING_MESSAGE

        self.model = UpdatesModel(self)
        self.setModel(self.model)
        self.setItemDelegate(UpdatesRowDelegate(self))

        self.setShowGrid(False)
        self.setFrameShape(QTableView.Shape.NoFrame)
        self.viewport().setAutoFillBackground(True)
        self.viewport().setStyleSheet(_VIEWPORT_GLASS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setMouseTracking(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(52)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSortingEnabled(False)

        header = _UpdatesHeader(self)
        self.setHorizontalHeader(header)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, mode in ((0, QHeaderView.ResizeMode.Fixed),
                          (2, QHeaderView.ResizeMode.Interactive),
                          (3, QHeaderView.ResizeMode.Fixed),
                          (4, QHeaderView.ResizeMode.Fixed),
                          (5, QHeaderView.ResizeMode.Fixed),
                          (6, QHeaderView.ResizeMode.Fixed),
                          (7, QHeaderView.ResizeMode.Fixed)):
            header.setSectionResizeMode(col, mode)
        self.setColumnWidth(0, 46)
        self.setColumnWidth(2, 190)
        self.setColumnWidth(3, 96)
        self.setColumnWidth(4, 110)
        self.setColumnWidth(5, 104)
        self.setColumnWidth(6, 100)
        self.setColumnWidth(7, 44)
        # The "Installed" date column is only shown by the Installed view.
        self.setColumnHidden(6, True)

        header.select_all_changed.connect(self._on_header_select_all)
        header.sort_requested.connect(self._on_sort_requested)

        self.model.checked_changed.connect(self._on_checked_changed)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self._arrow = _ArrowAnimator(self, self)

        self._empty = _EmptyOverlay(self)
        self._empty.setVisible(False)
        self._fade = _BottomFade(self)
        self._fade.setVisible(False)

        self._pix_cache = {}

    # ── public API ────────────────────────────────────────────────────
    def set_packages(self, packages):
        self._loading_enrich = False
        self.model.set_packages(packages or [])
        self._header_sync()
        self.set_loading(False)
        self._start_enrich()
        self._sync_overlays()

    def set_loading(self, loading, message=None):
        self._loading = bool(loading)
        if message:
            self._loading_message = message
        if loading:
            # Drop stale rows from the previous visit so the loading state
            # renders over a clean empty table instead of on top of the old
            # page's items.
            self.model.set_packages([])
            self._header_sync()
            self.scrollToTop()
        self._sync_overlays()

    def row_count(self):
        return self.model.rowCount()

    def checked_packages(self):
        return self.model.checked_packages()

    def set_all_checked(self, state):
        self.model.set_all_checked(state)
        self._header_sync()

    def toggle_select_all(self):
        self.set_all_checked(not self.model.is_all_checked())

    def package_at(self, row):
        return self.model.package_at(row)

    # ── internals ─────────────────────────────────────────────────────
    def set_enrich(self, enabled):
        """Toggle background metadata enrichment (descriptions / download sizes)."""
        self._enrich = bool(enabled)

    def set_empty_text(self, title, subtitle, hint=None):
        """Override the empty-state message (Installed vs Updates wording)."""
        self._empty.set_text(title, subtitle, hint)

    def show_installed_date(self, visible):
        """Show/hide the "Installed" date column (Installed view only)."""
        self.setColumnHidden(6, not visible)
        self.viewport().update()

    def set_installed_mode(self, installed):
        """Switch the row menu to Installed-view behaviour (Update only when
        available, plus an Uninstall action)."""
        self._installed_mode = bool(installed)

    def _header_sync(self):
        header = self.horizontalHeader()
        if hasattr(header, "set_select_all_state"):
            checked = self.model.is_all_checked()
            indeterminate = len(self.model._checked) > 0 and not checked
            header.set_select_all_state(checked, indeterminate)

    def _on_header_select_all(self, state):
        self.set_all_checked(state)

    def _on_sort_requested(self, col, asc):
        self.model.sort(col, Qt.SortOrder.AscendingOrder if asc else Qt.SortOrder.DescendingOrder)
        try:
            self.clearSelection()
        except Exception:
            pass
        header = self.horizontalHeader()
        if hasattr(header, "set_sort"):
            header.set_sort(col, asc)

    def sort_by_column(self, col, asc=True):
        """Public API for external sort controls (e.g. the source panel)."""
        self.model._sort_col = col
        self.model._sort_asc = asc
        self._on_sort_requested(col, asc)

    def _on_checked_changed(self, checked, total):
        self._header_sync()
        self.checks_changed.emit(checked, total)

    def _on_selection_changed(self, selected, deselected):
        rows = set(i.row() for i in self.selectionModel().selectedRows())
        if len(rows) == 1:
            pkg = self.model.package_at(next(iter(rows)))
            if pkg:
                self.row_selected.emit(pkg)
        else:
            self.row_cleared.emit()

    def _sync_overlays(self):
        geom = self.viewport().geometry()
        self._empty.setGeometry(geom)

        # Bottom fade: soften a partially visible row instead of hard-clipping it
        row_h = self.verticalHeader().sectionSize(0)
        rem = geom.height() % row_h if row_h else 0
        clipped = rem != 0 and self.model.rowCount() * row_h > geom.height()
        self._fade.setVisible(bool(clipped))
        if clipped:
            self._fade.setGeometry(geom.x(), geom.y() + geom.height() - rem, geom.width(), rem)
            self._fade.raise_()

        if self._loading:
            self._empty.set_loading(True, self._loading_message)
            self._empty.setVisible(True)
        elif self.model.rowCount() == 0:
            self._empty.set_loading(False)
            self._empty.setVisible(True)
        else:
            self._empty.set_loading(False)
            self._empty.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_overlays()

    # ── icons ─────────────────────────────────────────────────────────
    def source_pixmap(self, source, size=16):
        key = ("src", source, size)
        if key in self._pix_cache:
            return self._pix_cache[key]
        pm = None
        try:
            icon = self._app.get_source_icon(source, size)
            if icon and not icon.isNull():
                pm = icon.pixmap(size, size)
        except Exception:
            pm = None
        if pm is None or pm.isNull():
            pm = _make_fallback_pixmap(size, _SOURCE_COLORS.get(source, _TEXT_MUTED))
        self._pix_cache[key] = pm
        return pm

    # ── hover ─────────────────────────────────────────────────────────
    def hovered_row(self):
        return self._hover_row

    def menu_hover_row(self):
        return self._menu_hover_row

    def arrow_progress(self, row):
        return self._arrow.progress_for(row)

    def _row_at(self, pos):
        return self.indexAt(pos).row()

    def _col_at(self, pos):
        return self.indexAt(pos).column()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        row = self.indexAt(pos).row()
        col = self.indexAt(pos).column()
        if row != self._hover_row:
            self._hover_row = row
            self._arrow.set_hover(row)
            self.viewport().update()
        new_menu_row = row if col == 7 else -1
        if new_menu_row != self._menu_hover_row:
            self._menu_hover_row = new_menu_row
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_row = -1
        self._menu_hover_row = -1
        self._arrow.set_hover(-1)
        self.viewport().update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            idx = self.indexAt(pos)
            col = idx.column() if idx.isValid() else -1
            if col == 7:
                self._open_row_menu(idx.row(), pos)
                return
            if idx.isValid():
                self._toggle_check(idx.row(), pos)
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            current = self.currentIndex()
            if current.isValid():
                self._toggle_check(current.row(), None)
                return
        super().keyPressEvent(event)

    def _toggle_check(self, row, pos):
        if row < 0:
            return
        pkg = self.model.package_at(row)
        if pkg is None:
            return
        name = pkg.get("name")
        idx = self.model.index(row, 0)
        checked = name in self.model._checked
        self.model.setData(idx, Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked,
                           Qt.ItemDataRole.CheckStateRole)
        sel_model = self.selectionModel()
        flag = sel_model.SelectionFlag.Select if not checked else sel_model.SelectionFlag.Deselect
        sel_model.select(idx, flag | sel_model.SelectionFlag.Rows)
        if not checked:
            self.setCurrentIndex(idx)

    def _row_has_update(self, pkg):
        return bool(pkg.get("new_version")) and pkg.get("new_version") != pkg.get("version")

    def _open_row_menu(self, row, pos):
        if row < 0:
            return
        pkg = self.model.package_at(row)
        if pkg is None:
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: rgba(22, 25, 32, 235); color: #F3F4F6;
                    border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 18px; border-radius: 4px; }
            QMenu::item:selected { background-color: rgba(47, 129, 247, 0.28); color: #fff; }
            QMenu::separator { height: 1px; background: rgba(255, 255, 255, 0.10); margin: 4px 8px; }
        """)
        if self._installed_mode:
            if self._row_has_update(pkg):
                act_update = menu.addAction("Update")
                act_update.triggered.connect(lambda: self.menu_action.emit("update", pkg))
            act_uninstall = menu.addAction("Uninstall")
            act_uninstall.triggered.connect(lambda: self.menu_action.emit("uninstall", pkg))
            act_details = menu.addAction("View Details")
            act_details.triggered.connect(lambda: self.menu_action.emit("details", pkg))
            menu.addSeparator()
            if self._row_has_update(pkg):
                act_ignore = menu.addAction("Ignore update")
                act_ignore.triggered.connect(lambda: self.menu_action.emit("ignore", pkg))
            act_browser = menu.addAction("View in browser")
            act_browser.triggered.connect(lambda: self.menu_action.emit("browser", pkg))
            act_copy = menu.addAction("Copy name")
            act_copy.triggered.connect(lambda: self.menu_action.emit("copy", pkg))
        else:
            act_update = menu.addAction("Update")
            act_update.triggered.connect(lambda: self.menu_action.emit("update", pkg))
            act_details = menu.addAction("View Details")
            act_details.triggered.connect(lambda: self.menu_action.emit("details", pkg))
            menu.addSeparator()
            act_ignore = menu.addAction("Ignore update")
            act_ignore.triggered.connect(lambda: self.menu_action.emit("ignore", pkg))
            act_browser = menu.addAction("View in browser")
            act_browser.triggered.connect(lambda: self.menu_action.emit("browser", pkg))
            act_copy = menu.addAction("Copy name")
            act_copy.triggered.connect(lambda: self.menu_action.emit("copy", pkg))
        global_pos = self.viewport().mapToGlobal(pos if pos is not None else QPoint(10, 10))
        menu.exec(global_pos)

    # ── enrichment ────────────────────────────────────────────────────
    def _start_enrich(self):
        if self._loading_enrich or not self._enrich:
            return
        self._loading_enrich = True
        packages = [p for p in self.model._pkgs if p.get("source") in ("pacman", "Flatpak")]
        if not packages:
            self._loading_enrich = False
            return

        worker = _EnrichWorker(packages)

        def _finish(meta):
            self.model.set_metadata(meta)
            self.model._apply_sort()
            self._loading_enrich = False
            app = getattr(self, "_app", None)
            if app is not None:
                try:
                    base = getattr(app, "updates_all", None)
                    if base:
                        for pkg in base:
                            entry = meta.get(pkg.get("name")) or meta.get(pkg.get("id"))
                            if entry and entry.get("download_size"):
                                pkg["download_size"] = entry["download_size"]
                    refresh = getattr(app, "_refresh_updates_summary", None)
                    if refresh:
                        refresh()
                except Exception:
                    pass

        worker.finished.connect(_finish)

        def _runner():
            try:
                worker.finished.emit(worker.fetch_meta())
            except Exception:
                worker.finished.emit({})

        Thread(target=_runner, daemon=True).start()


class UpdatesRowDelegate(QStyledItemDelegate):
    """Paints the premium row contents."""

    def __init__(self, table):
        super().__init__(table)
        self._table = table
        self._name_font = QFont()
        self._name_font.setPointSize(10)
        self._name_font.setWeight(QFont.Weight.DemiBold)
        self._desc_font = QFont()
        self._desc_font.setPointSize(8)
        self._ver_font = QFont()
        self._ver_font.setPointSize(9)
        self._badge_font = QFont()
        self._badge_font.setPointSize(8)
        self._badge_font.setWeight(QFont.Weight.DemiBold)
        self._menu_font = QFont()
        self._menu_font.setPointSize(12)
        self._menu_font.setWeight(QFont.Weight.Bold)

    def sizeHint(self, option, index):
        return QSize(0, 52)

    def _row_rect(self, option):
        """Full row rectangle across all columns (for the row highlight band)."""
        table = self._table
        try:
            left = table.columnViewportPosition(0)
            right = (table.columnViewportPosition(table.columnCount() - 1)
                     + table.columnWidth(table.columnCount() - 1))
        except Exception:
            return QRectF(option.rect)
        top = option.rect.top()
        height = max(option.rect.height(), table.verticalHeader().sectionSize(0))
        return QRectF(left, top, max(1, right - left), height)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect = QRectF(option.rect)
        row = index.row()
        col = index.column()
        row_rect = self._row_rect(option)

        self._paint_row_background(painter, row_rect, option, row)

        pkg = self._table.model.package_at(row)
        if pkg is None:
            painter.restore()
            return

        # Clip all cell content to its own column so nothing overlaps neighbors
        painter.save()
        painter.setClipRect(rect)

        if col == 0:
            self._paint_check(painter, option, index)
        elif col == 1:
            self._paint_package(painter, rect, option, pkg)
        elif col == 2:
            self._paint_version(painter, rect, pkg, row)
        elif col == 3:
            self._paint_size(painter, rect, pkg)
        elif col == 4:
            self._paint_label(painter, rect, pkg.get("source", ""), _TEXT_SEC)
        elif col == 5:
            status = pkg.get("status") or classify_update(pkg.get("version"), pkg.get("new_version"))
            self._paint_chip(painter, rect, status, _STATUS_COLORS.get(status, _TEXT_MUTED))
        elif col == 6:
            self._paint_date(painter, rect, pkg)
        elif col == 7:
            self._paint_menu(painter, rect, row)
        painter.restore()
        painter.restore()

    def _paint_row_background(self, painter, rect, option, row):
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = row == self._table.hovered_row()

        if selected:
            band = QRectF(rect.left() + 2, rect.top() + 1, rect.width() - 4, rect.height() - 2)
            path = QPainterPath()
            path.addRoundedRect(band, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, _ROW_SELECTED)
            bar = QRectF(rect.left() + 2, band.top() + 7, 3, band.height() - 14)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_ACCENT)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(bar, 2, 2)
            painter.drawPath(bar_path)
        elif hovered:
            band = QRectF(rect.left() + 2, rect.top() + 1, rect.width() - 4, rect.height() - 2)
            path = QPainterPath()
            path.addRoundedRect(band, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, _ROW_HOVER)

        # hairline separator under the row (skipped on the selected row)
        if not selected:
            pen = QPen(_SEPARATOR)
            pen.setWidthF(1)
            painter.setPen(pen)
            painter.drawLine(QPointF(rect.left() + 14, rect.bottom()), QPointF(rect.right() - 14, rect.bottom()))

    def _paint_check(self, painter, option, index):
        rect = QRectF(option.rect)
        state = index.data(Qt.ItemDataRole.CheckStateRole)
        checked = state == Qt.CheckState.Checked
        csize = 18
        cx = rect.left() + (rect.width() - csize) / 2
        cy = rect.top() + (rect.height() - csize) / 2
        r = QRectF(cx, cy, csize, csize)
        path = QPainterPath()
        path.addRoundedRect(r, 5, 5)
        if checked:
            painter.fillPath(path, _ACCENT)
            pen = QPen(QColor(255, 255, 255), 1.9)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(r.left() + 4, r.center().y()), QPointF(r.center().x() - 1, r.bottom() - 4))
            painter.drawLine(QPointF(r.center().x() - 1, r.bottom() - 4), QPointF(r.right() - 3, r.top() + 4))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            painter.fillPath(path, QColor(255, 255, 255, 14))
            painter.drawPath(path)

    def _paint_menu(self, painter, rect, row):
        csize = 26
        cx = rect.left() + (rect.width() - csize) / 2
        cy = rect.top() + (rect.height() - csize) / 2
        if row == self._table.menu_hover_row():
            circle = QRectF(cx - 3, cy - 3, csize + 6, csize + 6)
            path = QPainterPath()
            path.addEllipse(circle)
            painter.fillPath(path, QColor(255, 255, 255, 22))
        painter.setFont(self._menu_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), rect.height()),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextSingleLine, "\u22EE")

    def _paint_package(self, painter, rect, option, pkg):
        source = pkg.get("source", "")

        # clean source icon, no tile box
        pm = self._table.source_pixmap(source, 18)
        ix = rect.left() + 12
        iy = rect.top() + (rect.height() - 18) / 2
        painter.drawPixmap(QPointF(ix, iy), pm)

        text_left = ix + 18 + 10
        avail_w = max(20, rect.right() - text_left - 4)

        name = pkg.get("name") or pkg.get("id") or ""
        name_fm = QFontMetrics(self._name_font)
        name_el = name_fm.elidedText(name, Qt.TextElideMode.ElideRight, int(avail_w))
        painter.setFont(self._name_font)
        painter.setPen(_TEXT)
        painter.drawText(QRectF(text_left, rect.top() + 7, avail_w, 16),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         name_el)

        desc = pkg.get("description") or _fallback_description(pkg)
        desc_fm = QFontMetrics(self._desc_font)
        desc_el = desc_fm.elidedText(desc, Qt.TextElideMode.ElideRight, int(avail_w))
        painter.setFont(self._desc_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(text_left, rect.top() + 26, avail_w, 15),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         desc_el)

    def _paint_version(self, painter, rect, pkg, row):
        current = pkg.get("version") or ""
        new = pkg.get("new_version") or current
        fm = QFontMetrics(self._ver_font)
        cell_left = rect.left() + 6
        cell_w = max(20, rect.width() - 12)
        line_h = 15

        if not new or new == current:
            painter.setFont(self._ver_font)
            painter.setPen(_TEXT_SEC)
            painter.drawText(QRectF(cell_left, rect.top(), cell_w, rect.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                             current or "—")
            return

        # current version on top, new version stacked underneath
        cur_el = fm.elidedText(current, Qt.TextElideMode.ElideMiddle, int(cell_w))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_MUTED)
        painter.drawText(QRectF(cell_left, rect.top() + 6, cell_w, line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         cur_el)

        new_el = fm.elidedText(new, Qt.TextElideMode.ElideMiddle, int(cell_w - 14))
        new_top = rect.top() + 27
        painter.setPen(QPen(_GREEN, 1.6))
        painter.setFont(self._ver_font)
        painter.drawText(QRectF(cell_left, new_top, 12, line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         "\u2191")
        painter.setPen(_GREEN)
        painter.drawText(QRectF(cell_left + 12, new_top, max(10, cell_w - 12), line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         new_el)

    def _paint_size(self, painter, rect, pkg):
        size = pkg.get("download_size")
        if not size:
            return
        fm = QFontMetrics(self._ver_font)
        el = fm.elidedText(size, Qt.TextElideMode.ElideLeft, int(max(12, rect.width() - 10)))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 4, rect.top(), rect.width() - 10, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextSingleLine,
                         el)
    def _paint_label(self, painter, rect, text, color):
        fm = QFontMetrics(self._badge_font)
        avail = max(10, rect.width() - 12)
        el = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(avail))
        painter.setFont(self._badge_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 6, rect.top(), avail, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         el)

    def _paint_date(self, painter, rect, pkg):
        text = _fmt_date(pkg.get("installed_date"))
        fm = QFontMetrics(self._ver_font)
        el = fm.elidedText(text, Qt.TextElideMode.ElideLeft, int(max(12, rect.width() - 10)))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 4, rect.top(), rect.width() - 10, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         el)

    def _paint_chip(self, painter, rect, text, color):
        fm = QFontMetrics(self._badge_font)
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
        # minimal colored dot identifying the status type
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(chip.left() + 13, chip.center().y()), dot / 2, dot / 2)
        painter.setFont(self._badge_font)
        painter.setPen(_TEXT)
        painter.drawText(QRectF(chip.left() + 13 + dot + 6, chip.top(), tw, chip.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine,
                         text)


def _fallback_description(pkg):
    source = pkg.get("source", "")
    return {
        "pacman": "Official repository package",
        "AUR": "Arch User Repository package",
        "Flatpak": "Flatpak application",
        "npm": "Global npm package",
        "Local": "Local update entry",
    }.get(source, "Update available")


def _make_fallback_pixmap(size, color):
    pm = QIcon(_icon_data(size, color)).pixmap(size, size)
    return pm


def _icon_data(size, color):
    from PyQt6.QtGui import QPixmap
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(1, 1, size - 2, size - 2, size / 3, size / 3)
    p.end()
    return pm


class _BottomFade(QWidget):
    """Soft fade over a partially visible row so it blends into the panel
    instead of being hard-clipped by the bottom edge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        grad.setColorAt(0.0, QColor(9, 9, 11, 0))
        grad.setColorAt(1.0, QColor(8, 8, 10, 235))
        painter.fillRect(r, grad)


class _EmptyBadge(QWidget):
    """Circular mint-glow badge with a white checkmark."""

    def __init__(self, size=76, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        cx = cy = s / 2
        r = s / 2 - 4

        # soft radial glow
        glow = QRadialGradient(cx, cy, r)
        glow.setColorAt(0.0, QColor(88, 202, 143, 46))
        glow.setColorAt(0.55, QColor(88, 202, 143, 22))
        glow.setColorAt(1.0, QColor(88, 202, 143, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # thin ring
        p.setPen(QPen(QColor(88, 202, 143, 90), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2))

        # white checkmark
        pen = QPen(QColor(255, 255, 255, 235), 3.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(s * 0.28, s * 0.52)
        path.lineTo(s * 0.45, s * 0.68)
        path.lineTo(s * 0.72, s * 0.38)
        p.drawPath(path)
        p.end()


class _EmptyOverlay(QWidget):
    """Centered empty state shown while loading or when there are no rows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()

        self._badge = _EmptyBadge(76)
        layout.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel("All caught up")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self._title.font()
        f.setPointSize(13)
        f.setWeight(QFont.Weight.DemiBold)
        self._title.setFont(f)
        self._title.setStyleSheet("color: #EDEDEF; background: transparent; border: none;")
        layout.addWidget(self._title)

        self._sub = QLabel("Your system is up to date")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setStyleSheet("color: #8B8D97; background: transparent; border: none;")
        layout.addWidget(self._sub)

        self._hint = QLabel("Updates will appear here automatically when available")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("color: #5C5E66; background: transparent; border: none;")
        layout.addWidget(self._hint)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(240)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; border-radius: 3px;"
            " background: rgba(255,255,255,0.07); }"
            " QProgressBar::chunk { background: #00BFAE; border-radius: 3px; }")
        layout.addSpacing(6)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

    def set_text(self, title, subtitle, hint=None):
        """Change the empty-state wording; pass hint=None to hide that line."""
        self._title.setText(title)
        self._sub.setText(subtitle)
        if hint is None:
            self._hint.hide()
        else:
            self._hint.setText(hint)
            self._hint.show()

    def set_loading(self, loading, message=None):
        """Switch between the loading and the finished empty state."""
        if loading:
            self._title.setText(message or "Loading\u2026")
            self._sub.setText("Please wait, fetching package data")
            self._hint.hide()
            self._progress.show()
        else:
            self._progress.hide()
