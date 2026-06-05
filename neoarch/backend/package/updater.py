"""Package update orchestrator.

Handles updating packages from all sources (pacman, AUR, Flatpak, npm, Local)
with appropriate privilege elevation.
"""

import os
import json
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer

from neoarch.backend.workers import CommandWorker
from neoarch.backend.auth import get_askpass_env
from neoarch.backend import sys_utils

__all__ = [
    "update_packages", "update_core_tools",
    "_update_system_packages", "_update_flatpak", "_update_npm", "_update_aur",
]


def update_packages(app, packages_by_source: dict):
    """Update specific packages organized by source.

    Args:
        app: Main window instance (provides signals and UI state).
        packages_by_source: Dict mapping source names to package name lists.
    """
    app.install_cancel_event = __import__('threading').Event()

    def update():
        try:
            overall_success = True
            lock_detected = False
            lock_details = ""
            total_pkgs = sum(len(pkgs) for pkgs in packages_by_source.values())
            updated_pkgs = 0
            cancelled = False
            failed_sources = []

            def emit_progress(msg, inc=None):
                nonlocal updated_pkgs
                if inc:
                    updated_pkgs += inc
                pct = int((updated_pkgs / total_pkgs) * 100) if total_pkgs > 0 else -1
                try:
                    app.progress_update.emit(msg, pct)
                except Exception:
                    pass

            for source, pkgs in packages_by_source.items():
                if app.install_cancel_event.is_set():
                    app.log("Update cancelled by user")
                    cancelled = True
                    break
                emit_progress(f"Updating {source} packages...")
                source_count = len(pkgs)
                if source == 'pacman':
                    cmd = ["pacman", "-S", "--noconfirm"] + pkgs
                    worker = CommandWorker(cmd, sudo=True, cancel_event=app.install_cancel_event)
                    worker.output.connect(app.log)
                    worker.line_update.connect(app.log_line_update)
                    def _on_err(msg):
                        nonlocal overall_success, lock_detected, lock_details, failed_sources
                        app.log(msg)
                        m = (msg or '').lower()
                        if 'could not lock database' in m or 'unable to lock database' in m:
                            lock_detected = True
                            lock_details = msg
                        overall_success = False
                        if 'pacman' not in failed_sources:
                            failed_sources.append('pacman')
                    worker.error.connect(_on_err)
                    worker.run()
                    emit_progress(f"Completed {source} packages", source_count)
                    if app.install_cancel_event.is_set():
                        app.log("Update cancelled by user")
                        cancelled = True
                        break
                elif source == 'AUR':
                    preferred = app.settings.get('aur_helper', 'auto')
                    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
                    if not aur_helper:
                        app.log("Error: No AUR helper available. Install yay, paru, trizen, or pikaur.")
                        overall_success = False
                        continue
                    env = get_askpass_env()
                    cmd = [aur_helper, "-S", "--noconfirm"] + pkgs
                    worker = CommandWorker(cmd, sudo=False, env=env, cancel_event=app.install_cancel_event)
                    worker.output.connect(app.log)
                    worker.line_update.connect(app.log_line_update)
                    def _on_err_aur(msg):
                        nonlocal overall_success, failed_sources
                        app.log(msg)
                        overall_success = False
                        if 'AUR' not in failed_sources:
                            failed_sources.append('AUR')
                    worker.error.connect(_on_err_aur)
                    worker.run()
                    emit_progress(f"Completed {source} packages", source_count)
                    if app.install_cancel_event.is_set():
                        app.log("Update cancelled by user")
                        cancelled = True
                        break
                elif source == 'Flatpak':
                    cmd = ["flatpak", "update", "-y", "--noninteractive"] + pkgs
                    worker = CommandWorker(cmd, sudo=False, cancel_event=app.install_cancel_event)
                    worker.output.connect(app.log)
                    worker.line_update.connect(app.log_line_update)
                    def _on_err_fp(msg):
                        nonlocal overall_success, failed_sources
                        app.log(msg)
                        overall_success = False
                        if 'Flatpak' not in failed_sources:
                            failed_sources.append('Flatpak')
                    worker.error.connect(_on_err_fp)
                    worker.run()
                    emit_progress(f"Completed {source} packages", source_count)
                    if app.install_cancel_event.is_set():
                        app.log("Update cancelled by user")
                        cancelled = True
                        break
                elif source == 'npm':
                    env_user = os.environ.copy()
                    try:
                        npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                        os.makedirs(npm_prefix, exist_ok=True)
                        env_user['npm_config_prefix'] = npm_prefix
                        env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                        env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                    except Exception:
                        pass
                    env_sys = os.environ.copy()

                    user_pkgs, sys_pkgs, unknown_pkgs = [], [], []
                    for name in pkgs:
                        placed = False
                        try:
                            r_user = subprocess.run(["npm", "ls", "-g", name, "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=30)
                            if r_user.returncode in (0, 1) and r_user.stdout:
                                try:
                                    data = json.loads(r_user.stdout)
                                    deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                    if name in deps:
                                        user_pkgs.append(name)
                                        placed = True
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        if placed:
                            continue
                        try:
                            r_sys = subprocess.run(["npm", "ls", "-g", name, "--depth=0", "--json"], capture_output=True, text=True, timeout=30)
                            if r_sys.returncode in (0, 1) and r_sys.stdout:
                                try:
                                    data = json.loads(r_sys.stdout)
                                    deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                    if name in deps:
                                        sys_pkgs.append(name)
                                        placed = True
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        if not placed:
                            user_pkgs.append(name)

                    if user_pkgs:
                        cmd_u = ["npm", "update", "-g"] + user_pkgs
                        w_u = CommandWorker(cmd_u, sudo=False, env=env_user, cancel_event=app.install_cancel_event)
                        w_u.output.connect(app.log)
                        w_u.line_update.connect(app.log_line_update)
                        def _on_err_np_u(msg):
                            nonlocal overall_success, failed_sources
                            app.log(msg)
                            overall_success = False
                            if 'npm' not in failed_sources:
                                failed_sources.append('npm')
                        w_u.error.connect(_on_err_np_u)
                        w_u.run()
                    if sys_pkgs:
                        cmd_s = ["npm", "update", "-g"] + sys_pkgs
                        w_s = CommandWorker(cmd_s, sudo=True, env=env_sys, cancel_event=app.install_cancel_event)
                        w_s.output.connect(app.log)
                        w_s.line_update.connect(app.log_line_update)
                        def _on_err_np_s(msg):
                            nonlocal overall_success, failed_sources
                            app.log(msg)
                            overall_success = False
                            if 'npm' not in failed_sources:
                                failed_sources.append('npm')
                        w_s.error.connect(_on_err_np_s)
                        w_s.run()
                    emit_progress(f"Completed {source} packages", source_count)
                    if app.install_cancel_event.is_set():
                        app.log("Update cancelled by user")
                        cancelled = True
                        break
                elif source == 'Local':
                    entries = { (e.get('id') or e.get('name')): e for e in app.load_local_update_entries() }
                    for token in pkgs:
                        e = entries.get(token) or entries.get(token.strip())
                        if not e:
                            continue
                        upd = e.get('update_cmd')
                        if not upd:
                            continue
                        try:
                            process = subprocess.Popen(["bash", "-lc", upd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            while True:
                                line = process.stdout.readline() if process.stdout else ""
                                if not line and process.poll() is not None:
                                    break
                                if line:
                                    app.log(line.strip())
                            _, stderr = process.communicate()
                            if process.returncode != 0 and stderr:
                                app.log(f"Error: {stderr}")
                                overall_success = False
                        except Exception as ex:
                            app.log(str(ex))
                    emit_progress(f"Completed {source} packages", source_count)
                    if app.install_cancel_event.is_set():
                        app.log("Update cancelled by user")
                        cancelled = True
                        break
            if cancelled:
                try:
                    app.installation_progress.emit("cancelled", False)
                except Exception:
                    pass
            elif lock_detected:
                try:
                    app.ui_call.emit(lambda: app.show_busy_pm_warning(lock_details, retry_action=lambda: update_packages(app, packages_by_source)))
                except Exception:
                    pass
            elif overall_success:
                try:
                    app.progress_update.emit("Update complete!", 100)
                except Exception:
                    pass
                app.show_message.emit("Update Complete", f"Successfully updated {sum(len(v) for v in packages_by_source.values())} package(s).")
                try:
                    app.installation_progress.emit("success", False)
                except Exception:
                    pass
            else:
                failed_msg = "Some updates failed"
                if failed_sources:
                    failed_msg += f" ({', '.join(failed_sources)})"
                failed_msg += ". See console for details."
                try:
                    app.progress_update.emit(failed_msg, -1)
                except Exception:
                    pass
                app.show_message.emit("Update Partial", failed_msg)
                try:
                    app.installation_progress.emit("failed", False)
                except Exception:
                    pass
            try:
                app.ui_call.emit(app.refresh_packages)
            except Exception:
                pass
        except Exception as e:
            app.log(f"Error in update thread: {str(e)}")
        finally:
            try:
                if hasattr(app, 'install_cancel_event'):
                    delattr(app, 'install_cancel_event')
            except Exception:
                pass
    Thread(target=update, daemon=True).start()


def update_core_tools(app):
    """Update core system tools (pacman, Flatpak, npm, AUR helpers)."""
    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Updating tools...")
    app.loading_widget.start_animation()

    def do_update():
        try:
            app.progress_update.emit("Updating system packages...", 0)
            _update_system_packages(app)
            app.progress_update.emit("Updating Flatpak packages...", 25)
            _update_flatpak(app)
            app.progress_update.emit("Updating npm packages...", 50)
            _update_npm(app)
            app.progress_update.emit("Updating AUR packages...", 75)
            _update_aur(app)
            app.progress_update.emit("Tools updated!", 100)
            app.show_message.emit("Environment", "Tools updated")
        except Exception as e:
            try:
                app.progress_update.emit(f"Update failed: {str(e)}", -1)
            except Exception:
                pass
            app.show_message.emit("Environment", f"Update failed: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass
    Thread(target=do_update, daemon=True).start()


def _update_system_packages(app):
    """Update system packages with pacman."""
    deps = ["flatpak", "git", "nodejs", "npm", "docker"]
    if app.cmd_exists("pacman"):
        w1 = CommandWorker(["pacman", "-Syu", "--noconfirm"] + deps, sudo=True)
        w1.output.connect(app.log)
        w1.line_update.connect(app.log_line_update)
        w1.error.connect(app.log)
        w1.run()


def _update_flatpak(app):
    """Update Flatpak and ensure remote is configured."""
    try:
        app.ensure_flathub_user_remote()
    except Exception:
        pass
    try:
        update_ids = set()
        for scope in ([], ["--user"], ["--system"]):
            cmdu = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
            fu = subprocess.run(cmdu, capture_output=True, text=True, timeout=60, check=False)
            if fu.returncode == 0 and fu.stdout:
                for ln in [x for x in fu.stdout.strip().split('\n') if x.strip()]:
                    cols = ln.split('\t')
                    if cols:
                        update_ids.add(cols[0].strip())
    except Exception:
        pass
    if app.cmd_exists("flatpak"):
        w2 = CommandWorker(["flatpak", "--user", "update", "-y"], sudo=False)
        w2.output.connect(app.log)
        w2.line_update.connect(app.log_line_update)
        w2.error.connect(app.log)
        w2.run()


def _update_npm(app):
    """Update npm global packages."""
    if app.cmd_exists("npm"):
        env = os.environ.copy()
        try:
            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
            os.makedirs(npm_prefix, exist_ok=True)
            env['npm_config_prefix'] = npm_prefix
            env['NPM_CONFIG_PREFIX'] = npm_prefix
            env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
        except Exception:
            pass
        w3 = CommandWorker(["npm", "update", "-g"], sudo=False, env=env)
        w3.output.connect(app.log)
        w3.line_update.connect(app.log_line_update)
        w3.error.connect(app.log)
        w3.run()


def _update_aur(app):
    """Update AUR packages."""
    preferred = app.settings.get('aur_helper', 'auto')
    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
    if aur_helper:
        env = get_askpass_env()
        w4 = CommandWorker([aur_helper, "-Syu", "--noconfirm", "--sudoflags", "-A"], sudo=False, env=env)
        w4.output.connect(app.log)
        w4.line_update.connect(app.log_line_update)
        w4.error.connect(app.log)
        w4.run()
    else:
        app.log("No AUR helper available. Install yay, paru, trizen, or pikaur.")
