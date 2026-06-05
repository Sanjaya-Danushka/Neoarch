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
            return
        text = "The following dependencies are missing and are required for best experience:\n\n" + "\n".join(f"\u2022 {m}" for m in missing) + "\n\nInstall now?"
        reply = QMessageBox.question(self, "Setup Environment", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            Thread(target=lambda: self.install_dependencies(missing), daemon=True).start()

    def install_dependencies(self, missing):
        try:
            pacman_pkgs = [p for p in missing if p not in ["yay", "yay or paru"]]
            if pacman_pkgs:
                cmd = ["pacman", "-S", "--needed", "--noconfirm"] + pacman_pkgs
                worker = CommandWorker(cmd, sudo=True)
                worker.output.connect(self.log)
                worker.error.connect(self.log)
                done_event = Event()
                worker.finished.connect(lambda: done_event.set())
                worker.run()
                done_event.wait(timeout=1)
            if ("yay" in missing or "yay or paru" in missing) and self.cmd_exists("git"):
                self.install_aur_helper()
            self.show_message.emit("Environment", "Dependency setup completed")
        except Exception as e:
            self.show_message.emit("Environment", f"Setup failed: {str(e)}")

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
