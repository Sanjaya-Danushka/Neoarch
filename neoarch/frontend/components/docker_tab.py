"""Docker full-page view for NeoArch.

Premium dark-themed page for managing Docker containers, images, volumes,
and networks. Follows the NeoArch visual identity established by GitTab.
"""

import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QDialog, QComboBox,
    QCheckBox, QPlainTextEdit, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtSvg import QSvgRenderer

__all__ = ["DockerTab"]

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
_TEAL = "#00D4AA"
_ORANGE = "#FF9F1C"
_PURPLE = "#8B7CFF"
_BLUE = "#4C9AFF"
_GREEN = "#22C55E"
_RED = "#FF6B6B"

_SCROLL_QSS = (
    "QScrollArea { background: transparent; border: none; }"
    "QScrollBar:vertical { background: transparent; width: 6px; }"
    "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
    "  border-radius: 3px; min-height: 30px; }"
    "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

_INPUT_QSS = """
    QLineEdit {
        background-color: rgba(28, 30, 36, 0.9);
        color: #EDEDEF;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 12px;
        selection-background-color: rgba(0, 191, 174, 0.3);
    }
    QLineEdit:focus { border-color: rgba(0, 191, 174, 0.5); }
    QLineEdit::placeholder { color: #5C5E66; }
"""

_COMBO_QSS = """
    QComboBox {
        background-color: rgba(28, 30, 36, 0.9);
        color: #EDEDEF;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 11px;
        min-width: 100px;
    }
    QComboBox:focus { border-color: rgba(0, 191, 174, 0.4); }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox::down-arrow { image: none; border: none; }
    QComboBox QAbstractItemView {
        background-color: rgba(22, 23, 26, 0.98);
        color: #EDEDEF;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        selection-background-color: rgba(0, 191, 174, 0.15);
        outline: none;
    }
"""

_CHECKBOX_QSS = """
    QCheckBox {
        color: #C9C9CD; font-size: 11px; spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px; height: 16px; border-radius: 4px;
        border: 1.5px solid #5C5E66; background-color: rgba(28, 30, 36, 0.9);
    }
    QCheckBox::indicator:checked { background-color: #00BFAE; border-color: #00BFAE; }
    QCheckBox::indicator:hover { border-color: #00BFAE; }
"""

_PLAIN_QSS = """
    QPlainTextEdit {
        background-color: rgba(28, 30, 36, 0.9);
        color: #EDEDEF;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 6px 8px;
        font-size: 12px;
        selection-background-color: rgba(0, 191, 174, 0.3);
    }
    QPlainTextEdit:focus { border-color: rgba(0, 191, 174, 0.4); }
"""

_MENU_QSS = """
    QMenu { background-color: #2A2D33; color: #F0F0F0;
            border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
            padding: 4px; }
    QMenu::item { padding: 5px 20px; border-radius: 4px; font-size: 12px; }
    QMenu::item:selected { background-color: rgba(0, 191, 174, 0.18); }
"""


# ── helpers ────────────────────────────────────────────────────────

def _field_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {_TEXT2}; font-size: 11px; font-weight: 500;"
        "background: transparent; border: none; padding-top: 4px;")
    return lbl


