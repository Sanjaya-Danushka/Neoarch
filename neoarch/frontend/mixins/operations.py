"""
Operations mixin for NeoArch - package install/update/uninstall operations
"""

import os
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

from PyQt6.QtWidgets import QMessageBox, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from neoarch.backend.package import installer as install_service
from neoarch.backend.package import updater as update_service
from neoarch.backend.package import uninstaller as uninstall_service
from neoarch.backend.services import ignore as ignore_service


class _OperationsMixin:
    """Mixin providing package operation methods for the main window."""

    def sudo_install_selected(self):
        """Install selected packages with sudo privileges"""
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                pkg_name = name_item.text().strip() if name_item else ''
                if self.current_view == "discover":
                    source = ""
                    chip = self.package_table.cellWidget(row, 3)
                    if chip is not None:
                        labels = chip.findChildren(QLabel)
                        if labels:
                            source = labels[-1].text()
                else:
                    source_item = self.package_table.item(row, 4)
                    source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                install_token = pkg_name if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(install_token)
        
        if not packages_by_source:
            QMessageBox.information(self, "No Selection", "Please select packages to install.")
            return
        
        try:
            if self.current_view == "discover":
                sel_src = {s: True for s in packages_by_source.keys()}
            else:
                sel_src = None
            self.build_installed_index(sel_src)
        except Exception:
            pass
        to_install = {}
        idx = self.installed_index or {}
        for source, pkgs in packages_by_source.items():
            installed_set = idx.get(source) or set()
            remaining = [p for p in pkgs if p not in installed_set]
            if remaining:
                to_install[source] = remaining
        if not to_install:
            self.log_signal.emit("All selected packages are already installed")
            return
        package_list = "\n".join(f"• {pkg}" for src, pkgs in to_install.items() for pkg in pkgs)
        reply = QMessageBox.question(
            self, "Install Packages with Sudo",
            f"This will install the following packages with elevated privileges:\n\n{package_list}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.force_sudo_install = True
        except Exception:
            pass
        self._pending_install_packages = to_install
        self.log_signal.emit(f"Installing with sudo: {', '.join([f'{pkg} ({source})' for source, pkgs in to_install.items() for pkg in pkgs])}")
        install_service.install_packages(self, to_install)

    def perform_update_all(self):
        """Update all available packages."""
        self.log("Updating all packages…")
        if self.current_view != "updates":
            self.switch_view("updates")
        QTimer.singleShot(500, lambda: self._do_update_all())

    def _do_update_all(self):
        """Check all update checkboxes and trigger update."""
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None:
                checkbox.setChecked(True)
        self.update_selected()

    def toggle_select_all(self):
        """Toggle all checkboxes: if all checked, uncheck all; otherwise check all."""
        total = self.package_table.rowCount()
        checked = 0
        for row in range(total):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                checked += 1
        new_state = checked < total
        for row in range(total):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None:
                checkbox.setChecked(new_state)

    def clean_cache(self):
        """Clean pacman package cache."""
        self.log("Cleaning package cache…")
        try:
            env = self.get_askpass_env()
            result = subprocess.run(
                ["sudo", "-A", "pacman", "-Sc", "--noconfirm"],
                capture_output=True, text=True, timeout=60, env=env,
            )
            if result.returncode == 0:
                self.log("Cache cleaned successfully.")
            else:
                self.log(f"Cache clean: {result.stderr.strip()}")
        except Exception as e:
            self.log(f"Cache clean failed: {e}")

    def update_selected(self):
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                # Source column: Updates has Source at col 4; Installed at col 3
                source_col = 4 if self.current_view == "updates" else 3
                source_item = self.package_table.item(row, source_col)
                # On Installed view, only update rows that actually have an update available
                if self.current_view == "installed":
                    status_item = self.package_table.item(row, 4)
                    if not status_item or "Update" not in (status_item.text() or ""):
                        continue
                if not name_item:
                    continue
                pkg_name = name_item.text().strip()
                source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                token = pkg_name if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(token)
        if not packages_by_source:
            self.log("No packages selected for update")
            return
        self.log(f"Selected packages for update: {', '.join([f'{pkg} ({source})' for source, pkgs in packages_by_source.items() for pkg in pkgs])}")
        self._show_operation_spinner("Updating packages...")
        update_service.update_packages(self, packages_by_source)
    
    def ignore_selected(self):
        return ignore_service.ignore_selected(self)
    
    def manage_ignored(self):
        return ignore_service.manage_ignored(self)

    def cancel_installation(self):
        """Cancel the ongoing installation process"""
        if hasattr(self, 'install_cancel_event'):
            self.install_cancel_event.set()
            self.log("Installation cancellation requested...")

    def build_installed_index(self, selected_sources=None, force=False):
        idx = self.installed_index if (self.installed_index is not None and not force) else {'pacman': set(), 'AUR': set(), 'Flatpak': set(), 'npm': set()}
        show_pacman = show_aur = show_flatpak = show_npm = True
        if selected_sources is not None:
            try:
                show_pacman = bool(selected_sources.get("pacman", True))
                show_aur = bool(selected_sources.get("AUR", True))
                show_flatpak = bool(selected_sources.get("Flatpak", True))
                show_npm = bool(selected_sources.get("npm", True))
            except Exception:
                pass
        needed = set()
        if show_pacman or show_aur:
            needed.update(["pacman", "AUR"])
        if show_flatpak:
            needed.add("Flatpak")
        if show_npm:
            needed.add("npm")
        now = time.time()
        if (not force) and self.installed_index is not None:
            if (now - (self._installed_index_last_built or 0) < 30) and needed.issubset(self._installed_index_sources or set()):
                return
        _sources = self._installed_index_sources or set()
        built_any = False

        def _build_pacman():
            nonlocal built_any
            if (force or ('pacman' not in _sources) or ('AUR' not in _sources)) and (show_pacman or show_aur):
                r = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout:
                    names = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
                    idx['pacman'].update(names)
                    idx['AUR'].update(names)
                    _sources.update(["pacman", "AUR"])
                    built_any = True

        def _build_flatpak():
            nonlocal built_any
            import shutil as _sh
            if (force or ('Flatpak' not in _sources)) and show_flatpak and _sh.which('flatpak'):
                installed_flatpak = set()
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application"]
                        fp = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if fp.returncode == 0 and fp.stdout:
                            for ln in [x for x in fp.stdout.strip().split('\n') if x.strip()]:
                                app_id = ln.split('\t')[0].strip()
                                if app_id:
                                    installed_flatpak.add(app_id)
                    except Exception:
                        continue
                idx['Flatpak'].update(installed_flatpak)
                _sources.add("Flatpak")
                built_any = True

        def _build_npm():
            nonlocal built_any
            import shutil as _sh
            if (force or ('npm' not in _sources)) and show_npm and _sh.which('npm'):
                results = []
                np_def = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, timeout=30)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=30)
                results.append((np_user.returncode, np_user.stdout))
                for code, out in results:
                    if code == 0 and out and out.strip():
                        try:
                            data = json.loads(out)
                            deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                            for name in deps.keys():
                                idx['npm'].add(name)
                        except Exception:
                            pass
                _sources.add("npm")
                built_any = True

        with ThreadPoolExecutor(max_workers=3) as ex:
            fs = []
            if show_pacman or show_aur:
                fs.append(ex.submit(_build_pacman))
            if show_flatpak:
                fs.append(ex.submit(_build_flatpak))
            if show_npm:
                fs.append(ex.submit(_build_npm))
            for f in as_completed(fs):
                try:
                    f.result()
                except Exception:
                    pass

        self.installed_index = idx
        self._installed_index_sources = _sources
        if built_any:
            self._installed_index_last_built = now

    def is_package_installed(self, pkg):
        try:
            src = pkg.get('source', '')
            name = (pkg.get('id') or '').strip() if src == 'Flatpak' else (pkg.get('name') or '').strip()
            index = self.installed_index or {}
            return bool(name) and (name in (index.get(src) or set()))
        except Exception:
            return False

    def install_selected(self):
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                pkg_name = name_item.text().strip() if name_item else ''
                if self.current_view == "discover":
                    source = ""
                    chip = self.package_table.cellWidget(row, 3)
                    if chip is not None:
                        labels = chip.findChildren(QLabel)
                        if labels:
                            source = labels[-1].text()
                else:
                    source_item = self.package_table.item(row, 4)
                    source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                install_token = pkg_name if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(install_token)
        
        if not packages_by_source:
            self.log_signal.emit("No packages selected for installation")
            return
        # Filter out already installed packages
        try:
            if self.current_view == "discover":
                sel_src = {s: True for s in packages_by_source.keys()}
            else:
                sel_src = None
            self.build_installed_index(sel_src)
        except Exception:
            pass
        to_install = {}
        idx = self.installed_index or {}
        for source, pkgs in packages_by_source.items():
            installed_set = idx.get(source) or set()
            remaining = [p for p in pkgs if p not in installed_set]
            if remaining:
                to_install[source] = remaining
        if not to_install:
            self.log_signal.emit("All selected packages are already installed")
            return
        self.log_signal.emit(f"Selected packages: {', '.join([f'{pkg} ({source})' for source, pkgs in to_install.items() for pkg in pkgs])}")
        self.log_signal.emit(f"Proceeding with installation...")
        self._pending_install_packages = to_install
        install_service.install_packages(self, to_install)

    def _prewarm_installed_index_async(self):
        now = time.time()
        if self.installed_index is not None and (now - (self._installed_index_last_built or 0)) < 30:
            return
        try:
            def _run():
                try:
                    sel = {"pacman": True, "AUR": True, "Flatpak": False, "npm": False}
                    self.build_installed_index(sel)
                except Exception:
                    pass
            Thread(target=_run, daemon=True).start()
        except Exception:
            pass
    
    def _ensure_installed_index_async(self, selected_sources=None):
        try:
            if self._installed_index_building:
                return
            self._installed_index_building = True
            def _run():
                try:
                    self.build_installed_index(selected_sources)
                finally:
                    self._installed_index_building = False
                    QTimer.singleShot(0, self._mark_installed_in_visible_rows)
            Thread(target=_run, daemon=True).start()
        except Exception:
            self._installed_index_building = False
    
    def _mark_installed_in_visible_rows(self):
        try:
            if self.current_view != "discover" or not self.installed_index:
                return
            green = QColor(16, 185, 129)
            for row in range(self.package_table.rowCount()):
                name_item = self.package_table.item(row, 1)
                ver_item = self.package_table.item(row, 2)
                if not name_item or not ver_item:
                    continue
                chip = self.package_table.cellWidget(row, 3)
                src = self.get_source_text(row, "discover")
                pkg = {"name": name_item.text().strip(), "id": name_item.text().strip(), "source": src}
                if self.is_package_installed(pkg):
                    name_item.setForeground(green)
                    ver_item.setForeground(green)
                    tip = "Already installed"
                    name_item.setToolTip(tip)
                    ver_item.setToolTip(tip)
                    if chip is not None:
                        try:
                            labels = chip.findChildren(QLabel)
                            if labels:
                                labels[-1].setStyleSheet("color: rgb(16,185,129);")
                            chip.setToolTip(tip)
                        except Exception:
                            pass
                    try:
                        checkbox = self.get_row_checkbox(row)
                        if checkbox is not None:
                            checkbox.setEnabled(False)
                            checkbox.setToolTip(tip)
                    except Exception:
                        pass
            try:
                self._update_discover_install_btn_state()
            except Exception:
                pass
        except Exception:
            pass
    
    def uninstall_selected(self):
        selected_rows = self.package_table.selectionModel().selectedRows()
        if not selected_rows:
            self.log("No packages selected for uninstallation")
            return
        
        # Group selections by source
        packages_by_source = {}
        for model_index in selected_rows:
            row = model_index.row()
            name_item = self.package_table.item(row, 1)
            source_item = self.package_table.item(row, 3)
            if not name_item or not source_item:
                continue
            name = (name_item.text() or "").strip()
            source = (source_item.text() or "pacman").strip()
            if source not in packages_by_source:
                packages_by_source[source] = []
            token = name if source == 'Flatpak' else name
            packages_by_source[source].append(token)
        
        flat_summary = ', '.join([f"{pkg} ({src})" for src, pkgs in packages_by_source.items() for pkg in pkgs])
        self.log(f"Selected for uninstallation: {flat_summary}")
        self._show_operation_spinner("Uninstalling packages...")
        uninstall_service.uninstall_packages(self, packages_by_source)
    
    def install_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        source = pkg.get('source', 'pacman')
        name = (pkg.get('id') or '').strip() if source == 'Flatpak' else (pkg.get('name') or '').strip()
        if not name:
            return
        to_install = {source: [name]}
        self._pending_install_packages = to_install
        install_service.install_packages(self, to_install)

    def update_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        source = pkg.get('source', 'pacman')
        self._show_operation_spinner("Updating package...")
        update_service.update_packages(self, {source: [pkg['name']]})

    def uninstall_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        source = pkg.get('source', 'pacman')
        uninstall_service.uninstall_packages(self, {source: [pkg['name']]})

    def _on_ui_call(self, fn):
        try:
            if callable(fn):
                fn()
        except Exception:
            pass
