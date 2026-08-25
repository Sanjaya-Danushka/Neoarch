"""
AppImage manager tab: browse, install, update, and remove managed AppImages.

Premium dark-themed page matching the NeoArch visual identity established
by the Git Projects page: stat cards, compact list rows, section headers,
and identical spacing / radius / color conventions.
"""

import os
from threading import Thread

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPixmap, QIcon, QCursor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QFileDialog, QInputDialog, QMessageBox,
    QScrollArea, QMenu,
)

from neoarch.frontend.tokens import Colors, Fonts, Radii, Spacing

__all__ = ["AppImageTab"]

# ── design tokens ──────────────────────────────────────────────────
_BG = Colors.BG_SECONDARY
_SURFACE = Colors.SURFACE
_SURFACE_2 = Colors.SURFACE_2
_TEXT = Colors.TEXT
_TEXT2 = Colors.TEXT_2
_TEXT3 = Colors.TEXT_3
_ACCENT = Colors.ACCENT
_BORDER = Colors.BORDER
_BORDER_HOVER = Colors.BORDER_HOVER

_TEAL = Colors.TEAL
_ORANGE = Colors.ORANGE
_PURPLE = Colors.PURPLE
_BLUE = Colors.BLUE
_GREEN = Colors.GREEN
_RED = Colors.RED

_R_SM = int(Radii.SM)
_R_MD = int(Radii.MD)
_R_LG = int(Radii.LG)


def _svg_icon(rel_path, size, color="#FFFFFF"):
    from neoarch.resources.paths import PROJECT_ROOT
    path = os.path.join(str(PROJECT_ROOT), "assets", "icons", rel_path)
    try:
        r = QSvgRenderer(path)
        if r.isValid():
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r.render(p, QRectF(0, 0, size, size))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(QRectF(0, 0, size, size), QColor(color))
            p.end()
            return QIcon(pm)
    except Exception:
        pass
    return QIcon()


def _fmt_size(nbytes):
    if not nbytes:
        return "0 B"
    if nbytes < 1024:
        return f"{nbytes} B"
    for unit in ("KB", "MB", "GB"):
        nbytes /= 1024
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit == "GB" else f"{nbytes:.0f} {unit}"
    return f"{nbytes:.1f} TB"


def _file_size(path):
    try:
        return os.path.getsize(path) if path and os.path.isfile(path) else 0
    except OSError:
        return 0


def _detect_arch(entry):
    path = entry.get("bin_path", "")
    if not path:
        return ""
    base = os.path.basename(path).lower()
    if "x86_64" in base or "amd64" in base:
        return "x86_64"
    if "aarch64" in base or "arm64" in base:
        return "aarch64"
    if "i686" in base or "i386" in base:
        return "i686"
    return "x86_64"


# ── Stat Card ──────────────────────────────────────────────────────

