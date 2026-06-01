"""Filters and sources mixin for the main window."""

import os

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QCheckBox, QRadioButton

from neoarch.resources.paths import PROJECT_ROOT
from neoarch.frontend.styles import Styles
from neoarch.frontend.components.source_card import SourceCard
from neoarch.frontend.components.filter_card import FilterCard
from neoarch.frontend.components.plugins_sidebar import PluginsSidebar
from neoarch.managers.git_manager import GitManager
from neoarch.managers.docker_manager import DockerManager
from neoarch.backend.services import filter as filters_service

_BASE_DIR = str(PROJECT_ROOT)


class _FiltersMixin:
    def show_category_filter(self):
        self.log("Category filter")

    def get_row_checkbox(self, row):
        cell = self.package_table.cellWidget(row, 0)
        if not cell:
            return None
        if isinstance(cell, QCheckBox):
            return cell
        try:
            chks = cell.findChildren(QCheckBox)
            return chks[0] if chks else None
        except Exception:
            return None

    def create_filters_panel(self):
        self.filters_panel = QFrame()
        self.filters_panel.setStyleSheet(Styles.get_filters_panel_stylesheet())

        layout = QVBoxLayout(self.filters_panel)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(10)

        self.sources_section = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_section)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setSpacing(6)

        self.sources_title_label = QLabel("Sources")
        self.sources_title_label.setObjectName("sectionLabel")
        self.sources_title_label.setStyleSheet("""
            QLabel#sectionLabel {
                color: #8B8D97;
                font-size: 10px;
                font-weight: 500;
                padding: 0 2px 2px 2px;
                background: transparent;
                border: none;
            }
        """)
        self.sources_layout.addWidget(self.sources_title_label)

        layout.addWidget(self.sources_section)

        self.filters_section = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_section)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(6)

        layout.addWidget(self.filters_section)
        layout.addStretch()

        return self.filters_panel

    def update_filters_panel(self, view_id):
        # Clear existing filters section
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Recreate filters based on view
        if view_id == "updates":
            self.update_updates_sources()
        elif view_id == "installed":
            # For installed view, filter by update status
            self.filter_card = FilterCard(self)
            self.filter_card.filter_changed.connect(self.on_filter_selection_changed)

            # Add status filters
            self.filter_card.add_filter("Updates available")
            self.filter_card.add_filter("Installed")

            self.filters_layout.addWidget(self.filter_card)
        else:
            filter_options = []

        # Update visibility
        if view_id == "installed":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            self.update_installed_sources()
        elif view_id == "updates":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        elif view_id == "discover":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            self.update_discover_sources()
        elif view_id == "bundles":
            # No source or status filters for bundles
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        elif view_id == "plugins":
            # Show a VS Code-like extensions sidebar in filters_section
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            # Clear and add PluginsSidebar
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            try:
                self.plugins_sidebar = PluginsSidebar(self)
                self.plugins_sidebar.filter_changed.connect(self.on_plugins_filter_changed)
                # Populate sidebar with the same list as cards
                try:
                    if hasattr(self, 'plugins_view') and self.plugins_view:
                        self.plugins_sidebar.set_plugins(self.plugins_view.plugins)
                        cats = sorted({(p.get('category') or '') for p in self.plugins_view.plugins if p.get('category')})
                        try:
                            self.plugins_sidebar.set_categories(cats)
                        except Exception:
                            pass
                except Exception:
                    pass
                # Allow install from sidebar
                try:
                    self.plugins_sidebar.install_requested.connect(self.on_plugin_install_requested)
                    self.plugins_sidebar.uninstall_requested.connect(self.on_plugin_uninstall_requested)
                except Exception:
                    pass
                self.filters_layout.addWidget(self.plugins_sidebar)
            except Exception:
                pass
        elif view_id == "settings":
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        else:
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(True)

    def on_filter_selection_changed(self, filter_states):
        """Handle changes in filter selection"""
        # Apply filtering based on current view
        if self.current_view == "installed":
            self.apply_filters()
        elif self.current_view == "updates":
            self.apply_update_filters()
        elif self.current_view == "plugins":
            # Apply plugin status filters (Available/Installed)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.apply_filters(filter_states)

    def update_discover_sources(self):
        """Update the discover sources using the new SourceCard component"""
        # Clear existing sources layout (except the title label)
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Always create a new SourceCard component
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_source_selection_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)

        # Add the four main sources (exclude Local from Discover)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg")),
        ]

        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)

        self.sources_layout.addWidget(self.source_card)
        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
        else:
            try:
                self.git_manager.create_git_section()
            except Exception:
                pass
        try:
            if not hasattr(self, 'docker_manager') or self.docker_manager is None:
                pass  # inlined
                self.docker_manager = DockerManager(self.log_signal, self.show_message, self.sources_layout, self)
            else:
                try:
                    self.docker_manager.sources_layout = self.sources_layout
                except Exception:
                    pass
                try:
                    self.docker_manager.create_docker_section()
                except Exception:
                    pass
        except Exception:
            pass

    def update_updates_sources(self):
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg")),
            ("Local", os.path.join(_BASE_DIR, "assets", "icons", "discover", "local.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
        else:
            try:
                self.git_manager.create_git_section()
            except Exception:
                pass
        self.source_card.source_changed.connect(self.on_updates_source_changed)
        try:
            self.source_card.on_source_changed()
        except Exception:
            pass

    def update_installed_sources(self):
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_installed_source_changed)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        try:
            for obj_name in ("searchModeTitle",):
                w = self.source_card.findChild(QLabel, obj_name)
                if w:
                    w.setVisible(False)
            for rb in self.source_card.findChildren(QRadioButton, "searchModeRadio"):
                rb.setVisible(False)
        except Exception:
            pass
        self.sources_layout.addWidget(self.source_card)

    def update_plugins_sources(self):
        """Update plugins sources using the same SourceCard component as installed section"""
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_plugins_source_changed)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        try:
            for obj_name in ("searchModeTitle",):
                w = self.source_card.findChild(QLabel, obj_name)
                if w:
                    w.setVisible(False)
            for rb in self.source_card.findChildren(QRadioButton, "searchModeRadio"):
                rb.setVisible(False)
        except Exception:
            pass
        self.sources_layout.addWidget(self.source_card)

    def on_installed_source_changed(self, source_states):
        self.apply_filters()

    def on_plugins_source_changed(self, source_states):
        if hasattr(self, 'plugins_view') and self.plugins_view:
            self.plugins_view.apply_source_filters(source_states)

    def on_updates_source_changed(self, source_states):
        base = getattr(self, 'updates_all', self.all_packages)
        show_pacman = source_states.get("pacman", True)
        show_aur = source_states.get("AUR", True)
        show_flatpak = source_states.get("Flatpak", True)
        show_npm = source_states.get("npm", True)
        show_local = source_states.get("Local", True)
        filtered = []
        for pkg in base:
            s = pkg.get('source')
            if s == 'pacman' and show_pacman:
                filtered.append(pkg)
            elif s == 'AUR' and show_aur:
                filtered.append(pkg)
            elif s == 'Flatpak' and show_flatpak:
                filtered.append(pkg)
            elif s == 'npm' and show_npm:
                filtered.append(pkg)
            elif s == 'Local' and show_local:
                filtered.append(pkg)
        self.all_packages = filtered
        self.current_page = 0
        self.package_table.setRowCount(0)
        self.display_page()
        self.update_load_more_visibility()
        self.update_updates_header_counts()

        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)

    def on_source_selection_changed(self, source_states):
        """Handle changes in source selection"""
        if self.current_view == "discover" and hasattr(self, 'search_results') and self.search_results:
            self.display_discover_results(selected_sources=source_states)

    def apply_filters(self):
        return filters_service.apply_filters(self)

    def apply_update_filters(self):
        return filters_service.apply_update_filters(self)
