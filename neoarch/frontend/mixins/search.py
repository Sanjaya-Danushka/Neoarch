"""Search/discover mixin for the main window."""

import os
import re
import json
import subprocess
from threading import Thread

from neoarch.backend.services.suggestions import index_ready, refresh_names_index, suggest_names
from neoarch.frontend.mixins.views import _SELF_CONTAINED_VIEWS
from neoarch.resources.paths import PROJECT_ROOT


def _parse_version(value):
    """Best-effort numeric parse of a version string for comparisons."""
    return [int(m) for m in re.findall(r"\d+", str(value))] or [0]


class _SearchMixin:
    def on_large_search_requested(self, query):
        """Handle search request from large search box"""
        # Handle special dashboard actions
        if query == "__UPDATE_ALL__":
            self.log("Update All triggered from dashboard")
            self.perform_update_all()
            return
        if query == "__REFRESH_DB__":
            self.log("Syncing package databases\u2026")
            try:
                env = self.get_askpass_env()
                subprocess.run(
                    ["sudo", "-A", "pacman", "-Sy", "--noconfirm"],
                    capture_output=True, text=True, timeout=120, env=env,
                )
                self.log("Package databases synced.")
            except Exception as e:
                self.log(f"Database sync failed: {e}")
            self.refresh_packages()
            return
        if query == "__CLEAN_CACHE__":
            self.log("Cleaning package cache\u2026")
            self.clean_cache()
            return

        try:
            self.search_input.blockSignals(True)
            self.search_input.setText(query)
        finally:
            try:
                self.search_input.blockSignals(False)
            except Exception:
                pass
        try:
            self.search_input.setFocus()
            self.search_input.setCursorPosition(len(query))
        except Exception:
            pass
        self.perform_search()

    def on_large_search_submitted(self, query):
        """Handle explicit submit from large search box (enter/button)"""
        try:
            self.search_input.blockSignals(True)
            self.search_input.setText(query)
        finally:
            try:
                self.search_input.blockSignals(False)
            except Exception:
                pass
        self.perform_search()
        try:
            self.search_input.setFocus()
            self.search_input.setCursorPosition(len(query))
        except Exception:
            pass

    def on_search_text_changed(self):
        try:
            if getattr(self, 'current_view', '') == "plugins":
                # Immediate filtering for Plugins for a responsive feel
                self.perform_search()
                return
        except Exception:
            pass
        self.search_timer.start()

    def perform_search(self):
        query = self.search_input.text().strip()
        # Plugins view: always filter regardless of text length
        if getattr(self, 'current_view', '') == "plugins":
            try:
                self._plugins_search_query = query
                self._apply_plugins_filters()
            except Exception:
                pass
            return

        if len(query) < 2:
            if self.current_view == "discover":
                self.cancel_discover_search = True
                self.loading_context = "idle"
                self.loading_widget.stop_animation()
                self.loading_widget.setVisible(False)
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(False)
                self.large_search_box.setVisible(True)
                self.large_search_box.clear()
                self._hide_all_package_views()
                if hasattr(self, 'packages_content_area'):
                    self.packages_content_area.setVisible(False)
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                try:
                    if hasattr(self, 'updates_table') and self.updates_table:
                        self.updates_table.set_discover_mode(False)
                except Exception:
                    pass
                self.header_info.setText("Search and discover new packages to install")
                install_btn = getattr(self, 'discover_install_btn', None)
                if install_btn is not None:
                    install_btn.setVisible(False)
                for attr in ('_grid_view_btn', '_bundle_btn', '_sudo_btn'):
                    tb = getattr(self, attr, None)
                    if tb is not None:
                        tb.setVisible(False)
                try:
                    if hasattr(self, 'source_card') and self.source_card:
                        self.source_card.clear_results()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'filters_panel') and self.filters_panel:
                        self.filters_panel.setVisible(False)
                except Exception:
                    pass
                self._update_nav_greeting(getattr(self, '_cloud_auth', None).user if hasattr(self, '_cloud_auth') and self._cloud_auth else None)
            elif self.current_view == "installed":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self.search_results = None
                self.apply_filters()
                self._show_active_view()
            elif self.current_view == "updates":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self._recompute_updates()
                self._show_active_view()
            return
        if self.current_view == "discover":
            self.large_search_box.setVisible(False)
            if hasattr(self, '_greeting_label') and self._greeting_label:
                self._greeting_label.setVisible(False)
            if hasattr(self, 'packages_content_area'):
                self.packages_content_area.setVisible(True)
            self._show_active_view()
            self.search_discover_packages(query)
        else:
            self.filter_packages()

    def toggle_view_mode(self):
        # Self-contained pages have no grid/list toggle (except plugins).
        if getattr(self, 'current_view', '') in _SELF_CONTAINED_VIEWS:
            return
        navbar_dir = os.path.join(str(PROJECT_ROOT), "assets", "icons", "navbar")
        if self._view_mode == "table":
            self._view_mode = "grid"
            if getattr(self, 'current_view', '') == "plugins":
                if hasattr(self, 'plugins_view') and self.plugins_view:
                    self.plugins_view.setVisible(True)
                    self.plugins_view.show_grid_mode()
                if hasattr(self, 'packages_content_area'):
                    self.packages_content_area.setVisible(False)
            elif self.current_view in ("updates", "installed", "discover") and hasattr(self, 'updates_table'):
                self.updates_table.setVisible(False)
                self.package_table.setVisible(False)
                self.packages_grid.setVisible(True)
            else:
                self.package_table.setVisible(False)
                self.packages_grid.setVisible(True)
            if self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(navbar_dir, "list.svg"), 20))
                self._grid_view_btn.setToolTip("List View")
            if self.current_view != "plugins":
                self._populate_grid()
        else:
            self._view_mode = "table"
            if getattr(self, 'current_view', '') == "plugins":
                if hasattr(self, 'plugins_view') and self.plugins_view:
                    self.plugins_view.setVisible(False)
                if hasattr(self, 'packages_content_area'):
                    self.packages_content_area.setVisible(True)
                if hasattr(self, 'updates_table'):
                    self._sync_plugins_table()
                    self.updates_table.setVisible(True)
            elif self.current_view in ("updates", "installed", "discover") and hasattr(self, 'updates_table'):
                self.packages_grid.setVisible(False)
                self.package_table.setVisible(False)
                self.updates_table.setVisible(True)
            else:
                self.packages_grid.setVisible(False)
                self.package_table.setVisible(True)
            if self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(navbar_dir, "view.svg"), 20))
                self._grid_view_btn.setToolTip("Grid View")

    def _populate_grid(self):
        # Self-contained pages own their own card grid; never touch the legacy one.
        if getattr(self, 'current_view', '') in _SELF_CONTAINED_VIEWS:
            return
        self.packages_grid.clear()
        dataset = self.all_packages
        if self.current_view == "discover":
            if hasattr(self, 'filtered_results') and self.filtered_results:
                dataset = self.filtered_results
            else:
                dataset = self.search_results
        if not dataset:
            return
        total = min(len(dataset), (self.current_page + 1) * self.packages_per_page)
        for i in range(total):
            self.packages_grid.add_package(dataset[i], i)
        self.packages_grid._relayout()

    def on_search_mode_changed(self, search_mode):
        """Handle changes in search mode"""
        self.current_search_mode = search_mode
        current_query = self.search_input.text().strip()
        if current_query and self.current_view == "discover":
            self.search_discover_packages(current_query)

    def on_discover_sort_changed(self, field):
        """Re-sort the cached Discover results without re-searching."""
        if self.current_view == "discover":
            self._refresh_discover_results()

    def on_discover_installed_filter_changed(self, hide):
        """Show/hide already-installed packages in the Discover results."""
        if self.current_view == "discover":
            self._refresh_discover_results()

    def filter_packages(self):
        query = self.search_input.text().lower()

        if not query:
            if self.current_view == "discover":
                self.cancel_discover_search = True
                self.loading_context = "idle"
                self.loading_widget.stop_animation()
                self.loading_widget.setVisible(False)
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(False)
                self.large_search_box.setVisible(True)
                self._hide_all_package_views()
                if hasattr(self, 'packages_content_area'):
                    self.packages_content_area.setVisible(False)
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                try:
                    if hasattr(self, 'updates_table') and self.updates_table:
                        self.updates_table.set_discover_mode(False)
                except Exception:
                    pass
                self.header_info.setText("Search and discover new packages to install")
                try:
                    if hasattr(self, 'source_card') and self.source_card:
                        self.source_card.clear_results()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'filters_panel') and self.filters_panel:
                        self.filters_panel.setVisible(False)
                except Exception:
                    pass
                self._update_nav_greeting(getattr(self, '_cloud_auth', None).user if hasattr(self, '_cloud_auth') and self._cloud_auth else None)
            elif self.current_view == "installed":
                self.search_results = None
                self.apply_filters()
                return
            elif self.current_view == "updates":
                self.search_results = None
                self._recompute_updates()
                return
            else:
                return

        if self.current_view == "discover":
            if hasattr(self, '_greeting_label') and self._greeting_label:
                self._greeting_label.setVisible(False)
            self.search_discover_packages(query)
        elif self.current_view == "updates":
            self.search_results = None
            self._recompute_updates()
        elif self.current_view == "installed":
            self.search_results = [
                pkg for pkg in self.all_packages
                if query in (pkg.get('name') or '').lower()
                or query in (pkg.get('id') or '').lower()
            ]
            self.current_page = 0
            self.all_packages = self.search_results
            try:
                self.load_more_btn.setVisible(False)
            except Exception:
                pass
            try:
                self.updates_table.set_loading(False)
            except Exception:
                pass
            self._sync_installed_table(self.search_results)
            self._show_active_view()
        else:
            self.search_results = [pkg for pkg in self.all_packages if query in pkg['name'].lower()]
            self.current_page = 0

            self.package_table.setUpdatesEnabled(False)
            self.package_table.setRowCount(0)

            start = 0
            end = min(10, len(self.search_results))
            for pkg in self.search_results[start:end]:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))

            self.package_table.setUpdatesEnabled(True)

            has_more = end < len(self.search_results)
            self.load_more_btn.setVisible(has_more)
            if has_more:
                remaining = len(self.search_results) - end
                self.load_more_btn.setText(f"Load More ({remaining} remaining)")

    def search_discover_packages(self, query):
        self.package_table.setRowCount(0)
        self.search_results = []
        try:
            if hasattr(self, 'updates_table') and self.updates_table:
                self.updates_table.set_suggestions([])
        except Exception:
            pass
        # Prepare discover loading context
        self.cancel_discover_search = False
        self.loading_context = "discover"

        try:
            if hasattr(self, 'source_card') and self.source_card:
                _src = self.source_card.get_selected_sources()
            else:
                _src = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        except Exception:
            _src = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        show_pacman = bool(_src.get("pacman", True))
        show_aur = bool(_src.get("AUR", True))
        show_flatpak = bool(_src.get("Flatpak", True))
        show_npm = bool(_src.get("npm", True))

        # Show loading. Table mode uses the same in-table loading overlay as
        # the Updates/Installed pages; grid mode falls back to the spinner.
        if self._view_mode == "table":
            self._show_active_view()
            if hasattr(self, 'updates_table') and self.updates_table:
                self.updates_table.set_discover_mode(True)
                self.updates_table.set_loading(True, "Searching packages...")
        else:
            self.loading_widget.setVisible(True)
            self.loading_widget.set_message("Searching packages...")
            self.loading_widget.start_animation()
            self._hide_all_package_views()
            try:
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(False)
        except Exception:
            pass
        if hasattr(self, 'no_results_widget'):
            self.no_results_widget.setVisible(False)

        def search_in_thread():
            try:
                packages = []

                tokens = [t for t in query.split() if t]
                if show_pacman:
                    pacman_seen = set()
                    if len(tokens) > 1:
                        for tok in tokens:
                            try:
                                result = subprocess.run(["pacman", "-Ss", tok], capture_output=True, text=True, timeout=30)
                            except Exception:
                                result = None
                            if result and result.returncode == 0 and result.stdout:
                                lines = result.stdout.strip().split('\n')
                                i = 0
                                while i < len(lines):
                                    if lines[i].strip() and '/' in lines[i]:
                                        parts = lines[i].split()
                                        if len(parts) >= 2:
                                            name = parts[0].split('/')[-1]
                                            version = parts[1]
                                            description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                            key = ('pacman', name)
                                            if key not in pacman_seen:
                                                pacman_seen.add(key)
                                                packages.append({
                                                    'name': name,
                                                    'version': version,
                                                    'id': name,
                                                    'source': 'pacman',
                                                    'description': description,
                                                    'has_update': False
                                                })
                                    i += 1
                    else:
                        result = subprocess.run(["pacman", "-Ss", query], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0 and result.stdout:
                            lines = result.stdout.strip().split('\n')
                            i = 0
                            while i < len(lines):
                                if lines[i].strip() and '/' in lines[i]:
                                    parts = lines[i].split()
                                    if len(parts) >= 2:
                                        name = parts[0].split('/')[-1]
                                        version = parts[1]
                                        description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                        packages.append({
                                            'name': name,
                                            'version': version,
                                            'id': name,
                                            'source': 'pacman',
                                            'description': description,
                                            'has_update': False
                                        })
                                i += 1

                if show_aur:
                    result_aur = subprocess.run(["curl", "-s", f"https://aur.archlinux.org/rpc/?v=5&type=search&by=name&arg={query}"], capture_output=True, text=True, timeout=10)
                    if result_aur.returncode == 0:
                        try:
                            data = json.loads(result_aur.stdout)
                            if data.get('results'):
                                for pkg in data['results']:
                                    packages.append({
                                        'name': pkg.get('Name', ''),
                                        'version': pkg.get('Version', ''),
                                        'id': pkg.get('Name', ''),
                                        'source': 'AUR',
                                        'description': pkg.get('Description', ''),
                                        'tags': ', '.join(pkg.get('Keywords', []))
                                    })
                        except Exception:
                            pass

                if show_flatpak:
                    try:
                        if not getattr(self, "_flathub_checked", False):
                            try:
                                self.ensure_flathub_user_remote()
                            except Exception:
                                pass
                            try:
                                self._flathub_checked = True
                            except Exception:
                                pass
                    except Exception:
                        pass
                    result_flatpak = subprocess.run([
                        "flatpak", "search", "--columns=application,name,description,version", query
                    ], capture_output=True, text=True, timeout=30)
                    if result_flatpak.returncode == 0 and result_flatpak.stdout:
                        lines = [l for l in result_flatpak.stdout.strip().split('\n') if l.strip()]
                        for line in lines:
                            ls = line.strip()
                            low = ls.lower()
                            if ('no match' in low) or ('no results' in low) or ('not found' in low):
                                continue
                            cols = line.split('\t')
                            if len(cols) < 2:
                                continue
                            app_id = cols[0].strip()
                            app_name = cols[1].strip() if cols[1].strip() else app_id
                            description = cols[2].strip() if len(cols) > 2 else ''
                            version = cols[3].strip() if len(cols) > 3 else ''
                            if app_id and ('no match' not in app_id.lower()) and ('not found' not in app_id.lower()):
                                packages.append({
                                    'name': app_name,
                                    'version': version,
                                    'id': app_id,
                                    'source': 'Flatpak',
                                    'description': description,
                                    'has_update': False
                                })

                if show_npm:
                    try:
                        result_npm = subprocess.run(["npm", "search", "--json", query], capture_output=True, text=True, timeout=30)
                        if result_npm.returncode == 0 and result_npm.stdout:
                            npm_data = json.loads(result_npm.stdout)
                            for pkg in npm_data:
                                packages.append({
                                    'name': pkg.get('name', ''),
                                    'version': pkg.get('version', ''),
                                    'id': pkg.get('name', ''),
                                    'source': 'npm',
                                    'description': pkg.get('description', ''),
                                    'has_update': False
                                })
                    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
                        pass

                if not self.cancel_discover_search and self.loading_context == 'discover' and self.current_view == 'discover':
                    self.discover_results_ready.emit(packages)
            except Exception as e:
                self.log(f"Search error: {str(e)}")

        Thread(target=search_in_thread, daemon=True).start()

    def get_filtered_discover_results(self, selected_sources=None):
        if selected_sources is None:
            if hasattr(self, 'source_card') and self.source_card:
                selected_sources = self.source_card.get_selected_sources()
            else:
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        show_pacman = selected_sources.get("pacman", True)
        show_aur = selected_sources.get("AUR", True)
        show_flatpak = selected_sources.get("Flatpak", True)
        show_npm = selected_sources.get("npm", True)
        filtered = []
        for pkg in self.search_results:
            if pkg['source'] == 'pacman' and show_pacman:
                filtered.append(pkg)
            elif pkg['source'] == 'AUR' and show_aur:
                filtered.append(pkg)
            elif pkg['source'] == 'Flatpak' and show_flatpak:
                filtered.append(pkg)
            elif pkg['source'] == 'npm' and show_npm:
                filtered.append(pkg)
        query = self.search_input.text().strip().lower()
        search_mode = self.current_search_mode
        def get_sort_key(pkg):
            name_lower = pkg['name'].lower()
            id_lower = pkg['id'].lower()
            desc_lower = (pkg.get('description') or '').lower()
            exact = (name_lower == query) or (id_lower == query)
            starts = name_lower.startswith(query) or id_lower.startswith(query)
            contains = (query in name_lower) or (query in id_lower)
            desc_contains = (query in desc_lower)
            source_priority = {'pacman': 3, 'AUR': 2, 'Flatpak': 1, 'npm': 0}.get(pkg.get('source'), 0)
            if search_mode == 'name':
                exact_flag = (name_lower == query)
                starts_flag = name_lower.startswith(query)
                contains_flag = (query in name_lower)
                return (exact_flag, starts_flag, contains_flag, source_priority, desc_contains)
            elif search_mode == 'id':
                exact_flag = (id_lower == query)
                starts_flag = id_lower.startswith(query)
                contains_flag = (query in id_lower)
                return (exact_flag, starts_flag, contains_flag, source_priority, desc_contains)
            else:
                return (exact, starts, contains, source_priority, desc_contains)
        filtered.sort(key=get_sort_key, reverse=True)
        return filtered

    def display_discover_results(self, packages=None, selected_sources=None):
        # Safety: do nothing if the user is no longer on Discover
        if self.current_view != "discover" or self.loading_context != "discover":
            return
        if packages is not None:
            self.search_results = packages
        # Hide loading spinner and show packages
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
        except Exception:
            pass

        if selected_sources is None:
            selected_sources = {}
            try:
                if hasattr(self, 'source_card') and self.source_card:
                    selected_sources = self.source_card.get_selected_sources()
                else:
                    selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
            except Exception:
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}

        self._ensure_installed_index_async(selected_sources)
        self._refresh_discover_results(selected_sources)

    def _sort_discover(self, dataset, field, asc):
        """Sort Discover result dicts by a selected field."""
        try:
            if field == 'version':
                def key(p): return (_parse_version(p.get('version') or ''), (p.get('name') or '').lower())
            elif field == 'source':
                def key(p): return ((p.get('source') or '').lower(), (p.get('name') or '').lower())
            elif field == 'installed':
                def key(p): return ((not bool(self.is_package_installed(p))), (p.get('name') or '').lower())
            else:
                def key(p): return (p.get('name') or '').lower()
            return sorted(dataset, key=key, reverse=not asc)
        except Exception:
            return dataset

    def _refresh_discover_results(self, selected_sources=None):
        """Re-apply source / hide-installed / sort filters and re-render results."""
        if self.current_view != "discover":
            return
        if selected_sources is None:
            try:
                if hasattr(self, 'source_card') and self.source_card:
                    selected_sources = self.source_card.get_selected_sources()
                else:
                    selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
            except Exception:
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        filtered = self.get_filtered_discover_results(selected_sources)
        hide = False
        try:
            if hasattr(self, 'source_card') and self.source_card:
                hide = self.source_card.get_hide_installed()
        except Exception:
            hide = False
        if hide:
            filtered = [p for p in filtered if not self.is_package_installed(p)]
        field, asc = 'relevance', True
        try:
            if hasattr(self, 'source_card') and self.source_card:
                field = self.source_card.get_sort()
                asc = self.source_card.get_sort_asc()
        except Exception:
            pass
        if field != 'relevance':
            try:
                filtered = self._sort_discover(filtered, field, asc)
            except Exception:
                pass
        self.filtered_results = filtered
        self.current_page = 0
        try:
            query = (self.search_input.text() or '').strip()
        except Exception:
            query = ''
        self._update_discover_card_results(filtered, query)
        self._render_discover_rows(filtered, query)

    def _render_discover_rows(self, filtered, query):
        """Render the filtered Discover result set into the shared table."""
        try:
            if hasattr(self, 'updates_table') and self.updates_table:
                self.updates_table.set_discover_mode(True)
                self.updates_table.show_installed_date(False)
                self.updates_table.set_installed_mode(False)
                self.updates_table.set_enrich(True)
                if not filtered:
                    self.updates_table.set_empty_text(
                        f"No packages found matching '{query}'.", "Try a different search term")
                    self._offer_discover_suggestions(query)
                else:
                    self.updates_table.set_empty_text(
                        "No packages found", "Try a different search term")
                # Like the Updates page: show every result in one scrollable list,
                # no pagination / Load More button.
                mapped = [self._map_discover_pkg(p) for p in filtered]
                self.updates_table.set_packages(mapped)
        except Exception:
            pass

        self.load_more_btn.setVisible(False)

        if not filtered:
            self.header_info.setText(f"No packages found matching '{query}'.")
        else:
            count = len(filtered)
            self.header_info.setText(f"{count} packages were found, {count} of which match the specified filters")
        if hasattr(self, 'no_results_widget'):
            self.no_results_widget.setVisible(False)
        self._show_active_view()

        if self.current_view == "discover":
            has_results = bool(filtered)
            # Show the source panel only once results are displayed; hide it
            # on the idle Discover screen or when a search finds nothing.
            try:
                if hasattr(self, 'filters_panel') and self.filters_panel:
                    self.filters_panel.setVisible(has_results)
            except Exception:
                pass
            install_btn = getattr(self, 'discover_install_btn', None)
            if install_btn is not None:
                install_btn.setVisible(has_results)
                install_btn.setEnabled(False)

            # Show toolbar icons only when results are present
            for attr in ('_grid_view_btn', '_bundle_btn', '_sudo_btn'):
                tb = getattr(self, attr, None)
                if tb is not None:
                    tb.setVisible(has_results)
            if hasattr(self, '_greeting_label') and self._greeting_label:
                self._greeting_label.setVisible(not has_results)
        try:
            self._update_discover_install_btn_state()
        except Exception:
            pass

    def _offer_discover_suggestions(self, query):
        """Offer fuzzy 'Did you mean' suggestions for a zero-result search."""
        try:
            if not hasattr(self, 'updates_table') or not self.updates_table:
                return
            self.updates_table.set_suggestions([])
            query = (query or '').strip()
            if len(query) < 3:
                return
            suggestions = suggest_names(query, limit=3)
            if suggestions:
                self._apply_discover_suggestions(suggestions)
            elif not index_ready():
                # No usable name index yet: build it in the background and
                # apply the suggestions when the thread finishes.
                q = query

                def build_index():
                    try:
                        refresh_names_index()
                    except Exception:
                        pass
                    self.discover_suggestions_ready.emit(q)

                Thread(target=build_index, daemon=True).start()
        except Exception:
            pass

    def _apply_discover_suggestions(self, suggestions):
        try:
            if not suggestions or not hasattr(self, 'updates_table') or not self.updates_table:
                return
            if self.current_view != "discover":
                return
            self.updates_table.set_suggestions(suggestions, callback=self._search_suggested)
        except Exception:
            pass

    def _on_discover_suggestions_ready(self, query):
        """Apply suggestions after the background name index was built."""
        try:
            if self.current_view != "discover":
                return
            current = (self.search_input.text() or '').strip()
            if current != (query or '').strip():
                return
            self._apply_discover_suggestions(suggest_names(query, limit=3))
        except Exception:
            pass

    def _search_suggested(self, name):
        """Re-run the Discover search with a suggested package name."""
        try:
            if hasattr(self, 'search_input'):
                self.search_input.setText(name)
        except Exception:
            pass
        self.search_discover_packages(name)

    def _update_discover_card_results(self, filtered, query):
        """Reflect the current Discover result set on the source card.

        Shows per-source match counts, a total summary, and the per-source
        distribution bar. Only touches the card after a search, so the idle
        Discover screen (large search box, buttons) is left unchanged.
        """
        try:
            if not hasattr(self, 'source_card') or not self.source_card:
                return
            per = {}
            for pkg in filtered:
                s = pkg.get('source')
                if s not in per:
                    per[s] = 0
                per[s] += 1
            for name, item in self.source_card.sources.items():
                item.set_count(per.get(name, 0))
            if not filtered:
                self.source_card.set_summary(None)
                self.source_card.set_summary_distribution({})
                return
            noun = "packages found" if query else "packages"
            self.source_card.set_summary(len(filtered), noun=noun)
            self.source_card.set_summary_distribution(per)
        except Exception:
            pass
