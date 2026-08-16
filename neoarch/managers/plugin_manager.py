"""PluginsManager - install, launch, and uninstall plugins.

All privileged operations route through the same authentication pipeline as
the rest of the app (``ensure_session_auth`` + the shared install/uninstall
services), so the password prompt is always the standard NeoArch dialog.
"""

import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer

from neoarch.backend.package import installer as install_service
from neoarch.backend.package import uninstaller as uninstall_service

_SUPPORTED_SOURCES = ("pacman", "AUR", "Flatpak", "npm")


def _resolve_source(pkg):
    """Map a plugin ``pkg`` field to ``(source, plain_name)``.

    Examples: ``aur/yay`` -> ``('AUR', 'yay')``,
    ``org.gnome.Evolution.flatpak`` -> ``('Flatpak', 'org.gnome.Evolution')``,
    ``npm-typescript`` -> ``('npm', 'typescript')``, ``bleachbit`` -> pacman.
    """
    pkg = (pkg or "").strip()
    low = pkg.lower()
    if low.startswith("npm-"):
        return "npm", pkg[len("npm-"):]
    if "/" in pkg and low.startswith("aur/"):
        return "AUR", pkg.split("/", 1)[1].strip() or pkg
    if low.endswith(".flatpak"):
        return "Flatpak", pkg.rsplit(".", 1)[0]
    if low.startswith("brew-"):
        return "brew", pkg[len("brew-"):]
    return "pacman", pkg


class PluginsManager:
    """Manages plugin installation, launching, and removal"""

    def __init__(self, app):
        self.app = app

    def install_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            if plugins_view.is_installed(spec):
                self._message("Plugins", f"{spec.get('name')} is already installed")
                QTimer.singleShot(0, lambda: plugins_view.refresh_all(force=True))
                return
            pkg = spec.get('pkg')
            if not pkg:
                self._message("Plugins", "No package specified for installation")
                return
            source, name = _resolve_source(pkg)
            if source not in _SUPPORTED_SOURCES:
                self._message("Plugins", f"Unsupported package source: {source}")
                return
            if not self.app.ensure_session_auth():
                self._message("Plugins", "Install cancelled: authentication required.")
                return
            QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
            self.app.force_sudo_install = False
            self.app._pending_install_packages = {source: [name]}
            self._log(f"Installing plugin package: {name} ({source})")
            self._watch_completion(plugins_view, plugin_id, "install")
            install_service.install_packages(self.app, {source: [name]})
        except Exception as e:
            self._message("Plugins", f"Install error: {e}")

    def install_many_by_id(self, plugins_view, plugin_ids):
        """Install several plugins in a single batched operation (one command
        per source, one auth prompt). Skips plugins already installed."""
        try:
            specs = []
            for plugin_id in plugin_ids:
                spec = plugins_view.get_plugin(plugin_id)
                if not spec:
                    continue
                if plugins_view.is_installed(spec):
                    continue
                specs.append(spec)
            if not specs:
                self._message("Plugins", "Nothing to install: the selected plugins are already installed")
                return
            by_source = {}
            for spec in specs:
                pkg = spec.get('pkg')
                if not pkg:
                    self._message("Plugins", f"{spec.get('name')} has no package specified")
                    return
                source, name = _resolve_source(pkg)
                if source not in _SUPPORTED_SOURCES:
                    self._message("Plugins", f"Unsupported package source for {spec.get('name')}: {source}")
                    return
                by_source.setdefault(source, []).append(name)
            if not self.app.ensure_session_auth():
                self._message("Plugins", "Install cancelled: authentication required.")
                return
            for spec in specs:
                pid = spec.get('id')
                QTimer.singleShot(0, lambda pid=pid: plugins_view.set_installing(pid, True))
            self.app.force_sudo_install = False
            self.app._pending_install_packages = by_source
            self._log(f"Installing {len(specs)} plugin package(s): {by_source}")
            for spec in specs:
                self._watch_completion(plugins_view, spec.get('id'), "install")
            install_service.install_packages(self.app, by_source)
        except Exception as e:
            self._message("Plugins", f"Install error: {e}")

    def launch_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            cmd = spec.get('cmd')
            if not cmd:
                self._message("Plugins", "No launch command defined")
                return
            needs_root = plugin_id in ("timeshift",)
            terminal_apps = ["htop", "btop", "nvtop"]
            use_terminal = cmd in terminal_apps
            argv = [cmd]
            env = None
            if needs_root:
                if not self.app.ensure_session_auth():
                    self._message("Plugins", "Launch cancelled: authentication required.")
                    return
                argv = ["sudo", "-A"] + argv
                env = self.app.get_askpass_env()
            if use_terminal:
                terminal_cmd = self._get_terminal_command()
                if terminal_cmd:
                    argv = terminal_cmd + argv
            self._log(f"Launching: {' '.join(argv)}")
            try:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL, start_new_session=True, env=env)
            except Exception as e:
                self._message("Plugins", f"Launch failed: {e}")
        except Exception as e:
            self._message("Plugins", f"Launch error: {e}")

    def uninstall_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            pkg = spec.get('pkg')
            if not pkg:
                self._message("Plugins", "No package specified for uninstall")
                return
            if not plugins_view.is_installed(spec):
                QTimer.singleShot(0, lambda: plugins_view.refresh_all(force=True))
                return
            source, name = _resolve_source(pkg)
            if source not in _SUPPORTED_SOURCES:
                self._message("Plugins", f"Unsupported package source: {source}")
                return
            if not self.app.ensure_session_auth():
                self._message("Plugins", "Uninstall cancelled: authentication required.")
                return
            QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
            self._log(f"Uninstalling plugin package: {name} ({source})")
            self._watch_completion(plugins_view, plugin_id, "uninstall")
            uninstall_service.uninstall_packages(self.app, {source: [name]})
        except Exception as e:
            self._message("Plugins", f"Uninstall error: {e}")

    def _watch_completion(self, plugins_view, plugin_id, op="install"):
        """Reset the card state, flip it to its real installed state, and
        refresh once the shared service reports done."""
        app = self.app

        def on_progress(status, _can_cancel):
            if status not in ("success", "failed", "cancelled"):
                return
            try:
                app.installation_progress.disconnect(on_progress)
            except Exception:
                pass
            QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, False))
            if status == "success":
                QTimer.singleShot(0, lambda: plugins_view.set_installed(plugin_id, op == "install"))
            QTimer.singleShot(200, lambda: plugins_view.refresh_all(force=True))

        try:
            app.installation_progress.connect(on_progress)
        except Exception:
            pass

    def open_plugins_folder(self):
        try:
            folder = self.app.get_user_plugins_dir()
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
            subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._message("Plugins", f"Cannot open folder: {e}")

    def _log(self, msg):
        try:
            self.app.log_signal.emit(msg)
        except Exception:
            pass

    @staticmethod
    def _get_terminal_command():
        terminals = ["kitty", "alacritty", "gnome-terminal", "konsole", "xterm"]
        for term in terminals:
            if shutil.which(term):
                if term == "kitty":
                    return [term, "-e"]
                elif term == "alacritty":
                    return [term, "-e"]
                elif term == "gnome-terminal":
                    return [term, "--", "bash", "-c"]
                elif term == "konsole":
                    return [term, "-e"]
                elif term == "xterm":
                    return [term, "-e"]
        return None

    def _message(self, title, text):
        try:
            self.app.show_message.emit(title, text)
        except Exception:
            pass
