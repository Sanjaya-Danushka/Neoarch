"""
Operations mixin for NeoArch - package install/update/uninstall operations
"""

import os
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

from PyQt6.QtWidgets import QMessageBox, QLabel, QDialog
from PyQt6.QtCore import QTimer

from neoarch.backend.package import installer as install_service
from neoarch.backend.package import updater as update_service
from neoarch.backend.package import uninstaller as uninstall_service
from neoarch.backend.services import ignore as ignore_service
from neoarch.backend.services.i18n import _

# Per-session cache of fetched+scanned AUR packages so repeated installs of
# the same package don't re-fetch. {name: Optional[Dict] | None}
_aur_scan_cache = {}


class _OperationsMixin:
    """Mixin providing package operation methods for the main window."""

    def _preflight_aur_scan(self, names):
        """Fetch + statically scan AUR PKGBUILDs before installation.

        Returns ``{name: [findings]}`` (may contain empty lists). Returns
        ``None`` if any fetch fails, so callers can degrade to the legacy
        static notice instead of blocking the install.
        """
        from neoarch.backend.services import security_scan
        from neoarch.backend.services.aur_fetch import fetch_aur_pkgbuild

        result = {}
        for name in names:
            if name not in _aur_scan_cache:
                _aur_scan_cache[name] = fetch_aur_pkgbuild(name)
            data = _aur_scan_cache[name]
            if data is None:
                return None
            findings = security_scan.scan_pkgbuild(data["pkgbuild"])
            for scriptlet_name, text in data["scriptlets"].items():
                findings.extend(security_scan.scan_install_scriptlet(
                    text, scriptlet_name))
            result[name] = findings
        return result

    def _confirm_aur_security(self, aur_pkgs):
        """Gate AUR installs behind the pre-install security scan.

        Returns True to proceed. On any critical finding the user must
        explicitly accept the risk; warnings require a plain Continue; a
        clean scan (or a scan outage) falls back to the legacy notice.
        """
        from neoarch.frontend.components.security_check_dialog import (
            SecurityScanDialog)

        preflight = self._preflight_aur_scan(aur_pkgs)
        if preflight is not None:
            all_findings = [f for fs in preflight.values() for f in fs]
            by_pkg = {n: fs for n, fs in preflight.items() if fs}
            if all_findings:
                dialog = SecurityScanDialog(by_pkg, self)
                return dialog.exec() == SecurityScanDialog.DialogCode.Accepted
            clean = QMessageBox(
                QMessageBox.Icon.Information,
                _("AUR Security Notice"),
                _("All {n} scanned AUR packages are clean.").format(
                    n=len(aur_pkgs)),
                QMessageBox.StandardButton.Ok
                | QMessageBox.StandardButton.Cancel,
                self)
            clean.setInformativeText(_("Continue installing AUR packages?"))
            clean.setDefaultButton(QMessageBox.StandardButton.Ok)
            return clean.exec() == QMessageBox.StandardButton.Ok

        warn = QMessageBox(
            QMessageBox.Icon.Warning,
            _("AUR Security Notice"),
            _("AUR packages are built from third-party PKGBUILD scripts "
              "maintained by the community.\n\n{aur_pkgs}\n\n"
              "Always review the PKGBUILD and .install scriptlet before "
              "building. Proceeding with the AUR helper does not perform a "
              "static security scan.").format(
                  aur_pkgs=", ".join(aur_pkgs)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self)
        warn.setInformativeText(_("Continue installing AUR packages?"))
        warn.setDefaultButton(QMessageBox.StandardButton.No)
        return warn.exec() == QMessageBox.StandardButton.Yes

    def _db_lock_preflight(self, operation: str = "") -> bool:
        """Return False and show a dialog when the pacman DB is locked.

        Distinguishes three cases via ``sys_utils.check_db_lock``:

        * **ours**  — this app already holds the lock (an operation is running):
          block the request, there's no need to wait.
        * **other** — another package manager (pacman/yay/paru in a terminal)
          holds it: warn and let the user retry once it's done.
        * **stale** — a leftover ``/var/lib/pacman/db.lck`` from a crash/kill:
          offer to remove it so operations can proceed.

        ``None`` (no lock) always returns True.
        """
        from neoarch.backend.sys_utils import check_db_lock

        state = check_db_lock()
        if state is None:
            return True
        status = state.get("status")
        if status == "ours":
            self.log("Pacman DB already locked by this app; ignoring request.")
            return False
        if status == "other":
            self.show_busy_pm_warning(
                details=(f"Lock: /var/lib/pacman/db.lck held by "
                         f"{state.get('pid', 'another package manager')}"))
            return False
        if status == "stale":
            return self._offer_stale_lock_removal(operation)
        self.show_busy_pm_warning(
            details=(f"Lock: /var/lib/pacman/db.lck (pid "
                     f"{state.get('pid', 'unknown')})"))
        return False

    def _offer_stale_lock_removal(self, operation: str) -> bool:
        """Ask whether to delete a leftover pacman DB lock and proceed.

        The lock file is root-owned, so removal runs through the same
        session-auth/sudo path as every other privileged action.
        """
        from neoarch.backend.sys_utils import PACMAN_DB_LOCK

        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Icon.Question)
        dlg.setWindowTitle(_("Pacman Database Lock"))
        dlg.setText(_("A stale lock file was found:\n\n"
                      "{lock}\n\n"
                      "No package manager is running, so this is a leftover "
                      "from a previous interrupted operation.").format(
                          lock=PACMAN_DB_LOCK))
        if operation:
            dlg.setInformativeText(_(
                "Remove the stale lock and continue with \"{operation}\"?").format(
                    operation=operation))
        else:
            dlg.setInformativeText(_("Remove the stale lock and continue?"))
        remove_btn = dlg.addButton(_("Remove Lock"), QMessageBox.ButtonRole.AcceptRole)
        dlg.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
        dlg.setDefaultButton(remove_btn)
        dlg.exec()
        if dlg.clickedButton() != remove_btn:
            return False
        if not self.ensure_session_auth():
            self.log_signal.emit(
                "Stale lock removal cancelled: authentication required.")
            return False
        try:
            from neoarch.backend.session_auth import run_sudo_command
            run_sudo_command(["rm", "-f", PACMAN_DB_LOCK])
        except Exception as e:
            self.log(f"Could not remove stale pacman lock: {e}")
            self.show_busy_pm_warning(details=str(e))
            return False
        self.log(f"Removed stale pacman DB lock: {PACMAN_DB_LOCK}")
        return True

    def sudo_install_selected(self):
        """Install selected packages with sudo privileges"""
        if not self._db_lock_preflight(operation="Install packages"):
            return
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
            QMessageBox.information(self, _("No Selection"), _("Please select packages to install."))
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
        if 'AUR' in to_install:
            aur_pkgs = to_install['AUR']
            if not self._confirm_aur_security(aur_pkgs):
                return
        reply = QMessageBox.question(
            self, _("Install Packages with Sudo"),
            _("This will install the following packages with elevated privileges:\n\n{package_list}\n\nContinue?").format(package_list=package_list),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if not self.ensure_session_auth():
            self.log_signal.emit("Install cancelled: authentication required.")
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
        if not self._db_lock_preflight(operation="Update all packages"):
            return
        upgrades = getattr(self, 'updates_all', None)
        if upgrades is not None and len(upgrades) == 0:
            self.log("No updates available.")
            return
        if not self.ensure_session_auth():
            self.log("Update cancelled: authentication required.")
            return
        self.log("Updating all packages\u2026")
        if upgrades:
            self._do_update_all()
        else:
            self._pending_update_all = True
            self.load_updates()

    def _do_update_all(self):
        """Update all available packages directly from updates data."""
        updates = getattr(self, 'updates_all', None)
        if not updates:
            self.log("No updates available or updates not yet loaded.")
            return
        try:
            from neoarch.frontend.components.update_review_dialog import UpdateReviewDialog
            dlg = UpdateReviewDialog(updates, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.log("Update review cancelled.")
                return
        except Exception as e:
            self.log(f"Update review unavailable, continuing: {e}")
        packages_by_source = {}
        for pkg in updates:
            source = pkg.get('source', 'pacman')
            name = (pkg.get('name') or pkg.get('id') or '').strip()
            if not name:
                continue
            if source not in packages_by_source:
                packages_by_source[source] = []
            packages_by_source[source].append(name)
        if not packages_by_source:
            self.log("No packages to update.")
            return
        if not self.ensure_session_auth():
            self.log("Update cancelled: authentication required.")
            return
        self.log(f"Updating all packages: {', '.join([f'{pkg} ({source})' for source, pkgs in packages_by_source.items() for pkg in pkgs])}")
        self.installation_progress.emit("start", True)
        update_service.update_packages(self, packages_by_source, upgrade_all=True)

    def toggle_select_all(self):
        """Toggle all checkboxes: if all checked, uncheck all; otherwise check all."""
        if self.current_view in ("updates", "installed", "discover") and hasattr(self, 'updates_table'):
            try:
                if self.updates_table.row_count():
                    self.updates_table.toggle_select_all()
            except Exception:
                pass
            return
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
        """Clean package and system cache (BleachBit + pacman) in a background thread."""
        if not self.ensure_session_auth():
            self.log("Cache clean cancelled: authentication required.")
            return

        def _run():
            self.log("Cleaning package cache\u2026")
            # BleachBit system cache cleaning
            try:
                r = subprocess.run(["which", "bleachbit"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    self.log("Running BleachBit cache cleaner\u2026")
                    bb = subprocess.run(
                        ["bleachbit", "--clean", "system.cache", "system.tmp", "system.trash",
                         "system.recent_documents", "system.clipboard"],
                        capture_output=True, text=True, timeout=120,
                    )
                    if bb.returncode == 0:
                        self.log("BleachBit cleaned successfully.")
                    else:
                        self.log(f"BleachBit: {bb.stderr.strip() or 'completed with warnings'}")
                else:
                    self.log("BleachBit not installed, skipping.")
            except Exception as e:
                self.log(f"BleachBit skipped: {e}")
            # Pacman package cache clean
            try:
                env = self.get_askpass_env()
                result = subprocess.run(
                    ["sudo", "-A", "pacman", "-Sc", "--noconfirm"],
                    capture_output=True, text=True, timeout=60, env=env,
                )
                if result.returncode == 0:
                    self.log("Pacman cache cleaned successfully.")
                else:
                    self.log(f"Pacman cache clean: {result.stderr.strip()}")
            except Exception as e:
                self.log(f"Pacman cache clean failed: {e}")

        Thread(target=_run, daemon=True).start()

    def update_selected(self):
        if self.current_view in ("updates", "installed") and hasattr(self, 'updates_table'):
            return self._update_selected_updates_table()
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                # Source column: Updates has Source at col 4; Installed at col 3
                source_col = 4 if self.current_view == "updates" else 3
                source_item = self.package_table.item(row, source_col)
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
        if not self._confirm_partial_update(packages_by_source):
            return
        if not self.ensure_session_auth():
            self.log("Update cancelled: authentication required.")
            return
        self.log(f"Selected packages for update: {', '.join([f'{pkg} ({source})' for source, pkgs in packages_by_source.items() for pkg in pkgs])}")
        self.installation_progress.emit("start", True)
        update_service.update_packages(self, packages_by_source)

    def _update_selected_updates_table(self):
        """Update the packages checked in the redesigned updates table."""
        packages_by_source = {}
        for pkg in self.updates_table.checked_packages():
            source = pkg.get('source') or 'pacman'
            name = (pkg.get('name') or '').strip()
            if not name:
                continue
            # On the installed page only update rows that actually have an update
            if self.current_view == "installed":
                if pkg.get('status') == 'Installed':
                    continue
                if not pkg.get('new_version') or pkg.get('new_version') == pkg.get('version'):
                    continue
            packages_by_source.setdefault(source, []).append(name)
        if not packages_by_source:
            self.log("No packages selected for update")
            return
        if not self._confirm_partial_update(packages_by_source):
            return
        if not self.ensure_session_auth():
            self.log("Update cancelled: authentication required.")
            return
        self.log(f"Selected packages for update: {', '.join([f'{pkg} ({source})' for source, pkgs in packages_by_source.items() for pkg in pkgs])}")
        self.installation_progress.emit("start", True)
        update_service.update_packages(self, packages_by_source)

    def _confirm_partial_update(self, packages_by_source):
        """Warn once before applying a *partial* Arch update.

        A partial update is any Arch selection smaller than the full set of
        available pacman/AUR upgrades. Full selections (and selections that
        are exactly the whole set) skip the dialog. Returns False if the
        user cancels. Applies to every update entry point, so a single
        package updated from the detail card or the row menu is not silent
        either.
        """
        try:
            from neoarch.frontend.components.partial_update_dialog import (
                is_partial_update, PartialUpdateDialog)
            available = self._available_arch_updates()
            if not is_partial_update(available, packages_by_source):
                return True
            dlg = PartialUpdateDialog(available, packages_by_source, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.log("Partial update cancelled by user.")
                return False
        except Exception as e:
            self.log(f"Partial-update check skipped: {e}")
        return True

    def _available_arch_updates(self):
        """The pacman/AUR update set for the current page.

        Prefers the loaded ``updates_all`` list (Updates page); otherwise
        falls back to rows in the shared updates table that still have a
        pending upgrade, which covers the Installed page.
        """
        updates = getattr(self, 'updates_all', None) or []
        arch = [p for p in updates
                if (p.get('source') or '').upper() in ('PACMAN', 'AUR')]
        if arch:
            return arch
        try:
            tbl = getattr(self, 'updates_table', None)
            pkgs = tbl.model.packages() if tbl is not None else []
        except Exception:
            pkgs = []
        return [p for p in pkgs
                if (p.get('source') or '').upper() in ('PACMAN', 'AUR')
                and p.get('new_version')
                and p.get('new_version') != p.get('version')]
    
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
        if self.current_view == "discover":
            try:
                if hasattr(self, 'updates_table') and self.updates_table:
                    for pkg in self.updates_table.checked_packages():
                        if pkg.get('_installed'):
                            continue
                        source = pkg.get('source') or 'pacman'
                        pkg_name = (pkg.get('name') or '').strip()
                        if not pkg_name:
                            continue
                        if source not in packages_by_source:
                            packages_by_source[source] = []
                        packages_by_source[source].append(pkg_name)
            except Exception:
                pass
        else:
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
        if not self.ensure_session_auth():
            self.log_signal.emit("Install cancelled: authentication required.")
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
        """Mark already-installed Discover rows (green + disabled checkbox)."""
        try:
            if self.current_view != "discover" or not self.installed_index:
                return
            try:
                if hasattr(self, 'updates_table') and self.updates_table:
                    self.updates_table.mark_installed(self.is_package_installed)
            except Exception:
                pass
            try:
                hide = False
                if hasattr(self, 'source_card') and self.source_card:
                    hide = self.source_card.get_hide_installed()
                if hide and hasattr(self, '_refresh_discover_results'):
                    self._refresh_discover_results()
            except Exception:
                pass
            try:
                self._update_discover_install_btn_state()
            except Exception:
                pass
        except Exception:
            pass
    
    def uninstall_selected(self):
        if not self._db_lock_preflight(operation="Uninstall packages"):
            return
        if self.current_view in ("updates", "installed") and hasattr(self, 'updates_table'):
            checked = self.updates_table.checked_packages()
            if not checked:
                self.log("No packages selected for uninstallation")
                return
            packages_by_source = {}
            for pkg in checked:
                name = (pkg.get('name') or '').strip()
                source = (pkg.get('source') or 'pacman').strip()
                if not name:
                    continue
                packages_by_source.setdefault(source, []).append(name)
        else:
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
        if not self.ensure_session_auth():
            self.log("Uninstall cancelled: authentication required.")
            return
        self.log(f"Selected for uninstallation: {flat_summary}")
        self.installation_progress.emit("start", False)
        uninstall_service.uninstall_packages(self, packages_by_source)
    
    def install_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        if pkg.get('_view') == 'plugins':
            plugin_id = pkg.get('id') or pkg.get('name') or ''
            if plugin_id and hasattr(self, 'plugins_manager'):
                self.plugins_manager.install_by_id(self.plugins_view, plugin_id)
            return
        if not self.ensure_session_auth():
            self.log("Install cancelled: authentication required.")
            return
        source = pkg.get('source', 'pacman')
        if source in ('pacman', 'AUR') and not self._db_lock_preflight(
                operation="Install package"):
            return
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
        name = pkg.get('name') or pkg.get('id') or ''
        if not self._confirm_partial_update({source: [name]}):
            return
        if source in ('pacman', 'AUR') and not self._db_lock_preflight(
                operation="Update package"):
            return
        if not self.ensure_session_auth():
            self.log("Update cancelled: authentication required.")
            return
        self.installation_progress.emit("start", True)
        update_service.update_packages(self, {source: [name]})

    def uninstall_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        if pkg.get('_view') == 'plugins':
            plugin_id = pkg.get('id') or pkg.get('name') or ''
            if plugin_id and hasattr(self, 'plugins_manager'):
                self.plugins_manager.uninstall_by_id(self.plugins_view, plugin_id)
            return
        source = pkg.get('source', 'pacman')
        if source in ('pacman', 'AUR') and not self._db_lock_preflight(
                operation="Uninstall package"):
            return
        if not self.ensure_session_auth():
            self.log("Uninstall cancelled: authentication required.")
            return
        source = pkg.get('source', 'pacman')
        uninstall_service.uninstall_packages(self, {source: [pkg['name']]})

    def launch_from_detail(self):
        pkg = getattr(self.package_detail_card, '_pkg_data', None)
        if not pkg:
            return
        if pkg.get('_view') == 'plugins':
            plugin_id = pkg.get('id') or pkg.get('name') or ''
            if plugin_id and hasattr(self, 'plugins_manager'):
                self.plugins_manager.launch_by_id(self.plugins_view, plugin_id)

    def _on_ui_call(self, fn):
        try:
            if callable(fn):
                fn()
        except Exception:
            pass
