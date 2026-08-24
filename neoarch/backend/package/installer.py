"""Package installation orchestrator.

Dispatches package installation to the appropriate backend
(pacman, AUR, Flatpak, npm) based on source type, handling
authentication and progress tracking.
"""

import os
import pty
import re
import select
import subprocess
from threading import Thread, Event

from neoarch.backend.auth import get_auth_command, get_askpass_env
from neoarch.backend.workers import CommandWorker, strip_ansi
from neoarch.backend import sys_utils
from neoarch.backend.package.errors import classify_error

__all__ = ["install_packages"]


def _clean_pacman_cache(app):
    """Remove freshly downloaded pacman cache after a cancelled install."""
    try:
        env = get_askpass_env()
        subprocess.run(
            ["sudo", "-A", "pacman", "-Sc", "--noconfirm"],
            capture_output=True, text=True, timeout=120, env=env,
        )
    except Exception:
        pass


def _process_pty_buf(buf, parse_output_line, worker, final=False):
    """Process PTY buffer, handling \\r progress updates and \\n line endings.

    Progress updates (from \\r) go to worker.line_update for in-place console
    updates. Complete lines (from \\n) go to worker.output for appending.
    """
    while '\n' in buf:
        line, buf = buf.split('\n', 1)
        stripped = line.strip()
        if not stripped:
            continue
        if '\r' in line:
            parts = line.split('\r')
            stripped = strip_ansi(parts[-1].strip())
            if not stripped:
                continue
        parse_output_line(stripped)
        worker.output.emit(stripped)

    if '\r' in buf:
        parts = buf.split('\r')
        stripped = strip_ansi(parts[-1].strip())
        if stripped:
            parse_output_line(stripped)
            worker.line_update.emit(stripped)
        buf = parts[-1]

    if final and buf:
        stripped = strip_ansi(buf.strip())
        if stripped:
            parse_output_line(stripped)
            worker.output.emit(stripped)
        buf = ""

    return buf


