# === components: plugins_view.py ===
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy, QGraphicsDropShadowEffect
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer
from typing import Any
import os
import shutil

from neoarch.resources.plugin_data import get_plugins_data, get_all_plugins_data
from neoarch.resources.paths import ICONS_DIR, ASSETS_DIR, PLUGINS_ITEMS_DIR
from neoarch.frontend.components.updates_table import UpdatesTable
from neoarch.frontend.components.packages_grid_view import (
    PackageCard, _Chip, _CheckBox, _SmallLabel, _SourceLogo,
    _STATUS_COLORS, _TEXT_MUTED,
)


def _shadow(widget: QWidget, blur=24, offset=(4, 6), alpha=150):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(*offset)
    widget.setGraphicsEffect(s)


class CardState:
    """Encapsulates the state of a plugin card"""
    def __init__(self):
        self.is_installing = False
        self.is_installed_state = False
        self.matching_plugin = None
    
    def set_installing(self, installing):
        """Set the installing state"""
        self.is_installing = installing
    
    def get_installing(self):
        """Get the installing state"""
        return self.is_installing
    
    def set_installed_state(self, installed):
        """Set the installed state"""
        self.is_installed_state = installed
    
    def get_installed_state(self):
        """Get the installed state"""
        return self.is_installed_state
    
    def set_matching_plugin(self, plugin):
        """Set the matching plugin reference"""
        self.matching_plugin = plugin
    
    def get_matching_plugin(self):
        """Get the matching plugin reference"""
        return self.matching_plugin


def _canonical_source(source):
    """Normalize a package source to the canonical names used by the
    updates table / source logo assets (pacman, AUR, Flatpak, npm)."""
    return {
        "pacman": "pacman",
        "aur": "AUR",
        "flatpak": "Flatpak",
        "npm": "npm",
        "brew": "brew",
    }.get((source or "").lower(), source or "pacman")


_NEU_BTN_QSS = """
QPushButton {
    background-color: rgba(26, 28, 34, 0.95);
    color: #00BFAE;
    border: 1px solid rgba(0, 191, 174, 0.3);
    border-radius: 8px;
    font-weight: 700;
    font-size: 11px;
    padding: 0 14px;
}
QPushButton:hover {
    background-color: rgba(30, 32, 38, 0.95);
    border: 1px solid rgba(0, 191, 174, 0.6);
}
QPushButton:pressed {
    background-color: rgba(20, 22, 26, 0.95);
    border: 1px solid rgba(0, 191, 174, 0.8);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
"""

_DANGER_BTN_QSS = """
QPushButton {
    background-color: rgba(26, 28, 34, 0.95);
    color: #FF6B6B;
    border: 1px solid rgba(255, 107, 107, 0.3);
    border-radius: 8px;
    font-weight: 700;
    font-size: 11px;
    padding: 0 14px;
}
QPushButton:hover {
    background-color: rgba(30, 32, 38, 0.95);
    border: 1px solid rgba(255, 107, 107, 0.6);
}
QPushButton:pressed {
    background-color: rgba(20, 22, 26, 0.95);
    border: 1px solid rgba(255, 107, 107, 0.8);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
"""


