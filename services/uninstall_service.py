import os
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer
from utils.workers import CommandWorker


def uninstall_packages(app, packages_by_source: dict):
    def uninstall():
        app.log("Uninstallation thread started")
        try:
            for source, pkgs in packages_by_source.items():
                if not pkgs:
                    continue
                if source in ('pacman', 'AUR'):
                    cmd = ["pacman", "-R", "--noconfirm"] + pkgs
                    app.log(f"Running: {' '.join(cmd)}")
                    worker = CommandWorker(cmd, sudo=True)
                    worker.output.connect(app.log)
                    worker.error.connect(app.log)
                    worker.run()
                elif source == 'Flatpak':
                    cmd = ["flatpak", "uninstall", "-y", "--noninteractive"] + pkgs
                    app.log(f"Running: {' '.join(cmd)}")
                    worker = CommandWorker(cmd, sudo=False)
                    worker.output.connect(app.log)
                    worker.error.connect(app.log)
                    worker.run()
                elif source == 'npm':
                    # Try to uninstall from both user and system global locations as needed
                    def _build_user_env():
                        e = os.environ.copy()
                        try:
                            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                            os.makedirs(npm_prefix, exist_ok=True)
                            e['npm_config_prefix'] = npm_prefix
                            e['NPM_CONFIG_PREFIX'] = npm_prefix
                            e['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + e.get('PATH', '')
                        except Exception:
                            pass
                        return e

                    def _list_installed(env=None):
                        try:
                            r = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env, timeout=30)
                            if r.returncode == 0 and r.stdout and r.stdout.strip():
                                import json
                                data = json.loads(r.stdout)
                                deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                return set(deps.keys())
                        except Exception:
                            pass
                        return set()

                    def _npm_root_writable(env=None):
                        try:
                            r = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, env=env, timeout=10)
                            root = (r.stdout or '').strip()
                            return bool(root) and os.access(root, os.W_OK)
                        except Exception:
                            return False

                    # User global
                    user_env = _build_user_env()
                    user_pkgs = _list_installed(env=user_env)
                    targets = [p for p in pkgs if p in user_pkgs]
                    if targets:
                        cmd = ["npm", "uninstall", "-g"] + targets
                        app.log(f"Running: {' '.join(cmd)} (user)")
                        worker = CommandWorker(cmd, sudo=False, env=user_env)
                        worker.output.connect(app.log)
                        worker.error.connect(app.log)
                        worker.run()

                    # System/global prefix
                    sys_pkgs = _list_installed(env=os.environ.copy())
                    targets_sys = [p for p in pkgs if p in sys_pkgs]
                    if targets_sys:
                        sudo_needed = not _npm_root_writable(env=os.environ.copy())
                        cmd = ["npm", "uninstall", "-g"] + targets_sys
                        app.log(f"Running: {' '.join(cmd)} ({'sudo' if sudo_needed else 'no-sudo'})")
                        worker = CommandWorker(cmd, sudo=sudo_needed, env=os.environ.copy())
                        worker.output.connect(app.log)
                        worker.error.connect(app.log)
                        worker.run()
            app.show_message.emit("Uninstallation Complete", f"Successfully processed {sum(len(v) for v in packages_by_source.values())} package(s).")
            QTimer.singleShot(0, app.load_installed_packages)
        except Exception as e:
            app.log(f"Error in uninstallation thread: {str(e)}")
    Thread(target=uninstall, daemon=True).start()
