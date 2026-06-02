# === components: plugins_view.py ===
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QGraphicsDropShadowEffect
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from typing import Any
import os
import shutil

from neoarch.resources.plugin_data import get_plugins_data, get_all_plugins_data
from neoarch.resources.paths import ICONS_DIR, ASSETS_DIR


def _shadow(widget: QWidget, blur=24, offset=(4, 6), alpha=150):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(*offset)
    widget.setGraphicsEffect(s)


_SOURCE_GRADIENTS = {
    'pacman': ('#4FC3F7', '#2196F3'),
    'aur': ('#FF8A65', '#FF5722'),
    'flatpak': ('#26A69A', '#00897B'),
    'npm': ('#E53935', '#C62828'),
    'brew': ('#8B5CF6', '#6D28D9'),
    'pip': ('#4FC3F7', '#2196F3'),
}


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

    def __init__(self, main_app, get_icon_callback, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.get_icon_callback = get_icon_callback
        self._filter_text = ""
        self._installed_only = False
        self._categories = set()
        self._selected_category = None  # Track selected category
        self._current_cols = 2  # Track current column count
        self._all_cards = []  # Store all created cards for performance
        self._current_filter_states = {}  # Track current filter states
        self._current_source_states = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}  # Track source states
        self._all_filtered_cards = None
        self._all_filtered_search_cards = None
        
        # Pagination
        self._all_plugins = []  # All available plugins
        self._current_page = 1
        self._total_pages = 1
        self._items_per_page = 24
        self._card_cache = {}
        self._category_filtered_plugins = []
        self._is_layouting = False
        
        # Installation status cache — preserved across navigation, cleared only after install/uninstall
        self._installed_cache = {}
        
        # Debounce timer for resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize)
        
        self.grid_layout: Any = None
        self._pagination_bar: Any = None
        self._scroll_area: Any = None
        
        self._init_specs()
        self._init_ui()

    def _init_specs(self):
        """Initialize plugin specifications from external data file"""
        self.plugins = get_plugins_data()

    def _init_ui(self):
        self._list_mode = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Filter Buttons Row
        self.create_filter_buttons(layout)
        
        # Content stacked area
        self._content_stack = QFrame()
        self._content_stack.setObjectName("pluginContentStack")
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Apps Grid
        self.create_apps_grid(content_layout)

        # Apps Table (for list view)
        self._create_apps_table(content_layout)

        layout.addWidget(self._content_stack, 1)

        self._pagination_bar = self._create_pagination_bar()
        layout.addWidget(self._pagination_bar)

    def _create_apps_table(self, parent_layout):
        self._table_widget = QTableWidget()
        self._table_widget.setColumnCount(5)
        self._table_widget.setHorizontalHeaderLabels(["", "Plugin Name", "Version", "Source", "Status"])
        header = self._table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self._table_widget.setColumnWidth(0, 48)
        self._table_widget.setColumnWidth(2, 140)
        self._table_widget.setColumnWidth(3, 120)
        self._table_widget.setColumnWidth(4, 120)
        self._table_widget.verticalHeader().setVisible(False)
        self._table_widget.setAlternatingRowColors(True)
        self._table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_widget.setShowGrid(False)
        self._table_widget.verticalHeader().setDefaultSectionSize(48)
        self._table_widget.setStyleSheet("""
            QTableWidget {
                background-color: rgba(22, 23, 26, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
                gridline-color: rgba(255, 255, 255, 0.03);
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                color: #EDEDEF;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTableWidget::item:selected {
                background-color: rgba(0, 191, 174, 0.12);
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: rgba(14, 14, 16, 0.9);
                color: #8B8D97;
                font-weight: 600;
                font-size: 11px;
                padding: 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                text-transform: uppercase;
            }
        """)
        self._table_widget.setVisible(False)
        parent_layout.addWidget(self._table_widget, 1)

    def show_grid_mode(self):
        self._list_mode = False
        self._scroll_area.setVisible(True)
        self._table_widget.setVisible(False)
        self._render_current_page()

    def show_table_mode(self):
        self._list_mode = True
        self._scroll_area.setVisible(False)
        self._populate_table()
        self._table_widget.setVisible(True)

    def _populate_table(self):
        filtered = self._get_filtered_plugins()
        plugins = [c['plugin'] for c in filtered]
        start = (self._current_page - 1) * self._items_per_page
        end = min(start + self._items_per_page, len(plugins))
        page_plugins = plugins[start:end]

        self._table_widget.setUpdatesEnabled(False)
        self._table_widget.setRowCount(0)
        for plugin in page_plugins:
            row = self._table_widget.rowCount()
            self._table_widget.insertRow(row)

            cb = QCheckBox()
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.addWidget(cb)
            self._table_widget.setCellWidget(row, 0, cb_container)

            name = plugin.get('name') or plugin.get('id', '')
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(plugin.get('desc', ''))
            self._table_widget.setItem(row, 1, name_item)

            ver = plugin.get('version', plugin.get('ver', ''))
            ver_item = QTableWidgetItem(ver)
            ver_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_widget.setItem(row, 2, ver_item)

            source = plugin.get('source', 'pacman')
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_widget.setItem(row, 3, source_item)

            installed = self.is_installed(plugin)
            status_item = QTableWidgetItem("Installed" if installed else "Available")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if installed:
                status_item.setForeground(QColor("#00BFAE"))
            self._table_widget.setItem(row, 4, status_item)

        self._table_widget.setUpdatesEnabled(True)
        self._update_pagination_buttons()

    def _refresh_content(self):
        if self._list_mode and self._table_widget.isVisible():
            self._populate_table()
        else:
            self._render_current_page()

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

    def create_filter_buttons(self, parent_layout):
        """Create category filter buttons styled as navbar tabs"""
        container = QFrame()
        container.setObjectName("categoryFilterBar")
        container.setFixedHeight(44)
        container.setStyleSheet("""
            QFrame#categoryFilterBar {
                background-color: rgba(14, 14, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        categories = sorted({self._category_for(p) for p in self.plugins})
        all_filters = ["All"] + categories

        self._filter_buttons = {}
        for cat in all_filters:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat: self._on_filter_clicked(c))

            if cat == "All":
                btn.setChecked(True)

            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8B8D97;
                    border: none;
                    border-radius: 8px;
                    padding: 0 16px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.04);
                    color: #EDEDEF;
                }
                QPushButton:checked {
                    background-color: rgba(0, 191, 174, 0.1);
                    color: #EDEDEF;
                    font-weight: 600;
                }
            """)

            layout.addWidget(btn)
            self._filter_buttons[cat] = btn

        layout.addStretch()
        parent_layout.addWidget(container)

    def _on_filter_clicked(self, category):
        """Toggle exclusive filter button state and apply filter"""
        for cat, btn in self._filter_buttons.items():
            btn.setChecked(cat == category)
        if category == "All":
            self.show_all_apps()
        else:
            self.filter_by_category(category)


    @staticmethod
    def _get_scrollbar_stylesheet():
        """Return beautiful scrollbar stylesheet with dark rounded corners"""
        return """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea::corner {
                background: transparent;
                border: none;
            }
            /* Vertical Scrollbar */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(60, 60, 60, 0.7);
                border-radius: 6px;
                min-height: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(80, 80, 80, 0.9);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(100, 100, 100, 1);
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            
            /* Horizontal Scrollbar */
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(60, 60, 60, 0.7);
                border-radius: 6px;
                min-width: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(80, 80, 80, 0.9);
            }
            QScrollBar::handle:horizontal:pressed {
                background: rgba(100, 100, 100, 1);
            }
            QScrollBar::add-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                border: none;
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
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
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_layout.addWidget(grid_container)
        scroll.setWidget(scroll_widget)
        self._scroll_area = scroll
        parent_layout.addWidget(scroll, 1)

    def populate_app_cards(self):
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
            self._prewarm_installed_cache()
        if self._selected_category:
            self._category_filtered_plugins = [p for p in self._all_plugins if self._category_for(p) == self._selected_category]
        self._current_page = 1
        self._calc_items_per_page()
    
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
    
    @staticmethod
    def _category_for(plugin):
        cat = (plugin.get('category') or '').strip()
        if cat:
            c = cat.lower()
            synonyms = {
                'system': 'System Tools',
                'system tool': 'System Tools',
                'system tools': 'System Tools',
                'utility': 'Utility',
                'utilities': 'Utility',
                'dev': 'Development',
                'development': 'Development',
                'internet': 'Internet',
                'network': 'Internet',
                'graphics': 'Graphics',
                'multimedia': 'Multimedia',
                'audio': 'Multimedia',
                'video': 'Multimedia',
                'office': 'Office',
                'productivity': 'Office',
                'education': 'Education',
                'game': 'Games',
                'games': 'Games',
                'security': 'Security',
                'communication': 'Communication',
                'chat': 'Communication',
            }
            return synonyms.get(c, cat)
        tags = plugin.get('tags') or []
        tags_text = ' '.join(tags) if isinstance(tags, (list, tuple, set)) else str(tags)
        text = ' '.join([
            plugin.get('name', ''),
            plugin.get('desc', ''),
            plugin.get('id', ''),
            plugin.get('pkg', ''),
            tags_text,
        ]).lower()
        patterns = [
            (('vscode','visual studio','code','editor','ide','developer','dev','git','node','npm','python','qt','gcc','make','electron','android studio'), 'Development'),
            (('browser','firefox','chrome','web','network','mail','torrent','internet','ftp'), 'Internet'),
            (('image','photo','graphic','draw','paint','gimp','krita','inkscape','blender'), 'Graphics'),
            (('video','music','audio','player','vlc','mpv','spotify','media','ffmpeg'), 'Multimedia'),
            (('chat','telegram','discord','slack','message','voip','call','communication'), 'Communication'),
            (('system','monitor','btop','htop','terminal','shell','backup','timeshift','disk','partition','gparted','bleachbit'), 'System Tools'),
            (('game','steam','lutris','retroarch','games'), 'Games'),
            (('office','libreoffice','document','spreadsheet','writer','calc','pdf'), 'Office'),
            (('learn','education','anki','study'), 'Education'),
            (('password','privacy','guard','vpn','security','encrypt'), 'Security'),
        ]
        for kws, label in patterns:
            for kw in kws:
                if kw in text:
                    return label
        return 'Utility'
    
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
            return self.grid_layout.spacing() if self.grid_layout else 20
        except Exception:
            return 20

    def _calc_cols(self, viewport_width):
        spacing = self._layout_spacing()
        unit_w = 280 + spacing
        return max(1, min(6, (max(0, viewport_width) + spacing) // unit_w))

    def _calc_visible_rows(self, viewport_height):
        spacing = self._layout_spacing()
        row_h = 130 + spacing
        return max(1, (max(0, viewport_height) + spacing) // row_h)

    def _enforce_row_min_heights(self, upto_row):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            for r in range(0, max(0, int(upto_row)) + 1):
                self.grid_layout.setRowMinimumHeight(r, 130)
        except Exception:
            pass

    
    def _calc_items_per_page(self):
        try:
            viewport_w = self._scroll_area.viewport().width() if self._scroll_area else self.width()
            viewport_h = self._scroll_area.viewport().height() if self._scroll_area else self.height()
        except Exception:
            viewport_w = self.width()
            viewport_h = self.height()
        if viewport_w < 200 or viewport_h < 100:
            viewport_w = 900
            viewport_h = 600
        cols = self._calc_cols(viewport_w)
        self._current_cols = cols
        rows = max(2, self._calc_visible_rows(viewport_h))
        self._items_per_page = max(1, cols * rows * 3)

    def _get_current_plugins(self):
        if self._selected_category:
            return self._category_filtered_plugins
        return self._all_plugins

    def _get_visible_page_numbers(self):
        total = self._total_pages
        current = self._current_page
        if total <= 9:
            return list(range(1, total + 1))
        pages = set()
        pages.add(1)
        pages.add(total)
        pages.add(current)
        if current > 1:
            pages.add(current - 1)
        if current < total:
            pages.add(current + 1)
        if current > 2:
            pages.add(current - 2)
        if current < total - 1:
            pages.add(current + 2)
        sorted_pages = sorted(pages)
        result = []
        for i, p in enumerate(sorted_pages):
            if i > 0 and p - sorted_pages[i - 1] > 1:
                result.append(None)
            result.append(p)
        return result

    def _go_to_page(self, page):
        if page < 1 or page > self._total_pages or page == self._current_page:
            return
        self._current_page = page
        self._refresh_content()
        QTimer.singleShot(50, lambda: self._scroll_area and self._scroll_area.verticalScrollBar().setValue(0))

    def _go_to_first_page(self):
        self._go_to_page(1)

    def _go_to_prev_page(self):
        self._go_to_page(self._current_page - 1)

    def _go_to_next_page(self):
        self._go_to_page(self._current_page + 1)

    def _go_to_last_page(self):
        self._go_to_page(self._total_pages)

    def _get_filtered_plugins(self):
        has_search = hasattr(self, '_all_filtered_search_cards') and self._all_filtered_search_cards is not None
        has_combined = hasattr(self, '_current_filter_states') and self._current_filter_states
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
        if not filtered:
            self._clear_grid_and_hide_all()
            self._pagination_bar.setVisible(False)
            self._reset_row_stretches()
            return
        cols = self._current_cols
        start = (self._current_page - 1) * self._items_per_page
        end = min(start + self._items_per_page, len(filtered))
        page_cards = filtered[start:end]
        if not page_cards:
            self._clear_grid_and_hide_all()
            self._pagination_bar.setVisible(False)
            return
        self._begin_layout_update()
        self._clear_grid_and_hide_all()
        self._reset_row_stretches()
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        for i, card_data in enumerate(page_cards):
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        max_row = (len(page_cards) - 1) // cols
        self._enforce_row_min_heights(max_row)
        self._finish_layout_update()
        self._update_pagination_buttons()

    def _create_pagination_bar(self):
        bar = QFrame()
        bar.setObjectName("paginationBar")
        bar.setStyleSheet("""
            QFrame#paginationBar {
                background-color: rgba(14, 14, 16, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
                padding: 4px 8px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def _btn_style(active=False):
            if active:
                return ("QPushButton { background-color: rgba(0, 191, 174, 0.15); color: #EDEDEF; "
                        "border: 1px solid rgba(0, 191, 174, 0.3); border-radius: 6px; "
                        "padding: 4px 10px; font-size: 11px; font-weight: 600; }")
            return ("QPushButton { background-color: transparent; color: #8B8D97; "
                    "border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; "
                    "padding: 4px 10px; font-size: 11px; font-weight: 500; } "
                    "QPushButton:hover { background-color: rgba(255, 255, 255, 0.04); color: #EDEDEF; } "
                    "QPushButton:disabled { color: #5C5E66; border-color: rgba(255, 255, 255, 0.03); }")

        self._first_btn = QPushButton("\u25c0\u25c0")
        self._first_btn.setToolTip("First page")
        self._first_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._first_btn.setFixedHeight(28)
        self._first_btn.setStyleSheet(_btn_style())
        self._first_btn.clicked.connect(self._go_to_first_page)
        layout.addWidget(self._first_btn)

        self._prev_btn = QPushButton("\u25c0")
        self._prev_btn.setToolTip("Previous page")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.setFixedHeight(28)
        self._prev_btn.setStyleSheet(_btn_style())
        self._prev_btn.clicked.connect(self._go_to_prev_page)
        layout.addWidget(self._prev_btn)

        self._page_buttons_container = QHBoxLayout()
        self._page_buttons_container.setSpacing(4)
        layout.addLayout(self._page_buttons_container)

        self._info_btn = QPushButton()
        self._info_btn.setFixedHeight(28)
        self._info_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #5C5E66; border: none; "
            "padding: 4px 6px; font-size: 10px; }"
        )
        layout.addWidget(self._info_btn)

        self._next_btn = QPushButton("\u25b6")
        self._next_btn.setToolTip("Next page")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setFixedHeight(28)
        self._next_btn.setStyleSheet(_btn_style())
        self._next_btn.clicked.connect(self._go_to_next_page)
        layout.addWidget(self._next_btn)

        self._last_btn = QPushButton("\u25b6\u25b6")
        self._last_btn.setToolTip("Last page")
        self._last_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._last_btn.setFixedHeight(28)
        self._last_btn.setStyleSheet(_btn_style())
        self._last_btn.clicked.connect(self._go_to_last_page)
        layout.addWidget(self._last_btn)

        bar.setVisible(False)
        return bar

    def _update_pagination_buttons(self):
        filtered = self._get_filtered_plugins()
        total_plugins = len(filtered)
        if total_plugins == 0:
            self._pagination_bar.setVisible(False)
            return
        self._total_pages = max(1, (total_plugins + self._items_per_page - 1) // self._items_per_page)
        if self._total_pages <= 1:
            self._pagination_bar.setVisible(False)
            return
        self._pagination_bar.setVisible(True)

        def _btn_style(active=False):
            if active:
                return ("QPushButton { background-color: rgba(0, 191, 174, 0.15); color: #EDEDEF; "
                        "border: 1px solid rgba(0, 191, 174, 0.3); border-radius: 6px; "
                        "padding: 4px 10px; font-size: 11px; font-weight: 600; }")
            return ("QPushButton { background-color: transparent; color: #8B8D97; "
                    "border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; "
                    "padding: 4px 10px; font-size: 11px; font-weight: 500; } "
                    "QPushButton:hover { background-color: rgba(255, 255, 255, 0.04); color: #EDEDEF; } "
                    "QPushButton:disabled { color: #5C5E66; border-color: rgba(255, 255, 255, 0.03); }")

        self._first_btn.setEnabled(self._current_page > 1)
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._total_pages)
        self._last_btn.setEnabled(self._current_page < self._total_pages)

        while self._page_buttons_container.count():
            item = self._page_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for page in self._get_visible_page_numbers():
            if page is None:
                lbl = QLabel("\u2026")
                lbl.setStyleSheet("color: #5C5E66; padding: 4px 2px; font-size: 11px;")
                self._page_buttons_container.addWidget(lbl)
            else:
                btn = QPushButton(str(page))
                btn.setFixedSize(32, 28)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(_btn_style(active=(page == self._current_page)))
                btn.clicked.connect(lambda checked, p=page: self._go_to_page(p))
                self._page_buttons_container.addWidget(btn)

        start = (self._current_page - 1) * self._items_per_page + 1
        end = min(start + self._items_per_page - 1, total_plugins)
        self._info_btn.setText(f"{start}\u2013{end} of {total_plugins}")
        self._info_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #5C5E66; border: none; "
            "padding: 4px 6px; font-size: 10px; }"
        )

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
        """Create a beautifully designed app card with glassmorphism styling"""
        card = QFrame()
        card.setFixedSize(280, 130)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setObjectName("appCard")
        except Exception:
            pass

        card_state = CardState()
        card_state.set_installed_state(installed)
        card.card_state = card_state

        def set_card_installing(installing):
            card_state.set_installing(installing)
            if installing:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(False)
                    if widget.text() in ("Install", "Open"):
                        widget.setText("Installing\u2026")
                    elif widget.text() == "Uninstall":
                        widget.setText("Uninstalling\u2026")
            else:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(True)
                    if "Installing" in widget.text() or "Uninstalling" in widget.text():
                        if "Uninstalling" in widget.text():
                            widget.setText("Uninstall")
                        else:
                            widget.setText("Install" if not card_state.get_installed_state() else "Open")
        card.set_installing = set_card_installing

        source = self._get_package_source(plugin_spec)
        sc = _SOURCE_GRADIENTS.get(source, ('#00BFAE', '#00BFAE'))

        card.setStyleSheet(f"""
            QFrame#appCard {{
                background-color: rgba(22, 23, 26, 0.85);
                border-top: 1px solid rgba(255, 255, 255, 0.06);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(255, 255, 255, 0.03);
                border-right: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 14px;
            }}
            QFrame#appCard:hover {{
                border-top: 1px solid rgba(255, 255, 255, 0.10);
                border-bottom: 1px solid rgba(0, 0, 0, 0.35);
                background-color: rgba(26, 28, 32, 0.85);
            }}
        """)
        _shadow(card, blur=20, offset=(3, 5), alpha=160)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(_get_plugin_app_icon(32))
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(icon_label)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)

        name_label = QLabel(plugin_spec.get('name', plugin_spec.get('id')))
        name_label.setStyleSheet("""
            QLabel {
                color: #EDEDEF;
                font-weight: 600;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        name_col.addWidget(name_label)

        source_badge = self._source_badge(source)
        name_col.addWidget(source_badge)

        top.addLayout(name_col, 1)
        layout.addLayout(top)

        desc_label = QLabel(plugin_spec.get('desc', ''))
        desc_label.setStyleSheet("""
            QLabel {
                color: #8B8D97;
                font-size: 10px;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(30)
        layout.addWidget(desc_label)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        _neu_btn = """
            QPushButton {
                background-color: rgba(26, 28, 34, 0.95);
                color: #00BFAE;
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 8px;
                font-weight: 700;
                font-size: 11px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: rgba(30, 32, 38, 0.95);
                border: 1px solid rgba(0, 191, 174, 0.6);
            }
            QPushButton:pressed {
                background-color: rgba(20, 22, 26, 0.95);
                border: 1px solid rgba(0, 191, 174, 0.8);
            }
        """

        if installed:
            open_btn = QPushButton("Open")
            open_btn.setFixedHeight(30)
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.setStyleSheet(_neu_btn)
            open_btn.clicked.connect(lambda: self.launch_requested.emit(plugin_spec['id']))
            btn_row.addWidget(open_btn)

            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setFixedHeight(30)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.setStyleSheet(
                _neu_btn
                .replace("#00BFAE", "#FF6B6B")
                .replace("0, 191, 174", "255, 107, 107")
            )
            uninstall_btn.clicked.connect(lambda: (card.set_installing(True), self.uninstall_requested.emit(plugin_spec['id'])))
            btn_row.addWidget(uninstall_btn)
        else:
            install_btn = QPushButton("Install")
            install_btn.setFixedHeight(30)
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.setStyleSheet(_neu_btn)
            install_btn.clicked.connect(lambda: (card.set_installing(True), self.install_requested.emit(plugin_spec['id'])))
            btn_row.addWidget(install_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

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
        self._selected_category = None
        if hasattr(self, '_filter_buttons') and 'All' in self._filter_buttons:
            for cat, btn in self._filter_buttons.items():
                btn.setChecked(cat == "All")
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
        
        self._all_filtered_search_cards = filtered if has_search else None
        
        self._refresh_content()

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
    
    def filter_by_category(self, category):
        self._selected_category = category
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
        self._category_filtered_plugins = [p for p in self._all_plugins if self._category_for(p) == category]
        self._current_page = 1
        self._calc_items_per_page()
        self._refresh_content()
        if hasattr(self, '_filter_buttons'):
            for cat, btn in self._filter_buttons.items():
                btn.setChecked(cat == category)
    
    def show_all_apps(self):
        self._selected_category = None
        if hasattr(self, '_filter_buttons'):
            for cat, btn in self._filter_buttons.items():
                btn.setChecked(cat == "All")
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
        self._current_page = 1
        self._calc_items_per_page()
        self._refresh_content()
    
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
            self._calc_items_per_page()
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
        
        self._all_filtered_cards = filtered_cards
        
        self._current_page = 1
        self._refresh_content()
