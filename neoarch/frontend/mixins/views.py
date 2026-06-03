"""
Views mixin for NeoArch - UI setup, navigation, display, and progress
"""

import os
import subprocess
from threading import Thread

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QFrame, QSplitter,
    QScrollArea, QMessageBox, QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QItemSelectionModel
from PyQt6.QtGui import (
    QFont, QColor, QPixmap, QPainter, QPainterPath, QIcon, QFontMetrics,
)

from neoarch.resources.paths import PROJECT_ROOT
from neoarch.managers.docker_manager import DockerManager
from neoarch.managers.git_manager import GitManager
from neoarch.frontend.components.title_bar import _TitleBar
from neoarch.frontend.components.large_search_box import LargeSearchBox
from neoarch.frontend.components.packages_grid_view import PackagesGridView
from neoarch.frontend.components.package_detail_card import PackageDetailCard
from neoarch.frontend.components.loading_spinner import LoadingSpinner

from neoarch.frontend.components.source_card import SourceCard
from neoarch.backend.services import help as help_service
from neoarch.backend.package import loader as packages_service
from neoarch.backend.package import installer as install_service

_BASE_DIR = str(PROJECT_ROOT)

_C = {
    "text_sec": "#8B8D97",
    "text_muted": "#5C5E66",
    "accent": "#00BFAE",
}


