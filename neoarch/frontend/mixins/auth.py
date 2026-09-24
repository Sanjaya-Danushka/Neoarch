"""Authentication, first-run setup, and system utility mixin."""

import subprocess
import tempfile
import shutil
from threading import Thread, Event

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QMessageBox

from neoarch.backend import config_utils, sys_utils
from neoarch.frontend.tokens import Colors, Fonts
from neoarch.backend.auth import get_askpass_env as _get_askpass_env
from neoarch.backend.services.i18n import _
from neoarch.backend.workers import CommandWorker
from neoarch.backend.package.updater import update_core_tools


class DependencyAuthCancelled(RuntimeError):
    """User closed the authentication prompt — setup must stop, not fake success."""


class _AuthMixin:
    @staticmethod
    def get_ignore_file_path():
        return config_utils.get_ignore_file_path()

    @staticmethod
    def load_ignored_updates():
        return config_utils.load_ignored_updates()

    @staticmethod
    def save_ignored_updates(items):
        return config_utils.save_ignored_updates(items)

    @staticmethod
    def get_local_updates_file_path():
        return config_utils.get_local_updates_file_path()

    @staticmethod
    def load_local_update_entries():
        return config_utils.load_local_update_entries()

    @staticmethod
    def cmd_exists(cmd):
        return sys_utils.cmd_exists(cmd)

    @staticmethod
    def get_missing_dependencies():
        return sys_utils.get_missing_dependencies()

    def run_first_run_checks(self):
        """Silent dependency audit — prompt only when REQUIRED parts miss.

        Optional integrations (flatpak, docker, npm, ...) never block
        startup; they surface as an alert on About > Diagnostics.
        """
        import os as _os
        _fake = _os.environ.get("NEOARCH_FAKE_MISSING", "").strip()
        if _fake:
            self.log(f"[test] Simulating missing dependencies: {_fake}")
        try:
            missing_required = sys_utils.get_missing_required()
            missing_optional = sys_utils.get_missing_optional()
        except Exception as e:
            self.log(f"Dependency check failed: {e}")
            return

        self._update_dep_alert(missing_required + missing_optional)

        if not missing_required and not missing_optional:
            self.log("All required dependencies present")
            return

        if missing_optional:
            self.log(
                "Optional components missing: "
                f"{', '.join(missing_optional)} "
                "(see About > Diagnostics)")

        if not missing_required:
            return
        text = (_("The following components are required for NeoArch to work:\n\n{list}\n\nInstall now?").format(
                    list="\n".join(f"\u2022 {m}" for m in missing_required)))
        reply = QMessageBox.question(self, _("Setup Environment"), text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            if not self.ensure_session_auth():
                self.log("Dependency setup cancelled: authentication required.")
                return
            Thread(target=self.install_dependencies, args=(missing_required,), daemon=True).start()

    def install_dependencies(self, missing):
        """Attempt to install missing dependencies; returns whether all landed."""
        try:
            from neoarch.backend.session_auth import is_session_active
            self.log(f"Installing missing dependencies: {', '.join(missing)}")
            if not is_session_active():
                # Auth is handled up-front on the GUI thread; reaching this
                # point without a session means the user closed the prompt,
                # so stop instead of re-asking for every command.
                raise DependencyAuthCancelled(
                    "authentication cancelled \u2014 no session password cached")
            if not self.cmd_exists("git"):
                self.log("Installing git first...")
                self._run_sudo_install(["git"])
            pacman_pkgs = [p for p in missing if p not in ("yay or paru", "yay", "paru", "python-supabase")]
            if pacman_pkgs:
                pacman_pkgs = sys_utils.resolve_pkg_names(pacman_pkgs)
                self._run_sudo_install(pacman_pkgs)
            if "python-supabase" in missing:
                self._install_cloud_venv()
            if ("yay or paru" in missing or "yay" in missing or "paru" in missing) and self.cmd_exists("git"):
                self.install_aur_helper()
            # Whatever was attempted but is still missing cannot be fixed by
            # re-offering it — the prompt/pip loop ends here. Only the names the
            # user actually asked to install are suppressed; untouched optional
            # deps stay visible in Diagnostics. A fresh start re-evaluates all.
            still_missing = self.get_missing_dependencies()
            remaining = [n for n in missing if n in still_missing]
            for name in remaining:
                sys_utils.suppress_missing(name)
            self._update_dep_alert(self.get_missing_dependencies())
            if remaining:
                self.log(f"Could not install: {', '.join(remaining)} (not re-offered this session)")
                self.show_message.emit(_("Environment"), _("Dependency setup incomplete. Still missing: {list}").format(list=", ".join(remaining)))
                return False
            else:
                self.show_message.emit(_("Environment"), _("Dependency setup completed"))
                return True
        except DependencyAuthCancelled as e:
            self.log(f"Dependency setup cancelled: {e}")
            self.show_message.emit(
                _("Environment"),
                _("Dependency setup cancelled \u2014 authentication required"))
            raise
        except Exception as e:
            self.log(f"Setup failed: {str(e)}")
            self.show_message.emit(_("Environment"), _("Setup failed: {e}").format(e=str(e)))
            return False

    def _run_sudo_install(self, packages):
        done = Event()
        failed = {"v": False}
        worker = CommandWorker(["pacman", "-S", "--needed", "--noconfirm"] + packages, sudo=True)
        worker.output.connect(self.log)
        worker.error.connect(self.log)
        worker.error.connect(lambda _msg: failed.__setitem__("v", True))
        worker.finished.connect(lambda: done.set())
        worker.run()
        done.wait(timeout=600)
        if failed["v"]:
            raise RuntimeError(f"pacman install failed for: {', '.join(packages)}")

    def _install_cloud_venv(self):
        """Set up the app-owned venv hosting supabase for cloud sync.

        supabase pins httpx<0.26 while Arch ships httpx>=0.28, so it must NOT
        land in user site-packages — that would shadow pacman-owned httpx for
        every Python program under this user. An isolated app venv keeps the
        pinned dependency graph out of the system interpreter entirely.
        """
        self.log("Setting up cloud sync (supabase) in an app virtual environment...")
        sys_utils.ensure_cloud_venv(log_fn=self.log)
        if not sys_utils.is_cloud_venv_ready():
            raise RuntimeError("supabase did not become importable in the app venv")

    def install_aur_helper(self):
        tmpdir = tempfile.mkdtemp(prefix="neoarch-yay-")
        try:
            self.log("Installing yay AUR helper...")
            clone = subprocess.run([shutil.which("git") or "git", "clone", "https://aur.archlinux.org/yay-bin.git", tmpdir], capture_output=True, text=True, timeout=120, check=False)
            if clone.returncode != 0:
                self.log(f"Error: {clone.stderr}")
                return
            env, cleanup = self.prepare_askpass_env()
            cmd = f"cd '{tmpdir}' && makepkg -si --noconfirm"
            process = subprocess.Popen([shutil.which("bash") or "bash", "-lc", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            while True:
                line = process.stdout.readline() if process.stdout else ""
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log(line.strip())
            _, stderr = process.communicate()
            if process.returncode != 0 and stderr:
                self.log(f"Error: {stderr}")
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def ensure_session_auth(self) -> bool:
        """Lazily ensure an authenticated session exists.

        Returns True if a credential cache is already active, otherwise shows
        the authentication dialog once and returns its result. Use this right
        before any privileged operation so the password is only asked when it
        is actually needed.
        """
        from neoarch.backend.session_auth import setup_session_auth, is_session_active
        if is_session_active():
            return True
        self.log("Authentication required for this operation.")
        success = setup_session_auth(self)
        if success:
            self.log("Session authentication established")
        else:
            self.log("Session authentication declined or failed")
        return success

    def update_core_tools(self):
        if not self.ensure_session_auth():
            self.log("Tools update cancelled: authentication required.")
            return
        return update_core_tools(self)

    @staticmethod
    def prepare_askpass_env():
        from neoarch.backend.auth import prepare_askpass_env
        return prepare_askpass_env()

    @staticmethod
    def get_askpass_env():
        return _get_askpass_env()

    @staticmethod
    def check_authentication_tools():
        # NeoArch ships its own themed authentication dialog with session
        # caching; no external GUI auth tools are required anymore.
        pass

    @staticmethod
    def _snapshot_engine(settings):
        """Return the snapshot service module matching the configured backend."""
        if settings.get('snapshot_backend') == 'snapper':
            from neoarch.backend.services import snapper
            return snapper
        from neoarch.backend.services import snapshot as snapshot_svc
        return snapshot_svc

    def create_snapshot(self):
        if not self.ensure_session_auth():
            self.log("Snapshot cancelled: authentication required.")
            return
        return self._snapshot_engine(self.settings).create_snapshot(self)

    def revert_to_snapshot(self):
        if not self.ensure_session_auth():
            self.log("Snapshot cancelled: authentication required.")
            return
        return self._snapshot_engine(self.settings).revert_to_snapshot(self)

    def delete_snapshots(self):
        if not self.ensure_session_auth():
            self.log("Snapshot cancelled: authentication required.")
            return
        return self._snapshot_engine(self.settings).delete_snapshots(self)

    def install_snapshot_hooks(self):
        """Install system-wide pacman snapper hooks (Snapper only)."""
        if not self.ensure_session_auth():
            self.log("Hook install cancelled: authentication required.")
            return
        from neoarch.backend.services.snapper import install_pacman_hooks
        install_pacman_hooks(self)

    def remove_snapshot_hooks(self):
        """Remove the system-wide pacman snapper hooks."""
        if not self.ensure_session_auth():
            self.log("Hook removal cancelled: authentication required.")
            return
        from neoarch.backend.services.snapper import remove_pacman_hooks
        remove_pacman_hooks(self)

    # ── Built-in backup (replaces timeshift as default) ──

    def create_backup(self):
        from neoarch.backend.services.backup import create_backup
        self.log("Starting built-in backup...")
        self.loading_widget.setVisible(True)
        self.loading_widget.set_message("Creating backup...")
        self.loading_widget.start_animation()

        def on_progress(msg):
            try:
                self.ui_call.emit(lambda: self.log(msg))
            except Exception:
                pass

        def on_done(result):
            try:
                self.ui_call.emit(lambda: self.loading_widget.stop_animation())
                self.ui_call.emit(lambda: self.loading_widget.setVisible(False))
            except Exception:
                pass
            if result.get("snapshot"):
                self.show_message.emit(
                    "Backup",
                    f"Backup created: {result['path']}\nSnapshot: {result['snapshot']}")
            else:
                self.show_message.emit(
                    "Backup",
                    f"Backup created: {result['path']}\n"
                    "Note: BTRFS snapshot not available; package list + config saved.")

        create_backup(progress_cb=on_progress, finished_cb=on_done)

    def list_backups(self):
        from neoarch.backend.services.backup import list_backups
        backups = list_backups()
        if not backups:
            self.show_message.emit("Backup", "No backups found yet.")
            return
        lines = ["Available backups (newest first):", ""]
        for b in backups:
            snap = " [snapshot]" if b.get("snapshot") else ""
            pkg = b.get("packages", {})
            count = len(pkg.get("pacman_all", [])) if isinstance(pkg, dict) else 0
            lines.append(f"  {b['timestamp']} - {count} packages{snap}")
        self.show_message.emit("Backup", "\n".join(lines))

    def restore_backup(self):
        from neoarch.backend.services.backup import list_backups, restore_packages
        backups = list_backups()
        if not backups:
            self.show_message.emit("Backup", "No backups found to restore.")
            return
        from PyQt6.QtWidgets import (QDialog, QComboBox, QVBoxLayout, QLabel,
                                     QDialogButtonBox)
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Restore Backup"))
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(_("Select a backup to restore packages from:")))
        combo = QComboBox()
        for b in backups:
            pkg = b.get("packages", {})
            count = len(pkg.get("pacman_all", [])) if isinstance(pkg, dict) else 0
            combo.addItem(f"{b['timestamp']} ({count} packages)", b['path'])
        layout.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path = combo.currentData()
        reply = QMessageBox.question(
            self, "Confirm Restore",
            "Restore packages from this backup?\n\nMissing packages will be installed.\nThis may take a while.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.log(f"Restoring packages from {path}...")
        restore_packages(path, progress_cb=self.log, finished_cb=lambda ok: self.show_message.emit(
            "Backup", "Package restore completed" if ok else "Package restore failed"))

    def prune_backups(self):
        from neoarch.backend.services.backup import prune_backups
        removed = prune_backups()
        if removed:
            self.show_message.emit("Backup", f"Removed {len(removed)} old backup(s).")
        else:
            self.show_message.emit("Backup", "No old backups to remove.")

    # ── System hygiene: orphans, .pacnew, news ──

    def cleanup_orphans(self):
        """Remove orphaned packages, prompting for confirmation."""
        from neoarch.backend.services.hygiene import list_orphans, remove_orphans
        orphans = list_orphans()
        if not orphans:
            self.show_message.emit("Cleanup", "No orphaned packages found.")
            return
        reply = QMessageBox.question(
            self, "Remove Orphans",
            f"Remove {len(orphans)} orphaned package(s)?\n\n{', '.join(orphans[:10])}"
            + ("\n..." if len(orphans) > 10 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if not self.ensure_session_auth():
            self.log("Orphan cleanup cancelled: authentication required.")
            return
        self.log(f"Removing {len(orphans)} orphaned package(s)...")

        def on_done(ok):
            self.show_message.emit(
                "Cleanup",
                "Orphaned packages removed." if ok else "Failed to remove orphaned packages.")
            try:
                self._refresh_installed_health_async()
            except Exception:
                pass

        remove_orphans(progress_cb=self.log, finished_cb=on_done)

    def manage_pacnew(self):
        """Show the .pacnew file manager dialog."""
        from neoarch.backend.services.hygiene import list_pacnew, diff_pacnew, accept_pacnew, delete_pacnew
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                                     QListWidget, QListWidgetItem, QDialogButtonBox,
                                     QPlainTextEdit, QMessageBox, QSplitter)
        files = list_pacnew()
        if not files:
            self.show_message.emit("Config Files", "No .pacnew files found. System is clean.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(_(".pacnew Files"))
        scr = QGuiApplication.primaryScreen()
        if scr is not None:
            geo = scr.availableGeometry()
            dlg.resize(min(760, geo.width() - 120), min(560, geo.height() - 120))
        else:
            dlg.resize(760, 560)
        layout = QVBoxLayout(dlg)

        hint = QLabel(f"{len(files)} config files pending review. Select one to inspect the diff.")
        hint.setStyleSheet("color: #8B8D97;")
        layout.addWidget(hint)

        list_widget = QListWidget()
        for f in files:
            label = f"{f['package']} - {f['path']}"
            item = QListWidgetItem(label)
            item.setData(0x0100, f["path"])
            list_widget.addItem(item)

        # Resizable splitter between the file list and the diff preview: long
        # diffs previously lived in a fixed 200px pane whose "very last entry"
        # stayed hidden below the fold, even though the selection logic was
        # fine. The pane now grows with the dialog / drag handle.
        diff_view = QPlainTextEdit()
        diff_view.setReadOnly(True)
        diff_view.setMinimumHeight(160)
        diff_view.setPlaceholderText(_("Select a file to inspect its diff"))

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(list_widget)
        splitter.addWidget(diff_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([220, 320])
        layout.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        btn_accept = buttons.addButton("Accept .pacnew", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_delete = buttons.addButton("Delete .pacnew", QDialogButtonBox.ButtonRole.DestructiveRole)
        btn_close = buttons.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)

        def show_diff():
            item = list_widget.currentItem()
            if not item:
                return
            diff_view.setPlainText(diff_pacnew(item.data(0x0100)))

        def keep_selection():
            # After Accept/Delete the current row vanishes; move to an adjacent
            # item (never to an out-of-range row) so the diff doesn't blank out
            # and the last remaining entry stays reachable without reopening.
            if list_widget.count() == 0:
                diff_view.clear()
                return
            row = list_widget.currentRow()
            if row < 0:
                row = 0
            elif row >= list_widget.count():
                row = list_widget.count() - 1
            list_widget.setCurrentRow(row)
            show_diff()

        list_widget.currentItemChanged.connect(lambda *a: show_diff())

        def accept_current():
            item = list_widget.currentItem()
            if not item:
                return
            path = item.data(0x0100)
            reply = QMessageBox.question(
                self, "Accept .pacnew",
                f"Replace the current config with:\n\n{path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            if not self.ensure_session_auth():
                self.log("Config update cancelled: authentication required.")
                return
            if accept_pacnew(path):
                list_widget.takeItem(list_widget.row(item))
                keep_selection()
                self.show_message.emit("Config Files", "Config updated.")
                try:
                    self._refresh_installed_health_async()
                except Exception:
                    pass
            else:
                self.show_message.emit("Config Files", "Failed to apply .pacnew file.")

        def delete_current():
            item = list_widget.currentItem()
            if not item:
                return
            path = item.data(0x0100)
            reply = QMessageBox.question(
                self, "Delete .pacnew",
                f"Delete without applying?\n\n{path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            if delete_pacnew(path):
                list_widget.takeItem(list_widget.row(item))
                keep_selection()
                self.show_message.emit("Config Files", ".pacnew file deleted.")
                try:
                    self._refresh_installed_health_async()
                except Exception:
                    pass
            else:
                self.show_message.emit("Config Files", "Failed to delete .pacnew file.")

        btn_accept.clicked.connect(accept_current)
        btn_delete.clicked.connect(delete_current)
        btn_close.clicked.connect(dlg.reject)
        layout.addWidget(buttons)

        list_widget.setCurrentRow(0)
        show_diff()
        dlg.exec()

    def show_arch_news(self):
        """Fetch and display the latest Arch Linux news."""
        from neoarch.backend.services.hygiene import fetch_news, news_seen_status, mark_news_seen
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                                     QTextBrowser, QDialogButtonBox)
        self.log("Fetching Arch Linux news...")
        items = fetch_news()
        if not items:
            self.show_message.emit("Arch News", "Could not fetch news. Check your connection.")
            return
        entries = news_seen_status(items)
        unseen = sum(1 for e in entries if not e.get("seen"))
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Arch Linux News"))
        dlg.resize(720, 540)
        layout = QVBoxLayout(dlg)
        if unseen:
            hint = QLabel(f"Latest from archlinux.org — {unseen} new")
            hint.setStyleSheet("color: #00BFAE; font-weight: 600;")
        else:
            hint = QLabel(_("Latest from archlinux.org"))
            hint.setStyleSheet("color: #8B8D97;")
        layout.addWidget(hint)

        browser = QTextBrowser()
        html = []
        for entry in entries:
            date = entry.get("published", "")
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            badge = "" if entry.get("seen") else \
                f"<span style='background:{Colors.ACCENT};color:{Colors.BG};border-radius:4px;" \
                f"padding:1px 6px;font-size:{Fonts.XS};font-weight:700;'>NEW</span> "
            html.append(
                f"<h3 style='color:{Colors.ACCENT};'>{badge}{title}</h3>"
                f"<p style='color:#8B8D97;'>{date}</p>"
                f"<p>{summary}</p>"
                f"<p><a href='{link}'>{link}</a></p><hr>")
        browser.setHtml("\n".join(html))
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser, 1)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(dlg.reject)
        close_btn.accepted.connect(dlg.accept)
        layout.addWidget(close_btn)

        def _mark_read():
            for entry in entries:
                mark_news_seen(entry)
        dlg.finished.connect(lambda _res: _mark_read())
        dlg.exec()