class _StatCard(QFrame):
    def __init__(self, title, value, subtitle, color, parent=None):
        super().__init__(parent)
        self.setObjectName("aiStatCard")
        self.setFixedHeight(88)
        self.setStyleSheet(f"""
            QFrame#aiStatCard {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_R_LG}px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 11px; font-weight: 500;"
            "background: transparent; border: none;")
        layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel(str(value))
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: 700;"
            "background: transparent; border: none;")
        layout.addWidget(self._value_lbl)

        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 10px; font-weight: 400;"
            "background: transparent; border: none;")
        layout.addWidget(self._sub_lbl)

    def set_value(self, value, subtitle=None):
        self._value_lbl.setText(str(value))
        if subtitle is not None:
            self._sub_lbl.setText(subtitle)


# ── Badge ──────────────────────────────────────────────────────────

class _Badge(QLabel):
    def __init__(self, text, bg="rgba(255,255,255,0.06)", color=_TEXT2, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 600;"
            f"background: {bg}; border-radius: 4px; padding: 2px 7px;"
            "border: none;")
        self.setFixedHeight(18)


# ── App Row ────────────────────────────────────────────────────────

_SRC_COLORS = {
    "file": ("rgba(163, 166, 176, 0.12)", Colors.SRC_LOCAL),
    "url": ("rgba(76, 154, 255, 0.12)", _BLUE),
    "repo": ("rgba(255, 159, 28, 0.12)", _ORANGE),
}


class _AppRow(QFrame):
    """Single application row — identical structure to _ProjectRow."""

    update_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)
    open_requested = pyqtSignal(str)

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("aiAppRow")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#aiAppRow {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_R_MD}px;
            }}
            QFrame#aiAppRow:hover {{
                border-color: {_BORDER_HOVER};
                background: {_SURFACE_2};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # ── Left: identity ──
        left = QVBoxLayout()
        left.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        name_lbl = QLabel(entry.get("name", entry.get("id", "")))
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none;")
        top_row.addWidget(name_lbl)

        src_type = entry.get("source_type", "file")
        src_label = src_type.upper() if src_type == "repo" else src_type.capitalize()
        src_bg, src_color = _SRC_COLORS.get(src_type, ("rgba(255,255,255,0.06)", _TEXT2))
        top_row.addWidget(_Badge(src_label, src_bg, src_color))

        version = entry.get("version") or ""
        if version:
            top_row.addWidget(_Badge(version, "rgba(255,255,255,0.04)", _TEXT3))

        arch = _detect_arch(entry)
        if arch:
            top_row.addWidget(_Badge(arch, "rgba(255,255,255,0.04)", _TEXT3))

        top_row.addStretch(1)
        left.addLayout(top_row)

        src = entry.get("source", "")
        if src_type == "repo":
            owner = entry.get("owner", "")
            repo = entry.get("repo", "")
            sub = f"{owner}/{repo}" if owner else src
        elif src_type == "url":
            sub = src if len(src) < 60 else src[:57] + "..."
        else:
            sub = os.path.basename(src) if src else ""
        if sub:
            url_lbl = QLabel(sub)
            url_lbl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px;"
                "background: transparent; border: none;")
            left.addWidget(url_lbl)

        layout.addLayout(left, 1)

        # ── Middle: status ──
        middle = QVBoxLayout()
        middle.setSpacing(1)
        middle.setContentsMargins(20, 0, 20, 0)

        has_update = bool(entry.get("latest_version"))
        if has_update:
            status_text = f"↓ Update: {entry['latest_version']}"
            status_color = _BLUE
        elif entry.get("last_check") or entry.get("source_type") == "repo":
            status_text = "● Up to date"
            status_color = _GREEN
        else:
            status_text = "● Update info unavailable"
            status_color = _TEXT3

        status_lbl = QLabel(status_text)
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 11px; font-weight: 500;"
            "background: transparent; border: none;")
        middle.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignLeft)

        size = _file_size(entry.get("bin_path", ""))
        if size:
            info_lbl = QLabel(_fmt_size(size))
            info_lbl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px;"
                "background: transparent; border: none;")
            middle.addWidget(info_lbl, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(middle, 1)

        # ── Right: actions ──
        right = QHBoxLayout()
        right.setSpacing(6)

        aid = entry.get("id", "")

        if has_update:
            upd_btn = self._action_btn("Update", _ORANGE)
            upd_btn.clicked.connect(lambda: self.update_requested.emit(aid))
            right.addWidget(upd_btn)

        open_btn = self._action_btn("Open", _ACCENT)
        open_btn.clicked.connect(lambda: self.open_requested.emit(aid))
        right.addWidget(open_btn)

        menu_btn = QPushButton("···")
        menu_btn.setFixedSize(30, 28)
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT3};
                border: 1px solid {_BORDER}; border-radius: 6px;
                font-size: 14px; font-weight: 700; padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.06); color: {_TEXT2};
            }}
        """)
        menu_btn.clicked.connect(self._show_menu)
        right.addWidget(menu_btn)

        layout.addLayout(right)

    @staticmethod
    def _action_btn(text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.04);
                color: {color};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.08);
                border-color: rgba(255,255,255,0.14);
            }}
        """)
        return btn

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {_SURFACE_2};
                color: {_TEXT};
                border: 1px solid {_BORDER};
                border-radius: 8px;
                padding: 4px;
                font-size: 12px;
            }}
            QMenu::item {{ padding: 6px 16px; border-radius: 4px; }}
            QMenu::item:selected {{ background: rgba(0,191,174,0.15); }}
            QMenu::separator {{ height: 1px; background: {_BORDER}; margin: 4px 8px; }}
        """)
        aid = self.entry.get("id", "")

        if self.entry.get("latest_version"):
            act_up = menu.addAction("Update")
            act_up.triggered.connect(lambda: self.update_requested.emit(aid))

        menu.addSeparator()

        act_rm = menu.addAction("Remove")
        act_rm.triggered.connect(lambda: self.remove_requested.emit(aid))

        menu.exec(self.mapToGlobal(self.rect().topRight()))


