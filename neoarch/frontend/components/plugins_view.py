# === components: plugins_view.py ===
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from typing import Any
import os
import shutil

from neoarch.resources.plugin_data import get_plugins_data, get_all_plugins_data
from neoarch.resources.paths import ICONS_DIR, PLUGINS_ITEMS_DIR
from neoarch.frontend.tokens import Colors, SourceColors
from neoarch.frontend.components.packages_grid_view import (
    PackageCard, _Chip, _CheckBox, _SmallLabel, _SourceLogo,
    _STATUS_COLORS,
)

_ACCENT = Colors.ACCENT
_TEXT_MUTED = QColor(Colors.TEXT_3)


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
    (glass surface, source logo, status chip) with plugin action buttons.

    Installed cards show an "Open" button plus an "Uninstall" button that only
    appears on hover (double-click also launches). The action row is rebuilt
    in place by :meth:`set_installed` so buttons update in real time after an
    install/uninstall completes.
    """

    install_clicked = pyqtSignal(str)
    launch_clicked = pyqtSignal(str)
    uninstall_clicked = pyqtSignal(str)

    CARD_W = 280
    CARD_H = 150

    def __init__(self, plugin, installed, app=None, parent=None):
        self._plugin = plugin
        self._installed = bool(installed)
        self._installing = False
        self._hover = False
        super().__init__(plugin, 0, app, parent)

    def mouseDoubleClickEvent(self, event):
        if self._installed:
            self.launch_clicked.emit(self._plugin.get("id"))
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self._sync_uninstall_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._sync_uninstall_visibility()
        super().leaveEvent(event)

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
        self._uninstall_btn = None
        self._add_action_buttons(bottom)

        layout.addLayout(bottom)
        self._action_row = bottom
        self._sync_uninstall_visibility()

    def _add_action_buttons(self, row):
        """(Re)build the action buttons into ``row`` based on install state."""
        pid = self._plugin.get("id")
        if self._installed:
            open_btn = self._make_action_button("Open", _NEU_BTN_QSS)
            open_btn.clicked.connect(lambda: self.launch_clicked.emit(pid))
            row.addWidget(open_btn)
            self._action_buttons.append(open_btn)

            self._uninstall_btn = self._make_action_button("Uninstall", _DANGER_BTN_QSS)
            self._uninstall_btn.clicked.connect(lambda: self.uninstall_clicked.emit(pid))
            self._uninstall_btn.hide()
            row.addWidget(self._uninstall_btn)
            self._action_buttons.append(self._uninstall_btn)
        else:
            install_btn = self._make_action_button("Install", _NEU_BTN_QSS)
            install_btn.clicked.connect(lambda: self.install_clicked.emit(pid))
            row.addWidget(install_btn)
            self._action_buttons.append(install_btn)

    def _sync_uninstall_visibility(self):
        """Show the Uninstall button only while hovering and not installing."""
        if self._uninstall_btn is not None:
            self._uninstall_btn.setVisible(bool(self._hover) and not self._installing)

    def _set_status(self, status):
        color = _STATUS_COLORS.get(status, _TEXT_MUTED)
        chip = _Chip(status, color)
        if hasattr(self, '_action_row') and self._action_row is not None:
            try:
                self._action_row.replaceWidget(self.status_chip, chip)
            except Exception:
                self._action_row.insertWidget(0, chip, alignment=Qt.AlignmentFlag.AlignBottom)
        self.status_chip.hide()
        self.status_chip.deleteLater()
        self.status_chip = chip

    @staticmethod
    def _make_action_button(text, qss):
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(qss)
        return btn

    def set_installing(self, installing):
        self._installing = bool(installing)
        for b in self._action_buttons:
            b.setEnabled(not installing)
            if installing:
                if b is self._uninstall_btn:
                    b.setText("Uninstalling\u2026")
                elif b.text() in ("Install", "Open"):
                    b.setText("Installing\u2026")
            else:
                if "Installing" in b.text():
                    b.setText("Install" if not self._installed else "Open")
                elif "Uninstalling" in b.text():
                    b.setText("Uninstall")
        self._sync_uninstall_visibility()

    def set_installed(self, installed):
        """Flip a card to its installed/uninstalled action row in place so the
        button updates immediately after an install/uninstall completes."""
        installed = bool(installed)
        if installed == self._installed:
            return
        self._installed = installed
        self._installing = False
        self._action_buttons = []
        self._uninstall_btn = None
        row = self._action_row
        for i in reversed(range(row.count())):
            item = row.itemAt(i)
            widget = item.widget()
            if widget is None or widget is self.status_chip:
                continue
            widget.hide()
            widget.deleteLater()
            row.removeItem(item)
        self._add_action_buttons(row)
        self._set_status("Installed" if installed else "Available")
        self._sync_uninstall_visibility()


class PluginsView(QWidget):
    install_requested = pyqtSignal(str)   # plugin id
    install_many_requested = pyqtSignal(list)  # list of plugin ids (batch install)
    launch_requested = pyqtSignal(str)    # plugin id
    uninstall_requested = pyqtSignal(str) # plugin id
    selection_changed = pyqtSignal(int)   # count of selected installable items
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
        self._PAGE_SIZE = 50
        self._visible_count = 0

        # Installation status cache — preserved across navigation, cleared only after install/uninstall
        self._installed_cache = {}

        self._pending_live_query = None

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Loading state — identical to updates/discover page
        from neoarch.frontend.components.updates_table import _EmptyOverlay
        self._loading_overlay = _EmptyOverlay()
        self._loading_overlay.set_loading(True, "Loading plugins\u2026")
        layout.addWidget(self._loading_overlay)

        # Content stacked area
        self._content_stack = QFrame()
        self._content_stack.setObjectName("pluginContentStack")
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Apps Grid
        self.create_apps_grid(content_layout)

        layout.addWidget(self._content_stack, 1)
        self._content_stack.setVisible(False)

    def show_grid_mode(self):
        """Show the loading bar briefly, then transition to the card grid."""
        self._loading_overlay.setVisible(True)
        self._content_stack.setVisible(False)
        QTimer.singleShot(120, self._transition_from_loading)

    def _transition_from_loading(self):
        """Fade from the loading bar to the card grid."""
        self._loading_overlay.setVisible(False)
        self._content_stack.setVisible(True)
        self._scroll_area.setVisible(True)
        try:
            self._scroll_area.verticalScrollBar().setValue(0)
        except Exception:
            pass
        self._calc_grid_metrics()
        QTimer.singleShot(0, self._post_layout_recalc)

    def _post_layout_recalc(self):
        """Recalculate grid after the layout engine has settled."""
        self._calc_grid_metrics()
        self._render_current_page()

    def _render_grid_after_show(self):
        try:
            self._scroll_area.verticalScrollBar().setValue(0)
        except Exception:
            pass
        self._calc_grid_metrics()
        self._render_current_page()

    def _refresh_content(self):
        self._render_current_page()

    def _get_or_create_card(self, plugin_spec):
        """Return cached card data for a plugin, creating the widget lazily."""
        try:
            pid = plugin_spec.get('id')
        except Exception:
            pid = None
        if pid and pid in getattr(self, '_card_cache', {}):
            card_data = self._card_cache[pid]
            if card_data.get('widget') is None:
                card = self.create_app_card(plugin_spec, None, card_data.get('installed', False))
                card_data['widget'] = card
            return card_data
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
        # Maximum vertical policy: keep the grid sized to its content instead of
        # expanding to fill the viewport height, which vertically centered the
        # fixed-height cards in over-tall grid rows (visible when searching).
        grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
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

        self._load_more_btn = QPushButton("Load More")
        self._load_more_btn.setObjectName("loadMoreBtn")
        self._load_more_btn.setFixedHeight(40)
        self._load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_more_btn.setVisible(False)
        self._load_more_btn.clicked.connect(self._on_load_more)
        scroll_layout.addWidget(self._load_more_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        scroll.setWidget(scroll_widget)
        self._scroll_area = scroll
        parent_layout.addWidget(scroll, 1)

    def populate_app_cards(self):
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
            self._prewarm_installed_cache()
        self._calc_grid_metrics()

    def _create_all_cards(self):
        """Store plugin data without creating widgets (lazy creation)."""
        self._all_cards = []
        plugins = self._all_plugins or self.plugins
        for plugin in plugins:
            pid = plugin.get('id')
            if pid and pid in self._card_cache:
                card_data = self._card_cache[pid]
            else:
                installed = self.is_installed(plugin)
                card_data = {
                    'plugin': plugin,
                    'widget': None,
                    'installed': installed
                }
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
        color = SourceColors.get(source, Colors.TEXT_2)

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
            self._load_more_btn.setVisible(False)
            self._visible_count = 0
            return
        if self._visible_count == 0 or self._visible_count > len(filtered):
            self._visible_count = min(self._PAGE_SIZE, len(filtered))
        self._calc_grid_metrics()
        cols = self._current_cols
        card_w = self._card_width
        self._begin_layout_update()
        self._clear_grid_and_hide_all()
        self._reset_row_stretches()
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        visible = filtered[:self._visible_count]
        for i, card_data in enumerate(visible):
            if card_data.get('widget') is None:
                card = self.create_app_card(card_data['plugin'], None, card_data.get('installed', False))
                card_data['widget'] = card
                pid = card_data['plugin'].get('id')
                if pid:
                    self._card_cache[pid] = card_data
            card_data['widget'].setFixedWidth(card_w)
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        max_row = (len(visible) - 1) // cols
        self._enforce_row_min_heights(max_row)
        has_more = self._visible_count < len(filtered)
        self._load_more_btn.setVisible(has_more)
        if has_more:
            remaining = len(filtered) - self._visible_count
            self._load_more_btn.setText(f"Load More ({remaining} remaining)")
        self._finish_layout_update()

    def _on_load_more(self):
        self._visible_count += self._PAGE_SIZE
        self._render_current_page()

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
        card.toggled.connect(lambda _row, _state, c=card: self._on_card_selection_changed(c))
        return card

    def _prewarm_installed_cache(self):
        """Batch-check installed packages with a single pacman -Qq call (short timeout)"""
        try:
            from neoarch.resources.plugin_data import get_all_plugins_data
            plugins = get_all_plugins_data()
            import subprocess
            r = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, timeout=5, check=False)
            if r.returncode != 0 or not r.stdout:
                return
            installed = {l.strip() for l in r.stdout.strip().split('\n') if l.strip()}
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
                r = subprocess.run(["pacman", "-Qi", pkg], capture_output=True, text=True, timeout=5, check=False)
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
            force: If True, clears all caches and shows a brief loading spinner
                   (for post-install/uninstall refresh).
                   If False, preserves caches (for navigation) — much faster.
        """
        if force:
            # Brief loading bar to signal the refresh
            if hasattr(self, '_loading_overlay') and self._content_stack.isVisible():
                self._loading_overlay.setVisible(True)
                self._content_stack.setVisible(False)
            self.clear_installed_cache()
            self._card_cache.clear()
            self._all_cards = []
            self._all_filtered_search_cards = None
            self._all_filtered_cards = None
        self.populate_app_cards()
        if force:
            self._prewarm_installed_cache()
        if not self._current_filter_states:
            self._current_filter_states = {"Available": True, "Installed": True}
        self._apply_combined_filters()
        if force and hasattr(self, '_loading_overlay') and self._loading_overlay.isVisible():
            QTimer.singleShot(120, self._transition_from_loading)

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
        self._visible_count = 0

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
            if self._pending_live_query != query:
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
            for card_data in self._all_card_datas():
                if card_data.get('plugin', {}).get('id') == plugin_id:
                    card = card_data.get('widget')
                    if card is not None and hasattr(card, 'set_installing'):
                        card.set_installing(installing)
                    break
        except Exception:
            pass

    def set_installed(self, plugin_id: str, installed: bool):
        """Update a card's installed state in place so its action buttons
        (Install -> Open, and the hover-only Uninstall button) switch over in
        real time once an install/uninstall reports success."""
        installed = bool(installed)
        for card_data in list(self._all_cards) + list(self._all_filtered_search_cards or []):
            if card_data.get('plugin', {}).get('id') == plugin_id:
                card_data['installed'] = installed
                card = card_data.get('widget')
                if card is not None and hasattr(card, 'set_installed'):
                    card.set_installed(installed)
                if installed:
                    try:
                        self._installed_cache[plugin_id] = True
                    except Exception:
                        pass
                break
        self._update_selection_bar()

    # --- Batch selection -------------------------------------------------
    def _on_card_selection_changed(self, _card):
        self._update_selection_bar()

    def _all_card_datas(self):
        datas = list(getattr(self, '_all_cards', []) or [])
        for d in (getattr(self, '_all_filtered_search_cards', None) or []):
            if d not in datas:
                datas.append(d)
        return datas

    def selected_installable_ids(self):
        """Ids of checked cards that are not yet installed (batch install)."""
        ids = []
        for data in self._all_card_datas():
            if data.get('installed'):
                continue
            widget = data.get('widget')
            if widget is None or not hasattr(widget, 'is_checked') or not widget.is_checked():
                continue
            pid = data.get('plugin', {}).get('id')
            if pid:
                ids.append(pid)
        return ids

    def _update_selection_bar(self):
        try:
            n = len(self.selected_installable_ids())
            self.selection_changed.emit(n)
        except Exception:
            self.selection_changed.emit(0)

    def clear_selection(self):
        """Uncheck all cards and notify the toolbar."""
        for data in self._all_card_datas():
            widget = data.get('widget')
            if widget is not None and hasattr(widget, 'is_checked') and widget.is_checked():
                widget.set_checked(False)
        self.selection_changed.emit(0)

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
        if getattr(self, '_all_filtered_search_cards', None) is not None:
            self.apply_filter()
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
        self._visible_count = 0

        self._refresh_content()
