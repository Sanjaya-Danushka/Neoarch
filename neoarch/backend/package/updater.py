"""Package update orchestrator.

Handles updating packages from all sources (pacman, AUR, Flatpak, npm, Local)
with appropriate privilege elevation.
"""

import os
import json
import re
import subprocess
from threading import Thread

from neoarch.backend.workers import CommandWorker
from neoarch.backend.auth import get_askpass_env
from neoarch.backend import sys_utils

__all__ = [
    "update_packages", "update_core_tools",
    "_update_system_packages", "_update_flatpak", "_update_npm", "_update_aur",
]


_AUR_ERROR_HINTS = [
    (re.compile(r'no such file or directory'), "a build tool is missing (install base-devel)"),
    (re.compile(r'could not satisfy dependencies'), "there is a dependency conflict"),
    (re.compile(r'A failure occurred in build'), "a package failed to build"),
    (re.compile(r'exit status \d+'), "a package failed to build"),
    (re.compile(r'not found in remote repositories'), "a package was not found in the AUR"),
]


def _classify_aur_hint(msg):
    """Return a short human-readable hint for an AUR helper failure blob."""
    for pattern, label in _AUR_ERROR_HINTS:
        if pattern.search(msg or ''):
            return label
    return None


def parse_aur_failures(msg):
    """Parse AUR helper stderr into failed packages and a reason hint.

    Handles yay ("error making: <pkg>: <reason>") and paru ("Failed to
    install ... <pkg> - <reason>") output. Returns (failed, hint) where
    failed maps package names to their failure reasons.
    """
    failed = {}
    if not msg:
        return failed, None
    in_failed_section = False
    for line in msg.splitlines():
        text = line.strip()
        if not text:
            continue
        if 'manual intervention is required' in text.lower():
            in_failed_section = True
            continue
        m = re.search(r'error making:\s*(.+?):\s*(.*)$', text)
        if m:
            failed[m.group(1).strip()] = m.group(2).strip() or 'package failed to build'
            continue
        if in_failed_section:
            pkg = reason = None
            if ' - ' in text:
                pkg, _, reason = text.partition(' - ')
            else:
                sep = text.find(': ')
                if sep > 0:
                    pkg, reason = text[:sep], text[sep + 2:]
            if pkg and reason:
                failed[pkg.strip()] = reason.strip()
    return failed, _classify_aur_hint(msg)


def _clean_pacman_cache(app):
    """Remove freshly downloaded pacman cache after a cancelled operation.

    A cancelled update/install leaves downloaded packages in the pacman
    cache that are no longer needed, so scrub them before the operation
    reports "cancelled".
    """
    try:
        env = get_askpass_env()
        subprocess.run(
            ["sudo", "-A", "pacman", "-Sc", "--noconfirm"],
            capture_output=True, text=True, timeout=120, env=env,
        )
    except Exception:
        pass


def update_packages(app, packages_by_source: dict, upgrade_all: bool = False):
    """Update packages organized by source.

    Args:
        app: Main window instance (provides signals and UI state).
        packages_by_source: Dict mapping source names to package name lists.
        upgrade_all: When True (Update All), run a full system upgrade
            (pacman -Syu). When False, only the named targets are upgraded
            (pacman -Sy <targets>) so a single-app update does not touch the
            rest of the system.
    """
    app.install_cancel_event = __import__('threading').Event()

    def update():
        try:
            app._last_operation = "update"
            overall_success = True
            lock_detected = False
            lock_details = ""
            total_pkgs = sum(len(pkgs) for pkgs in packages_by_source.values())
            updated_pkgs = 0
            cancelled = False
            failed_sources = []
            aur_failures = {}
            aur_hint = None

            # Base percent offset of each source within the overall update.
            source_offsets = {}
            _acc = 0
            for source, pkgs in packages_by_source.items():
                source_offsets[source] = (_acc, len(pkgs))
                _acc += len(pkgs)

            def emit_progress(msg, inc=None):
                nonlocal updated_pkgs
                if inc:
                    updated_pkgs += inc
                pct = int((updated_pkgs / total_pkgs) * 100) if total_pkgs > 0 else -1
                try:
                    app.progress_update.emit(msg, pct)
                except Exception:
                    pass

            def pacman_progress_parser(source):
                """Yield per-package progress from pacman (X/Y) counters."""
                start, count = source_offsets.get(source, (0, 0))
                last = -1
                def _on_line(line):
                    nonlocal last
                    if not line:
                        return
                    m = re.search(r'\(\s*(\d+)\s*/\s*(\d+)\s*\)', line)
                    if not m or count <= 0:
                        return
                    x, y = int(m.group(1)), int(m.group(2))
                    if y <= 0:
                        return
                    frac = min(1.0, x / y)
                    pct = int(((start + frac * count) / total_pkgs) * 100) if total_pkgs else -1
                    pct = max(0, min(99, pct))
                    if pct != last:
                        last = pct
                        try:
                            app.progress_update.emit(f"Updating {source}: {x}/{y}", pct)
                        except Exception:
                            pass
                return _on_line

            for source, pkgs in packages_by_source.items():
                if app.install_cancel_event.is_set():
                    app.log("Update cancelled by user")
                    cancelled = True
                    break
                emit_progress(f"Updating {source} packages...")
                source_count = len(pkgs)
                if source == 'pacman':
                    if upgrade_all:
                        cmd = ["pacman", "-Syu", "--noconfirm"]
                    else:
                        cmd = ["pacman", "-Sy", "--noconfirm"] + pkgs
                    worker = CommandWorker(cmd, sudo=True, cancel_event=app.install_cancel_event)
                    worker.output.connect(app.log)
                    worker.line_update.connect(app.log_line_update)
                    worker.output.connect(pacman_progress_parser('pacman'))
                    worker.line_update.connect(pacman_progress_parser('pacman'))
                    def _on_err(msg):
                        nonlocal overall_success, lock_detected, lock_details
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
                        nonlocal overall_success, aur_hint
                        app.log(msg)
                        overall_success = False
                        if 'AUR' not in failed_sources:
                            failed_sources.append('AUR')
                        failed, hint = parse_aur_failures(msg)
                        aur_failures.update(failed)
                        if hint and not aur_hint:
                            aur_hint = hint
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
                        nonlocal overall_success
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
                            nonlocal overall_success
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
                            nonlocal overall_success
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
                # Tell the UI first, then scrub the freshly downloaded cache
                # (the worker thread blocking on pacman -Sc must not delay it).
                try:
                    _clean_pacman_cache(app)
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
                if aur_failures:
                    failed_msg += ": " + ", ".join(aur_failures.keys())
                if aur_hint:
                    failed_msg += f". {aur_hint.capitalize()}."
                failed_msg += " See console for details."
                try:
                    app.progress_update.emit(failed_msg, -1)
                except Exception:
                    pass
                app.show_message.emit("Update Partial", failed_msg)
                for name, reason in aur_failures.items():
                    app.log(f"  Failed AUR package: {name}: {reason}")
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