# ── Main AppImageTab ───────────────────────────────────────────────

class AppImageTab(QWidget):
    """Full-page AppImage management center."""

    data_changed = pyqtSignal()

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._busy = False
        self._entries = []
        self._search_text = ""
        self._sort_mode = "name_asc"
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        # ── Header ──
        self._build_header(root)

        # ── Stats row ──
        self._build_stats(root)

        # ── Spacer ──
        spacer = QWidget()
        spacer.setFixedHeight(12)
        spacer.setStyleSheet("background: transparent; border: none;")
        root.addWidget(spacer)

        # ── Scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 3px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._scroll.setWidget(self._content_widget)
        root.addWidget(self._scroll, 1)

        # ── Empty state (overlaid) ──
        self._build_empty_state()

    def _build_header(self, parent):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.setContentsMargins(0, 0, 0, 0)

        title = QLabel("AppImages")
        title.setStyleSheet(
            f"color: {_TEXT}; font-size: 20px; font-weight: 700;"
            "background: transparent; border: none;")
        left.addWidget(title)

        subtitle = QLabel("Browse and install applications from available sources")
        subtitle.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        left.addWidget(subtitle)

        row.addLayout(left, 1)

        add_file_btn = QPushButton(" Add from File")
        add_file_btn.setIcon(_svg_icon("ui/import.svg", 14, "#0C0C0E"))
        add_file_btn.setIconSize(QRectF(0, 0, 14, 14).toRect().size())
        add_file_btn.setFixedHeight(34)
        add_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_file_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: #0C0C0E;
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 10px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #E8EAF0; }}
            QPushButton:pressed {{ background-color: #D3D6DE; }}
        """)
        add_file_btn.clicked.connect(self.add_from_file)
        self._add_file_btn = add_file_btn
        row.addWidget(add_file_btn)

        parent.addLayout(row)

    def _build_stats(self, parent):
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(10)

        self._stat_total = _StatCard("Total AppImages", "0", "All managed AppImages", _TEAL)
        self._stat_updates = _StatCard("Updates Available", "0", "Ready to update", _BLUE)
        self._stat_size = _StatCard("Total Size", "0 B", "Disk usage", _PURPLE)
        self._stat_sources = _StatCard("Sources", "0", "Unique sources", _ORANGE)

        for card in (self._stat_total, self._stat_updates,
                     self._stat_size, self._stat_sources):
            self._stats_row.addWidget(card, 1)

        parent.addLayout(self._stats_row)

    def _build_empty_state(self):
        self._empty_frame = QFrame(self._content_widget)
        self._empty_frame.setStyleSheet("background: transparent; border: none;")
        el = QVBoxLayout(self._empty_frame)
        el.setContentsMargins(0, 60, 0, 0)
        el.setSpacing(8)
        el.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        icon = QLabel()
        icon.setFixedSize(48, 48)
        icon_pixmap = _svg_icon("appimage.svg", 48, "#A0A3B0")
        if not icon_pixmap.isNull():
            icon.setPixmap(icon_pixmap.pixmap(48, 48))
        else:
            icon.setText("📦")
            icon.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)

        t1 = QLabel("No AppImages yet")
        t1.setStyleSheet(
            f"color: {_TEXT}; font-size: 16px; font-weight: 600;"
            "background: transparent; border: none;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t1)

        t2 = QLabel("Add an AppImage from a local file or URL to get started.")
        t2.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t2)

        empty_add = QPushButton(" Add from File")
        empty_add.setIcon(_svg_icon("ui/import.svg", 14, "#0C0C0E"))
        empty_add.setIconSize(QRectF(0, 0, 14, 14).toRect().size())
        empty_add.setFixedHeight(36)
        empty_add.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_add.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF; color: #0C0C0E;
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 10px; padding: 0 20px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #E8EAF0; }}
            QPushButton:pressed {{ background-color: #D3D6DE; }}
        """)
        empty_add.clicked.connect(self.add_from_file)
        el.addWidget(empty_add, 0, Qt.AlignmentFlag.AlignCenter)

        t3 = QLabel("Portable  ·  Desktop Integration  ·  Updates  ·  Easy Removal")
        t3.setStyleSheet(
            f"color: {_TEXT3}; font-size: 10px;"
            "background: transparent; border: none;")
        t3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t3)

        self._empty_frame.setVisible(False)

    # ── Helpers ─────────────────────────────────────────────────────

    def _log(self, msg):
        try:
            self.main_app.log(msg)
        except Exception:
            pass

    def _set_busy(self, busy):
        self._busy = busy
        self._add_file_btn.setEnabled(not busy)

    # ── Filtering / sorting ─────────────────────────────────────────

    def _get_filtered_sorted(self):
        entries = list(self._entries)
        if self._search_text:
            q = self._search_text.lower()
            entries = [e for e in entries if q in e.get("name", "").lower()
                       or q in e.get("id", "").lower()
                       or q in e.get("source", "").lower()]
        key_map = {
            "name_asc": lambda e: e.get("name", "").lower(),
            "name_desc": lambda e: e.get("name", "").lower(),
            "newest": lambda e: e.get("installed_at", ""),
            "source": lambda e: e.get("source_type", ""),
        }
        reverse = self._sort_mode in ("name_desc", "newest")
        entries.sort(key=key_map.get(self._sort_mode, key_map["name_asc"]), reverse=reverse)
        return entries

    # ── Stats ───────────────────────────────────────────────────────

    def _update_stats(self):
        total = len(self._entries)
        updates = sum(1 for e in self._entries if e.get("latest_version"))
        total_size = sum(_file_size(e.get("bin_path", "")) for e in self._entries)
        sources = len({e.get("source_type", "") for e in self._entries})

        self._stat_total.set_value(total, "All managed AppImages")
        self._stat_updates.set_value(updates, "Ready to update")
        self._stat_size.set_value(_fmt_size(total_size), "Disk usage")
        self._stat_sources.set_value(sources, "Unique sources")

    # ── Rendering ───────────────────────────────────────────────────

    def _render_apps(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        filtered = self._get_filtered_sorted()
        self._empty_frame.setVisible(len(filtered) == 0)

        # ── Section header (inside scroll, like Git "Your Projects") ──
        header = QWidget()
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.setSpacing(8)

        total = len(self._entries)
        shown = len(filtered)
        if total == shown:
            count_text = f"{total} application{'s' if total != 1 else ''}"
        else:
            count_text = f"{shown} of {total} applications"

        label = QLabel(count_text)
        label.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 600;"
            "background: transparent; border: none;")
        hrow.addWidget(label)
        hrow.addStretch(1)

        sort_labels = {"name_asc": "Name A-Z", "name_desc": "Name Z-A",
                       "newest": "Newest", "source": "Source"}
        self._sort_btn = QPushButton(sort_labels.get(self._sort_mode, "Name A-Z"))
        self._sort_btn.setFixedHeight(28)
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: 1px solid {_BORDER}; border-radius: 6px;
                padding: 0 10px; font-size: 11px; font-weight: 500;
            }}
            QPushButton:hover {{ color: {_TEXT}; border-color: {_BORDER_HOVER}; }}
        """)
        self._sort_btn.clicked.connect(self._cycle_sort)
        hrow.addWidget(self._sort_btn)

        self._content_layout.addWidget(header)

        for entry in filtered:
            row = _AppRow(entry)
            row.update_requested.connect(self._on_update)
            row.remove_requested.connect(self._on_remove)
            row.open_requested.connect(self._on_open)
            self._content_layout.addWidget(row)

        self._content_layout.addStretch(1)

    # ── Public API ──────────────────────────────────────────────────

    def refresh(self):
        from neoarch.backend.services.appimage import list_appimages
        try:
            self._entries = list_appimages()
        except Exception as e:
            self._entries = []
            self._log(f"AppImage list error: {e}")
        self._update_stats()
        self._render_apps()

    # ── Actions ─────────────────────────────────────────────────────

    def _run(self, title, fn):
        if self._busy:
            return
        self._set_busy(True)

        def task():
            try:
                ok, msg = fn()
            except Exception as e:
                ok, msg = False, f"{e}"
            try:
                self.main_app.show_message.emit(title, msg)
            except Exception:
                QMessageBox.information(self, title, msg)
            QTimer.singleShot(0, self.refresh)
            QTimer.singleShot(0, self.data_changed.emit)

        Thread(target=task, daemon=True).start()

    def add_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select AppImage", os.path.expanduser("~"),
            "AppImage files (*.AppImage *.appimage);;All files (*)")
        if not path:
            return
        self._run("Add AppImage", lambda: _file_add(path))

    def add_from_url(self):
        name, ok = QInputDialog.getText(self, "Add from URL", "AppImage name (e.g. Obsidian):")
        if not ok or not name.strip():
            return
        url, ok = QInputDialog.getText(self, "Add from URL", "Direct download URL (.AppImage):")
        if not ok or not url.strip():
            return
        self._run("Add AppImage", lambda: _url_add(name.strip(), url.strip()))

    def check_updates(self):
        self._run("Check Updates", _check_all)

    def _on_update(self, aid):
        reply = QMessageBox.question(
            self, "Update AppImage", f"Update '{aid}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run("Update AppImage", lambda: _update_ids([aid]))

    def _on_remove(self, aid):
        reply = QMessageBox.question(
            self, "Remove AppImage",
            f"Remove '{aid}' and its desktop entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run("Remove AppImage", lambda: _remove_ids([aid]))

    def _on_open(self, aid):
        import subprocess
        from neoarch.backend.services import appimage
        try:
            entries = appimage.list_appimages()
            entry = next((e for e in entries if e.get("id") == aid), None)
        except Exception:
            entry = None
        if entry:
            path = entry.get("bin_path", "")
            if path and os.path.isfile(path):
                subprocess.Popen([path])

    def _cycle_sort(self):
        modes = ["name_asc", "name_desc", "newest", "source"]
        labels = ["Name A-Z", "Name Z-A", "Newest", "Source"]
        idx = modes.index(self._sort_mode) if self._sort_mode in modes else 0
        idx = (idx + 1) % len(modes)
        self._sort_mode = modes[idx]
        self._render_apps()

    def set_search(self, text):
        self._search_text = text
        self._render_apps()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_empty_frame') and self._empty_frame.isVisible():
            cw = self._content_widget.width()
            ch = self._content_widget.height()
            ew = min(380, cw - 40)
            self._empty_frame.setGeometry(
                int((cw - ew) / 2), 40, ew, ch - 60)


# ── Backend wrappers ───────────────────────────────────────────────

def _file_add(path):
    from neoarch.backend.services import appimage
    appimage.add_from_file(path)
    return True, f"Added {os.path.basename(path)}."


def _url_add(name, url):
    from neoarch.backend.services import appimage
    entry = appimage.add_from_url(name, url)
    return True, f"Added {entry.get('name', name)}."


def _check_all():
    from neoarch.backend.services import appimage
    results = appimage.check_all_updates()
    if not results:
        return True, "All AppImages up to date."
    return True, f"{len(results)} update(s) available:\n" + "\n".join(
        f"  {r.get('name', r.get('id', ''))}: {r.get('latest_version', '')}" for r in results)


def _update_ids(ids):
    from neoarch.backend.services import appimage
    done = []
    for aid in ids:
        if appimage.install_update(aid):
            done.append(aid)
    return True, f"Updated {len(done)}/{len(ids)} AppImage(s)."


def _remove_ids(ids):
    from neoarch.backend.services import appimage
    for aid in ids:
        appimage.remove_appimage(aid)
    return True, f"Removed {len(ids)} AppImage(s)."
