"""Git Projects full-page view for NeoArch.

Premium dark-themed page for cloning, building, updating, and managing
Git repositories.  Follows the NeoArch visual identity established by
PluginsView and the Updates/Installed table pages.
"""

import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QScrollArea, QMenu, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QRectF, QPoint,
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QCursor, QIcon, QPixmap,
)
from PyQt6.QtSvg import QSvgRenderer
from neoarch.resources.paths import PROJECT_ROOT

__all__ = ["GitTab"]

# ── design tokens ──────────────────────────────────────────────────
_BG = "#191A1F"
_SURFACE = "#16171A"
_SURFACE_2 = "#1E1F24"
_TEXT = "#EDEDEF"
_TEXT2 = "#8B8D97"
_TEXT3 = "#5C5E66"
_ACCENT = "#00BFAE"
_BORDER = "rgba(255,255,255,0.06)"
_BORDER_HOVER = "rgba(255,255,255,0.10)"
_RADIUS_SM = 8
_RADIUS_MD = 10
_RADIUS_LG = 14
_RADIUS_CARD = 16

# Semantic colors
_TEAL = "#00D4AA"
_ORANGE = "#FF9F1C"


def _svg_icon(rel_path, size, color="#FFFFFF"):
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
_PURPLE = "#8B7CFF"
_BLUE = "#4C9AFF"
_GREEN = "#22C55E"
_RED = "#FF6B6B"
_YELLOW = "#FBBF24"


def _relative_time(ts):
    """Return a human-readable relative time string."""
    if not ts:
        return "Unknown"
    diff = time.time() - ts
    if diff < 60:
        return "Just now"
    if diff < 3600:
        m = int(diff / 60)
        return f"{m}m ago"
    if diff < 86400:
        h = int(diff / 3600)
        return f"{h}h ago"
    d = int(diff / 86400)
    return f"{d}d ago"


def _fmt_size(nbytes):
    if nbytes < 1024:
        return f"{nbytes} B"
    for unit in ("KB", "MB", "GB"):
        nbytes /= 1024
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit == "GB" else f"{nbytes:.0f} {unit}"
    return f"{nbytes:.1f} TB"