def install_packages(app, packages_by_source: dict):
    """Install packages from multiple sources.

    Handles pacman, AUR, Flatpak, and npm sources with appropriate
    privilege elevation for each. Runs in a background thread.

    Args:
        app: Main window instance (provides signals and UI state).
        packages_by_source: Dict mapping source names to package name lists.
    """
    def install():
        app._last_operation = "install"
        app.install_cancel_event = Event()
        app.installation_progress.emit("start", True)
        app.log_signal.emit("Installation thread started")

        success = True
        current_download_info = ""
        terminal_emitted = False

        def _emit_terminal(status, can_cancel=False):
            nonlocal terminal_emitted
            terminal_emitted = True
            app.installation_progress.emit(status, can_cancel)

        total_packages = sum(len(pkgs) for pkgs in packages_by_source.values())
        total_sources = len(packages_by_source)
        completed_packages = 0
        completed_sources = 0
        force_sudo = bool(getattr(app, 'force_sudo_install', False))

        def get_progress_percent():
            if total_packages == 0:
                return -1
            base = int((completed_packages / total_packages) * 100)
            return min(99, base)

        def update_progress_message(msg: str = ""):
            base_msg = f"Installing: {completed_packages}/{total_packages} packages"
            percent = get_progress_percent()
            try:
                parts = [base_msg]
                if current_download_info:
                    parts.append(current_download_info)
                if msg and msg != current_download_info:
                    parts.append(msg)
                full = " • ".join(parts)
                app.progress_update.emit(full, percent)
            except Exception:
                pass

        def parse_output_line(line: str):
            nonlocal current_download_info
            if "downloading" in line.lower() and ("mib" in line.lower() or "kib" in line.lower() or "gib" in line.lower()):
                size_match = re.search(r'\(([-\d.]+)\s*(MiB|KiB|GiB|B)\)', line)
                if size_match:
                    size, unit = size_match.groups()
                    current_download_info = f"Downloading {size} {unit}"
                    update_progress_message("")
            elif re.search(r'\[.*\]\s*\d+%', line):
                progress_match = re.search(r'(\d+)%', line)
                if progress_match:
                    percentage = progress_match.group(1)
                    if current_download_info:
                        current_download_info = f"{current_download_info} - {percentage}%"
                    else:
                        current_download_info = f"Downloading... {percentage}%"
                    update_progress_message("")
            elif "installed" in line.lower() or "upgraded" in line.lower():
                current_download_info = ""
                update_progress_message("")

        try:
            app._installed_packages = {}
            for source, packages in packages_by_source.items():
                if app.install_cancel_event.is_set():
                    app.log_signal.emit("Installation cancelled by user")
                    _emit_terminal("cancelled")
                    return

                update_progress_message(f"Installing from {source}...")

                env = os.environ.copy()

                if source == 'pacman':
                    cmd = ["pacman", "-S", "--noconfirm"] + packages
                elif source == 'AUR':
                    preferred = app.settings.get('aur_helper', 'auto')
                    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
                    if not aur_helper:
                        app.log_signal.emit("Error: No AUR helper available. Install yay, paru, trizen, or pikaur.")
                        success = False
                        break
                    cmd = [aur_helper, "-S", "--noconfirm"] + packages
                elif source == 'Flatpak':
                    try:
                        app.ensure_flathub_user_remote()
                    except Exception:
                        pass
                    if force_sudo:
                        cmd = ["flatpak", "install", "-y", "--noninteractive", "flathub"] + packages
                    else:
                        cmd = ["flatpak", "--user", "install", "-y", "--noninteractive", "flathub"] + packages
                elif source == 'npm':
                    if not force_sudo and sys_utils.npm_user_mode_enabled():
                        try:
                            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                            os.makedirs(npm_prefix, exist_ok=True)
                            env['npm_config_prefix'] = npm_prefix
                            env['NPM_CONFIG_PREFIX'] = npm_prefix
                            env['PREFIX'] = npm_prefix
                            env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
                        except Exception:
                            pass
                    cmd = ["npm", "install", "-g"] + packages
                else:
                    app.log_signal.emit(f"Unknown source {source} for packages {packages}")
                    continue

                app.log_signal.emit(f"Running command for {source}: {' '.join(cmd)}")

                if app.install_cancel_event.is_set():
                    app.log_signal.emit("Installation cancelled by user")
                    _emit_terminal("cancelled")
                    return

                if source == 'AUR':
                    app.log_signal.emit(f"AUR install (as user): {' '.join(cmd)}")
                if source == 'AUR' or (source == 'Flatpak' and force_sudo):
                    if not env.get('SUDO_ASKPASS'):
                        env = get_askpass_env(env)

                worker = CommandWorker(cmd, sudo=False, env=env)
                worker.output.connect(app.log_signal.emit)
                worker.line_update.connect(app.log_line_update)
                worker.error.connect(app.log_signal.emit)
                worker.output.connect(parse_output_line)

                try:
                    exec_cmd = worker.command
                    if source == 'pacman':
                        auth_cmd = get_auth_command(worker.env)
                        exec_cmd = auth_cmd + exec_cmd
                        app.log_signal.emit(f"Pacman command with {auth_cmd[0]}: {' '.join(exec_cmd)}")
                    elif force_sudo and source in ('Flatpak', 'npm'):
                        auth_cmd = get_auth_command(worker.env)
                        exec_cmd = auth_cmd + exec_cmd

                    if source in ('pacman', 'AUR'):
                        if 'DISPLAY' not in worker.env and 'DISPLAY' in os.environ:
                            worker.env['DISPLAY'] = os.environ['DISPLAY']
                        if 'XAUTHORITY' not in worker.env and 'XAUTHORITY' in os.environ:
                            worker.env['XAUTHORITY'] = os.environ['XAUTHORITY']
                        if 'WAYLAND_DISPLAY' not in worker.env and 'WAYLAND_DISPLAY' in os.environ:
                            worker.env['WAYLAND_DISPLAY'] = os.environ['WAYLAND_DISPLAY']
                        if 'DBUS_SESSION_BUS_ADDRESS' not in worker.env and 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                            worker.env['DBUS_SESSION_BUS_ADDRESS'] = os.environ['DBUS_SESSION_BUS_ADDRESS']

                    use_pty = source in ('pacman', 'AUR')

                    if use_pty:
                        master_fd, slave_fd = pty.openpty()
                        process = subprocess.Popen(
                            exec_cmd,
                            stdout=slave_fd,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL,
                            close_fds=True,
                            text=True,
                            start_new_session=True,
                            env=worker.env
                        )
                        os.close(slave_fd)
                    else:
                        process = subprocess.Popen(
                            exec_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL,
                            text=True,
                            bufsize=1,
                            start_new_session=True,
                            env=worker.env
                        )

                    buf = ""
                    stderr_collected = ""

                    if use_pty:
                        stderr_fd = None
                        if process.stderr is not None:
                            stderr_fd = process.stderr.fileno()
                            os.set_blocking(stderr_fd, False)
                        poller = select.poll()
                        poller.register(master_fd, select.POLLIN)
                        if stderr_fd is not None:
                            poller.register(stderr_fd, select.POLLIN)

                        while True:
                            if app.install_cancel_event.is_set():
                                process.terminate()
                                try:
                                    process.wait(timeout=5)
                                except subprocess.TimeoutExpired:
                                    process.kill()
                                app.log_signal.emit("Installation cancelled by user")
                                _emit_terminal("cancelled")
                                return

                            if process.poll() is not None:
                                break

                            try:
                                events = poller.poll(200)
                                for fd, event in events:
                                    if event & select.POLLHUP:
                                        continue
                                    if fd == master_fd and event & select.POLLIN:
                                        data = os.read(master_fd, 4096)
                                        if data:
                                            buf += data.decode('utf-8', errors='replace')
                                            buf = _process_pty_buf(buf, parse_output_line, worker)
                                    elif (stderr_fd is not None
                                          and fd == stderr_fd
                                          and event & select.POLLIN):
                                        data = os.read(stderr_fd, 4096)
                                        if data:
                                            chunk = data.decode('utf-8', errors='replace')
                                            stderr_collected += chunk
                                            for err_line in chunk.splitlines():
                                                err_line = err_line.strip()
                                                if err_line:
                                                    worker.output.emit(err_line)
                            except OSError:
                                break

                        # Drain remaining PTY data
                        try:
                            while True:
                                data = os.read(master_fd, 4096)
                                if not data:
                                    break
                                buf += data.decode('utf-8', errors='replace')
                        except OSError:
                            pass
                        _process_pty_buf(buf, parse_output_line, worker, final=True)
                        try:
                            os.close(master_fd)
                        except OSError:
                            pass

                        # Drain remaining stderr
                        if stderr_fd is not None:
                            try:
                                while True:
                                    chunk = os.read(stderr_fd, 4096)
                                    if not chunk:
                                        break
                                    stderr_collected += chunk.decode('utf-8', errors='replace')
                            except OSError:
                                pass
                            try:
                                process.stderr.close()
                            except Exception:
                                pass
                    else:
                        # Pipe mode (Flatpak, npm) — read stdout + stderr concurrently
                        err_buf = ""
                        while True:
                            if app.install_cancel_event.is_set():
                                process.terminate()
                                try:
                                    process.wait(timeout=5)
                                except subprocess.TimeoutExpired:
                                    process.kill()
                                app.log_signal.emit("Installation cancelled by user")
                                _emit_terminal("cancelled")
                                return

                            if process.poll() is not None:
                                break

                            fds_to_watch = [process.stdout]
                            if process.stderr:
                                fds_to_watch.append(process.stderr)
                            ready, _, _ = select.select(fds_to_watch, [], [], 0.2)
                            for f in ready:
                                if f is process.stdout:
                                    line = process.stdout.readline()
                                    if line:
                                        line = line.strip()
                                        parse_output_line(line)
                                        worker.output.emit(line)
                                elif f is process.stderr:
                                    chunk = process.stderr.readline()
                                    if chunk:
                                        err_buf += chunk

                        # Drain remaining
                        if process.stdout:
                            for line in process.stdout:
                                if line:
                                    line = line.strip()
                                    parse_output_line(line)
                                    worker.output.emit(line)
                        if process.stderr:
                            remaining = process.stderr.read()
                            if remaining:
                                err_buf += remaining
                        stderr_collected = err_buf

                    if process.returncode == 0:
                        completed_packages += len(packages)
                        completed_sources += 1
                        app._installed_packages[source] = packages
                        update_progress_message(f"Completed {source} packages")
                        app.log_signal.emit(f"Successfully installed {len(packages)} {source} package(s)")
                    else:
                        success = False
                        if stderr_collected:
                            result = classify_error(stderr_collected, source)
                            app._last_install_result = result
                            app.log_signal.emit(f"Error: {result.title} — {result.message}")
                            app.log_signal.emit(f"Process stderr: {stderr_collected}")
                            if source == 'AUR' and ("cancelled" in stderr_collected.lower() or "authentication failed" in stderr_collected.lower() or process.returncode == 1):
                                if "sudo: no askpass program specified" in stderr_collected.lower() or "authentication agent" in stderr_collected.lower():
                                    app.log_signal.emit("Error: Authentication failed - no GUI password dialog available")
                                    app.log_signal.emit("Start the operation again and authenticate in the NeoArch dialog.")
                                else:
                                    app.log_signal.emit("AUR installation cancelled by user")
                                _emit_terminal("cancelled")
                                return
                            if source == 'npm' and ("EACCES" in stderr_collected or "permission denied" in stderr_collected.lower()):
                                try:
                                    app.log_signal.emit("Permission denied installing npm package(s). Retrying with system privileges (polkit)...")
                                    env2 = os.environ.copy()
                                    auth_cmd2 = get_auth_command(env2)
                                    exec_cmd2 = auth_cmd2 + ["npm", "install", "-g"] + packages
                                    process2 = subprocess.Popen(
                                        exec_cmd2,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        stdin=subprocess.DEVNULL, text=True, bufsize=1,
                                        start_new_session=True, env=env2
                                    )
                                    while True:
                                        if app.install_cancel_event.is_set():
                                            process2.terminate()
                                            try:
                                                process2.wait(timeout=5)
                                            except subprocess.TimeoutExpired:
                                                process2.kill()
                                            app.log_signal.emit("Installation cancelled by user")
                                            _emit_terminal("cancelled")
                                            return
                                        if process2.poll() is not None:
                                            if process2.stdout:
                                                for line in process2.stdout:
                                                    if line:
                                                        line2 = line.strip()
                                                        parse_output_line(line2)
                                                        worker.output.emit(line2)
                                            break
                                        if process2.stdout and select.select([process2.stdout], [], [], 0.2)[0]:
                                            line2 = process2.stdout.readline()
                                            if line2:
                                                line2 = line2.strip()
                                                parse_output_line(line2)
                                                worker.output.emit(line2)
                                    if process2.returncode == 0:
                                        success = True
                                        completed_packages += len(packages)
                                        completed_sources += 1
                                        app._installed_packages[source] = packages
                                        update_progress_message(f"Completed {source} packages (elevated)")
                                        app.log_signal.emit(f"Successfully installed {len(packages)} {source} package(s) with system privileges")
                                    else:
                                        err2 = process2.stderr.read() if process2.stderr else ''
                                        worker.error.emit(f"Error: {err2 or stderr_collected}")
                                    continue
                                except Exception as _e:
                                    worker.error.emit(f"Error: {str(_e)}")

                            worker.error.emit(f"Error: {result.title} — {result.message}")
                finally:
                    pass

            if success and not app.install_cancel_event.is_set():
                try:
                    app.progress_update.emit("Installation complete!", 100)
                except Exception:
                    pass
                app.log_signal.emit("Install completed")
                app.show_message.emit("Installation Complete", f"Successfully installed {total_packages} package(s).")
                _emit_terminal("success")
            elif not success and not app.install_cancel_event.is_set():
                app.log_signal.emit("Install failed")
                _emit_terminal("failed")

        except Exception as e:
            app.log_signal.emit(f"Error in installation thread: {str(e)}")
            _emit_terminal("failed")
        finally:
            if not terminal_emitted:
                try:
                    was_cancelled = (hasattr(app, 'install_cancel_event')
                                     and app.install_cancel_event.is_set())
                    status = "cancelled" if was_cancelled else "failed"
                    app.log_signal.emit(f"Safety emit: {status}")
                    app.installation_progress.emit(status, False)
                except Exception:
                    pass
            try:
                if hasattr(app, 'install_cancel_event') and app.install_cancel_event.is_set():
                    _clean_pacman_cache(app)
            except Exception:
                pass
            try:
                if hasattr(app, 'force_sudo_install'):
                    app.force_sudo_install = False
            except Exception:
                pass
            if hasattr(app, 'install_cancel_event'):
                delattr(app, 'install_cancel_event')

    Thread(target=install, daemon=True).start()