class _ViewsMixin:
    """Mixin providing view/display/navigation methods for the main window."""

    def set_minimal_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        with QPainter(pixmap) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setBrush(QColor(0, 212, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)

            font = QFont("Segoe UI", 32, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(26, 26, 26))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")

        icon = QIcon(pixmap)
        self.setWindowIcon(icon)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        # Outer container with margins for glow visibility
        outer = QWidget()
        outer.setObjectName("appOuter")
        self.setCentralWidget(outer)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(0)

        # Content wrapper with glow border effect
        wrapper = QFrame()
        wrapper.setObjectName("appWindow")

        glow = QGraphicsDropShadowEffect(wrapper)
        glow.setBlurRadius(28)
        glow.setOffset(0, 0)
        glow.setColor(QColor(0, 191, 174, 60))
        wrapper.setGraphicsEffect(glow)

        outer_layout.addWidget(wrapper)

        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        # Custom title bar
        title_bar = _TitleBar()
        wrapper_layout.addWidget(title_bar)

        # Body: sidebar + content
        body = QWidget()
        body.setObjectName("appBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = self.create_sidebar()
        body_layout.addWidget(sidebar)

        content = self.create_content_area()
        body_layout.addWidget(content, 1)

        wrapper_layout.addWidget(body, 1)

        # Ensure proper sizing
        self.adjustSize()

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(72)
        sidebar.setMinimumHeight(650)
        sidebar.setObjectName("sidebar")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 10)
        layout.setSpacing(2)

        # ── Brand header (logo only) ──
        logo_label = QLabel()
        logo_label.setObjectName("sidebarLogo")
        logo_label.setFixedSize(36, 36)
        logo_path = os.path.join(_BASE_DIR, "assets", "icons", "logo.png")
        pm = QPixmap(logo_path)
        if not pm.isNull():
            logo_label.setPixmap(pm.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("⬡")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(12)

        # ── Section: Main ──
        sec_main = QLabel()
        sec_main.setObjectName("sidebarSection")
        sec_main.setFixedHeight(0)
        layout.addWidget(sec_main)

        _base = os.path.join(_BASE_DIR, "assets", "icons")
        nav_items = [
            ("Home", "discover", os.path.join(_base, "discover.svg")),
            ("Installed", "installed", os.path.join(_base, "installed.svg")),
            ("Updates", "updates", os.path.join(_base, "updates.svg")),
        ]

        self.nav_buttons = {}
        self._nav_tooltips = {}
        for text, view_id, icon in nav_items:
            btn = self._create_sidebar_btn(icon, text, view_id)
            self.nav_buttons[view_id] = btn
            layout.addWidget(btn)

        # ── Section: System ──
        sec_sys = QLabel()
        sec_sys.setObjectName("sidebarSection")
        sec_sys.setFixedHeight(0)
        layout.addWidget(sec_sys)

        sys_items = [
            ("Sources", "plugins", os.path.join(_base, "plugins.svg")),
            ("Bundles", "bundles", os.path.join(_base, "local-builds.svg")),
            ("Settings", "settings", os.path.join(_base, "settings.svg")),
        ]
        for text, view_id, icon in sys_items:
            btn = self._create_sidebar_btn(icon, text, view_id)
            self.nav_buttons[view_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # ── Footer ──
        footer = QVBoxLayout()
        footer.setContentsMargins(0, 0, 8, 0)
        footer.setSpacing(2)

        # User avatar / login button
        self.user_avatar_btn = QPushButton()
        self.user_avatar_btn.setObjectName("sidebarBtn")
        self.user_avatar_btn.setFixedHeight(48)
        self.user_avatar_btn.setToolTip("Sign in to sync favourites")
        self.user_avatar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_avatar_label = QLabel()
        self.user_avatar_label.setObjectName("sidebarNavIcon")
        self.user_avatar_label.setFixedSize(48, 48)
        self.user_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_avatar_icon = self.get_svg_icon(os.path.join(_BASE_DIR, "assets", "icons", "user.svg"), 24)
        if not default_avatar_icon.isNull():
            self.user_avatar_label.setPixmap(default_avatar_icon.pixmap(24, 24))
        else:
            self.user_avatar_label.setText("👤")
        avatar_layout = QHBoxLayout(self.user_avatar_btn)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.addWidget(self.user_avatar_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.user_avatar_btn.clicked.connect(self._on_avatar_clicked)
        footer.addWidget(self.user_avatar_btn)

        about_btn = QPushButton()
        about_btn.setObjectName("sidebarBtn")
        about_btn.setFixedHeight(48)
        about_btn.setToolTip("About")
        about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_label = QLabel()
        icon_label.setObjectName("sidebarNavIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_icon_path = os.path.join(_BASE_DIR, "assets", "icons", "about.svg")
        icon = self.get_svg_icon(about_icon_path, 24)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(24, 24))
        about_btn_layout = QHBoxLayout(about_btn)
        about_btn_layout.setContentsMargins(0, 0, 0, 0)
        about_btn_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        about_btn.clicked.connect(self.show_about)
        footer.addWidget(about_btn)
        layout.addLayout(footer)

        return sidebar

    def _create_sidebar_btn(self, icon_path: str, text: str, view_id: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("sidebarBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(48)
        btn.setToolTip(text)

        lay = QHBoxLayout(btn)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        icon_label = QLabel()
        icon_label.setObjectName("sidebarNavIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = self.get_svg_icon(icon_path, 24)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(24, 24))
        lay.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Badge for Updates (overlay, top-right)
        if view_id == "updates":
            badge = QLabel(btn)
            badge.setObjectName("navBadge")
            badge.setFixedHeight(16)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setVisible(False)
            badge.setStyleSheet(f"""
                QLabel#navBadge {{
                    background-color: {_C['accent']};
                    color: #0C0C0E;
                    border-radius: 7px;
                    font-size: 9px;
                    font-weight: 700;
                    padding: 0 5px;
                    min-width: 12px;
                }}
            """)
            badge.move(28, 2)

        btn.clicked.connect(lambda checked=False, v=view_id: self._handle_nav(v))
        self._nav_tooltips[view_id] = text
        return btn

    def _handle_nav(self, view_id: str):
        try:
            self.switch_view(view_id)
        except Exception:
            import traceback, sys
            traceback.print_exc()
            sys.stdout.flush()

    def set_updates_count(self, count):
        """Update the updates count in nav and header."""
        # Update dashboard counter if visible
        try:
            if hasattr(self, 'large_search_box'):
                n = int(count) if count is not None else 0
                self.large_search_box.refresh_counts(updates=n)
        except Exception:
            pass
        # Update badge on nav button
        badge = self.nav_badges.get("updates")
        if badge is not None:
            try:
                n = int(count) if count is not None else 0
                if n > 0:
                    text = str(n)
                    badge.setText(text)
                    # Dynamically size the badge to fit the text
                    fm = badge.fontMetrics()
                    w = max(18, fm.horizontalAdvance(text) + 8)
                    badge.setFixedSize(w, 18)
                    # Anchor to top-right of icon container
                    parent = badge.parentWidget()
                    if parent is not None:
                        badge.move(max(0, parent.width() - badge.width()), 0)
                    badge.setVisible(True)
                else:
                    badge.setVisible(False)
            except Exception:
                pass
        # Reflect count in tooltip
        btn = self.nav_buttons.get("updates") if hasattr(self, 'nav_buttons') else None
        if btn:
            try:
                n = int(count) if count is not None else 0
                btn.setToolTip(f"Updates ({n})" if n > 0 else "Updates")
            except Exception:
                pass

    def update_updates_header_counts(self):
        """Update the header info subtitle for Updates with real counts."""
        if self.current_view != "updates":
            return
        total = len(getattr(self, 'updates_all', []) or [])
        matched = len(self.all_packages or [])
        try:
            self.header_info.setText(f"{total} packages were found, {matched} of which match the specified filters")
        except Exception:
            pass

    def update_installed_header_counts(self):
        """Update the header info subtitle for Installed with total installed count."""
        if self.current_view != "installed":
            return
        total = len(getattr(self, 'installed_all', []) or [])
        try:
            self.header_info.setText(f"{total} packages installed")
        except Exception:
            pass

    def create_bottom_card_button(self, icon_path, text, callback):
        btn = QPushButton()
        btn.setObjectName("bottomCardBtn")

        # Create horizontal layout for icon + text
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(12, 16, 12, 16)  # Balanced padding
        layout.setSpacing(8)  # Space between icon and text

        # Icon label - smaller for bottom cards
        icon_label = QLabel()
        icon_label.setObjectName("bottomCardIcon")
        icon_label.setFixedSize(28, 28)  # Smaller than main nav
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Try to load and render SVG in white
        pixmap = self.get_svg_icon(icon_path, 28).pixmap(28, 28)
        if pixmap and not pixmap.isNull():
            icon_label.setPixmap(pixmap)
        else:
            # Fallback to black icon or emoji
            icon = QIcon(icon_path)
            if not icon.isNull():
                icon_label.setPixmap(icon.pixmap(28, 28))
            else:
                emoji = "⚙️" if "settings" in icon_path else "ℹ️"
                icon_label.setText(emoji)

        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Text label - right of icon
        text_label = QLabel(text)
        text_label.setObjectName("bottomCardText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Left align text, vertically centered
        layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

        btn.clicked.connect(callback)

        return btn

    def ensure_flathub_user_remote(self):
        try:
            result = subprocess.run([
                "flatpak", "--user", "remotes"
            ], capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or "flathub" not in (result.stdout or ""):
                subprocess.run([
                    "flatpak", "--user", "remote-add", "--if-not-exists",
                    "flathub", "https://flathub.org/repo/flathub.flatpakrepo"
                ], capture_output=True, text=True, timeout=30)
        except Exception:
            pass
        try:
            self._flathub_checked = True
        except Exception:
            pass

    def create_toolbar_button(self, icon_path, tooltip, callback, icon_size=22):
        """Create a reusable toolbar button with icon and tooltip"""
        btn = QPushButton()
        btn.setFixedSize(42, 42)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 42, 48, 0.9),
                    stop:1 rgba(28, 30, 36, 0.9));
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 21px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(50, 52, 58, 0.9),
                    stop:1 rgba(34, 36, 42, 0.9));
                border: 1px solid rgba(0, 191, 174, 0.25);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 26, 0.9),
                    stop:1 rgba(24, 26, 32, 0.9));
                border: 1px solid rgba(0, 191, 174, 0.4);
            }
        """)

        glow = QGraphicsDropShadowEffect(btn)
        glow.setBlurRadius(20)
        glow.setColor(QColor(0, 0, 0, 160))
        glow.setOffset(3, 4)
        btn.setGraphicsEffect(glow)

        # Try to load SVG icon, fallback to emoji
        icon = self.get_svg_icon(icon_path, icon_size)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))
        else:
            # Fallback to emoji based on icon path
            emoji = self.get_fallback_icon(icon_path)
            if "help" in icon_path.lower():
                emoji = "❓"
            elif "add" in icon_path.lower() or "sudo" in icon_path.lower():
                emoji = "➕"
            btn.setText(emoji)

        return btn

    def _add_right_toolbar_icons(self, layout, show_install_file=False, show_sudo=False, show_bundle=False, show_grid_filter=True):
        """Add common right-side navbar icons to any toolbar layout."""
        navbar_dir = os.path.join(_BASE_DIR, "assets", "icons", "navbar")

        if show_grid_filter:
            self._grid_view_btn = self.create_toolbar_button(
                os.path.join(navbar_dir, "view.svg"),
                "Grid View",
                self.toggle_view_mode
            )
            layout.addWidget(self._grid_view_btn)

            self._filter_btn = self.create_toolbar_button(
                os.path.join(navbar_dir, "Filter.svg"),
                "Filter Packages",
                self.show_category_filter
            )
            self._filter_btn.setProperty("defaultStyle", self._filter_btn.styleSheet())
            layout.addWidget(self._filter_btn)

        if show_install_file:
            self._install_file_btn = self.create_toolbar_button(
                os.path.join(navbar_dir, "install_from_file.svg"),
                "Install from File",
                self.install_from_local_file
            )
            layout.addWidget(self._install_file_btn)

        if show_bundle:
            self._bundle_btn = self.create_toolbar_button(
                os.path.join(_BASE_DIR, "assets", "icons", "local-builds.svg"),
                "Add selected to Bundle",
                self.add_selected_to_bundle
            )
            layout.addWidget(self._bundle_btn)

        if show_sudo:
            self._sudo_btn = self.create_toolbar_button(
                os.path.join(navbar_dir, "insatllwithsudo.svg"),
                "Install with Sudo Privileges",
                self.sudo_install_selected
            )
            layout.addWidget(self._sudo_btn)

    def _show_active_view(self):
        self.packages_grid.setVisible(self._view_mode == "grid")
        self.package_table.setVisible(self._view_mode == "table")
        if self._view_mode == "grid":
            self._populate_grid()

    def _hide_all_package_views(self):
        self.package_table.setVisible(False)
        self.packages_grid.setVisible(False)
        if hasattr(self, 'package_detail_card'):
            self.package_detail_card.clear()

    def _update_nav_greeting(self, user=None):
        if not hasattr(self, '_greeting_label') or not self._greeting_label:
            return
        if self.current_view != "discover":
            self._greeting_label.setVisible(False)
            return
        import getpass
        from datetime import datetime
        from PyQt6.QtGui import QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap
        from PyQt6.QtCore import QRectF, Qt
        h = datetime.now().hour
        if h < 12:
            prefix = "Good morning"
        elif h < 17:
            prefix = "Good afternoon"
        else:
            prefix = "Good evening"
        if user and user.name:
            name = user.name
        else:
            try:
                name = getpass.getuser()
            except Exception:
                name = "User"
        text = f"{prefix}, {name}!"
        font = QFont()
        font.setPixelSize(18)
        font.setBold(True)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        pw, ph = tw + 8, th + 4
        pm = QPixmap(pw, ph)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, pw, 0)
        grad.setColorAt(0.0, QColor("#FFFFFF"))
        grad.setColorAt(1.0, QColor("#4A9EFF"))
        p.setFont(font)
        p.setPen(QPen(grad, 1))
        p.drawText(QRectF(0, 0, pw, ph), Qt.AlignmentFlag.AlignCenter, text)
        p.end()
        self._greeting_label.setPixmap(pm)
        self._greeting_label.setVisible(True)

    def _update_bundle_buttons(self):
        empty = not self.bundle_items
        for btn in ('_bundle_select_all_btn', '_bundle_remove_sel_btn', '_bundle_clear_btn'):
            b = getattr(self, btn, None)
            if b:
                b.setVisible(not empty)
        sep = getattr(self, '_bundle_sep1', None)
        if sep:
            sep.setVisible(not empty)
        for btn in ('_bundle_install_btn', '_bundle_export_btn', '_bundle_save_cloud_btn'):
            b = getattr(self, btn, None)
            if b:
                b.setEnabled(not empty)

    def install_from_local_file(self):
        self.log("Install from local file")

    def create_content_area(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self.create_header()
        layout.addWidget(header)

        # Main Content (Splitter)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)

        # Left panel: Filters/Sources
        left_panel = self.create_filters_panel()
        splitter.addWidget(left_panel)

        # Right panel: Packages table + Console
        right_panel = self.create_packages_panel()
        splitter.addWidget(right_panel)

        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        splitter.setSizes([180, 1000])

        layout.addWidget(splitter, 1)

        return content

    def create_header(self):
        header = QFrame()
        header.setObjectName("appHeader")
        header.setFixedHeight(60)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self.header_label = QLabel("Home")
        self.header_label.setObjectName("headerLabel")
        layout.addWidget(self.header_label)

        self.header_info = QLabel("Dashboard and package discovery")
        self.header_info.setObjectName("headerInfo")
        layout.addWidget(self.header_info)

        layout.addStretch()

        search_input = QLineEdit()
        search_input.setPlaceholderText("Quick search…")
        search_input.setFixedWidth(220)
        search_input.setFixedHeight(36)
        self.search_input = search_input
        layout.addWidget(search_input)

        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_dir = os.path.join(_BASE_DIR, "assets", "icons", "discover")
        refresh_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "refresh.svg"), 18))
        refresh_btn.setToolTip("Refresh")
        refresh_btn.clicked.connect(self.refresh_packages)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(28, 30, 36, 0.75);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(34, 36, 42, 0.85);
                border-color: rgba(255,255,255,0.12);
            }
        """)
        layout.addWidget(refresh_btn)

        return header

    def show_docker_install_dialog(self):
        """Show Docker container management dialog"""
        if not self.docker_manager:
            pass  # inlined
            self.docker_manager = DockerManager(self.log_signal, self.show_message, self.sources_layout, self)

        self.docker_manager.install_from_docker()

    def show_community_hub(self):
        """Show Community Hub for plugins and extensions"""
        try:
            # Switch to plugins view and show community tab
            self.switch_view("settings")
            # Wait a moment for the settings UI to load
            QTimer.singleShot(100, self.switch_to_community_tab)
        except Exception as e:
            self._show_message("Community Hub", f"Error opening community hub: {e}")

    def on_plugin_install_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.install_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Install error: {e}")

    def on_plugin_launch_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.launch_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Launch error: {e}")

    def on_plugin_uninstall_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.uninstall_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Uninstall error: {e}")

    def open_plugins_folder(self):
        try:
            folder = self.get_user_plugins_dir()
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
            subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._show_message("Plugins", f"Cannot open folder: {e}")

    def show_git_install_dialog(self):
        """Show Git repository installation dialog"""
        if not self.git_manager:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)

        self.git_manager.install_from_git()

    def show_help(self):
        """Show help dialog"""
        help_service.show_help(self, getattr(self, 'current_view', ''))

    def show_settings(self):
        self.switch_view("settings")

    def on_plugins_filter_changed(self, text, installed_only):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                cats = []
                try:
                    if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                        cats = self.plugins_sidebar.get_selected_categories()
                except Exception:
                    cats = []
                self.plugins_view.set_filter(text, installed_only, cats)
        except Exception:
            pass

    def create_packages_panel(self):
        panel = QWidget()
        self.packages_panel_layout = QVBoxLayout(panel)
        self.packages_panel_layout.setContentsMargins(12, 12, 12, 12)
        self.packages_panel_layout.setSpacing(12)

        # Toolbar
        self.toolbar_widget = QWidget()
        self.toolbar_layout = QVBoxLayout(self.toolbar_widget)
        self.toolbar_layout.setContentsMargins(0,0,0,0)
        # Keep toolbar fixed-height and top-aligned so it doesn't shift during loading
        try:
            self.toolbar_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.toolbar_widget, 0, Qt.AlignmentFlag.AlignTop)

        # Large search box for discover page
        self.large_search_box = LargeSearchBox()
        self.large_search_box.search_requested.connect(self.on_large_search_requested)
        # Explicit submit from large box (enter or button)
        try:
            self.large_search_box.search_submitted.connect(self.on_large_search_submitted)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.large_search_box)

        # Loading spinner widget
        self.loading_widget = LoadingSpinner(message="Checking for updates...")
        self.loading_widget.setVisible(False)  # Hidden by default

        # Cancel button for installation
        self.cancel_install_btn = QPushButton("Cancel Installation")
        self.cancel_install_btn.setMinimumHeight(36)
        self.cancel_install_btn.setVisible(False)
        self.cancel_install_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 50, 50, 0.15);
                color: #FF6B6B;
                border: 1px solid rgba(220, 50, 50, 0.3);
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 0.25);
                border-color: rgba(220, 50, 50, 0.5);
            }
        """)
        self.cancel_install_btn.clicked.connect(self.cancel_installation)

        # Container for loading widget and cancel button (centered both axes)
        self.loading_container = QWidget()
        self.loading_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        loading_layout = QVBoxLayout(self.loading_container)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        loading_layout.setSpacing(12)
        loading_layout.addStretch()  # Top stretch for vertical centering
        loading_layout.addWidget(self.loading_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        loading_layout.addWidget(self.cancel_install_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        loading_layout.addStretch()  # Bottom stretch for vertical centering
        self.loading_container.setVisible(False)

        self.packages_panel_layout.addWidget(self.loading_container, 1)
        self.no_results_widget = QFrame()
        nr_layout = QVBoxLayout(self.no_results_widget)
        nr_layout.setContentsMargins(0, 40, 0, 40)
        nr_layout.setSpacing(8)
        self.no_results_title = QLabel("No results found")
        self.no_results_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_title.setStyleSheet("color: #8B8D97; font-size: 18px; font-weight: 600; background: transparent;")
        self.no_results_desc = QLabel("")
        self.no_results_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_desc.setStyleSheet("color: #5C5E66; font-size: 13px; background: transparent;")
        nr_layout.addWidget(self.no_results_title)
        nr_layout.addWidget(self.no_results_desc)
        self.no_results_widget.setVisible(False)
        self.packages_panel_layout.addWidget(self.no_results_widget)

        # Settings container (hidden by default)
        self.settings_container = QScrollArea()
        self.settings_container.setWidgetResizable(True)
        self.settings_container.setVisible(False)
        self.settings_root = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_root)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(0)
        self.settings_container.setWidget(self.settings_root)
        self.settings_container.horizontalScrollBar().setVisible(False)
        self.packages_panel_layout.addWidget(self.settings_container, 1)

        # Plugins view placeholder — created lazily in switch_view("plugins")
        self.plugins_view = None

        # Container for table area + detail card side panel
        self.packages_content_area = QWidget()
        packages_content_layout = QHBoxLayout(self.packages_content_area)
        packages_content_layout.setContentsMargins(0, 0, 0, 0)
        packages_content_layout.setSpacing(12)

        # Left side: table + grid + load more
        self.packages_table_area = QWidget()
        table_area_layout = QVBoxLayout(self.packages_table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(8)

        # Packages Table
        self.package_table = QTableWidget()
        self.package_table.setColumnCount(5)
        self.package_table.setHorizontalHeaderLabels(
            ["", "Package Name", "Version", "New Version", "Source"]
        )
        self.package_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.package_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.verticalHeader().setVisible(False)
        self.package_table.setAlternatingRowColors(True)
        self.package_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.package_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.package_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.package_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.package_table.setShowGrid(False)
        self.package_table.setIconSize(QSize(20, 20))
        self.package_table.setWordWrap(True)
        self.package_table.verticalHeader().setDefaultSectionSize(56)
        table_area_layout.addWidget(self.package_table, 1)

        # Packages Grid View (hidden by default, toggled via toolbar button)
        self.packages_grid = PackagesGridView()
        self.packages_grid.setVisible(False)
        table_area_layout.addWidget(self.packages_grid, 1)

        self.load_more_btn = QPushButton("Load More Packages")
        self.load_more_btn.setObjectName("loadMoreBtn")
        self.load_more_btn.setMinimumHeight(44)
        self.load_more_btn.clicked.connect(self.load_more_packages)
        self.load_more_btn.setVisible(False)
        table_area_layout.addWidget(self.load_more_btn)

        packages_content_layout.addWidget(self.packages_table_area, 1)

        # Right side: detail card for selected package
        self.package_detail_card = PackageDetailCard()
        self.package_detail_card.install_requested.connect(self.install_from_detail)
        self.package_detail_card.update_requested.connect(self.update_from_detail)
        self.package_detail_card.uninstall_requested.connect(self.uninstall_from_detail)
        self.package_detail_card.check_updates_btn.clicked.connect(self._check_updates_for_detail)
        self.package_detail_card.updates_check_completed.connect(self._on_update_check_result)
        packages_content_layout.addWidget(self.package_detail_card, 0, Qt.AlignmentFlag.AlignRight)

        self.packages_panel_layout.addWidget(self.packages_content_area, 1)

        # Console toggle button (bottom-right)
        icon_dir = os.path.join(_BASE_DIR, "assets", "icons", "discover")
        self.console_toggle_btn = QPushButton()
        self.console_toggle_btn.setFixedSize(42, 42)
        self.console_toggle_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "terminal.svg"), 20))
        self.console_toggle_btn.setIconSize(QSize(20, 20))
        self.console_toggle_btn.setToolTip("Show Console")
        self.console_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.console_toggle_btn.clicked.connect(self.toggle_console)
        self.console_toggle_btn.setVisible(False)
        self.console_toggle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 42, 48, 0.95),
                    stop:1 rgba(28, 30, 36, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 21px;
                padding: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(50, 52, 58, 0.95),
                    stop:1 rgba(34, 36, 42, 0.95));
                border: 1px solid rgba(0, 191, 174, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 26, 0.95),
                    stop:1 rgba(24, 26, 32, 0.95));
                border: 1px solid rgba(0, 191, 174, 0.5);
            }
        """)
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(20)
        btn_shadow.setColor(QColor(0, 0, 0, 160))
        btn_shadow.setOffset(3, 4)
        self.console_toggle_btn.setGraphicsEffect(btn_shadow)
        self.packages_panel_layout.addWidget(self.console_toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Console Output
        self.console_label = QLabel("Console Output")
        self.console_label.setObjectName("sectionLabel")
        self.packages_panel_layout.addWidget(self.console_label)
        # Hidden by default; shown via the bottom-right toggle
        try:
            self.console_label.setVisible(False)
        except Exception:
            pass

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        try:
            self.console.document().setMaximumBlockCount(500)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.console)
        try:
            self.console.setVisible(False)
        except Exception:
            pass

        return panel

    def update_toolbar(self):
        # Clear existing toolbar — hide and remove all items
        def _clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    w = item.widget()
                    w.hide()
                    w.deleteLater()
                elif item.layout():
                    _clear_layout(item.layout())
                    item.layout().deleteLater()
        _clear_layout(self.toolbar_layout)

        self.discover_select_all_btn = None
        self.discover_install_btn = None
        self._grid_view_btn = None
        self._filter_btn = None
        self._install_file_btn = None
        self._bundle_btn = None
        self._bundle_select_all_btn = None
        self._bundle_sep1 = None
        self._bundle_remove_sel_btn = None
        self._bundle_clear_btn = None
        self._bundle_install_btn = None
        self._bundle_export_btn = None
        self._bundle_save_cloud_btn = None
        self._sudo_btn = None
        self._greeting_label = None

        if self.current_view == "updates":
            layout = QHBoxLayout()
            layout.setSpacing(12)

            btn_style = f"""
                QPushButton {{
                    background-color: rgba(28, 30, 36, 0.75);
                    color: #EDEDEF;
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 10px;
                    padding: 8px 18px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: rgba(34, 36, 42, 0.85);
                    border-color: rgba(255,255,255,0.12);
                }}
                QPushButton:pressed {{
                    background-color: rgba(38, 40, 48, 0.9);
                }}
            """

            select_all_btn = QPushButton("Select All")
            select_all_btn.setMinimumHeight(36)
            select_all_btn.setStyleSheet(btn_style)
            select_all_btn.clicked.connect(self.toggle_select_all)
            layout.addWidget(select_all_btn)

            update_btn = QPushButton("Update Selected")
            update_btn.setMinimumHeight(36)
            update_btn.setStyleSheet(btn_style)
            update_btn.clicked.connect(self.update_selected)
            layout.addWidget(update_btn)

            ignore_btn = QPushButton("Ignore Selected")
            ignore_btn.setMinimumHeight(36)
            ignore_btn.setStyleSheet(btn_style)
            ignore_btn.clicked.connect(self.ignore_selected)
            layout.addWidget(ignore_btn)

            manage_btn = QPushButton("Manage Ignored")
            manage_btn.setMinimumHeight(36)
            manage_btn.setStyleSheet(btn_style)
            manage_btn.clicked.connect(self.manage_ignored)
            layout.addWidget(manage_btn)

            layout.addStretch()
            self._add_right_toolbar_icons(layout, show_sudo=True)

            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "installed":
            layout = QHBoxLayout()
            layout.setSpacing(12)

            select_all_btn = QPushButton("Select All")
            select_all_btn.setMinimumHeight(36)
            select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
            """)
            select_all_btn.clicked.connect(self.toggle_select_all)
            layout.addWidget(select_all_btn)

            update_btn = QPushButton("Update Selected")
            update_btn.setMinimumHeight(36)
            update_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            update_btn.clicked.connect(self.update_selected)
            layout.addWidget(update_btn)

            uninstall_btn = QPushButton("Uninstall Selected")
            uninstall_btn.setMinimumHeight(36)
            uninstall_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            uninstall_btn.clicked.connect(self.uninstall_selected)
            layout.addWidget(uninstall_btn)

            layout.addStretch()
            self._add_right_toolbar_icons(layout, show_install_file=True, show_sudo=True)

            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "discover":
            layout = QHBoxLayout()
            layout.setSpacing(8)  # Tighter spacing

            self.discover_select_all_btn = QPushButton("Select All")
            self.discover_select_all_btn.setMinimumHeight(36)
            self.discover_select_all_btn.clicked.connect(self.toggle_select_all)
            self.discover_select_all_btn.setVisible(False)
            layout.addWidget(self.discover_select_all_btn)

            self.discover_install_btn = QPushButton("Install Selected")
            self.discover_install_btn.setMinimumHeight(36)
            self.discover_install_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                QPushButton:disabled { color: rgba(240, 240, 240, 0.3); border-color: rgba(240, 240, 240, 0.1); }
            """)
            self.discover_install_btn.clicked.connect(self.install_selected)
            self.discover_install_btn.setVisible(False)
            self.discover_install_btn.setEnabled(False)
            layout.addWidget(self.discover_install_btn)

            self._greeting_label = QLabel()
            self._greeting_label.setVisible(False)
            layout.addWidget(self._greeting_label)

            layout.addStretch()  # Push remaining buttons to the right

            self._add_right_toolbar_icons(layout, show_install_file=True, show_sudo=True)

            # Hide grid/filter/bundle/sudo until search results are shown
            if self._grid_view_btn:
                self._grid_view_btn.setVisible(False)
            if self._filter_btn:
                self._filter_btn.setVisible(False)
            if self._bundle_btn:
                self._bundle_btn.setVisible(False)
            if self._sudo_btn:
                self._sudo_btn.setVisible(False)

            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "plugins":
            layout = QHBoxLayout()
            layout.setSpacing(12)

            layout.addStretch()

            self._add_right_toolbar_icons(layout, show_bundle=False)

            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "bundles":
            layout = QHBoxLayout()
            layout.setSpacing(16)

            def _sep():
                s = QFrame()
                s.setFrameShape(QFrame.Shape.VLine)
                s.setStyleSheet("QFrame { color: rgba(255,255,255,0.08); }")
                s.setFixedWidth(1)
                return s

            # Group 1 — Select All
            self._bundle_select_all_btn = QPushButton("Select All")
            self._bundle_select_all_btn.setMinimumHeight(36)
            self._bundle_select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
            """)
            self._bundle_select_all_btn.clicked.connect(self.toggle_select_all)
            layout.addWidget(self._bundle_select_all_btn)
            self._bundle_sep1 = _sep()
            layout.addWidget(self._bundle_sep1)

            # Group 2 — Bundle operations
            grp2 = QHBoxLayout()
            grp2.setSpacing(6)

            self._bundle_install_btn = QPushButton("Install Bundle")
            self._bundle_install_btn.setMinimumHeight(36)
            self._bundle_install_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                QPushButton:disabled { color: #5C5E66; border-color: rgba(92, 94, 102, 0.3); }
                """
            )
            self._bundle_install_btn.clicked.connect(self.install_bundle)
            grp2.addWidget(self._bundle_install_btn)

            self._bundle_export_btn = QPushButton("Export Bundle")
            self._bundle_export_btn.setMinimumHeight(36)
            self._bundle_export_btn.setStyleSheet(self._bundle_install_btn.styleSheet())
            self._bundle_export_btn.clicked.connect(self.export_bundle)
            grp2.addWidget(self._bundle_export_btn)

            import_btn = QPushButton("Import Bundle")
            import_btn.setMinimumHeight(36)
            import_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
            """)
            import_btn.clicked.connect(self.import_bundle)
            grp2.addWidget(import_btn)

            self._bundle_remove_sel_btn = QPushButton("Remove Selected")
            self._bundle_remove_sel_btn.setMinimumHeight(36)
            self._bundle_remove_sel_btn.setStyleSheet(self._bundle_install_btn.styleSheet())
            self._bundle_remove_sel_btn.clicked.connect(self.remove_selected_from_bundle)
            grp2.addWidget(self._bundle_remove_sel_btn)

            self._bundle_clear_btn = QPushButton("Clear Bundle")
            self._bundle_clear_btn.setMinimumHeight(36)
            self._bundle_clear_btn.setStyleSheet(self._bundle_install_btn.styleSheet())
            self._bundle_clear_btn.clicked.connect(self.clear_bundle)
            grp2.addWidget(self._bundle_clear_btn)

            layout.addLayout(grp2)
            layout.addWidget(_sep())

            # Group 3 — Cloud
            cloud_style = """
                QPushButton {
                    background-color: transparent;
                    color: #00BFAE;
                    border: 1px solid rgba(0, 191, 174, 0.5);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(0, 191, 174, 0.15);
                    border-color: #00BFAE;
                }
                QPushButton:pressed {
                    background-color: rgba(0, 191, 174, 0.25);
                }
            """

            grp3 = QHBoxLayout()
            grp3.setSpacing(6)

            self._bundle_save_cloud_btn = QPushButton("☁ Save to Cloud")
            self._bundle_save_cloud_btn.setMinimumHeight(36)
            self._bundle_save_cloud_btn.setStyleSheet(cloud_style + "QPushButton:disabled { color: #5C5E66; border-color: rgba(92, 94, 102, 0.3); }")
            self._bundle_save_cloud_btn.clicked.connect(self._cloud_save_favourites)
            self._bundle_save_cloud_btn.setToolTip("Upload bundle items to cloud (replace remote)")
            grp3.addWidget(self._bundle_save_cloud_btn)

            load_cloud_btn = QPushButton("☁ Load from Cloud")
            load_cloud_btn.setMinimumHeight(36)
            load_cloud_btn.setStyleSheet(cloud_style)
            load_cloud_btn.clicked.connect(self._cloud_sync_favourites)
            load_cloud_btn.setToolTip("Download bundle items from cloud (replace local)")
            grp3.addWidget(load_cloud_btn)

            layout.addLayout(grp3)

            layout.addStretch()
            self._add_right_toolbar_icons(layout, show_bundle=False, show_grid_filter=False)
            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "settings":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            layout.addStretch()
            self._add_right_toolbar_icons(layout, show_bundle=False)
            self.toolbar_layout.addLayout(layout)

    def show_welcome_animation(self):
        """Display a welcome animation in the console when the app first opens"""
        welcome_messages = [
            "🌟 Welcome to NeoArch Package Manager!",
            "🚀 Ready to elevate your Arch experience",
            "📦 Search, install, and manage packages with ease",
            "⚡ Multi-repo support: pacman, AUR, Flatpak & npm",
            "🔍 Start by searching for packages above"
        ]

        self.welcome_index = 0

        def animate_next_message():
            if self.welcome_index < len(welcome_messages):
                self.log(welcome_messages[self.welcome_index])
                self.welcome_index += 1
                QTimer.singleShot(800, animate_next_message)  # 800ms delay between messages
            else:
                # Clear the console after the animation completes
                QTimer.singleShot(2000, lambda: self.console.clear())  # Wait 2 seconds then clear

        # Start the animation
        animate_next_message()

    def switch_view(self, view_id, load=True):
        self.current_view = view_id
        try:
            _installing = getattr(self, "_installing", False) or hasattr(self, 'install_cancel_event')
        except Exception:
            _installing = False
        if not _installing:
            self.console.clear()
        # Stop any spinners and cancel background loads when switching views
        try:
            self.loading_widget.stop_animation()
            self.loading_widget.setVisible(False)
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
            self.cancel_install_btn.setVisible(False)
            self.settings_container.setVisible(False)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.setVisible(False)
            # plugins_tab_widget removed - plugins_view is handled above
            if hasattr(self, 'no_results_widget'):
                self.no_results_widget.setVisible(False)
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(False)
        except Exception:
            pass
        # Restore packages content area visibility (hidden by plugins/settings)
        if hasattr(self, 'packages_content_area'):
            self.packages_content_area.setVisible(True)
        # Restore toolbar visibility (hidden by settings)
        if hasattr(self, 'toolbar_widget'):
            self.toolbar_widget.setVisible(True)
        # Clear detail card
        if hasattr(self, 'package_detail_card'):
            self.package_detail_card.clear()
        # Cancel ongoing non-install tasks
        self.cancel_update_load = True
        self.cancel_discover_search = True
        # Tag the current view as the active loading context
        self.loading_context = view_id

        # Update button states
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == view_id)

        # Update header
        headers = {
            "updates": (os.path.join(_BASE_DIR, "assets", "icons", "discover", "update12.svg"), "Software Updates", ""),
            "installed": (os.path.join(_BASE_DIR, "assets", "icons", "discover", "installed.svg"), "Installed Packages", ""),
            "discover": (os.path.join(_BASE_DIR, "assets", "icons", "discover", "search.svg"), "Home", "Dashboard and package discovery"),
            "plugins": (os.path.join(_BASE_DIR, "assets", "icons", "plugins.svg"), "Sources & Plugins", "Manage package sources and extensions"),
            "bundles": (os.path.join(_BASE_DIR, "assets", "icons", "local-builds.svg"), "Bundles", "Create, import, export, and install bundles of packages"),
            "settings": (os.path.join(_BASE_DIR, "assets", "icons", "settings.svg"), "Settings", "Configure NeoArch settings"),
        }

        header_data = headers.get(view_id, ("NeoArch", ""))
        if len(header_data) == 3:
            _, title, subtitle = header_data
        else:
            title, subtitle = header_data
        self.header_label.setText(title)
        self.header_info.setText(subtitle)
        # Update dynamic counts if on updates/installed
        if view_id == "updates":
            QTimer.singleShot(0, self.update_updates_header_counts)
        elif view_id == "installed":
            QTimer.singleShot(0, self.update_installed_header_counts)

        self.update_table_columns(view_id)
        self.update_filters_panel(view_id)
        self.update_toolbar()
        self.search_input.clear()
        if view_id != "discover":
            self.large_search_box.setVisible(False)

        # Show filters panel for all views except settings and bundles
        if hasattr(self, 'filters_panel'):
            self.filters_panel.setVisible(view_id not in ("settings", "bundles"))

        # Update greeting in navbar
        self._update_nav_greeting(getattr(self, '_cloud_auth', None).user if hasattr(self, '_cloud_auth') and self._cloud_auth else None)

        # Reset to table view for non-plugin sections
        if view_id != "plugins" and self._view_mode != "table":
            self._view_mode = "table"
            if hasattr(self, '_grid_view_btn') and self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(_BASE_DIR, "assets", "icons", "navbar", "view.svg"), 20))
                self._grid_view_btn.setToolTip("Grid View")

        # Load data for view
        if view_id == "updates":
            # Prepare UI for loading updates
            try:
                self.large_search_box.setVisible(False)
            except Exception:
                pass
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            if load:
                try:
                    self.loading_widget.set_message("Syncing package databases...")
                    self.loading_widget.setVisible(True)
                    self.loading_widget.start_animation()
                    if hasattr(self, 'loading_container'):
                        self.loading_container.setVisible(True)
                except Exception:
                    pass
                self._hide_all_package_views()
                self.load_updates()
        elif view_id == "installed":
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            try:
                self.loading_widget.set_message("Loading installed packages...")
                self.loading_widget.setVisible(True)
                self.loading_widget.start_animation()
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
            try:
                self._hide_all_package_views()
            except Exception:
                pass
            self.load_installed_packages()
        elif view_id == "discover":
            self.large_search_box.setVisible(True)
            self._hide_all_package_views()
            if hasattr(self, 'packages_content_area'):
                self.packages_content_area.setVisible(False)
            self.load_more_btn.setVisible(False)
            self.package_table.setRowCount(0)
            self.header_info.setText("Search and discover new packages to install")
            try:
                self.search_input.setPlaceholderText("Search for packages")
            except Exception:
                pass
            # Removed verbose log: self.log("Type a package name to search in AUR and official repositories")
            # Hide console in Discover view
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            try:
                _installing = getattr(self, "_installing", False) or hasattr(self, 'install_cancel_event')
            except Exception:
                _installing = False
            if _installing:
                try:
                    self.loading_widget.set_message("Installing packages...")
                    self.loading_widget.setVisible(True)
                    self.loading_widget.start_animation()
                    if hasattr(self, 'loading_container'):
                        self.loading_container.setVisible(True)
                except Exception:
                    pass
                try:
                    self.large_search_box.setVisible(False)
                    self._hide_all_package_views()
                except Exception:
                    pass
                try:
                    self.cancel_install_btn.setVisible(True)
                except Exception:
                    pass
        elif view_id == "bundles":
            self.package_table.setRowCount(0)
            self.header_info.setText("Create, import, export, and install bundles of packages across sources")
            self._show_active_view()
            self.load_more_btn.setVisible(False)
            try:
                self.search_input.setPlaceholderText("Search for packages")
            except Exception:
                pass
            # Show console in non-settings views
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            try:
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            QTimer.singleShot(0, self.refresh_bundles_table)
        elif view_id == "plugins":
            self._view_mode = "grid"
            if hasattr(self, '_grid_view_btn') and self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(_BASE_DIR, "assets", "icons", "navbar", "list.svg"), 20))
                self._grid_view_btn.setToolTip("List View")
            try:
                self.loading_widget.setVisible(False)
                self.loading_widget.stop_animation()
            except Exception:
                pass
            try:
                self.search_input.setPlaceholderText("Search extensions")
            except Exception:
                pass
            self.large_search_box.setVisible(False)
            self.settings_container.setVisible(False)
            self._hide_all_package_views()
            self.load_more_btn.setVisible(False)

            # Clear any existing source cards from sources_layout
            while self.sources_layout.count() > 1:
                item = self.sources_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()

            # Clear filters layout
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Update visibility like installed view
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)

            # Add source cards like installed section
            self.update_plugins_sources()

            # Hide packages content area (has stretch=1, would push plugins to bottom)
            if hasattr(self, 'packages_content_area'):
                self.packages_content_area.setVisible(False)

            # Lazy-create plugins view on first visit
            if self.plugins_view is None:
                from neoarch.frontend.components.plugins_view import PluginsView
                self.plugins_view = PluginsView(self, self.get_svg_icon)
                self.plugins_view.install_requested.connect(self.on_plugin_install_requested)
                self.plugins_view.launch_requested.connect(self.on_plugin_launch_requested)
                try:
                    self.plugins_view.uninstall_requested.connect(self.on_plugin_uninstall_requested)
                except Exception:
                    pass
                self.packages_panel_layout.insertWidget(5, self.plugins_view, 1)
            try:
                self.plugins_view.setVisible(True)
            except Exception:
                pass
            self.plugins_view.refresh_all()

            self.header_info.setText("Install and launch extensions like BleachBit and Timeshift")
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
        elif view_id == "settings":
            # Show settings panel, hide package table & search
            try:
                self.loading_widget.setVisible(False)
                self.loading_widget.stop_animation()
            except Exception:
                pass
            self.large_search_box.setVisible(False)
            self._hide_all_package_views()
            self.load_more_btn.setVisible(False)
            self.settings_container.setVisible(True)
            # Hide toolbar (grid view, filter, actions — none apply to settings)
            if hasattr(self, 'toolbar_widget'):
                self.toolbar_widget.setVisible(False)
            # Hide packages content area (has stretch=1, would push settings to bottom)
            if hasattr(self, 'packages_content_area'):
                self.packages_content_area.setVisible(False)

            # Retain source checkboxes; no clearing needed

            # Clear filters layout
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Hide sources and filters sections in settings view
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)

            # Hide console in Settings view
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            self.header_info.setText("Configure NeoArch settings and plugins")
            QTimer.singleShot(0, self.build_settings_ui)
        # Notify plugins about view change
        try:
            self.run_plugin_hook('on_view_changed', view_id)
        except Exception:
            pass
        # Other views: ensure console visible (not in settings/plugins/discover)
        if view_id in ("",):
            try:
                self.console_label.setVisible(True)
                self.console.setVisible(True)
            except Exception:
                pass

    def _apply_common_table_style(self):
        self.package_table.setShowGrid(False)
        self.package_table.setIconSize(QSize(20, 20))
        self.package_table.setWordWrap(True)
        self.package_table.verticalHeader().setDefaultSectionSize(56)
        self.package_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def update_table_columns(self, view_id):
        self._apply_common_table_style()
        if view_id == "installed":
            self.package_table.setColumnCount(5)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Version", "Source", "Status"])
            self.package_table.setObjectName("")
            self.package_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.package_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.package_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            self.package_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.package_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 140)
            self.package_table.setColumnWidth(3, 120)
            self.package_table.setColumnWidth(4, 120)
        elif view_id == "bundles":
            self.package_table.setColumnCount(4)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Version", "Source"])
            self.package_table.setObjectName("bundlesTable")
            header = self.package_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 140)
            self.package_table.setColumnWidth(3, 120)
        elif view_id == "discover":
            self.package_table.setColumnCount(4)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Version", "Source"])
            self.package_table.setObjectName("discoverTable")
            header = self.package_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 140)
            self.package_table.setColumnWidth(3, 120)
        else:
            self.package_table.setColumnCount(5)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Version", "New Version", "Source"])
            self.package_table.setObjectName("")
            header = self.package_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 140)
            self.package_table.setColumnWidth(3, 140)
            self.package_table.setColumnWidth(4, 120)

    def load_updates(self):
        return packages_service.load_updates(self)

    def load_installed_packages(self):
        return packages_service.load_installed_packages(self)

    def on_packages_loaded(self, packages):
        # Ignore results if user has navigated away from the originating view
        if self.loading_context != self.current_view or self.current_view not in ("updates", "installed"):
            return
        self.all_packages = packages
        if self.current_view == "updates":
            self.updates_all = packages
        elif self.current_view == "installed":
            self.installed_all = packages
        self.current_page = 0
        self.packages_per_page = 10
        self.package_table.setRowCount(0)
        self.display_page()
        if self.current_view == "updates" and hasattr(self, 'source_card') and self.source_card:
            try:
                states = self.source_card.get_selected_sources()
                self.on_updates_source_changed(states)
            except Exception:
                pass
        elif self.current_view == "installed" and hasattr(self, 'source_card') and self.source_card:
            try:
                states = self.source_card.get_selected_sources()
                self.on_installed_source_changed(states)
            except Exception:
                pass


        # Hide loading spinner, stop animation, and show packages
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        self._show_active_view()
        # Show console toggle button for updates view like Discover
        try:
            if self.current_view in ("updates", "installed") and hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
                self.console_toggle_btn.setToolTip("Show Console")
        except Exception:
            pass
        # Update counts and nav badge
        if self.current_view == "updates":
            try:
                self.set_updates_count(len(self.updates_all or []))
            except Exception:
                pass
            self.update_updates_header_counts()
        elif self.current_view == "installed":
            self.update_installed_header_counts()

    def on_load_error(self):
        # Hide loading spinner, stop animation, and show packages table (empty)
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        self._show_active_view()
        try:
            if self.current_view in ("updates", "installed") and hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
                self.console_toggle_btn.setToolTip("Show Console")
        except Exception:
            pass
        self.log("Failed to load packages. Please check the logs for details.")

    def on_installation_progress(self, status, can_cancel):
        if status == "start":
            try:
                self._installing = True
            except Exception:
                pass
            self.load_more_btn.setVisible(False)
            self.loading_widget.set_message("Installing packages...")
            self.loading_widget.set_progress(-1)
            self.loading_widget.setVisible(True)
            self.loading_widget.start_animation()
            try:
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
            try:
                if hasattr(self, 'large_search_box'):
                    self.large_search_box.setVisible(False)
            except Exception:
                pass
            try:
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
            except Exception:
                pass
            try:
                self._hide_all_package_views()
            except Exception:
                pass
            # Keep console accessible via toggle, but hide the panel by default
            try:
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            self.cancel_install_btn.setVisible(can_cancel)
        elif status == "success":
            try:
                self._installing = False
            except Exception:
                pass
            self._install_succeeded = True
            self.loading_widget.set_message("Success")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly to show success, then hide
            QTimer.singleShot(1500, lambda: self.finish_installation_progress())
        elif status == "failed":
            try:
                self._installing = False
            except Exception:
                pass
            installed = getattr(self, '_installed_packages', None) or {}
            if installed:
                self._install_succeeded = True
                self.loading_widget.set_message("Install partially completed")
            else:
                self.loading_widget.set_message("Install failed")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly, then hide
            QTimer.singleShot(2000, lambda: self.finish_installation_progress())
        elif status == "cancelled":
            try:
                self._installing = False
            except Exception:
                pass
            self.loading_widget.set_message("Installation cancelled")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly to show cancellation, then hide
            QTimer.singleShot(1500, lambda: self.finish_installation_progress())

    def on_progress_update(self, message, percent):
        try:
            self.loading_widget.set_message(message)
            self.loading_widget.set_progress(percent)
        except Exception:
            pass

    def _show_operation_spinner(self, message):
        """Show loading spinner for an ongoing operation."""
        self._hide_all_package_views()
        self.load_more_btn.setVisible(False)
        self.loading_widget.set_message(message)
        self.loading_widget.set_progress(-1)
        self.loading_widget.setVisible(True)
        self.loading_widget.start_animation()
        self.loading_container.setVisible(True)
        try:
            self.large_search_box.setVisible(False)
            self.no_results_widget.setVisible(False)
        except Exception:
            pass

    def finish_installation_progress(self):
        try:
            self._installing = False
        except Exception:
            pass
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        self.loading_widget.hide_progress()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        try:
            self._show_active_view()
        except Exception:
            pass
        self.update_load_more_visibility()
        if self.current_view == "discover":
            installed = getattr(self, '_installed_packages', None)
            if not installed:
                installed = getattr(self, '_pending_install_packages', None)
            if installed and self.installed_index is not None:
                if self.installed_index is None:
                    self.installed_index = {}
                for source, pkgs in installed.items():
                    self.installed_index.setdefault(source, set()).update(pkgs)
                self._mark_installed_in_visible_rows()
            self._pending_install_packages = None
            self._installed_packages = None
            self._install_succeeded = False

    def update_load_more_visibility(self):
        if self.current_view == "discover":
            if hasattr(self, 'filtered_results') and self.filtered_results:
                total = len(self.filtered_results)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)
        elif self.current_view == "installed":
            if self.all_packages:
                total = len(self.all_packages)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)
        elif self.current_view == "updates":
            if self.all_packages:
                total = len(self.all_packages)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)

    def display_page(self):
        self.package_table.setUpdatesEnabled(False)
        start = self.current_page * self.packages_per_page
        end = start + self.packages_per_page
        page_packages = self.all_packages[start:end]

        for pkg in page_packages:
            if self.current_view == "installed":
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
            elif self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))

        self.package_table.setUpdatesEnabled(True)
        if self._view_mode == "grid":
            self._populate_grid()
        # Make sure nothing is selected by default
        try:
            self.package_table.clearSelection()
        except Exception:
            pass

        has_more = end < len(self.all_packages)
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = len(self.all_packages) - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        # Keep header subtitle accurate for Updates
        if self.current_view == "updates":
            self.update_updates_header_counts()

    def load_more_packages(self):
        self.current_page += 1
        start = self.current_page * self.packages_per_page
        end = start + self.packages_per_page

        if self.current_view == "discover":
            dataset = self.get_filtered_discover_results()
            if self.installed_index is None:
                try:
                    ss = self.source_card.get_selected_sources() if hasattr(self, 'source_card') and self.source_card else None
                except Exception:
                    ss = None
                self._ensure_installed_index_async(ss)
        else:
            dataset = self.search_results if self.search_results else self.all_packages

        page_packages = dataset[start:end]
        total = len(dataset)

        self.package_table.setUpdatesEnabled(False)
        for pkg in page_packages:
            if self.current_view == "installed":
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
            elif self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))
        self.package_table.setUpdatesEnabled(True)
        if self._view_mode == "grid":
            self._populate_grid()

        has_more = end < total
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = total - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        else:
            self.log("All results loaded")

        # Uncheck the newly loaded items
        old_count = self.package_table.rowCount() - len(page_packages)
        for i in range(old_count, self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(i)
            if checkbox is not None:
                checkbox.setChecked(False)

    def add_discover_row(self, pkg):
        row = self.package_table.rowCount()
        self.package_table.insertRow(row)

        checkbox = QCheckBox()
        checkbox.setObjectName("tableCheckbox")
        checkbox.setChecked(False)
        self.apply_checkbox_accent(checkbox, pkg.get('source', ''))
        cb_container = QWidget()
        cb_container.setStyleSheet("background: transparent;")
        cb_layout = QHBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.addStretch()
        cb_layout.addWidget(checkbox)
        cb_layout.addStretch()
        self.package_table.setCellWidget(row, 0, cb_container)
        checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))

        name_item = QTableWidgetItem(pkg['name'])
        name_item.setToolTip(pkg['name'])
        name_item.setData(Qt.ItemDataRole.UserRole, pkg)
        name_item.setIcon(self._discover_name_icon)
        self.package_table.setItem(row, 1, name_item)
        ver_item = QTableWidgetItem(pkg['version'])
        ver_item.setIcon(self._discover_version_icon)
        self.package_table.setItem(row, 2, ver_item)
        source_chip = QWidget()
        source_chip.setObjectName("sourceChip")
        chip_layout = QHBoxLayout(source_chip)
        chip_layout.setContentsMargins(6, 2, 6, 2)
        chip_layout.setSpacing(6)
        chip_icon = QLabel()
        source_icon = self.get_source_icon(pkg.get('source', ''), 16)
        if not source_icon.isNull():
            chip_icon.setPixmap(source_icon.pixmap(16, 16))
        chip_layout.addWidget(chip_icon)
        chip_text = QLabel(pkg.get('source', ''))
        chip_layout.addWidget(chip_text)
        self.package_table.setCellWidget(row, 3, source_chip)
        try:
            installed = self.is_package_installed(pkg)
        except Exception:
            installed = False
        if installed:
            green = QColor(16, 185, 129)
            name_item.setForeground(green)
            ver_item.setForeground(green)
            tip = "Already installed"
            name_item.setToolTip(tip)
            ver_item.setToolTip(tip)
            try:
                chip_text.setStyleSheet("color: rgb(16,185,129);")
                source_chip.setToolTip(tip)
            except Exception:
                pass
            try:
                checkbox.setEnabled(False)
                checkbox.setToolTip(tip)
            except Exception:
                pass

    def add_package_row(self, name, pkg_id, version, new_version, source, pkg_data=None):
        row = self.package_table.rowCount()
        self.package_table.insertRow(row)

        checkbox = QCheckBox()
        checkbox.setObjectName("tableCheckbox")
        # Always start unchecked in all views
        checkbox.setChecked(False)
        self.apply_checkbox_accent(checkbox, source if source else "")
        cb_container = QWidget()
        cb_container.setStyleSheet("background: transparent;")
        cb_layout = QHBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.addStretch()
        cb_layout.addWidget(checkbox)
        cb_layout.addStretch()
        self.package_table.setCellWidget(row, 0, cb_container)
        checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))

        name_item = QTableWidgetItem(name)
        name_item.setIcon(self._discover_name_icon)
        if pkg_data:
            name_item.setData(Qt.ItemDataRole.UserRole, pkg_data)
        self.package_table.setItem(row, 1, name_item)
        ver_item = QTableWidgetItem(version)
        ver_item.setIcon(self._discover_version_icon)
        self.package_table.setItem(row, 2, ver_item)

        if self.current_view == "installed" and pkg_data:
            self.package_table.setItem(row, 3, QTableWidgetItem(pkg_data.get('source', 'pacman')))
            status = "⬆️ Update available" if pkg_data.get('has_update') else "✓ Up to date"
            status_item = QTableWidgetItem(status)
            if pkg_data.get('has_update'):
                status_item.setForeground(QColor(255, 165, 0))
            else:
                status_item.setForeground(QColor(16, 185, 129))
            self.package_table.setItem(row, 4, status_item)
        elif self.package_table.columnCount() > 3:
            new_version_item = QTableWidgetItem(new_version)
            if self.current_view == "updates":
                new_version_item.setForeground(QColor(16, 185, 129))
            self.package_table.setItem(row, 3, new_version_item)
            self.package_table.setItem(row, 4, QTableWidgetItem(source))

    def refresh_packages(self):
        if self.current_view == "updates":
            self.load_updates()
        elif self.current_view == "installed":
            self.load_installed_packages()
        elif self.current_view == "discover":
            query = self.search_input.text().strip()
            if query:
                self.search_discover_packages(query)
            else:
                self.package_table.setRowCount(0)

    def get_source_text(self, row, view_id=None):
        vid = view_id or self.current_view
        try:
            if vid in ("discover", "bundles"):
                cell = self.package_table.cellWidget(row, 3)
                if cell:
                    labels = cell.findChildren(QLabel)
                    if labels:
                        return labels[-1].text()
                return ""
            elif vid == "updates":
                itm = self.package_table.item(row, 4)
                return itm.text() if itm else ""
            elif vid == "installed":
                itm = self.package_table.item(row, 3)
                return itm.text() if itm else ""
        except Exception:
            return ""
        return ""

    def get_row_info(self, row, view_id=None):
        vid = view_id or self.current_view
        name_item = self.package_table.item(row, 1)
        version_item = self.package_table.item(row, 2)
        name = name_item.text().strip() if name_item else ""
        version = version_item.text().strip() if version_item else ""
        source = self.get_source_text(row, vid)
        return {"name": name, "id": name, "version": version, "source": source}

    def on_selection_changed(self):
        if self._updating_selection:
            return
        self._updating_selection = True
        selected_rows = set(index.row() for index in self.package_table.selectionModel().selectedRows())
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None:
                checkbox.blockSignals(True)
                checkbox.setChecked(row in selected_rows)
                checkbox.blockSignals(False)
        self._updating_selection = False

        if len(selected_rows) == 1:
            row = next(iter(selected_rows))
            self._show_detail_for_row(row)
        else:
            self.package_detail_card.clear()

        self._update_discover_install_btn_state()

    def _show_detail_for_row(self, row):
        try:
            name_item = self.package_table.item(row, 1)
            ver_item = self.package_table.item(row, 2)
            if not name_item:
                self.package_detail_card.clear()
                return

            stored = name_item.data(Qt.ItemDataRole.UserRole) or {}
            name = name_item.text().strip()
            version = ver_item.text().strip() if ver_item else ''

            source = self.get_source_text(row)
            new_version = ''
            has_update = False
            installed = False
            description = stored.get('description', '')

            if self.current_view == "installed":
                source_item = self.package_table.item(row, 3)
                source = source_item.text() if source_item else 'pacman'
                status_item = self.package_table.item(row, 4)
                if status_item:
                    has_update = 'Update' in status_item.text()
                installed = True
            elif self.current_view == "updates":
                source_item = self.package_table.item(row, 4)
                source = source_item.text() if source_item else 'pacman'
                nv_item = self.package_table.item(row, 3)
                new_version = nv_item.text().strip() if nv_item else ''
                has_update = True
                installed = True
            else:
                source = self.get_source_text(row, 'discover')
                pkg = {'name': name, 'id': name, 'source': source}
                installed = self.is_package_installed(pkg)

            pkg_data = {
                'name': name,
                'id': stored.get('id', name),
                'version': version,
                'new_version': new_version,
                'source': source,
                'installed': installed,
                'has_update': has_update,
                'description': description,
                '_view': self.current_view,
            }
            self.package_detail_card.show_package(pkg_data)
        except Exception:
            self.package_detail_card.clear()

    def _check_updates_for_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        source = pkg.get('source', '')
        name = (pkg.get('id') or '').strip() if source == 'Flatpak' else (pkg.get('name') or '').strip()
        if not name:
            return

        self.package_detail_card.check_updates_btn.setText("Checking...")
        self.package_detail_card.check_updates_btn.setEnabled(False)

        card = self.package_detail_card

        def _run():
            has_updates = False
            new_ver = ''
            check_ok = False
            try:
                if source == 'Flatpak':
                    r = subprocess.run(
                        ["flatpak", "remote-ls", "--updates", name],
                        capture_output=True, text=True, timeout=30
                    )
                    check_ok = True
                    has_updates = r.returncode == 0 and bool(r.stdout.strip())
                    if has_updates and r.stdout.strip():
                        parts = r.stdout.strip().split('\t')
                        if len(parts) >= 2:
                            new_ver = parts[1]
                else:
                    r = subprocess.run(
                        ["pacman", "-Qu", name],
                        capture_output=True, text=True, timeout=30
                    )
                    check_ok = True
                    has_updates = r.returncode == 0 and bool(r.stdout.strip())
                    if has_updates and r.stdout.strip():
                        parts = r.stdout.strip().split()
                        if len(parts) >= 2:
                            new_ver = parts[1]
            except Exception:
                pass

            card.updates_check_completed.emit(name, new_ver, has_updates, check_ok)

        Thread(target=_run, daemon=True).start()

    def _on_update_check_result(self, name, new_version, has_updates, check_ok):
        try:
            pkg_data = getattr(self.package_detail_card, '_pkg_data', None)
            if not pkg_data or pkg_data.get('name') != name:
                return
            if has_updates:
                pkg_data['has_update'] = True
                pkg_data['new_version'] = new_version
                pkg_data['installed'] = True
                self.package_detail_card.show_package(pkg_data)
            elif check_ok:
                self.package_detail_card.check_updates_btn.setVisible(False)
                self.package_detail_card.up_to_date_label.setVisible(True)
            else:
                self.package_detail_card.check_updates_btn.setText("Check Failed")
                self.package_detail_card.check_updates_btn.setEnabled(True)
        except Exception:
            self.package_detail_card.check_updates_btn.setText("Check for Updates")
            self.package_detail_card.check_updates_btn.setEnabled(True)

    def _update_discover_install_btn_state(self):
        if not hasattr(self, 'discover_install_btn') or self.discover_install_btn is None:
            return
        has_checked = False
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked() and checkbox.isEnabled():
                has_checked = True
                break
        self.discover_install_btn.setEnabled(has_checked)

    def on_checkbox_changed(self, row, state):
        if self._updating_selection:
            return
        self._updating_selection = True
        sel_model = self.package_table.selectionModel()
        idx = self.package_table.model().index(row, 0)
        if state == Qt.CheckState.Checked.value:
            sel_model.select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        else:
            sel_model.select(idx, QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows)

        selected_rows = set(index.row() for index in sel_model.selectedRows())
        if len(selected_rows) == 1 and row in selected_rows:
            self._show_detail_for_row(row)
        else:
            self.package_detail_card.clear()

        self._updating_selection = False
        self._update_discover_install_btn_state()

    def _show_message(self, title, text):
        self.log(f"{title}: {text}")

    def display_message(self, title, text):
        """Public method to show a message in the console"""
        self.log(f"{title}: {text}")

    def show_busy_pm_warning(self, details: str = "", retry_action=None):
        try:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Package Manager Busy")
            dlg.setText("Another package manager is running")
            dlg.setInformativeText("The package database is locked. Close other package tools (pacman, pamac, yay/paru) and retry.")
            if details:
                dlg.setDetailedText(details)
            if callable(retry_action):
                retry_btn = dlg.addButton("Retry", QMessageBox.ButtonRole.AcceptRole)
                dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                dlg.setDefaultButton(retry_btn)
                dlg.exec()
                if dlg.clickedButton() == retry_btn:
                    try:
                        retry_action()
                    except Exception:
                        pass
            else:
                dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
                dlg.exec()
        except Exception:
            pass

    def log(self, message):
        try:
            self.ui_call.emit(lambda: self.console.append(message))
        except Exception:
            pass

    def toggle_console(self):
        try:
            showing = self.console.isVisible()
        except Exception:
            showing = False
        new_state = not showing
        try:
            self.console.setVisible(new_state)
            self.console_label.setVisible(new_state)
        except Exception:
            pass

        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setToolTip("Hide Console" if new_state else "Show Console")
        except Exception:
            pass

        try:
            if hasattr(self, 'large_search_box') and hasattr(self.large_search_box, 'recent_activity'):
                self.large_search_box.recent_activity.setVisible(not new_state)
        except Exception:
            pass

    def _on_avatar_clicked(self):
        from PyQt6.QtWidgets import QMenu
        cm = getattr(self, '_cloud_auth', None)
        if cm and cm.is_logged_in:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1C1E24; color: #F3F4F6;
                    border: 1px solid #373A43; border-radius: 8px; padding: 4px;
                }
                QMenu::item { padding: 8px 16px; border-radius: 4px; }
                QMenu::item:selected { background-color: #00BFAE; color: #fff; }
            """)
            save_act = menu.addAction("Save Favourites to Cloud")
            save_act.triggered.connect(self._cloud_save_favourites)
            sync_act = menu.addAction("Load Favourites from Cloud")
            sync_act.triggered.connect(self._cloud_sync_favourites)
            menu.addSeparator()
            logout_act = menu.addAction("Sign Out")
            logout_act.triggered.connect(self._cloud_logout)
            menu.exec(self.user_avatar_btn.mapToGlobal(self.user_avatar_btn.rect().center()))
        else:
            self._cloud_login()

    def _cloud_login(self):
        from neoarch.backend.cloud_auth import CloudAuthManager
        cm = getattr(self, '_cloud_auth', None)
        if cm:
            cm.start_login()

    def _cloud_logout(self):
        from neoarch.backend.cloud_auth import CloudAuthManager
        cm = getattr(self, '_cloud_auth', None)
        if cm:
            cm.logout()
        self.user_avatar_label.setText("👤")

    def _cloud_ensure_login(self):
        cm = getattr(self, '_cloud_auth', None)
        if not cm or not cm.is_logged_in:
            self.log("Not signed in — open browser to log in")
            self._cloud_login()
            return False
        return True

    def _cloud_save_favourites(self):
        if not self._cloud_ensure_login():
            return
        cm = getattr(self, '_cloud_auth', None)
        if not self.bundle_items:
            ok = cm.delete_all_favorites()
            if ok:
                self.log("Cleared cloud favourites")
            else:
                self.log("Cloud: nothing to clear")
            return
        ok = cm.save_favorites("My Favourites", self.bundle_items)
        if ok:
            self.log(f"☁ Saved {len(self.bundle_items)} items to cloud")
        else:
            self.log("☁ Failed to save to cloud")

    def _cloud_sync_favourites(self):
        if not self._cloud_ensure_login():
            return
        cm = getattr(self, '_cloud_auth', None)
        faves = cm.get_favorites()
        if faves:
            self.bundle_items = list(faves)
            from neoarch.backend.services.bundle import refresh_bundles_table
            refresh_bundles_table(self)
            self.log(f"☁ Synced {len(faves)} items from cloud")
        else:
            self.log("☁ No cloud favourites found — bundle unchanged")

    def _make_circular_pixmap(self, pixmap, size=36):
        result = QPixmap(size, size)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        painter.drawPixmap(0, 0, scaled.copy(x, y, size, size))
        painter.end()
        return result

    def _load_avatar_image(self, url, name, size=36):
        try:
            try:
                import requests
                resp = requests.get(url, timeout=5, headers={"User-Agent": "NeoArch"})
                data = resp.content if resp.status_code == 200 else None
            except ImportError:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "NeoArch"})
                data = urllib.request.urlopen(req, timeout=5).read()

            if data:
                pixmap = QPixmap()
                if pixmap.loadFromData(data) and not pixmap.isNull():
                    circular = self._make_circular_pixmap(pixmap, size)
                    self.user_avatar_label.setPixmap(circular)
                    self.user_avatar_label.setStyleSheet("")
                    self.user_avatar_btn.setToolTip(f"Signed in as {name}")
                    return True
        except Exception:
            pass
        return False

    def update_user_avatar(self, user):
        size = 36
        self.user_avatar_label.setFixedSize(size, size)

        if user and user.avatar_url:
            if not self._load_avatar_image(user.avatar_url, user.name, size):
                initials = user.name[:2].upper() if user.name else "?"
                self.user_avatar_label.setText(initials)
                self.user_avatar_label.setStyleSheet(f"""
                    color: #00BFAE; font-weight: bold; font-size: 14px;
                    background-color: rgba(0,191,174,0.15);
                    border-radius: {size // 2}px;
                """)
                self.user_avatar_btn.setToolTip(f"Signed in as {user.name}")
        else:
            default = self.get_svg_icon(os.path.join(_BASE_DIR, "assets", "icons", "user.svg"), 20)
            if not default.isNull():
                self.user_avatar_label.setPixmap(default.pixmap(20, 20))
            else:
                self.user_avatar_label.setText("👤")
            self.user_avatar_label.setStyleSheet("")
            self.user_avatar_btn.setToolTip("Sign in to sync favourites")

    def show_about(self):
        help_service.show_about(self)

    def closeEvent(self, event):
        from neoarch.backend.session_auth import cleanup_session
        cleanup_session()
        super().closeEvent(event)
