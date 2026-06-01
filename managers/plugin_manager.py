import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer


class PluginsManager:
    def __init__(self, app):
        self.app = app

    def install_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            # Already installed?
            if plugins_view.is_installed(spec):
                self._message("Plugins", f"{spec.get('name')} is already installed")
                QTimer.singleShot(0, plugins_view.refresh_all)
                return
            pkg = spec.get('pkg')
            if not pkg:
                self._message("Plugins", "No package specified for installation")
                return
            from utils.workers import get_auth_command
            auth_cmd = get_auth_command()
            cmd = auth_cmd + ["pacman", "-S", "--noconfirm", pkg]
            self._log(f"Installing plugin package: {' '.join(cmd)}")

            def _run():
                try:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:  # type: ignore
                        if line:
                            self._log(line.rstrip())
                    rc = proc.wait()
                    if rc == 0:
                        self._message("Plugins", f"Installed {spec.get('name')}")
                    else:
                        self._message("Plugins", f"Install failed (code {rc})")
                except Exception as e:
                    self._message("Plugins", f"Install failed: {e}")
                finally:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, False))
                    QTimer.singleShot(200, plugins_view.refresh_all)

            Thread(target=_run, daemon=True).start()
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
            use_pkexec = plugin_id in ("timeshift",)
            terminal_apps = ["htop", "btop", "nvtop"]
            use_terminal = cmd in terminal_apps
            argv = [cmd]
            if use_pkexec:
                from utils.workers import get_auth_command
                auth_cmd = get_auth_command()
                argv = auth_cmd + argv
            if use_terminal:
                terminal_cmd = self._get_terminal_command()
                if terminal_cmd:
                    argv = terminal_cmd + argv
            self._log(f"Launching: {' '.join(argv)}")
            try:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
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
            # If not installed, just refresh UI
            if not plugins_view.is_installed(spec):
                QTimer.singleShot(0, plugins_view.refresh_all)
                return
            from utils.workers import get_auth_command
            auth_cmd = get_auth_command()
            cmd = auth_cmd + ["pacman", "-R", "--noconfirm", pkg]
            self._log(f"Uninstalling plugin package: {' '.join(cmd)}")

            def _run():
                try:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:  # type: ignore
                        if line:
                            self._log(line.rstrip())
                    rc = proc.wait()
                    if rc == 0:
                        self._message("Plugins", f"Uninstalled {spec.get('name')}")
                    else:
                        self._message("Plugins", f"Uninstall failed (code {rc})")
                except Exception as e:
                    self._message("Plugins", f"Uninstall failed: {e}")
                finally:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, False))
                    QTimer.singleShot(200, plugins_view.refresh_all)

            Thread(target=_run, daemon=True).start()
        except Exception as e:
            self._message("Plugins", f"Uninstall error: {e}")

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
