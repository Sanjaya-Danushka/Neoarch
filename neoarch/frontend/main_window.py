# cSpell:disable
"""
Main window module for NeoArch Package Manager
"""

import os
from typing import Any

from PyQt6.QtWidgets import QMainWindow, QSizePolicy, QWidget
from PyQt6.QtCore import Qt, QTimer, QEvent, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QCursor

from neoarch.backend.services import network_latency
from neoarch.resources.paths import PROJECT_ROOT
from neoarch.managers.plugin_manager import PluginsManager
from neoarch.frontend.styles import Styles
from neoarch.frontend.themes import ThemeManager
from neoarch.frontend.components.title_bar import _get_brand_icon_path
from neoarch.frontend.mixins.icons import _IconsMixin, _build_window_icon
from neoarch.frontend.mixins.auth import _AuthMixin
from neoarch.frontend.mixins.plugins import _PluginsMixin
from neoarch.frontend.mixins.settings import _SettingsMixin
from neoarch.frontend.mixins.bundles import _BundlesMixin
from neoarch.frontend.mixins.search import _SearchMixin
from neoarch.frontend.mixins.filters import _FiltersMixin
from neoarch.frontend.mixins.views import _ViewsMixin
from neoarch.frontend.mixins.operations import _OperationsMixin

_BASE_DIR = str(PROJECT_ROOT)
_DISCOVER_ICON_DIR = os.path.join(_BASE_DIR, "assets", "icons", "discover")

network_latency.install()
network_latency.start_probing()