class _PluginPackageCard(PackageCard):
    """Plugin card reusing the Updates/Discover PackageCard design language
    (glass surface, source logo, status chip) with plugin action buttons."""

    install_clicked = pyqtSignal(str)
    launch_clicked = pyqtSignal(str)
    uninstall_clicked = pyqtSignal(str)

    CARD_W = 280
    CARD_H = 150

    def __init__(self, plugin, installed, app=None, parent=None):
        self._plugin = plugin
        self._installed = bool(installed)
        super().__init__(plugin, 0, app, parent)

    def _build(self):
        source = _canonical_source(PluginsView._get_package_source(self._plugin))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 9)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(9)

        self.logo = _SourceLogo(self._app, source, 26)
        top.addWidget(self.logo)

        name = self._plugin.get("name") or self._plugin.get("id") or ""
        self.name_label = _SmallLabel(name, 11, QFont.Weight.Bold, "#EEF0F4")
        self.name_label.setToolTip(name)
        top.addWidget(self.name_label, 1)

        self.checkbox = _CheckBox()
        self.checkbox.toggled.connect(self._on_check)
        top.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top)

        desc = self._plugin.get("desc") or ""
        self.desc_label = _SmallLabel(desc, 8, QFont.Weight.Normal, "#8B8D97")
        self.desc_label.setToolTip(desc)
        layout.addWidget(self.desc_label)

        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        status = "Installed" if self._installed else "Available"
        self.status_chip = _Chip(status, _STATUS_COLORS.get(status, _TEXT_MUTED))
        bottom.addWidget(self.status_chip, alignment=Qt.AlignmentFlag.AlignBottom)

        bottom.addStretch(1)

        self._action_buttons = []
        pid = self._plugin.get("id")
        if self._installed:
            open_btn = self._make_action_button("Open", _NEU_BTN_QSS)
            open_btn.clicked.connect(lambda: self.launch_clicked.emit(pid))
            bottom.addWidget(open_btn)
            self._action_buttons.append(open_btn)

            uninstall_btn = self._make_action_button("Uninstall", _DANGER_BTN_QSS)
            uninstall_btn.clicked.connect(lambda: self.uninstall_clicked.emit(pid))
            bottom.addWidget(uninstall_btn)
            self._action_buttons.append(uninstall_btn)
        else:
            install_btn = self._make_action_button("Install", _NEU_BTN_QSS)
            install_btn.clicked.connect(lambda: self.install_clicked.emit(pid))
            bottom.addWidget(install_btn)
            self._action_buttons.append(install_btn)

        layout.addLayout(bottom)

    @staticmethod
    def _make_action_button(text, qss):
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(qss)
        return btn

    def set_installing(self, installing):
        for b in self._action_buttons:
            b.setEnabled(not installing)
            if installing:
                if b.text() in ("Install", "Open"):
                    b.setText("Installing\u2026")
                elif b.text() == "Uninstall":
                    b.setText("Uninstalling\u2026")
            else:
                if "Installing" in b.text():
                    b.setText("Install" if not self._installed else "Open")
                elif "Uninstalling" in b.text():
                    b.setText("Uninstall")


class ElideLabel(QLabel):
    def __init__(self, text="", parent=None, max_lines=2):
        super().__init__(text, parent)
        self._full_text = text or ""
        self._max_lines = max(1, int(max_lines))
        try:
            self.setWordWrap(True)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        except Exception:
            pass

    def set_max_lines(self, n):
        try:
            self._max_lines = max(1, int(n))
        except Exception:
            self._max_lines = 1
        self._apply_elide()

    def setText(self, text):
        self._full_text = text or ""
        self._apply_elide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_elide()

    def _apply_elide(self):
        try:
            fm = self.fontMetrics()
            width = max(0, self.width())
            if width <= 0:
                QLabel.setText(self, self._full_text)
                return
            if self._max_lines <= 1:
                el = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, width)
                QLabel.setText(self, el)
                return
            words = (self._full_text or "").split()
            lines = []
            current = ""
            i = 0
            while i < len(words):
                w = words[i]
                trial = (current + " " + w).strip()
                if fm.horizontalAdvance(trial) <= width:
                    current = trial
                    i += 1
                else:
                    if current:
                        lines.append(current)
                    else:
                        lines.append(fm.elidedText(w, Qt.TextElideMode.ElideRight, width))
                        i += 1
                    current = ""
                if len(lines) == self._max_lines - 1:
                    remaining = " ".join(words[i:])
                    last = (current + (" " if current and remaining else "") + remaining).strip()
                    el = fm.elidedText(last, Qt.TextElideMode.ElideRight, width)
                    lines.append(el)
                    current = ""
                    break
            if current and len(lines) < self._max_lines:
                lines.append(current)
            QLabel.setText(self, "\n".join(lines[: self._max_lines]))
        except Exception:
            try:
                QLabel.setText(self, self._full_text)
            except Exception:
                pass

GENERIC_PLUGIN_ICON = "\U0001f9e9"

_PLUGIN_APP_ICON = None

def _get_plugin_app_icon(size=32):
    global _PLUGIN_APP_ICON
    if _PLUGIN_APP_ICON is None:
        _PLUGIN_APP_ICON = {}
    if size not in _PLUGIN_APP_ICON:
        path = str(ASSETS_DIR / "plugins" / "app.svg")
        try:
            renderer = QSvgRenderer(path)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            _PLUGIN_APP_ICON[size] = pixmap
        except Exception:
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            _PLUGIN_APP_ICON[size] = pixmap
    return _PLUGIN_APP_ICON[size]

