"""Authentication, first-run setup, and system utility mixin."""

import os
import subprocess
import tempfile
import shutil
from threading import Thread, Event

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from neoarch.backend import config_utils, sys_utils
from neoarch.backend.auth import get_askpass_env as _get_askpass_env
from neoarch.backend.workers import CommandWorker
from neoarch.backend.package.updater import update_core_tools
from neoarch.backend.services.snapshot import (
    create_snapshot,
    revert_to_snapshot,
    restore_snapshot,
    delete_snapshots,
)


class _AuthMixin:
    def get_ignore_file_path(self):
        return config_utils.get_ignore_file_path()

    def load_ignored_updates(self):
        return config_utils.load_ignored_updates()

    def save_ignored_updates(self, items):
        return config_utils.save_ignored_updates(items)

    def get_local_updates_file_path(self):
        return config_utils.get_local_updates_file_path()

    def load_local_update_entries(self):
        return config_utils.load_local_update_entries()

    def cmd_exists(self, cmd):
        return sys_utils.cmd_exists(cmd)

    def get_missing_dependencies(self):
        return sys_utils.get_missing_dependencies()

    def run_first_run_checks(self):
        missing = self.get_missing_dependencies()
        if not missing:
            self.log("All required dependencies present")
            return
        text = "The following dependencies are missing and are required for best experience:\n\n" + "\n".join(f"\u2022 {m}" for m in missing) + "\n\nInstall now?"
        reply = QMessageBox.question(self, "Setup Environment", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            Thread(target=self.install_dependencies, args=(missing,), daemon=True).start()

    def install_dependencies(self, missing):
        try:
            self.log(f"Installing missing dependencies: {', '.join(missing)}")
            if not self.cmd_exists("git"):
                self.log("Installing git first...")
                self._run_sudo_install(["git"])
            pacman_pkgs = [p for p in missing if p not in ("yay or paru", "yay", "paru", "python-supabase")]
            if pacman_pkgs:
                self._run_sudo_install(pacman_pkgs)
            if "python-supabase" in missing:
                self._install_pip_module("supabase")
            if ("yay or paru" in missing or "yay" in missing or "paru" in missing) and self.cmd_exists("git"):
                self.install_aur_helper()
            remaining = self.get_missing_dependencies()
            if remaining:
                self.log(f"Still missing after setup: {', '.join(remaining)}")
                self.show_message.emit("Environment", f"Dependency setup incomplete. Still missing: {', '.join(remaining)}")
            else:
                self.show_message.emit("Environment", "Dependency setup completed")
        except Exception as e:
            self.log(f"Setup failed: {str(e)}")
            self.show_message.emit("Environment", f"Setup failed: {str(e)}")

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

    def _install_pip_module(self, module):
        self.log(f"Installing Python module via pip: {module}")
        done = Event()
        failed = {"v": False}
        worker = CommandWorker(["pip", "install", "--user", "--break-system-packages", module], sudo=False)
        worker.output.connect(self.log)
        worker.error.connect(self.log)
        worker.error.connect(lambda _msg: failed.__setitem__("v", True))
        worker.finished.connect(lambda: done.set())
        worker.run()
        done.wait(timeout=300)
        if failed["v"]:
            raise RuntimeError(f"pip install failed for: {module}")

    def install_aur_helper(self):
        tmpdir = tempfile.mkdtemp(prefix="neoarch-yay-")
        try:
            self.log("Installing yay AUR helper...")
            clone = subprocess.run(["git", "clone", "https://aur.archlinux.org/yay-bin.git", tmpdir], capture_output=True, text=True, timeout=120)
            if clone.returncode != 0:
                self.log(f"Error: {clone.stderr}")
                return
            env, cleanup = self.prepare_askpass_env()
            cmd = f"cd '{tmpdir}' && makepkg -si --noconfirm"
            process = subprocess.Popen(["bash", "-lc", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
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

    def _startup_auth_and_sync(self):
        try:
            self._startup_auth_and_sync_impl()
        except Exception as e:
            self.log(f"Session auth skipped: {e}")
            self._finish_startup_no_auth()

    def _startup_auth_and_sync_impl(self):
        from neoarch.backend.session_auth import setup_session_auth, is_session_active

        if is_session_active():
            QTimer.singleShot(50, lambda: self.switch_view("updates"))
            return

        success = setup_session_auth(self)
        if success:
            self.log("Session authentication established")
            QTimer.singleShot(50, lambda: self.switch_view("updates"))
        else:
            self.log("Session authentication declined or failed")
            self._finish_startup_no_auth()

    def _finish_startup_no_auth(self):
        self.switch_view("updates")

    def update_core_tools(self):
        return update_core_tools(self)

    def get_sudo_askpass(self):
        from neoarch.backend.auth import get_sudo_askpass
        return get_sudo_askpass()

    def prepare_askpass_env(self):
        from neoarch.backend.auth import prepare_askpass_env
        return prepare_askpass_env()

    def get_askpass_env(self):
        return _get_askpass_env()

    def check_authentication_tools(self):
        pass
        is_supported, message = sys_utils.check_aur_authentication_support()
        if not is_supported:
            QTimer.singleShot(2000, lambda: self.show_message.emit("AUR Authentication Warning", message))

    def create_snapshot(self):
        return create_snapshot(self)

    def revert_to_snapshot(self):
        return revert_to_snapshot(self)

    def _restore_snapshot(self, snapshot_num):
        return restore_snapshot(self, snapshot_num)

    def delete_snapshots(self):
        return delete_snapshots(self)

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
        dlg.setWindowTitle("Restore Backup")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Select a backup to restore packages from:"))
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
        self.log(f"Removing {len(orphans)} orphaned package(s)...")

        def on_done(ok):
            self.show_message.emit(
                "Cleanup",
                "Orphaned packages removed." if ok else "Failed to remove orphaned packages.")

        remove_orphans(progress_cb=self.log, finished_cb=on_done)

    def manage_pacnew(self):
        """Show the .pacnew file manager dialog."""
        from neoarch.backend.services.hygiene import list_pacnew, diff_pacnew, accept_pacnew, delete_pacnew
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                     QListWidget, QListWidgetItem, QDialogButtonBox,
                                     QPlainTextEdit, QMessageBox)
        files = list_pacnew()
        if not files:
            self.show_message.emit("Config Files", "No .pacnew files found. System is clean.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(".pacnew Files")
        dlg.resize(760, 520)
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
        layout.addWidget(list_widget, 1)

        diff_view = QPlainTextEdit()
        diff_view.setReadOnly(True)
        diff_view.setMaximumHeight(200)
        layout.addWidget(diff_view)

        buttons = QDialogButtonBox()
        btn_accept = buttons.addButton("Accept .pacnew", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_delete = buttons.addButton("Delete .pacnew", QDialogButtonBox.ButtonRole.DestructiveRole)
        btn_close = buttons.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)

        def show_diff():
            item = list_widget.currentItem()
            if not item:
                return
            diff_view.setPlainText(diff_pacnew(item.data(0x0100)))

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
            if accept_pacnew(path):
                list_widget.takeItem(list_widget.row(item))
                diff_view.clear()
                self.show_message.emit("Config Files", "Config updated.")
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
                diff_view.clear()
                self.show_message.emit("Config Files", ".pacnew file deleted.")
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
        dlg.setWindowTitle("Arch Linux News")
        dlg.resize(720, 540)
        layout = QVBoxLayout(dlg)
        if unseen:
            hint = QLabel(f"Latest from archlinux.org — {unseen} new")
            hint.setStyleSheet("color: #00BFAE; font-weight: 600;")
        else:
            hint = QLabel("Latest from archlinux.org")
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
                "<span style='background:#00BFAE;color:#0C0C0E;border-radius:4px;" \
                "padding:1px 6px;font-size:10px;font-weight:700;'>NEW</span> "
            html.append(
                f"<h3 style='color:#00BFAE;'>{badge}{title}</h3>"
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