def _base_url(url):
    """Strip .git suffix and protocol for display."""
    if not url:
        return ""
    u = url
    for prefix in ("https://", "http://", "git@"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    u = u.replace(":", "/")
    if u.endswith(".git"):
        u = u[:-4]
    return u


# ── Stat Card ──────────────────────────────────────────────────────

class _StatCard(QFrame):
    """Compact overview stat card."""

    def __init__(self, title, value, subtitle, color, parent=None):
        super().__init__(parent)
        self.setObjectName("gitStatCard")
        self.setFixedHeight(88)
        self._color = color
        self._value_text = value
        self._subtitle_text = subtitle

        self.setStyleSheet(f"""
            QFrame#gitStatCard {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_LG}px;
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
        self._value_text = value
        self._value_lbl.setText(str(value))
        if subtitle is not None:
            self._subtitle_text = subtitle
            self._sub_lbl.setText(subtitle)


# ── Chip / Badge ───────────────────────────────────────────────────

class _Badge(QLabel):
    """Small inline badge for build system / language."""

    def __init__(self, text, bg="rgba(255,255,255,0.06)", color=_TEXT2, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 600;"
            f"background: {bg}; border-radius: 4px; padding: 2px 7px;"
            "border: none;")
        self.setFixedHeight(18)


# ── Donut Chart ────────────────────────────────────────────────────

class _DonutChart(QWidget):
    """Minimal donut chart for storage visualization."""

    def __init__(self, size=100, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._segments = []  # [(fraction, color)]

    def set_segments(self, segments):
        """segments = [(fraction, QColor), ...]"""
        self._segments = segments
        self.update()

    def paintEvent(self, event):
        if not self._segments:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 4
        inner = r * 0.62

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("rgba(255,255,255,0.04)"))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Segments
        start = -90 * 16  # 12 o'clock in 1/16 degree
        span_total = int(360 * 16 * 0.995)
        for frac, color in self._segments:
            span = int(frac * span_total)
            if span < 1:
                continue
            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPie(QRectF(cx - r, cy - r, r * 2, r * 2), start, span)
            start += span

        # Cut out center
        p.setBrush(QColor(_BG))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - inner, cy - inner, inner * 2, inner * 2))
        p.end()


# ── Project Row ────────────────────────────────────────────────────

class _ProjectRow(QFrame):
    """Single project row in the project list."""

    pull_requested = pyqtSignal(str)    # repo_path
    build_requested = pyqtSignal(str)
    open_requested = pyqtSignal(str)
    menu_requested = pyqtSignal(object, QPoint)  # repo_info, pos

    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.setObjectName("gitProjectRow")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#gitProjectRow {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_MD}px;
            }}
            QFrame#gitProjectRow:hover {{
                border-color: {_BORDER_HOVER};
                background: {_SURFACE_2};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # ── Left: project identity ──
        left = QVBoxLayout()
        left.setSpacing(0)
        left.setContentsMargins(0, 0, 0, 0)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)

        # Name
        name_lbl = QLabel(repo.get("name", ""))
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none;")
        top_row.addWidget(name_lbl)

        # Build system badge
        bs = repo.get("build_system", "")
        if bs:
            bs_bg = "rgba(0,191,174,0.12)" if bs == "PKGBUILD" else "rgba(255,255,255,0.06)"
            bs_color = _ACCENT if bs == "PKGBUILD" else _TEXT2
            top_row.addWidget(_Badge(bs, bs_bg, bs_color))

        # Language badge
        lang = repo.get("language", "")
        if lang:
            top_row.addWidget(_Badge(lang, "rgba(139,124,255,0.12)", _PURPLE))

        # PKGBUILD badge
        if repo.get("has_pkgbuild") and bs != "PKGBUILD":
            top_row.addWidget(_Badge("PKGBUILD", "rgba(0,191,174,0.12)", _ACCENT))

        top_row.addStretch(1)
        left.addLayout(top_row)

        # URL
        url = _base_url(repo.get("url", ""))
        if url:
            url_lbl = QLabel(url)
            url_lbl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px;"
                "background: transparent; border: none;")
            left.addWidget(url_lbl)

        layout.addLayout(left, 1)

        # ── Middle: status ──
        middle = QVBoxLayout()
        middle.setSpacing(1)
        middle.setContentsMargins(20, 0, 20, 0)

        # Status chip
        status_text, status_color = self._compute_status(repo)
        status_lbl = QLabel(status_text)
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 11px; font-weight: 500;"
            "background: transparent; border: none;")
        middle.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignLeft)

        # Branch + updated
        branch = repo.get("branch", "")
        updated = _relative_time(repo.get("last_commit") or repo.get("mtime", 0))
        info_parts = []
        if branch:
            info_parts.append(branch)
        info_parts.append(f"Updated {updated}")
        info_lbl = QLabel(" · ".join(info_parts))
        info_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 10px;"
            "background: transparent; border: none;")
        middle.addWidget(info_lbl, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(middle, 1)

        # ── Right: actions ──
        right = QHBoxLayout()
        right.setSpacing(6)
        right.setContentsMargins(0, 0, 0, 0)

        behind = repo.get("behind", 0)
        modified = repo.get("modified_count", 0)

        if behind > 0:
            pull_btn = self._action_btn(f"Update ({behind})", _ORANGE)
            pull_btn.clicked.connect(lambda: self.pull_requested.emit(repo["path"]))
            right.addWidget(pull_btn)
        elif modified > 0:
            pull_btn = self._action_btn("Status", _TEXT2)
            pull_btn.clicked.connect(lambda: self.pull_requested.emit(repo["path"]))
            right.addWidget(pull_btn)
        else:
            pull_btn = self._action_btn("Pull", _TEXT2)
            pull_btn.clicked.connect(lambda: self.pull_requested.emit(repo["path"]))
            right.addWidget(pull_btn)

        build_btn = self._action_btn("Build", _TEXT2)
        build_btn.clicked.connect(lambda: self.build_requested.emit(repo["path"]))
        right.addWidget(build_btn)

        open_btn = self._action_btn("Open", _ACCENT)
        open_btn.clicked.connect(lambda: self.open_requested.emit(repo["path"]))
        right.addWidget(open_btn)

        # Three-dot menu
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
        menu_btn.clicked.connect(
            lambda: self.menu_requested.emit(self.repo, QCursor.pos()))
        right.addWidget(menu_btn)

        layout.addLayout(right)

    @staticmethod
    def _compute_status(repo):
        modified = repo.get("modified_count", 0)
        behind = repo.get("behind", 0)
        if behind > 0:
            return f"↓ {behind} commits behind", _ORANGE
        if modified > 0:
            return f"● Modified ({modified})", _YELLOW
        return "● Clean", _GREEN

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


# ── Build Activity Row ─────────────────────────────────────────────

class _BuildRow(QWidget):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        icon = "✓" if entry.get("success") else "✕"
        color = _GREEN if entry.get("success") else _RED

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(14)
        icon_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 700;"
            "background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(entry.get("name", ""))
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 11px; font-weight: 600;"
            "background: transparent; border: none;")
        layout.addWidget(name_lbl)

        msg = entry.get("message", "")
        if len(msg) > 30:
            msg = msg[:30] + "…"
        msg_lbl = QLabel(msg)
        msg_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 11px;"
            "background: transparent; border: none;")
        layout.addWidget(msg_lbl, 1)

        ts = entry.get("time", 0)
        time_lbl = QLabel(time.strftime("%I:%M %p", time.localtime(ts)) if ts else "")
        time_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 10px;"
            "background: transparent; border: none;")
        layout.addWidget(time_lbl)


# ── Main GitTab ────────────────────────────────────────────────────

class GitTab(QWidget):
    """Full-page Git Projects view."""

    clone_requested = pyqtSignal()

    def __init__(self, manager, main_app, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.main_app = main_app
        self._repos = []
        self._search_text = ""
        self._sort_mode = "updated"
        self._show_grid = False
        self._init_ui()
        self.manager.repos_changed.connect(self.refresh)
        self.refresh()

    # ── UI construction ────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        # ── Header ──
        self._build_header(root)

        # ── Stats row ──
        self._build_stats(root)

        # ── Spacer before projects ──
        spacer = QWidget()
        spacer.setFixedHeight(12)
        spacer.setStyleSheet("background: transparent; border: none;")
        root.addWidget(spacer)

        # ── Scroll area for projects ──
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

        # ── Bottom panels (build activity + storage) ──
        self._build_bottom_panels(root)

        # ── Empty state (overlaid) ──
        self._build_empty_state()

    def _build_header(self, parent):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Git Projects")
        title.setStyleSheet(
            f"color: {_TEXT}; font-size: 20px; font-weight: 700;"
            "background: transparent; border: none;")
        left.addWidget(title)

        subtitle = QLabel("Clone, build, update, and manage Git projects")
        subtitle.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        left.addWidget(subtitle)

        row.addLayout(left, 1)

        # Clone button
        clone_btn = QPushButton(" Clone Repository")
        clone_btn.setIcon(_svg_icon("discover/git.svg", 16, "#0C0C0E"))
        clone_btn.setIconSize(QRectF(0, 0, 16, 16).toRect().size())
        clone_btn.setFixedHeight(34)
        clone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clone_btn.setStyleSheet(f"""
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
        clone_btn.clicked.connect(self._on_clone)
        row.addWidget(clone_btn)

        parent.addLayout(row)

    def _build_stats(self, parent):
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(10)
        self._stats_row.setContentsMargins(0, 0, 0, 0)

        self._stat_total = _StatCard("Total Projects", "0", "All Git projects", _TEAL)
        self._stat_updates = _StatCard("Updates Available", "0", "Projects to update", _ORANGE)
        self._stat_builds = _StatCard("Builds Today", "0", "Successful builds", _PURPLE)
        self._stat_disk = _StatCard("Disk Usage", "—", "Across all projects", _BLUE)

        for card in (self._stat_total, self._stat_updates,
                     self._stat_builds, self._stat_disk):
            self._stats_row.addWidget(card, 1)

        parent.addLayout(self._stats_row)

    def _build_bottom_panels(self, parent):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 4, 0, 0)

        _scroll_qss = (
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 2px; min-height: 20px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        _frame_qss = f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_LG}px;
            }}
        """

        # Build Activity
        build_frame = QFrame()
        build_frame.setStyleSheet(_frame_qss)
        build_frame.setFixedHeight(140)
        bl = QVBoxLayout(build_frame)
        bl.setContentsMargins(12, 6, 12, 6)
        bl.setSpacing(2)

        bh = QHBoxLayout()
        bh.setSpacing(8)
        bh.setContentsMargins(0, 0, 0, 0)
        bh_title = QLabel("Build Activity")
        bh_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;")
        bh.addWidget(bh_title)
        bh.addStretch(1)
        bl.addLayout(bh)

        self._build_list_layout = QVBoxLayout()
        self._build_list_layout.setSpacing(0)
        self._build_list_layout.setContentsMargins(0, 0, 0, 0)
        build_inner = QWidget()
        build_inner.setLayout(self._build_list_layout)
        build_scroll = QScrollArea()
        build_scroll.setWidgetResizable(True)
        build_scroll.setWidget(build_inner)
        build_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        build_scroll.setStyleSheet(_scroll_qss)
        bl.addWidget(build_scroll)

        row.addWidget(build_frame, 2)

        # Storage
        storage_frame = QFrame()
        storage_frame.setStyleSheet(_frame_qss)
        storage_frame.setFixedHeight(140)
        sl = QVBoxLayout(storage_frame)
        sl.setContentsMargins(12, 6, 12, 6)
        sl.setSpacing(2)

        sl_title = QLabel("Repository Storage")
        sl_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;")
        sl.addWidget(sl_title)

        # Donut + total
        top = QHBoxLayout()
        top.setSpacing(8)
        self._donut = _DonutChart(48)
        top.addWidget(self._donut, 0, Qt.AlignmentFlag.AlignTop)

        self._disk_total = QLabel("—")
        self._disk_total.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 700;"
            "background: transparent; border: none;")
        top.addWidget(self._disk_total, 0, Qt.AlignmentFlag.AlignTop)
        top.addStretch(1)
        sl.addLayout(top)

        self._disk_list_layout = QVBoxLayout()
        self._disk_list_layout.setSpacing(2)
        self._disk_list_layout.setContentsMargins(0, 0, 0, 0)
        disk_inner = QWidget()
        disk_inner.setLayout(self._disk_list_layout)
        disk_scroll = QScrollArea()
        disk_scroll.setWidgetResizable(True)
        disk_scroll.setWidget(disk_inner)
        disk_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        disk_scroll.setStyleSheet(_scroll_qss)
        sl.addWidget(disk_scroll)

        row.addWidget(storage_frame, 1)
        parent.addLayout(row)

    def _build_empty_state(self):
        self._empty_frame = QFrame(self._content_widget)
        self._empty_frame.setObjectName("gitEmptyState")
        self._empty_frame.setStyleSheet(f"""
            QFrame#gitEmptyState {{
                background: transparent; border: none;
            }}
        """)
        el = QVBoxLayout(self._empty_frame)
        el.setContentsMargins(0, 60, 0, 0)
        el.setSpacing(8)
        el.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        icon = QLabel("📂")
        icon.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(icon)

        t1 = QLabel("No Git projects yet")
        t1.setStyleSheet(
            f"color: {_TEXT}; font-size: 16px; font-weight: 600;"
            "background: transparent; border: none;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t1)

        t2 = QLabel("Clone a repository to build and manage software projects.")
        t2.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t2)

        empty_clone = QPushButton(" Clone Repository")
        empty_clone.setIcon(_svg_icon("discover/git.svg", 16, "#FFFFFF"))
        empty_clone.setIconSize(QRectF(0, 0, 16, 16).toRect().size())
        empty_clone.setFixedHeight(36)
        empty_clone.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_clone.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: {_RADIUS_SM}px;
                padding: 0 20px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        empty_clone.clicked.connect(self._on_clone)
        el.addWidget(empty_clone, 0, Qt.AlignmentFlag.AlignCenter)

        t3 = QLabel("Supports Cargo · CMake · Make · Meson · Go · npm · PKGBUILD")
        t3.setStyleSheet(
            f"color: {_TEXT3}; font-size: 10px;"
            "background: transparent; border: none;")
        t3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t3)

        self._empty_frame.setVisible(False)

    # ── Public API ─────────────────────────────────────────────────

    def refresh(self):
        """Reload repository data from the manager and update all panels."""
        self._repos = self.manager.get_repos()
        self._update_stats()
        self._render_projects()
        self._render_build_history()
        self._render_storage()

    # ── Stats ──────────────────────────────────────────────────────

    def _update_stats(self):
        stats = self.manager.get_stats(self._repos)
        self._stat_total.set_value(stats["total"], "All Git projects")
        self._stat_updates.set_value(stats["updates"], "Projects to update")
        self._stat_builds.set_value(stats["builds_today"], "Successful builds")
        self._stat_disk.set_value(stats["disk_usage_fmt"], "Across all projects")

    # ── Project list ───────────────────────────────────────────────

    def _get_filtered_sorted(self):
        repos = list(self._repos)
        if self._search_text:
            q = self._search_text.lower()
            repos = [r for r in repos if q in r.get("name", "").lower()
                     or q in r.get("url", "").lower()
                     or q in r.get("branch", "").lower()]
        if self._sort_mode == "updated":
            repos.sort(key=lambda r: r.get("mtime", 0), reverse=True)
        elif self._sort_mode == "name":
            repos.sort(key=lambda r: r.get("name", "").lower())
        elif self._sort_mode == "size":
            repos.sort(key=lambda r: r.get("disk_usage", 0), reverse=True)
        elif self._sort_mode == "branch":
            repos.sort(key=lambda r: r.get("branch", "").lower())
        return repos

    def _render_projects(self):
        # Clear existing rows
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # ── Projects section header (inside scroll) ──
        header = QWidget()
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.setSpacing(8)

        label = QLabel("Your Projects")
        label.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 600;"
            "background: transparent; border: none;")
        hrow.addWidget(label)
        hrow.addStretch(1)

        self._sort_btn = QPushButton("Last Updated")
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

        repos = self._get_filtered_sorted()
        self._empty_frame.setVisible(len(repos) == 0)

        for repo in repos:
            row = _ProjectRow(repo)
            row.pull_requested.connect(self._on_pull)
            row.build_requested.connect(self._on_build)
            row.open_requested.connect(self._on_open)
            row.menu_requested.connect(self._on_row_menu)
            self._content_layout.addWidget(row)

        self._content_layout.addStretch(1)

    # ── Build history ──────────────────────────────────────────────

    def _render_build_history(self):
        while self._build_list_layout.count():
            item = self._build_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        history = self.manager.get_build_history()[:5]
        if not history:
            lbl = QLabel("No recent builds")
            lbl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 11px;"
                "background: transparent; border: none; padding: 8px 0;")
            self._build_list_layout.addWidget(lbl)
        else:
            for entry in history:
                self._build_list_layout.addWidget(_BuildRow(entry))

    # ── Storage ────────────────────────────────────────────────────

    def _render_storage(self):
        while self._disk_list_layout.count():
            item = self._disk_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        total = sum(r.get("disk_usage", 0) for r in self._repos)
        self._disk_total.setText(_fmt_size(total))

        # Donut segments
        colors = [_TEAL, _PURPLE, _BLUE, _ORANGE, _YELLOW, _RED, "#6EE7B7", "#C084FC"]
        segments = []
        for i, repo in enumerate(sorted(self._repos, key=lambda r: r.get("disk_usage", 0), reverse=True)):
            size = repo.get("disk_usage", 0)
            if size and total:
                segments.append((size / total, colors[i % len(colors)]))
        self._donut.set_segments(segments[:8])

        # List
        for i, repo in enumerate(sorted(self._repos, key=lambda r: r.get("disk_usage", 0), reverse=True)[:6]):
            row = QHBoxLayout()
            row.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(10)
            dot.setStyleSheet(
                f"color: {colors[i % len(colors)]}; font-size: 8px;"
                "background: transparent; border: none;")
            row.addWidget(dot)

            name = QLabel(repo.get("name", ""))
            name.setStyleSheet(
                f"color: {_TEXT}; font-size: 11px;"
                "background: transparent; border: none;")
            row.addWidget(name, 1)

            size = QLabel(_fmt_size(repo.get("disk_usage", 0)))
            size.setStyleSheet(
                f"color: {_TEXT2}; font-size: 11px;"
                "background: transparent; border: none;")
            row.addWidget(size)

            container = QWidget()
            container.setLayout(row)
            self._disk_list_layout.addWidget(container)

    # ── Slots ──────────────────────────────────────────────────────

    def _on_clone(self):
        self.manager.install_from_git()

    def _on_pull(self, path):
        self.manager.update_repo(path)

    def _on_build(self, path):
        self.manager.build_repo(path)

    def _on_open(self, path):
        self.manager.open_repo(path)

    def _on_row_menu(self, repo, pos):
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
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: rgba(0,191,174,0.15);
            }}
            QMenu::separator {{
                height: 1px; background: {_BORDER};
                margin: 4px 8px;
            }}
        """)
        path = repo.get("path", "")

        act_pull = menu.addAction("Pull / Update")
        act_pull.triggered.connect(lambda: self._on_pull(path))

        act_build = menu.addAction("Build")
        act_build.triggered.connect(lambda: self._on_build(path))

        act_open = menu.addAction("Open Folder")
        act_open.triggered.connect(lambda: self._on_open(path))

        menu.addSeparator()

        if repo.get("has_pkgbuild"):
            act_pkg = menu.addAction("Build Package")
            act_pkg.triggered.connect(lambda: self._on_build(path))

        act_remove = menu.addAction("Remove")
        act_remove.triggered.connect(lambda: self._on_remove(repo))

        menu.exec(pos)

    def _on_remove(self, repo):
        reply = QMessageBox.question(
            self, "Remove Repository",
            f"Permanently delete '{repo.get('name', '')}' from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_repo(repo.get("path", ""))

    def set_search(self, text):
        self._search_text = text
        self._render_projects()

    def _cycle_sort(self):
        modes = ["updated", "name", "size", "branch"]
        labels = ["Last Updated", "Name", "Size", "Branch"]
        idx = modes.index(self._sort_mode) if self._sort_mode in modes else 0
        idx = (idx + 1) % len(modes)
        self._sort_mode = modes[idx]
        self._sort_btn.setText(labels[idx])
        self._render_projects()

    def _toggle_view(self):
        self._show_grid = not self._show_grid
        self._toggle_btn.setText("☰" if not self._show_grid else "≡")
        self._toggle_btn.setToolTip("Grid View" if not self._show_grid else "List View")
        self._render_projects()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition empty state
        if hasattr(self, '_empty_frame') and self._empty_frame.isVisible():
            cw = self._content_widget.width()
            ch = self._content_widget.height()
            ew = min(380, cw - 40)
            self._empty_frame.setGeometry(
                int((cw - ew) / 2), 40, ew, ch - 60)