class _StatCard(QFrame):
    """Compact overview stat card — matches GitTab design."""

    def __init__(self, title, value, subtitle, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(88)
        self._color = color

        self.setStyleSheet(f"""
            QFrame {{
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
        self._value_lbl.setText(str(value))
        if subtitle is not None:
            self._sub_lbl.setText(subtitle)


class _TabButton(QPushButton):
    """Segmented-control tab button."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)
        self.toggled.connect(lambda c: self._update_style(c))

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0, 191, 174, 0.14);
                    color: {_TEAL};
                    border: 1px solid rgba(0, 191, 174, 0.25);
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: 12px; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {_TEXT2};
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: 12px; font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {_TEXT};
                    background: rgba(255, 255, 255, 0.04);
                }}
            """)


# ── main tab ───────────────────────────────────────────────────────

class DockerTab(QWidget):
    """Full-page Docker manager."""

    def __init__(self, manager, main_app, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.main_app = main_app
        self._active_tab = "containers"
        self._search_text = ""
        self._containers = []
        self._images = []
        self._volumes = []
        self._networks = []
        self._init_ui()
        try:
            self.manager.containers_changed.connect(self.refresh)
        except Exception:
            pass
        self.refresh()

    # ── layout ──────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)
        self._build_header(root)
        self._build_stats(root)

        spacer = QWidget()
        spacer.setFixedHeight(12)
        spacer.setStyleSheet("background: transparent; border: none;")
        root.addWidget(spacer)

        self._build_segmented_nav(root)
        self._build_content(root)
        self._build_empty_state()

    def _build_header(self, parent):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Docker")
        title.setStyleSheet(
            f"color: {_TEXT}; font-size: 20px; font-weight: 700;"
            "background: transparent; border: none;")
        left.addWidget(title)

        subtitle = QLabel("Manage containers, images, and Docker resources")
        subtitle.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        left.addWidget(subtitle)
        row.addLayout(left, 1)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search...")
        self._search_input.setFixedWidth(180)
        self._search_input.setFixedHeight(32)
        self._search_input.setStyleSheet(_INPUT_QSS)
        self._search_input.textChanged.connect(self._on_search)
        row.addWidget(self._search_input)

        self._run_btn = QPushButton("+ Run Container")
        self._run_btn.setFixedHeight(34)
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setStyleSheet(f"""
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
        self._run_btn.clicked.connect(self.run_container)
        row.addWidget(self._run_btn)

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(34, 34)
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06);
                color: {_TEXT2};
                border: 1px solid {_BORDER};
                border-radius: 10px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.10); color: {_TEXT}; }}
        """)
        self._refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self._refresh_btn)

        parent.addLayout(row)

    def _build_stats(self, parent):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        self._stat_containers = _StatCard("Containers", "—", "All containers", _TEAL)
        self._stat_running = _StatCard("Running", "—", "Currently active", _TEAL)
        self._stat_images = _StatCard("Images", "—", "Local images", _PURPLE)
        self._stat_disk = _StatCard("Storage", "—", "Docker disk usage", _BLUE)
        row.addWidget(self._stat_containers)
        row.addWidget(self._stat_running)
        row.addWidget(self._stat_images)
        row.addWidget(self._stat_disk)
        parent.addLayout(row)

    def _build_segmented_nav(self, parent):
        row = QHBoxLayout()
        row.setSpacing(4)
        row.setContentsMargins(0, 0, 0, 0)
        self._tabs = {}
        for key, label in [("containers", "Containers"), ("images", "Images"),
                           ("volumes", "Volumes"), ("networks", "Networks")]:
            btn = _TabButton(label)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            self._tabs[key] = btn
            row.addWidget(btn)
        row.addStretch(1)
        parent.addLayout(row)

    def _build_content(self, parent):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(_SCROLL_QSS)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._scroll.setWidget(self._content_widget)
        parent.addWidget(self._scroll, 1)

    def _build_empty_state(self):
        self._empty_widget = QWidget()
        el = QVBoxLayout(self._empty_widget)
        el.setContentsMargins(40, 80, 40, 80)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("🐳")
        icon.setStyleSheet("font-size: 48px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(icon)
        el.addSpacing(12)
        t = QLabel("No containers yet")
        t.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 600;"
            "background: transparent; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(t)
        s = QLabel("Run a Docker image to create your first container.")
        s.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(s)
        el.addSpacing(16)
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        run_btn = QPushButton("+ Run Container")
        run_btn.setFixedHeight(34)
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF; color: #0C0C0E;
                border: 1px solid rgba(255,255,255,0.9);
                border-radius: 10px; padding: 0 18px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #E8EAF0; }}
            QPushButton:pressed {{ background: #D3D6DE; }}
        """)
        run_btn.clicked.connect(self.run_container)
        btn_row.addWidget(run_btn)
        pull_btn = QPushButton("Pull Image")
        pull_btn.setFixedHeight(34)
        pull_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pull_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: 1px solid {_BORDER}; border-radius: 10px;
                padding: 0 20px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.04); color: {_TEXT}; }}
        """)
        pull_btn.clicked.connect(self._show_pull_dialog)
        btn_row.addWidget(pull_btn)
        el.addLayout(btn_row)
        self._empty_widget.hide()

    # ── tab switching ───────────────────────────────────────────────

    def _switch_tab(self, key):
        self._active_tab = key
        for k, btn in self._tabs.items():
            btn.setChecked(k == key)
        self._render_content()

    # ── refresh ─────────────────────────────────────────────────────

    def refresh(self):
        if getattr(self, '_refreshing', False):
            return
        self._refreshing = True
        try:
            if not shutil.which("docker"):
                self._stat_containers.set_value("—")
                self._stat_running.set_value("—")
                self._stat_images.set_value("—")
                self._stat_disk.set_value("—")
                return
            self._containers = self.manager.load_containers(include_all=True)
            self._images = self.manager.list_images()
            self._volumes = self.manager.list_volumes()
            self._networks = self.manager.list_networks()
            running = sum(1 for c in self._containers if c.get('status', '').startswith('Up'))
            stopped = len(self._containers) - running
            self._stat_containers.set_value(str(len(self._containers)), f"{running} running, {stopped} stopped")
            self._stat_running.set_value(str(running), "Currently active")
            self._stat_images.set_value(str(len(self._images)), "Local images")
            self._stat_disk.set_value(str(len(self._volumes)) + " vols", "Docker volumes")
            self._render_content()
        finally:
            self._refreshing = False

    def _render_content(self):
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            w = child.widget()
            if w:
                w.setParent(None)

        has_any = bool(
            self._containers or self._images or self._volumes or self._networks)

        if self._active_tab == "containers":
            self._render_containers()
        elif self._active_tab == "images":
            self._render_images()
        elif self._active_tab == "volumes":
            self._render_volumes()
        elif self._active_tab == "networks":
            self._render_networks()

        self._empty_widget.hide()
        if self._active_tab == "containers" and not self._containers:
            self._content_layout.addWidget(self._empty_widget)
            self._empty_widget.show()
        self._content_layout.addStretch(1)

    def _on_search(self, text):
        self._search_text = text.strip().lower()
        self._render_content()

    # ── containers tab ──────────────────────────────────────────────

    def _render_containers(self):
        q = self._search_text
        running = [c for c in self._containers
                   if c.get('status', '').startswith('Up')
                   and (not q or q in c.get('name', '').lower() or q in c.get('image', '').lower())]
        stopped = [c for c in self._containers
                   if not c.get('status', '').startswith('Up')
                   and (not q or q in c.get('name', '').lower() or q in c.get('image', '').lower())]

        if running:
            hdr = self._section_header(f"Running Containers ({len(running)})")
            self._content_layout.addWidget(hdr)
            for c in running:
                self._content_layout.addWidget(self._container_row(c, running=True))

        if stopped:
            hdr = self._section_header(f"Other Containers ({len(stopped)})")
            self._content_layout.addWidget(hdr)
            for c in stopped:
                self._content_layout.addWidget(self._container_row(c, running=False))

        # Resource usage
        if running:
            self._content_layout.addWidget(self._section_header("Resource Usage"))
            self._content_layout.addWidget(self._resource_panel())

    def _container_row(self, c, running=True):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_MD}px;
            }}
            QFrame:hover {{
                border-color: {_BORDER_HOVER};
            }}
        """)
        frame.setFixedHeight(52)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(10)

        dot = QLabel("●")
        dot.setFixedWidth(10)
        if running:
            dot.setStyleSheet(f"color: {_TEAL}; font-size: 8px; background: transparent; border: none;")
        else:
            status = c.get('status', '')
            if 'code 1' in status.lower() or 'exited' in status.lower():
                dot.setStyleSheet(f"color: {_RED}; font-size: 8px; background: transparent; border: none;")
            else:
                dot.setStyleSheet(f"color: {_TEXT3}; font-size: 8px; background: transparent; border: none;")
        lay.addWidget(dot)

        name = QLabel(c.get('name', ''))
        name.setStyleSheet(f"color: {_TEXT}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        lay.addWidget(name)

        image = QLabel(c.get('image', ''))
        image.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(image)

        lay.addStretch(1)

        status_lbl = QLabel(c.get('status', ''))
        status_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(status_lbl)

        # Actions
        if running:
            for text, slot, color in [
                ("Logs", lambda cid=c['id']: self._show_logs(cid), None),
                ("Restart", lambda cid=c['id']: self.manager.restart_container(cid), None),
                ("Stop", lambda cid=c['id']: self.manager.stop_container(cid), _RED),
            ]:
                btn = QPushButton(text)
                btn.setFixedHeight(24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if color:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: rgba(255,107,107,0.10);
                            color: {_RED}; border: 1px solid rgba(255,107,107,0.2);
                            border-radius: 8px; padding: 0 10px;
                            font-size: 10px; font-weight: 600;
                        }}
                        QPushButton:hover {{ background: rgba(255,107,107,0.20); }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent; color: {_TEXT2};
                            border: 1px solid {_BORDER}; border-radius: 8px;
                            padding: 0 10px; font-size: 10px; font-weight: 500;
                        }}
                        QPushButton:hover {{ background: rgba(255,255,255,0.06); color: {_TEXT}; }}
                    """)
                btn.clicked.connect(slot)
                lay.addWidget(btn)
        else:
            for text, slot in [
                ("Start", lambda cid=c['id']: self.manager.start_container(cid)),
                ("Logs", lambda cid=c['id']: self._show_logs(cid)),
                ("Remove", lambda cid=c['id']: self._remove_container(cid)),
            ]:
                btn = QPushButton(text)
                btn.setFixedHeight(24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if text == "Remove":
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: rgba(255,107,107,0.10);
                            color: {_RED}; border: 1px solid rgba(255,107,107,0.2);
                            border-radius: 8px; padding: 0 10px;
                            font-size: 10px; font-weight: 600;
                        }}
                        QPushButton:hover {{ background: rgba(255,107,107,0.20); }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent; color: {_TEXT2};
                            border: 1px solid {_BORDER}; border-radius: 8px;
                            padding: 0 10px; font-size: 10px; font-weight: 500;
                        }}
                        QPushButton:hover {{ background: rgba(255,255,255,0.06); color: {_TEXT}; }}
                    """)
                btn.clicked.connect(slot)
                lay.addWidget(btn)

        frame.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        frame.customContextMenuRequested.connect(
            lambda pos, cid=c['id']: self._context_menu(pos, cid))
        return frame

    def _resource_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_LG}px;
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(24)

        for label, value, color in [
            ("CPU", "—", _TEAL),
            ("Memory", "—", _BLUE),
            ("Network", "—", _PURPLE),
            ("Disk", "—", _BLUE),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setContentsMargins(0, 0, 0, 0)
            vl = QLabel(value)
            vl.setStyleSheet(
                f"color: {_TEXT}; font-size: 14px; font-weight: 600;"
                "background: transparent; border: none;")
            col.addWidget(vl)
            tl = QLabel(label)
            tl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px;"
                "background: transparent; border: none;")
            col.addWidget(tl)
            lay.addLayout(col)

        lay.addStretch(1)
        return frame

    # ── images tab ──────────────────────────────────────────────────

    def _render_images(self):
        q = self._search_text
        images = [i for i in self._images
                  if not q or q in i.get('repo', '').lower() or q in i.get('tag', '').lower()]

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._section_header(f"Docker Images ({len(images)})"))
        row.addStretch(1)
        pull_btn = QPushButton("+ Pull Image")
        pull_btn.setFixedHeight(28)
        pull_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pull_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 7px;
                padding: 0 14px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        pull_btn.clicked.connect(self._show_pull_dialog)
        row.addWidget(pull_btn)
        w = QWidget()
        w.setLayout(row)
        self._content_layout.addWidget(w)

        for img in images:
            self._content_layout.addWidget(self._image_row(img))

    def _image_row(self, img):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_MD}px;
            }}
            QFrame:hover {{ border-color: {_BORDER_HOVER}; }}
        """)
        frame.setFixedHeight(44)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(10)

        name = QLabel(f"{img.get('repo', '')}:{img.get('tag', '')}")
        name.setStyleSheet(f"color: {_TEXT}; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        lay.addWidget(name)

        size = QLabel(img.get('size', ''))
        size.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(size)

        lay.addStretch(1)

        run_btn = QPushButton("Run")
        run_btn.setFixedHeight(24)
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,191,174,0.10); color: {_ACCENT};
                border: 1px solid rgba(0,191,174,0.2); border-radius: 8px;
                padding: 0 10px; font-size: 10px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(0,191,174,0.18); }}
        """)
        ref = f"{img.get('repo', '')}:{img.get('tag', '')}"
        run_btn.clicked.connect(lambda checked=False, r=ref: self.run_container(image=r))
        lay.addWidget(run_btn)

        rm_btn = QPushButton("Remove")
        rm_btn.setFixedHeight(24)
        rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rm_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,107,107,0.10); color: {_RED};
                border: 1px solid rgba(255,107,107,0.2); border-radius: 8px;
                padding: 0 10px; font-size: 10px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(255,107,107,0.20); }}
        """)
        rm_btn.clicked.connect(lambda checked=False, iid=img.get('id', ''): self.manager.remove_image(iid))
        lay.addWidget(rm_btn)

        return frame

    # ── volumes tab ─────────────────────────────────────────────────

    def _render_volumes(self):
        q = self._search_text
        vols = [v for v in self._volumes
                if not q or q in v.get('name', '').lower()]

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._section_header(f"Docker Volumes ({len(vols)})"))
        row.addStretch(1)
        create_btn = QPushButton("+ Create Volume")
        create_btn.setFixedHeight(28)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 7px;
                padding: 0 14px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        create_btn.clicked.connect(self._show_create_volume_dialog)
        row.addWidget(create_btn)
        w = QWidget()
        w.setLayout(row)
        self._content_layout.addWidget(w)

        for vol in vols:
            self._content_layout.addWidget(self._volume_row(vol))

    def _volume_row(self, vol):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_MD}px;
            }}
            QFrame:hover {{ border-color: {_BORDER_HOVER}; }}
        """)
        frame.setFixedHeight(44)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(10)

        name = QLabel(vol.get('name', ''))
        name.setStyleSheet(f"color: {_TEXT}; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        lay.addWidget(name)

        size = QLabel(vol.get('size', ''))
        size.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(size)

        lay.addStretch(1)

        rm_btn = QPushButton("Remove")
        rm_btn.setFixedHeight(24)
        rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rm_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,107,107,0.10); color: {_RED};
                border: 1px solid rgba(255,107,107,0.2); border-radius: 8px;
                padding: 0 10px; font-size: 10px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(255,107,107,0.20); }}
        """)
        rm_btn.clicked.connect(lambda checked=False, n=vol['name']: self._remove_volume(n))
        lay.addWidget(rm_btn)

        return frame

    # ── networks tab ────────────────────────────────────────────────

    def _render_networks(self):
        q = self._search_text
        nets = [n for n in self._networks
                if not q or q in n.get('name', '').lower()]

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._section_header(f"Docker Networks ({len(nets)})"))
        row.addStretch(1)
        create_btn = QPushButton("+ Create Network")
        create_btn.setFixedHeight(28)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 7px;
                padding: 0 14px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        create_btn.clicked.connect(self._show_create_network_dialog)
        row.addWidget(create_btn)
        w = QWidget()
        w.setLayout(row)
        self._content_layout.addWidget(w)

        for net in nets:
            self._content_layout.addWidget(self._network_row(net))

    def _network_row(self, net):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS_MD}px;
            }}
            QFrame:hover {{ border-color: {_BORDER_HOVER}; }}
        """)
        frame.setFixedHeight(44)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(10)

        name = QLabel(net.get('name', ''))
        name.setStyleSheet(f"color: {_TEXT}; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        lay.addWidget(name)

        driver = QLabel(net.get('driver', ''))
        driver.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(driver)

        count = QLabel(f"{net.get('containers', 0)} containers")
        count.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(count)

        lay.addStretch(1)

        rm_btn = QPushButton("Remove")
        rm_btn.setFixedHeight(24)
        rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rm_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,107,107,0.10); color: {_RED};
                border: 1px solid rgba(255,107,107,0.2); border-radius: 8px;
                padding: 0 10px; font-size: 10px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(255,107,107,0.20); }}
        """)
        rm_btn.clicked.connect(lambda checked=False, n=net['name']: self._remove_network(n))
        lay.addWidget(rm_btn)

        return frame

    # ── shared helpers ──────────────────────────────────────────────

    def _section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none; padding-top: 4px;")
        return lbl

    def _remove_container(self, cid):
        reply = QMessageBox.question(
            self, "Remove Container",
            f"Force-remove container {cid[:12]}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_container(cid)

    def _remove_volume(self, name):
        reply = QMessageBox.question(
            self, "Remove Volume",
            f"Remove volume '{name}'?\n\nWarning: Data stored in this volume may be permanently deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_volume(name)

    def _remove_network(self, name):
        reply = QMessageBox.question(
            self, "Remove Network",
            f"Remove network '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_network(name)

    def _context_menu(self, pos, cid):
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        start_act = menu.addAction("Start")
        stop_act = menu.addAction("Stop")
        restart_act = menu.addAction("Restart")
        logs_act = menu.addAction("View Logs")
        shell_act = menu.addAction("Open Shell")
        remove_act = menu.addAction("Remove")
        action = menu.exec(self.mapToGlobal(pos))
        if action == start_act:
            self.manager.start_container(cid)
        elif action == stop_act:
            self.manager.stop_container(cid)
        elif action == restart_act:
            self.manager.restart_container(cid)
        elif action == logs_act:
            self._show_logs(cid)
        elif action == shell_act:
            self.manager.open_container_shell(cid)
        elif action == remove_act:
            self._remove_container(cid)

    # ── run container dialog ────────────────────────────────────────

    def run_container(self, image=None):
        self.manager.show_advanced_run_dialog(prefill_image=image)

    def _show_logs(self, cid):
        dialog = QDialog()
        dialog.setWindowTitle("Container Logs")
        dialog.setMinimumSize(640, 420)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1E1E1E;
                color: #F0F0F0;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {_RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet(f"background: {_SURFACE}; border-radius: {_RADIUS_LG}px {_RADIUS_LG}px 0 0;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 0, 10, 0)
        title = QLabel(f"{cid[:12]} — Logs")
        title.setStyleSheet(
            f"color: {_TEXT}; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;")
        hl.addWidget(title)
        hl.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: none; font-size: 14px; border-radius: 4px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.08); }}
        """)
        close_btn.clicked.connect(dialog.accept)
        hl.addWidget(close_btn)
        layout.addWidget(hdr)

        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E; color: #C9C9C9;
                border: none;
                font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
                padding: 12px;
            }
        """)
        layout.addWidget(log_view, 1)

        logs = self.manager.get_container_logs(cid, tail=300)
        log_view.setPlainText(logs)
        log_view.verticalScrollBar().setValue(log_view.verticalScrollBar().maximum())

        dialog.exec()

    # ── pull image dialog ───────────────────────────────────────────

    def _show_pull_dialog(self):
        dialog = QDialog()
        dialog.setWindowTitle("Pull Image")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(18, 19, 22, 0.98);
                color: {_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {_RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Pull Docker Image")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {_TEXT};"
            "background: transparent; border: none;")
        layout.addWidget(title)

        layout.addWidget(_field_label("Image name"))
        image_input = QLineEdit()
        image_input.setPlaceholderText("nginx:latest")
        image_input.setStyleSheet(_INPUT_QSS)
        layout.addWidget(image_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.04); color: {_TEXT}; }}
        """)
        btn_row.addWidget(cancel_btn)
        pull_btn = QPushButton("Pull")
        pull_btn.setDefault(True)
        pull_btn.setFixedHeight(34)
        pull_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        pull_btn.clicked.connect(lambda: (
            self.manager.pull_image(image_input.text().strip()),
            dialog.accept(),
        ))
        btn_row.addWidget(pull_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    # ── create volume dialog ────────────────────────────────────────

    def _show_create_volume_dialog(self):
        dialog = QDialog()
        dialog.setWindowTitle("Create Volume")
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(18, 19, 22, 0.98);
                color: {_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {_RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Create Docker Volume")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {_TEXT};"
            "background: transparent; border: none;")
        layout.addWidget(title)

        layout.addWidget(_field_label("Volume name"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("my-volume")
        name_input.setStyleSheet(_INPUT_QSS)
        layout.addWidget(name_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.04); color: {_TEXT}; }}
        """)
        btn_row.addWidget(cancel_btn)
        create_btn = QPushButton("Create")
        create_btn.setDefault(True)
        create_btn.setFixedHeight(34)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        create_btn.clicked.connect(lambda: (
            self.manager.create_volume(name_input.text().strip()),
            dialog.accept(),
        ))
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    # ── create network dialog ───────────────────────────────────────

    def _show_create_network_dialog(self):
        dialog = QDialog()
        dialog.setWindowTitle("Create Network")
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(18, 19, 22, 0.98);
                color: {_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {_RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Create Docker Network")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {_TEXT};"
            "background: transparent; border: none;")
        layout.addWidget(title)

        layout.addWidget(_field_label("Network name"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("my-network")
        name_input.setStyleSheet(_INPUT_QSS)
        layout.addWidget(name_input)

        layout.addWidget(_field_label("Driver"))
        driver_combo = QComboBox()
        driver_combo.addItems(["bridge", "overlay", "host", "none"])
        driver_combo.setStyleSheet(_COMBO_QSS)
        layout.addWidget(driver_combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_TEXT2};
                border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.04); color: {_TEXT}; }}
        """)
        btn_row.addWidget(cancel_btn)
        create_btn = QPushButton("Create")
        create_btn.setDefault(True)
        create_btn.setFixedHeight(34)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: #0C0C0E;
                border: none; border-radius: 8px;
                padding: 0 20px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #00D4C1; }}
        """)
        create_btn.clicked.connect(lambda: (
            self._do_create_network(name_input.text().strip(), driver_combo.currentText()),
            dialog.accept(),
        ))
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def _do_create_network(self, name, driver):
        import subprocess as sp
        from threading import Thread as _T
        def task():
            try:
                result = sp.run(
                    ["docker", "network", "create", "--driver", driver, name],
                    check=False, capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0:
                    self.manager.log_signal.emit(f"Created network: {name}")
                    self.manager.show_message.emit("Network Created", f"Created network {name}")
                else:
                    self.manager.log_signal.emit(f"Failed: {(result.stderr or '').strip()}")
            except Exception as e:
                self.manager.log_signal.emit(f"Error: {e}")
            QTimer.singleShot(0, self.refresh)
        _T(target=task, daemon=True).start()
