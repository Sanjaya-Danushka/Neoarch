"""Filters and sources mixin for the main window."""

import os

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QCheckBox, QRadioButton, QScrollArea
from PyQt6.QtCore import Qt

from neoarch.resources.paths import PROJECT_ROOT
from neoarch.frontend.styles import Styles
from neoarch.frontend.components.source_card import SourceCard

from neoarch.frontend.components.plugins_sidebar import PluginsSidebar
from neoarch.backend.services import filter as filters_service
from neoarch.frontend.components.updates_table import classify_update, _parse_size, _parse_version

_BASE_DIR = str(PROJECT_ROOT)


def _fmt_size(b):
    try:
        mb = float(b) / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GiB"
        return f"{mb:.1f} MiB"
    except Exception:
        return ""


class _FiltersMixin:
    def _get_filter_names(self):
        if self.current_view == "installed":
            return ("Updates available",)
        if self.current_view == "updates":
            return ()
        return ("Available", "Installed")

    def _update_filter_btn_state(self):
        if not hasattr(self, '_filter_btn') or not self._filter_btn:
            return
        if self.current_view == "installed":
            states = getattr(self, '_installed_filter_states', {})
            all_on = not states.get("Updates available", False)
        elif hasattr(self, 'plugins_view') and self.plugins_view:
            states = getattr(self.plugins_view, '_current_filter_states', {})
            all_on = all(states.get(n, True) for n in ("Available", "Installed"))
        else:
            all_on = True
        if all_on:
            self._filter_btn.setStyleSheet(self._filter_btn.property("defaultStyle") or "")
        else:
            self._filter_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 191, 174, 0.2),
                        stop:1 rgba(0, 191, 174, 0.1));
                    border: 1px solid rgba(0, 191, 174, 0.35);
                    border-radius: 21px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 191, 174, 0.28),
                        stop:1 rgba(0, 191, 174, 0.15));
                    border: 1px solid rgba(0, 191, 174, 0.5);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 191, 174, 0.35),
                        stop:1 rgba(0, 191, 174, 0.2));
                    border: 1px solid rgba(0, 191, 174, 0.6);
                }
            """)

    def _make_toggle_icon(self, checked, size=18):
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
        from PyQt6.QtCore import Qt
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_h = 14
        track_y = (size - track_h) // 2
        knob_d = 12
        knob_y = track_y + 1
        pad = 2
        if checked:
            p.setBrush(QColor("#00BFAE"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, track_y, size, track_h, track_h // 2, track_h // 2)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(size - knob_d - pad, knob_y, knob_d, knob_d)
        else:
            p.setBrush(QColor(0, 0, 0, 0))
            p.setPen(QPen(QColor(100, 102, 110), 2))
            p.drawRoundedRect(1, track_y, size - 2, track_h, track_h // 2, track_h // 2)
            p.setBrush(QColor(80, 82, 90))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(pad, knob_y, knob_d, knob_d)
        p.end()
        from PyQt6.QtGui import QIcon
        return QIcon(pm)

    def show_category_filter(self):
        if not hasattr(self, '_filter_btn') or not self._filter_btn:
            return
        self._update_filter_btn_state()
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self._filter_btn)
        menu.setObjectName("filterTogglePopup")
        menu.setStyleSheet("""
            QMenu#filterTogglePopup {
                background-color: rgba(22, 23, 26, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 6px;
            }
            QMenu#filterTogglePopup::item {
                padding: 10px 14px;
                border-radius: 8px;
                margin: 1px 0;
                color: #EDEDEF;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
            }
            QMenu#filterTogglePopup::item:selected {
                background-color: rgba(255, 255, 255, 0.04);
                color: #FFFFFF;
            }
            QMenu#filterTogglePopup::icon {
                padding-right: 10px;
            }
        """)

        filter_names = self._get_filter_names()

        if self.current_view == "installed":
            if not hasattr(self, '_installed_filter_states'):
                self._installed_filter_states = {"Updates available": False}
            current = self._installed_filter_states
        elif hasattr(self, 'plugins_view') and self.plugins_view:
            current = getattr(self.plugins_view, '_current_filter_states', {})
        else:
            current = {}

        for name in filter_names:
            checked = current.get(name, True)
            action = menu.addAction(self._make_toggle_icon(checked), name)
            action.setCheckable(True)
            action.setChecked(checked)
            def make_handler(n):
                return lambda ch: self._on_filter_chip_toggled(n, ch)
            action.triggered.connect(make_handler(name))

        menu.exec(self._filter_btn.mapToGlobal(
            self._filter_btn.rect().bottomLeft()
        ))

    def _on_filter_chip_toggled(self, filter_name, checked):
        if self.current_view == "installed":
            if not hasattr(self, '_installed_filter_states'):
                self._installed_filter_states = {"Updates available": False}
            self._installed_filter_states[filter_name] = checked
            # Sync with the FilterCard in the left panel (block signals to avoid loop)
            if hasattr(self, 'filter_card') and self.filter_card:
                self.filter_card.blockSignals(True)
                self.filter_card.set_selected_filters(self._installed_filter_states)
                self.filter_card.blockSignals(False)
            self.apply_filters()
        elif hasattr(self, 'plugins_view') and self.plugins_view:
            states = getattr(self.plugins_view, '_current_filter_states', {})
            states[filter_name] = checked
            self.plugins_view.apply_filters(states)
        self._update_filter_btn_state()

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
        self.filters_panel.setMinimumWidth(260)
        self.filters_panel.setStyleSheet("""
            QFrame {
                background-color: #0C0C0E;
            }
        """)

        panel_layout = QVBoxLayout(self.filters_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        scroll = QScrollArea(self.filters_panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sources_section = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_section)
        self.sources_layout.setContentsMargins(12, 0, 12, 0)
        self.sources_layout.setSpacing(0)

        layout.addWidget(self.sources_section, 1)

        self.filters_section = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_section)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(8)

        layout.addWidget(self.filters_section)

        scroll.setWidget(container)
        panel_layout.addWidget(scroll)

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
            pass
        else:
            filter_options = []

        # Update visibility
        if view_id == "installed":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_installed_sources()
        elif view_id == "updates":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
        elif view_id == "discover":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_discover_sources()
        elif view_id == "bundles":
            # No source or status filters for bundles
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        elif view_id in ("git", "docker"):
            # No source or status filters for Git/Docker pages
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        elif view_id == "plugins":
            # Show a VS Code-like extensions sidebar in filters_section
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(True)
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
        else:
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)

    def on_filter_selection_changed(self, filter_states):
        """Handle changes in filter selection"""
        # Apply filtering based on current view
        if self.current_view == "installed":
            self._installed_filter_states = filter_states.copy()
            self._update_filter_btn_state()
            self.apply_filters()
        elif self.current_view == "updates":
            self._recompute_updates()
        elif self.current_view == "plugins":
            # Apply plugin status filters (Available/Installed)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.apply_filters(filter_states)

    def update_discover_sources(self):
        """Update the discover sources using the new SourceCard component"""
        # Clear existing sources layout
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
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
        self.source_card.configure_sections(show_search=True)

    def update_updates_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
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
        self.source_card.source_changed.connect(self.on_updates_source_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        self.source_card.search_mode_changed.connect(self._recompute_updates)
        self.source_card.status_filter_changed.connect(self._recompute_updates)
        self.source_card.sort_changed.connect(self._recompute_updates)
        self.source_card.set_action_callbacks(
            update_all=self.perform_update_all,
            ignore_selected=self.ignore_selected,
            manage_ignored=self.manage_ignored,
        )
        self.source_card.configure_sections(
            show_status=True, show_sort=True, show_actions=True,
            show_summary=True, show_search=True, show_counts=True,
        )
        try:
            self.source_card.on_source_changed()
        except Exception:
            pass
        self._refresh_updates_summary()
        self._recompute_updates()

    def update_installed_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
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
        self.sources_layout.addWidget(self.source_card)
        self.source_card.health_action.connect(self.on_installed_health_action)
        self.source_card.sort_changed.connect(self.apply_filters)
        self.source_card.configure_sections(
            show_search=False, show_health=True, show_counts=True, show_summary=True, show_sort=True,
        )
        self._refresh_installed_sources()
        self._refresh_installed_health_async()

    def on_installed_health_action(self, action):
        if action == "orphans":
            self.cleanup_orphans()
        elif action == "pacnew":
            self.manage_pacnew()
        elif action == "outdated":
            self.switch_view("updates")

    def _refresh_installed_sources(self):
        """Populate the installed source card: counts, distribution, health, summary."""
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'installed_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = 0
            per[s] += 1
        try:
            for name, item in self.source_card.sources.items():
                item.set_count(per.get(name, 0))
        except Exception:
            pass
        try:
            self.source_card.set_distribution(per)
        except Exception:
            pass
        outdated = sum(1 for p in base if p.get('has_update'))
        sizes = getattr(self, '_installed_sizes', None) or {}
        total_b = sum(sizes.values())
        size_text = f"{_fmt_size(total_b)} on disk" if total_b > 0 else ""
        try:
            self.source_card.set_health(
                orphans=len(getattr(self, '_orphans_list', None) or []),
                pacnew=len(getattr(self, '_pacnew_list', None) or []),
                outdated=outdated,
            )
        except Exception:
            pass
        try:
            self.source_card.set_summary(len(base), size_text, noun="packages installed")
        except Exception:
            pass

    def _refresh_installed_health_async(self):
        """Fetch orphans, .pacnew files, installed sizes, and explicit set in background."""
        try:
            def _run():
                try:
                    from neoarch.backend.services.hygiene import list_orphans, list_pacnew, list_installed_sizes, list_explicit_packages
                    orphans = list_orphans()
                    pacnew = list_pacnew()
                    sizes = list_installed_sizes()
                    explicit = list_explicit_packages()
                except Exception:
                    orphans, pacnew, sizes, explicit = [], [], {}, set()
                self.ui_call.emit(lambda: self._apply_installed_health(orphans, pacnew, sizes, explicit))
            from threading import Thread
            Thread(target=_run, daemon=True).start()
        except Exception:
            pass

    def _apply_installed_health(self, orphans, pacnew, sizes, explicit=None):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        self._orphans_list = orphans or []
        self._pacnew_list = pacnew or []
        self._installed_sizes = sizes or {}
        if explicit is not None:
            self._explicit_packages = explicit
        self._refresh_installed_sources()
        if explicit is not None:
            try:
                self.apply_filters()
            except Exception:
                pass

    def update_plugins_sources(self):
        """Update plugins sources using the same SourceCard component as installed section"""
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
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
        self.sources_layout.addWidget(self.source_card)
        self.source_card.configure_sections(show_search=False)

    def on_installed_source_changed(self, source_states):
        self.apply_filters()

    def on_plugins_source_changed(self, source_states):
        if hasattr(self, 'plugins_view') and self.plugins_view:
            self.plugins_view.apply_source_filters(source_states)

    def on_updates_source_changed(self, source_states):
        self._recompute_updates()

    def _pkg_status(self, pkg):
        try:
            return pkg.get("status") or classify_update(pkg.get("version"), pkg.get("new_version"))
        except Exception:
            return "Maintenance"

    def _matches_query(self, pkg, query, mode):
        name = (pkg.get('name') or '').lower()
        pid = (pkg.get('id') or pkg.get('name') or '').lower()
        if mode == 'name':
            return query in name
        if mode == 'id':
            return query in pid
        return query in name or query in pid

    def _sort_updates(self, dataset, field, asc):
        try:
            if field == 'size':
                def key(p): return _parse_size(p.get('download_size') or '')
            elif field == 'version':
                def key(p): return (_parse_version(p.get('version')), _parse_version(p.get('new_version')))
            elif field == 'status':
                def key(p): return classify_update(p.get('version'), p.get('new_version'))
            elif field == 'source':
                def key(p): return (p.get('source') or '').lower()
            else:
                def key(p): return (p.get('name') or '').lower()
            return sorted(dataset, key=key, reverse=not asc)
        except Exception:
            return dataset

    def _refresh_updates_summary(self):
        """Refresh per-source counts and the total size summary from updates_all."""
        if self.current_view != "updates" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'updates_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = [0, 0.0]
            per[s][0] += 1
            per[s][1] += _parse_size(pkg.get('download_size') or '')
        try:
            for name, item in self.source_card.sources.items():
                n, b = per.get(name, (0, 0.0))
                item.set_count(n, _fmt_size(b))
        except Exception:
            pass
        total_b = sum(per[s][1] for s in per)
        known = sum(1 for p in base if _parse_size(p.get('download_size') or '') > 0)
        size_text = ""
        if total_b > 0:
            prefix = "~" if known < len(base) else ""
            size_text = f"{prefix}{_fmt_size(total_b)}"
        try:
            self.source_card.set_summary(len(base), size_text)
        except Exception:
            pass

    def _recompute_updates(self):
        """Compose source, status, search, and sort filters for the updates view."""
        if self.current_view != "updates":
            return
        self._refresh_updates_summary()
        dataset = list(getattr(self, 'updates_all', None) or [])
        states = {}
        try:
            states = self.source_card.get_selected_sources()
        except Exception:
            states = {}
        if states:
            dataset = [p for p in dataset if states.get(p.get('source'), True)]
        try:
            active = self.source_card.get_active_statuses()
            dataset = [p for p in dataset if self._pkg_status(p) in active]
        except Exception:
            pass
        query = ""
        try:
            query = (self.search_input.text() or '').strip().lower()
        except Exception:
            pass
        if query:
            mode = 'both'
            try:
                mode = self.source_card.get_search_mode()
            except Exception:
                pass
            dataset = [p for p in dataset if self._matches_query(p, query, mode)]
        field, asc = 'name', True
        try:
            field = self.source_card.get_sort()
            asc = self.source_card.get_sort_asc()
        except Exception:
            pass
        dataset = self._sort_updates(dataset, field, asc)
        self.all_packages = dataset
        self.current_page = 0
        try:
            self.load_more_btn.setVisible(False)
        except Exception:
            pass
        try:
            col_map = {"name": 1, "size": 3, "version": 2, "status": 5, "source": 4}
            self.updates_table.sort_by_column(col_map.get(field, 1), asc)
        except Exception:
            pass
        if query:
            total = len(getattr(self, 'updates_all', None) or [])
            self.header_info.setText(
                f"{total} packages were found, {len(dataset)} of which match the specified filters")
        else:
            self.update_updates_header_counts()
        try:
            self._sync_updates_table(dataset)
        except Exception:
            pass

    def on_source_selection_changed(self, source_states):
        """Handle changes in source selection"""
        if self.current_view == "discover" and hasattr(self, 'search_results') and self.search_results:
            self.display_discover_results(selected_sources=source_states)

    def apply_filters(self):
        return filters_service.apply_filters(self)

    def apply_update_filters(self):
        return filters_service.apply_update_filters(self)