class ArchPkgManagerUniGetUI(_ViewsMixin, _OperationsMixin, _BundlesMixin, _SearchMixin, _FiltersMixin, _PluginsMixin, _SettingsMixin, _AuthMixin, _IconsMixin, QMainWindow):
    packages_ready = pyqtSignal(list, object, bool)  # packages, load_id, is_final
    discover_results_ready = pyqtSignal(list)
    discover_suggestions_ready = pyqtSignal(str)
    show_message = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    load_error = pyqtSignal()
    search_timer = QTimer()
    installation_progress = pyqtSignal(str, bool)  # status, can_cancel
    progress_update = pyqtSignal(str, int)  # message, percent (-1 = indeterminate)
    ui_call = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        from neoarch.resources.paths import APP_EDITION
        self.setWindowTitle(f"NeoArch — {APP_EDITION} Edition")
        self.setGeometry(100, 100, 1600, 900)  # Increased width to accommodate sidebar
        self.setMinimumSize(1280, 850)  # Set minimum size (fits Discover dashboard without scroll)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(Styles.get_dark_stylesheet())
        self._theme_manager = ThemeManager(self)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        self._theme_manager.load_saved()
        # Re-apply stylesheet after theme load
        self.setStyleSheet(Styles.get_dark_stylesheet())
        icon_path = _get_brand_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(_build_window_icon(icon_path))
        # self.set_minimal_icon()
        self._resize_margin = 6
        self._resize_edge = None
        self._edge_cursor = None
        self._resize_active = False
        self.setMouseTracking(True)
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self)
        except Exception:
            pass
        
        self.current_view = "updates"
        self._user_has_navigated = False
        self.updating = False
        self.all_packages = []
        self.search_results = []
        self.packages_per_page = 10
        self.current_page = 0
        self.loader_thread: Any = None
        self.git_manager: Any = None
        self.docker_manager: Any = None
        self.current_search_mode = 'both'
        self.filtered_results = []
        self.installed_index: Any = None
        self._installed_index_building = False
        self._installed_index_last_built = 0
        self._installed_index_sources = set()
        self._installed_filter_states = {"Updates available": False}
        # Working bundle state (list of {name,id,source,version?})
        self.bundle_items = []
        # Settings state
        self.settings = self.load_settings()
        # Plugins runtime
        self.plugins = []
        self.plugin_timer = QTimer()
        self.plugin_timer.setInterval(60000)
        self.plugin_timer.timeout.connect(self.run_plugin_tick)
        self._icon_cache = {}
        self._source_icon_cache = {}
        self._discover_name_icon = self.get_svg_icon(os.path.join(_DISCOVER_ICON_DIR, "packagename.svg"), 20)
        self._discover_version_icon = self.get_svg_icon(os.path.join(_DISCOVER_ICON_DIR, "version.svg"), 18)
        self._flathub_checked = False
        self.plugins_manager = PluginsManager(self)
        self.packages_ready.connect(self.on_packages_loaded)
        self.discover_results_ready.connect(self.display_discover_results)
        self.discover_suggestions_ready.connect(self._on_discover_suggestions_ready)
        self.show_message.connect(self._show_message)
        self.log_signal.connect(self.log)
        self.load_error.connect(self.on_load_error)
        self.installation_progress.connect(self.on_installation_progress)
        self.progress_update.connect(self.on_progress_update)
        self.ui_call.connect(self._on_ui_call)
        # Background loading coordination
        self.loading_context: Any = None
        self.cancel_update_load = False
        self._updating_selection = False
        self._view_mode = "table"
        self._grid_view_btn = None
        self.cancel_discover_search = False
        # Nav badges (e.g., updates count)
        self.nav_badges = {}
        # Attributes initialized in other methods
        self.settings_widgets = {}
        self.settings_content_layout: Any = None
        self.settings_nav_buttons = {}
        self.source_card: Any = None
        self.filters_panel: Any = None

        # Cloud auth (Supabase sync)
        from neoarch.backend.cloud_auth import CloudAuthManager
        self._cloud_auth = CloudAuthManager()
        self._cloud_auth.login_changed.connect(self._on_cloud_user_changed)

        self.setup_ui()
        # Set initial nav button state
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == self.current_view)
        self.center_window()
        
        # Initialize the default view (UI only, no data loading — deferred to auth flow)
        self.switch_view(self.current_view, load=False)
        
        # Show welcome animation in console on first launch
        QTimer.singleShot(500, self.show_welcome_animation)
        # Initialize plugins shortly after UI is ready
        QTimer.singleShot(1000, self.initialize_plugins)
        QTimer.singleShot(1200, self._prewarm_installed_index_async)
        
        # Debounce search input
        self.search_timer.setInterval(800)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        try:
            self.search_input.returnPressed.connect(self.perform_search)
        except Exception:
            pass
        QTimer.singleShot(1500, self.run_first_run_checks)
        # Restore cloud avatar UI state
        QTimer.singleShot(2000, lambda: self._on_cloud_user_changed(self._cloud_auth.user))

    def _on_cloud_user_changed(self, user):
        if hasattr(self, 'update_user_avatar'):
            self.update_user_avatar(user)
        if hasattr(self, '_update_nav_greeting'):
            self._update_nav_greeting(user)

    def _on_theme_changed(self, theme_id):
        """Reapply the main stylesheet when the theme changes."""
        from neoarch.frontend.tokens import DARK_STYLESHEET
        self.setStyleSheet(DARK_STYLESHEET)

    def closeEvent(self, event):
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception:
            pass
        super().closeEvent(event)

    # ── Frameless window edge resizing ──────────────────────────────

    def _edge_at(self, pos: QPoint):
        if self.isMaximized() or self.isFullScreen():
            return None
        w, h = self.width(), self.height()
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m
        if left and top:
            return Qt.Edge.TopEdge | Qt.Edge.LeftEdge
        if right and top:
            return Qt.Edge.TopEdge | Qt.Edge.RightEdge
        if left and bottom:
            return Qt.Edge.LeftEdge | Qt.Edge.BottomEdge
        if right and bottom:
            return Qt.Edge.RightEdge | Qt.Edge.BottomEdge
        if left:
            return Qt.Edge.LeftEdge
        if right:
            return Qt.Edge.RightEdge
        if top:
            return Qt.Edge.TopEdge
        if bottom:
            return Qt.Edge.BottomEdge
        return None

    @staticmethod
    def _cursor_for_edge(edge):
        corners = {
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.TopEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeBDiagCursor,
            Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
        }
        if edge in corners:
            return corners[edge]
        shapes = {
            Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
            Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
        }
        return shapes.get(edge)

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype in (QEvent.Type.MouseButtonRelease, QEvent.Type.Resize):
            if self._resize_active:
                self._resize_active = False
                self.unsetCursor()
                self._edge_cursor = None
            if etype == QEvent.Type.Resize:
                return super().eventFilter(obj, event)
        if etype == QEvent.Type.MouseMove or etype == QEvent.Type.MouseButtonPress:
            if self.isMaximized() or self.isFullScreen():
                return super().eventFilter(obj, event)
            if not (isinstance(obj, QWidget) and obj.window() is self):
                return super().eventFilter(obj, event)
            if self._resize_active:
                return True
            local = obj.mapTo(self, event.position().toPoint())
            edge = self._edge_at(local)
            if etype == QEvent.Type.MouseMove:
                if edge is not None:
                    self._edge_cursor = self._cursor_for_edge(edge)
                    self.setCursor(self._edge_cursor)
                elif self._edge_cursor is not None:
                    self._edge_cursor = None
                    self.unsetCursor()
            elif etype == QEvent.Type.MouseButtonPress:
                if edge is not None and event.button() == Qt.MouseButton.LeftButton:
                    handle = self.windowHandle()
                    if handle is not None:
                        self._resize_active = True
                        handle.startSystemResize(edge)
                        return True
        return super().eventFilter(obj, event)


