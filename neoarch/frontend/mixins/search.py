"""Search/discover mixin for the main window."""

import os
import json
import subprocess
from threading import Thread

from neoarch.resources.paths import PROJECT_ROOT


class _SearchMixin:
    def on_large_search_requested(self, query):
        """Handle search request from large search box"""
        # Handle special dashboard actions
        if query == "__UPDATE_ALL__":
            self.log("Update All triggered from dashboard")
            if self.current_view != "updates":
                self.switch_view("updates")
            self.perform_update_all()
            return
        if query == "__REFRESH_DB__":
            self.log("Refreshing databases\u2026")
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
                installed_only = False
                cats = []
                if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                    try:
                        installed_only = (self.plugins_sidebar.group.checkedId() == 1)
                    except Exception:
                        installed_only = False
                    try:
                        cats = self.plugins_sidebar.get_selected_categories()
                    except Exception:
                        cats = []
                if hasattr(self, 'plugins_view') and self.plugins_view:
                    self.plugins_view.set_filter(query, installed_only, cats)
                # Keep sidebar search box in sync with the top search
                if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                    try:
                        self.plugins_sidebar.search.blockSignals(True)
                        self.plugins_sidebar.search.setText(query)
                    finally:
                        self.plugins_sidebar.search.blockSignals(False)
            except Exception:
                pass
            return

        if len(query) < 2:
            if self.current_view == "discover":
                self.large_search_box.setVisible(True)
                self.large_search_box.clear()
                self._hide_all_package_views()
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                self.header_info.setText("Search and discover new packages to install")
                btn = getattr(self, 'discover_select_all_btn', None)
                if btn is not None:
                    btn.setVisible(False)
                install_btn = getattr(self, 'discover_install_btn', None)
                if install_btn is not None:
                    install_btn.setVisible(False)
                for attr in ('_grid_view_btn', '_filter_btn', '_bundle_btn', '_sudo_btn'):
                    tb = getattr(self, attr, None)
                    if tb is not None:
                        tb.setVisible(False)
            elif self.current_view == "installed":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self.apply_filters()
                self._show_active_view()
            elif self.current_view == "updates":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self.apply_update_filters()
                self._show_active_view()
            return
        if self.current_view == "discover":
            self.large_search_box.setVisible(False)
            self._show_active_view()
            self.search_discover_packages(query)
        else:
            self.filter_packages()

    def toggle_view_mode(self):
        navbar_dir = os.path.join(str(PROJECT_ROOT), "assets", "icons", "navbar")
        if self._view_mode == "table":
            self._view_mode = "grid"
            self.package_table.setVisible(False)
            self.packages_grid.setVisible(True)
            if self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(navbar_dir, "list.svg"), 20))
                self._grid_view_btn.setToolTip("List View")
            self._populate_grid()
        else:
            self._view_mode = "table"
            self.packages_grid.setVisible(False)
            self.package_table.setVisible(True)
            if self._grid_view_btn:
                self._grid_view_btn.setIcon(self.get_svg_icon(os.path.join(navbar_dir, "view.svg"), 20))
                self._grid_view_btn.setToolTip("Grid View")

    def _populate_grid(self):
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

    def filter_packages(self):
        query = self.search_input.text().lower()

        if not query:
            if self.current_view == "discover":
                self.large_search_box.setVisible(True)
                self._hide_all_package_views()
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                self.header_info.setText("Search and discover new packages to install")
            elif self.current_view == "installed":
                self.apply_filters()
                return
            elif self.current_view == "updates":
                self.apply_update_filters()
                return
            else:
                return

        if self.current_view == "discover":
            self.search_discover_packages(query)
        else:
            self.search_results = [pkg for pkg in self.all_packages if query in pkg['name'].lower()]
            self.current_page = 0

            self.package_table.setUpdatesEnabled(False)
            self.package_table.setRowCount(0)

            start = 0
            end = min(10, len(self.search_results))
            for pkg in self.search_results[start:end]:
                if self.current_view == "installed":
                    self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
                else:
                    self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))

            self.package_table.setUpdatesEnabled(True)

            has_more = end < len(self.search_results)
            self.load_more_btn.setVisible(has_more)
            if has_more:
                remaining = len(self.search_results) - end
                self.load_more_btn.setText(f"Load More ({remaining} remaining)")
            if self.current_view == "updates":
                try:
                    total = len(getattr(self, 'updates_all', []) or [])
                    matched = len(self.search_results or [])
                    self.header_info.setText(f"{total} packages were found, {matched} of which match the specified filters")
                except Exception:
                    pass

    def search_discover_packages(self, query):
        self.package_table.setRowCount(0)
        self.search_results = []
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

        # Show loading spinner
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
        self._show_active_view()
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
        except Exception:
            pass

        if selected_sources is None:
            selected_sources = {}
            if hasattr(self, 'source_card') and self.source_card:
                selected_sources = self.source_card.get_selected_sources()
            else:
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}

        filtered = self.get_filtered_discover_results(selected_sources)
        self.filtered_results = filtered
        self.current_page = 0
        query = self.search_input.text().strip()

        self.package_table.setUpdatesEnabled(False)
        self.package_table.setRowCount(0)
        self._ensure_installed_index_async(selected_sources)

        start = 0
        end = min(self.packages_per_page, len(filtered))
        for pkg in filtered[start:end]:
            if self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg['version'], pkg['source'])

        self.package_table.setUpdatesEnabled(True)

        has_more = end < len(filtered)
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = len(filtered) - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")

        if not filtered:
            self.header_info.setText(f"No packages found matching '{query}'.")
            self._hide_all_package_views()
            if hasattr(self, 'no_results_widget'):
                self.no_results_desc.setText(f"No packages found matching '{query}'.")
                self.no_results_widget.setVisible(True)
        else:
            count = len(filtered)
            self.header_info.setText(f"{count} packages were found, {count} of which match the specified filters")
            if hasattr(self, 'no_results_widget'):
                self.no_results_widget.setVisible(False)
            self._show_active_view()

        if self.current_view == "discover":
            has_results = bool(filtered)
            btn = getattr(self, 'discover_select_all_btn', None)
            if btn is not None:
                btn.setVisible(has_results)
            install_btn = getattr(self, 'discover_install_btn', None)
            if install_btn is not None:
                install_btn.setVisible(has_results)
                install_btn.setEnabled(False)

            # Show toolbar icons only when results are present
            for attr in ('_grid_view_btn', '_filter_btn', '_bundle_btn', '_sudo_btn'):
                tb = getattr(self, attr, None)
                if tb is not None:
                    tb.setVisible(has_results)