class PluginCard(QFrame):
    def __init__(self, spec: dict, icon: QIcon, installed: bool, on_install, on_open, on_uninstall, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.on_install = on_install
        self.on_open = on_open
        self.on_uninstall = on_uninstall
        self.setObjectName("pluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(88)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(self._style())
        _shadow(self, blur=18, offset=(3, 4), alpha=140)

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(_get_plugin_app_icon(36))
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        title_text = spec.get('name') or spec.get('id') or "Unknown"
        title = ElideLabel(title_text, self, max_lines=1)
        title.setObjectName("pluginTitle")
        try:
            title.setToolTip(title_text)
        except Exception:
            pass
        desc_text = spec.get('desc', "")
        desc = ElideLabel(desc_text, self, max_lines=1)
        desc.setObjectName("pluginDesc")
        try:
            desc.setToolTip(desc_text)
        except Exception:
            pass
        text_col.addWidget(title)
        text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.status_label = QLabel()
        self.status_label.setObjectName("pluginStatus")
        layout.addWidget(self.status_label)

        self.action_btn = QPushButton()
        self.action_btn.setFixedHeight(30)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.action_btn)

        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setFixedHeight(28)
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_btn.setVisible(False)
        layout.addWidget(self.uninstall_btn)

        self.update_state(installed)

    def update_state(self, installed: bool):
        self.status_label.setText("Installed" if installed else "")
        if installed:
            self.action_btn.setText("Open")
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(42, 44, 50, 0.9),
                        stop:1 rgba(30, 32, 38, 0.9));
                    color: #EDEDEF;
                    border-top: 1px solid rgba(255, 255, 255, 0.08);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.25);
                    border-left: 1px solid rgba(255, 255, 255, 0.04);
                    border-right: 1px solid rgba(0, 0, 0, 0.15);
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 5px 16px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(52, 54, 60, 0.95),
                        stop:1 rgba(38, 40, 46, 0.95));
                    border-top: 1px solid rgba(255, 255, 255, 0.12);
                }
                QPushButton:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(26, 28, 34, 0.95),
                        stop:1 rgba(36, 38, 44, 0.95));
                    border-top: 1px solid rgba(0, 0, 0, 0.2);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                }
            """)
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_open(self.spec))
            self.uninstall_btn.setVisible(True)
            self.uninstall_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8B8D97;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 10px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(229, 57, 53, 0.08);
                    border-color: #E53935;
                    color: #E53935;
                }
                QPushButton:pressed {
                    background-color: rgba(229, 57, 53, 0.15);
                }
            """)
            self.uninstall_btn.clicked.disconnect() if self.uninstall_btn.receivers(self.uninstall_btn.clicked) else None
            self.uninstall_btn.clicked.connect(lambda: self.on_uninstall(self.spec))
        else:
            self.action_btn.setText("Install")
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 207, 188, 0.9),
                        stop:1 rgba(0, 175, 160, 0.9));
                    color: #0C0C0E;
                    border-top: 1px solid rgba(255, 255, 255, 0.15);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.25);
                    border-left: 1px solid rgba(255, 255, 255, 0.08);
                    border-right: 1px solid rgba(0, 0, 0, 0.15);
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 5px 16px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 220, 200, 0.95),
                        stop:1 rgba(0, 190, 174, 0.95));
                }
                QPushButton:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 155, 140, 0.95),
                        stop:1 rgba(0, 175, 160, 0.95));
                    border-top: 1px solid rgba(0, 0, 0, 0.2);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                }
            """)
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_install(self.spec))
            self.uninstall_btn.setVisible(False)

    def set_installing(self, installing: bool):
        try:
            if installing:
                self.action_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)
                self.action_btn.setText("Installing\u2026")
                self.status_label.setText("Installing\u2026")
            else:
                self.action_btn.setEnabled(True)
                self.uninstall_btn.setEnabled(True)
                self.update_state(self.status_label.text().lower().startswith("installed"))
        except Exception:
            pass

    def _style(self):
        return """
        QFrame#pluginCard {
            background-color: rgba(22, 23, 26, 0.85);
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 14px;
            margin: 4px 0;
        }
        QFrame#pluginCard:hover {
            border-top: 1px solid rgba(255, 255, 255, 0.10);
            border-bottom: 1px solid rgba(0, 0, 0, 0.35);
            background-color: rgba(26, 28, 32, 0.85);
        }
        QLabel#pluginTitle {
            color: #EDEDEF;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#pluginDesc {
            color: #8B8D97;
            font-size: 11px;
        }
        QLabel#pluginStatus {
            color: #00BFAE;
            font-size: 10px;
            font-weight: 600;
            padding: 0 6px;
        }
        """


class PluginsView(QWidget):
    install_requested = pyqtSignal(str)   # plugin id
    launch_requested = pyqtSignal(str)    # plugin id
    uninstall_requested = pyqtSignal(str) # plugin id
    live_search_ready = pyqtSignal(list)  # live search specs (main thread)

    def __init__(self, main_app, get_icon_callback, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.get_icon_callback = get_icon_callback
        self._filter_text = ""
        self._installed_only = False
        self._categories = set()
        self._current_cols = 2  # Track current column count
        self._all_cards = []  # Store all created cards for performance
        self._current_filter_states = {}  # Track current filter states
        self._current_source_states = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}  # Track source states
        self._all_filtered_cards = None
        self._all_filtered_search_cards = None
        self._sort_mode = "name_asc"
        
        self._all_plugins = []  # All available plugins
        self._card_cache = {}
        self._is_layouting = False
        
        # Installation status cache — preserved across navigation, cleared only after install/uninstall
        self._installed_cache = {}
        
        # Debounce timer for resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize)
        
        self.grid_layout: Any = None
        self._scroll_area: Any = None
        
        self._init_specs()
        self._init_ui()
        self.live_search_ready.connect(self._on_live_search_ready)

    def _init_specs(self):
        """Initialize plugin specifications from external data file"""
        self.plugins = get_plugins_data()

    def _init_ui(self):
        self._list_mode = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Content stacked area
        self._content_stack = QFrame()
        self._content_stack.setObjectName("pluginContentStack")
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Apps Grid
        self.create_apps_grid(content_layout)

        # Apps Table (list view) — same redesigned table as Updates/Discover
        self._plugins_table = UpdatesTable(self.main_app)
        self._plugins_table.set_plugins_mode(True)
        self._plugins_table.setVisible(False)
        self._plugins_table.menu_action.connect(self._on_table_menu_action)
        self._plugins_table.set_empty_text("No plugins found", "Try a different search or filter")
        content_layout.addWidget(self._plugins_table, 1)

        layout.addWidget(self._content_stack, 1)

    def show_grid_mode(self):
        self._list_mode = False
        self._scroll_area.setVisible(True)
        self._plugins_table.setVisible(False)
        QTimer.singleShot(0, self._render_grid_after_show)

    def _render_grid_after_show(self):
        try:
            self._scroll_area.verticalScrollBar().setValue(0)
        except Exception:
            pass
        self._calc_grid_metrics()
        self._render_current_page()

    def show_table_mode(self):
        self._list_mode = True
        self._scroll_area.setVisible(False)
        self._plugins_table.setVisible(True)
        self._populate_table()

    @staticmethod
    def _map_plugin_row(plugin):
        """Map a plugin spec to the shared updates-table contract."""
        name = plugin.get('name') or plugin.get('id', '')
        return {
            'name': name,
            'id': plugin.get('id') or name,
            'version': plugin.get('version', plugin.get('ver', '')),
            'new_version': plugin.get('version', plugin.get('ver', '')),
            'source': _canonical_source(PluginsView._get_package_source(plugin)),
            'description': plugin.get('desc') or '',
            'download_size': '',
            'installed_date': 0,
            'status': 'Installed' if plugin.get('_installed') else 'Available',
            '_installed': bool(plugin.get('_installed')),
            '_src': plugin,
        }

    def _populate_table(self):
        self._plugins_table.set_loading(True, "Loading plugins\u2026")
        filtered = self._get_filtered_plugins()
        rows = []
        for card_data in filtered:
            plugin = dict(card_data['plugin'])
            plugin['_installed'] = bool(card_data.get('installed', self.is_installed(plugin)))
            rows.append(self._map_plugin_row(plugin))
        self._plugins_table.set_packages(rows)
        self._plugins_table.model.clear_sort()
        self._plugins_table.set_empty_text("No plugins found", "Try a different search or filter")

    def _refresh_content(self):
        if self._list_mode and self._plugins_table.isVisible():
            self._populate_table()
        else:
            self._render_current_page()

    def _on_table_menu_action(self, action, pkg):
        """Route plugin table menu actions to the view's signals."""
        plugin = pkg.get('_src') if isinstance(pkg, dict) else None
        if plugin is None:
            return
        pid = plugin.get('id')
        if action == "launch":
            self.launch_requested.emit(pid)
        elif action == "install":
            self.install_requested.emit(pid)
        elif action == "uninstall":
            self.uninstall_requested.emit(pid)
        elif action == "browser":
            main_app = getattr(self, 'main_app', None)
            if main_app is not None and hasattr(main_app, '_open_package_page'):
                try:
                    main_app._open_package_page(pkg)
                except Exception:
                    pass
        elif action == "copy":
            name = (plugin.get('name') or plugin.get('id') or '').strip()
            if name:
                try:
                    from PyQt6.QtWidgets import QApplication
                    QApplication.clipboard().setText(name)
                except Exception:
                    pass


    def _get_or_create_card(self, plugin_spec):
        """Return cached card data for a plugin or create it."""
        try:
            pid = plugin_spec.get('id')
        except Exception:
            pid = None
        if pid and pid in getattr(self, '_card_cache', {}):
            return self._card_cache[pid]
        installed = self.is_installed(plugin_spec)
        card = self.create_app_card(plugin_spec, None, installed)
        data = {
            'plugin': plugin_spec,
            'widget': card,
            'installed': installed
        }
        try:
            if pid:
                self._card_cache[pid] = data
        except Exception:
            pass
        return data

    def _clear_grid_and_hide_all(self):
        """Clear all items from grid layout and hide orphaned widgets"""
        if not hasattr(self, 'grid_layout'):
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().hide()
        self._reset_row_stretches()


    @staticmethod
    def _get_scrollbar_stylesheet():
        """Scrollbar styling matching the Updates/Discover card grid."""
        return """
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
            QScrollBar:horizontal {
                background: rgba(255,255,255,0.03);
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255,255,255,0.15);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """

    def create_apps_grid(self, parent_layout):
        """Create the apps grid section"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.verticalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.horizontalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.setStyleSheet(self._get_scrollbar_stylesheet())
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        
        grid_container = QWidget()
        grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        self._live_search_label = QLabel("")
        self._live_search_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_search_label.setStyleSheet(
            "color: #8B8D97; font-size: 13px; border: none; padding: 24px;")
        self._live_search_label.hide()
        scroll_layout.addWidget(self._live_search_label)
        
        scroll_layout.addWidget(grid_container)
        scroll.setWidget(scroll_widget)
        self._scroll_area = scroll
        parent_layout.addWidget(scroll, 1)

    def populate_app_cards(self):
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
            self._prewarm_installed_cache()
        self._calc_grid_metrics()
    
    def _create_all_cards(self):
        """Create all plugin cards once for better performance"""
        self._all_cards = []
        plugins = self._all_plugins or self.plugins
        for plugin in plugins:
            pid = plugin.get('id')
            if pid and pid in self._card_cache:
                card_data = self._card_cache[pid]
            else:
                installed = self.is_installed(plugin)
                card = self.create_app_card(plugin, None, installed)
                card_data = {
                    'plugin': plugin,
                    'widget': card,
                    'installed': installed
                }
                if pid:
                    self._card_cache[pid] = card_data
            self._all_cards.append(card_data)

    @staticmethod
    def _get_package_source(plugin_spec):
        """Determine package source from plugin spec"""
        pkg = plugin_spec.get('pkg', '').lower()
        if pkg.startswith('npm-') or 'npm' in pkg:
            return 'npm'
        elif pkg.startswith('aur/') or 'aur' in pkg:
            return 'aur'
        elif pkg.endswith('.flatpak') or 'flatpak' in pkg:
            return 'flatpak'
        elif pkg.startswith('brew-') or 'brew' in pkg:
            return 'brew'
        else:
            return 'pacman'
    
    def _render_source_icon(self, source, size=14):
        """Render a source SVG icon to a QPixmap"""
        path = self._get_source_icon(source)
        try:
            renderer = QSvgRenderer(path)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return pixmap
        except Exception:
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            return pixmap

    def _source_badge(self, source):
        """Create a source badge widget with icon and label"""
        colors = {
            'pacman': '#4FC3F7',
            'aur': '#FF8A65',
            'flatpak': '#26A69A',
            'npm': '#E53935',
            'brew': '#8B5CF6',
        }
        color = colors.get(source, '#8B8D97')

        badge = QWidget()
        badge.setObjectName("sourceBadge")
        badge.setStyleSheet(f"""
            QWidget#sourceBadge {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
            }}
        """)
        layout = QHBoxLayout(badge)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        icon_pixmap = self._render_source_icon(source, 12)
        if not icon_pixmap.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(icon_pixmap)
            icon_label.setFixedSize(12, 12)
            icon_label.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(icon_label)

        text = QLabel(source)
        text.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 9px;
                font-weight: 600;
                border: none;
                background: transparent;
            }}
        """)
        layout.addWidget(text)
        return badge

    @staticmethod
    def _get_source_icon(source):
        """Get icon path for package source"""
        base_path = os.path.join(str(ICONS_DIR), "discover")
        icons = {
            'pacman': os.path.join(base_path, 'pacman.svg'),
            'aur': os.path.join(base_path, 'aur.svg'),
            'flatpak': os.path.join(base_path, 'flatpack.svg'),
            'npm': os.path.join(base_path, 'node.svg'),
            'brew': os.path.join(base_path, 'pacman.svg'),
            'pip': os.path.join(base_path, 'pacman.svg')
        }
        return icons.get(source, os.path.join(base_path, 'pacman.svg'))

    # --- Layout helpers to keep calculations consistent ---
    def _layout_spacing(self):
        try:
            return self.grid_layout.spacing() if self.grid_layout else 14
        except Exception:
            return 14

    def _calc_cols(self, viewport_width):
        spacing = self._layout_spacing()
        min_w = 210
        cols = 3
        while cols > 1 and viewport_width < cols * min_w + (cols - 1) * spacing:
            cols -= 1
        return cols

    def _enforce_row_min_heights(self, upto_row):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            for r in range(0, max(0, int(upto_row)) + 1):
                self.grid_layout.setRowMinimumHeight(r, 150)
        except Exception:
            pass

    def _calc_grid_metrics(self):
        try:
            viewport_w = self._scroll_area.viewport().width() if self._scroll_area else self.width()
        except Exception:
            viewport_w = self.width()
        if viewport_w < 200:
            viewport_w = 900
        spacing = self._layout_spacing()
        cols = self._calc_cols(viewport_w)
        self._current_cols = cols
        avail = max(1, viewport_w - (cols - 1) * spacing)
        self._card_width = max(210, avail // cols)

    def _get_current_plugins(self):
        return self._all_plugins

    def _get_filtered_plugins(self):
        has_search = hasattr(self, '_all_filtered_search_cards') and self._all_filtered_search_cards is not None
        has_combined = (bool(getattr(self, '_current_filter_states', None))
                        or getattr(self, '_all_filtered_cards', None) is not None)
        if has_search and has_combined and hasattr(self, '_all_filtered_cards'):
            search_ids = {c['plugin'].get('id') for c in self._all_filtered_search_cards}
            combined_ids = {c['plugin'].get('id') for c in self._all_filtered_cards}
            intersection = search_ids & combined_ids
            return [c for c in self._all_filtered_search_cards if c['plugin'].get('id') in intersection]
        if has_search:
            return self._all_filtered_search_cards
        if has_combined and hasattr(self, '_all_filtered_cards'):
            return self._all_filtered_cards
        plugins = self._get_current_plugins()
        return [self._get_or_create_card(p) for p in plugins]

    def _render_current_page(self):
        filtered = self._get_filtered_plugins()
        try:
            if filtered:
                self._live_search_label.hide()
        except Exception:
            pass
        if not filtered:
            self._clear_grid_and_hide_all()
            self._reset_row_stretches()
            return
        self._calc_grid_metrics()
        cols = self._current_cols
        card_w = self._card_width
        self._begin_layout_update()
        self._clear_grid_and_hide_all()
        self._reset_row_stretches()
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        for i, card_data in enumerate(filtered):
            card_data['widget'].setFixedWidth(card_w)
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        max_row = (len(filtered) - 1) // cols
        self._enforce_row_min_heights(max_row)
        self._finish_layout_update()

    def _begin_layout_update(self):
        if self._is_layouting:
            return False
        self._is_layouting = True
        try:
            self.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.setUpdatesEnabled(False)
                self._scroll_area.viewport().setUpdatesEnabled(False)
        except Exception:
            pass
        return True

    def _finish_layout_update(self):
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.viewport().setUpdatesEnabled(True)
                self._scroll_area.setUpdatesEnabled(True)
                self._scroll_area.viewport().update()
        except Exception:
            pass
        try:
            self.setUpdatesEnabled(True)
        except Exception:
            pass
        self._is_layouting = False

    def create_app_card(self, plugin_spec, icon, installed):
        """Create a plugin card in the shared Updates/Discover card style
        (glass surface, source logo, status chip) with action buttons."""
        card = _PluginPackageCard(plugin_spec, installed, self.main_app)
        pid = plugin_spec.get('id')

        card.install_clicked.connect(
            lambda: (card.set_installing(True), self.install_requested.emit(pid)))
        card.launch_clicked.connect(lambda: self.launch_requested.emit(pid))
        card.uninstall_clicked.connect(
            lambda: (card.set_installing(True), self.uninstall_requested.emit(pid)))
        return card



    def _prewarm_installed_cache(self):
        """Batch-check installed packages with a single pacman -Qq call (short timeout)"""
        try:
            from neoarch.resources.plugin_data import get_all_plugins_data
            plugins = get_all_plugins_data()
            import subprocess
            r = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, timeout=5)
            if r.returncode != 0 or not r.stdout:
                return
            installed = set(l.strip() for l in r.stdout.strip().split('\n') if l.strip())
            for p in plugins:
                pid = p.get('id')
                pkg = p.get('pkg', '')
                if not pid or pid in self._installed_cache:
                    continue
                plain = pkg.replace('aur/', '').replace('.flatpak', '').replace('.Flatpak', '')
                if plain:
                    self._installed_cache[pid] = plain in installed
        except Exception:
            pass

    def is_installed(self, spec):
        pid = spec.get('id')
        if pid in self._installed_cache:
            return self._installed_cache[pid]
        cmd = spec.get('cmd')
        pkg = spec.get('pkg')
        result = False
        try:
            if cmd and shutil.which(cmd):
                result = True
            else:
                import subprocess
                r = subprocess.run(["pacman", "-Qi", pkg], capture_output=True, text=True, timeout=5)
                result = r.returncode == 0
        except Exception:
            result = False
        if pid:
            self._installed_cache[pid] = result
        return result

    def clear_installed_cache(self):
        self._installed_cache.clear()

    def refresh_all(self, force=False):
        """Refresh all plugin cards to reflect current installation state

        Args:
            force: If True, clears all caches (for post-install/uninstall refresh).
                   If False, preserves caches (for navigation) — much faster.
        """
        if force:
            self.clear_installed_cache()
            self._card_cache.clear()
            self._all_cards = []
            self._all_filtered_search_cards = None
            self._all_filtered_cards = None
        self.populate_app_cards()
        # Always apply filters so there's exactly one render
        if not self._current_filter_states:
            self._current_filter_states = {"Available": True, "Installed": True}
        self._apply_combined_filters()

    def get_plugin(self, plugin_id):
        for spec in self.plugins:
            if spec['id'] == plugin_id:
                return spec
        return None

    def set_filter(self, text: str, installed_only: bool, categories=None):
        self._filter_text = (text or "").strip().lower()
        self._installed_only = bool(installed_only)
        self._categories = set((categories or []))
        self.apply_filter()

    def apply_filter(self):
        """Apply text, installed, and category filters to the plugins view"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        has_search = bool(self._filter_text) or self._installed_only or self._categories
        
        # Filter and display cards based on search text, installed status, and categories
        filtered = []
        for card_data in self._all_cards:
            if not has_search:
                break
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check installed filter
            if self._installed_only and not is_installed:
                continue
            
            # Check category filter
            if self._categories:
                plugin_category = plugin.get('category', '')
                if plugin_category not in self._categories:
                    continue
            
            # Check search text filter
            if self._filter_text:
                name = (plugin.get('name', '') or '').lower()
                desc = (plugin.get('desc', '') or '').lower()
                plugin_id = (plugin.get('id', '') or '').lower()
                
                # Match if search text is in name, description, or id
                if not (self._filter_text in name or self._filter_text in desc or self._filter_text in plugin_id):
                    continue
            
            filtered.append(card_data)
        
        self._all_filtered_search_cards = self._sort_cards(filtered) if has_search else None
        
        # Live search fallback: text query with no curated matches -> query pacman/AUR
        if self._filter_text and not self._installed_only and not self._categories and not filtered:
            self._run_live_search(self._filter_text)

        self._refresh_content()

    def _run_live_search(self, query):
        """Query pacman + AUR live when the curated catalog has no matches."""
        try:
            from threading import Thread
            def _search():
                specs = []
                try:
                    from neoarch.backend.services.search import search_live_packages
                    specs = search_live_packages(query)
                except Exception:
                    specs = []
                self.live_search_ready.emit([query, specs])
            self._pending_live_query = query
            try:
                self._live_search_label.setText("Searching official repos and AUR...")
                self._live_search_label.show()
            except Exception:
                pass
            Thread(target=_search, daemon=True).start()
        except Exception:
            pass

    def _on_live_search_ready(self, payload):
        """Handle live search results on the main thread (widgets require it)."""
        try:
            query, specs = payload
            if getattr(self, '_pending_live_query', None) != query:
                return
            self._pending_live_query = None
            if not specs:
                try:
                    self._live_search_label.setText("No packages found. Try a different search.")
                except Exception:
                    pass
                return
            card_datas = []
            for spec in specs:
                spec = dict(spec)
                spec['icon'] = os.path.join(PLUGINS_ITEMS_DIR, 'default.png')
                existing = self.get_plugin(spec['id'])
                if existing:
                    spec = existing
                installed = self.is_installed(spec)
                card = self.create_app_card(spec, None, installed)
                card_datas.append({
                    'plugin': spec,
                    'installed': installed,
                    'widget': card,
                })
            self._all_filtered_search_cards = card_datas
            try:
                self._live_search_label.hide()
            except Exception:
                pass
            self._refresh_content()
        except Exception:
            pass

    def set_installing(self, plugin_id: str, installing: bool):
        """Update installing state for a plugin card"""
        try:
            # Find the card with this plugin_id
            for card_data in self._all_cards:
                if card_data['plugin'].get('id') == plugin_id:
                    card = card_data['widget']
                    if hasattr(card, 'set_installing'):
                        card.set_installing(installing)
                    break
        except Exception:
            pass
    
    
    def _reset_row_stretches(self):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            rc = max(0, self.grid_layout.rowCount())
            for r in range(rc + 4):
                self.grid_layout.setRowStretch(r, 0)
                self.grid_layout.setRowMinimumHeight(r, 0)
        except Exception:
            pass
    
    def resizeEvent(self, event):
        """Handle window resize to update grid layout"""
        super().resizeEvent(event)
        # Debounce resize events to prevent performance issues
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
            self._resize_timer.start(150)  # Wait 150ms after resize stops
    
    def _handle_resize(self):
        if not hasattr(self, 'grid_layout') or not self.plugins:
            return
        if not self._list_mode:
            old_cols = self._current_cols
            self._calc_grid_metrics()
            if self._current_cols != old_cols:
                self._render_current_page()
    
    def _update_grid_layout(self):
        self._refresh_content()
    
    def apply_filters(self, filter_states):
        """Apply Available/Installed filters to the plugins view"""
        # Store current filter states
        self._current_filter_states = filter_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()
    
    def apply_source_filters(self, source_states):
        """Apply source filters (pacman, AUR, Flatpak, npm) to the plugins view"""
        # Store current source states
        self._current_source_states = source_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()

    def set_sort(self, mode):
        """Set the sort order for the plugins list/grid."""
        self._sort_mode = mode or "name_asc"
        self._apply_combined_filters()

    def _sort_cards(self, cards):
        mode = self._sort_mode
        try:
            if mode == "name_desc":
                return sorted(cards, key=lambda c: (c['plugin'].get('name') or c['plugin'].get('id') or '').lower(), reverse=True)
            if mode == "category":
                return sorted(cards, key=lambda c: ((c['plugin'].get('category') or '').lower(), (c['plugin'].get('name') or c['plugin'].get('id') or '').lower()))
            if mode == "source":
                return sorted(cards, key=lambda c: (self._get_package_source(c['plugin']), (c['plugin'].get('name') or c['plugin'].get('id') or '').lower()))
            if mode == "installed":
                return sorted(cards, key=lambda c: (not c['installed'], (c['plugin'].get('name') or c['plugin'].get('id') or '').lower()))
            return sorted(cards, key=lambda c: (c['plugin'].get('name') or c['plugin'].get('id') or '').lower())
        except Exception:
            return cards
    
    def _apply_combined_filters(self):
        """Apply both status and source filters together"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        # Get filter states
        show_available = self._current_filter_states.get('Available', True)
        show_installed = self._current_filter_states.get('Installed', True)
        
        # Get source states
        show_pacman = self._current_source_states.get('pacman', True)
        show_aur = self._current_source_states.get('AUR', True)
        show_flatpak = self._current_source_states.get('Flatpak', True)
        show_npm = self._current_source_states.get('npm', True)
        
        # Filter cards based on both status and source
        filtered_cards = []
        for card_data in self._all_cards:
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check status filter
            status_match = (is_installed and show_installed) or (not is_installed and show_available)
            
            # Check source filter
            source = self._get_package_source(plugin).lower()
            source_match = False
            if source == 'pacman' and show_pacman:
                source_match = True
            elif source == 'aur' and show_aur:
                source_match = True
            elif source == 'flatpak' and show_flatpak:
                source_match = True
            elif source == 'npm' and show_npm:
                source_match = True
            
            # Include card only if both filters match
            if status_match and source_match:
                filtered_cards.append(card_data)
        
        self._all_filtered_cards = self._sort_cards(filtered_cards)
        
        self._refresh_content()
