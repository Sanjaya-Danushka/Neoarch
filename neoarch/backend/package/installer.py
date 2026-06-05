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

__all__ = ["install_packages"]


def _process_pty_buf(buf, parse_output_line, worker, final=False):
    """Process PTY buffer, handling \r progress updates and \n line endings.

    Progress updates (from \r) go to worker.line_update for in-place console
    updates. Complete lines (from \n) go to worker.output for appending.
    """
    while '\n' in buf:
        line, buf = buf.split('\n', 1)
        stripped = line.strip()
        if not stripped:
            continue
        if '\r' in line:
            parts = line.split('\r')
            stripped = strip_ansi(parts[-1].strip())
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
        app.install_cancel_event = Event()
        app.installation_progress.emit("start", True)
        app.log_signal.emit("Installation thread started")

        success = True
        current_download_info = ""

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
                    app.installation_progress.emit("cancelled", False)
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
                    if not force_sudo:
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
                    app.installation_progress.emit("cancelled", False)
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
                    while True:
                        if app.install_cancel_event.is_set():
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                            app.log_signal.emit("Installation cancelled by user")
                            app.installation_progress.emit("cancelled", False)
                            return

                        if process.poll() is not None:
                            break

                        if use_pty:
                            try:
                                data = os.read(master_fd, 4096)
                                if data:
                                    buf += data.decode('utf-8', errors='replace')
                                    buf = _process_pty_buf(buf, parse_output_line, worker)
                            except OSError:
                                pass
                        else:
                            if process.stdout and select.select([process.stdout], [], [], 0.2)[0]:
                                line = process.stdout.readline()
                                if line:
                                    line = line.strip()
                                    parse_output_line(line)
                                    worker.output.emit(line)

                    if use_pty:
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
                    else:
                        if process.stdout:
                            for line in process.stdout:
                                if line:
                                    line = line.strip()
                                    parse_output_line(line)
                                    worker.output.emit(line)

                    if process.returncode == 0:
                        completed_packages += len(packages)
                        completed_sources += 1
                        app._installed_packages[source] = packages
                        update_progress_message(f"Completed {source} packages")
                        app.log_signal.emit(f"Successfully installed {len(packages)} {source} package(s)")
                    else:
                        success = False
                        if process.stderr:
                            error_output = process.stderr.read()
                            if error_output:
                                app.log_signal.emit(f"Process stderr: {error_output}")
                                if source == 'AUR' and ("cancelled" in error_output.lower() or "authentication failed" in error_output.lower() or process.returncode == 1):
                                    if "sudo: no askpass program specified" in error_output.lower() or "authentication agent" in error_output.lower():
                                        app.log_signal.emit("Error: Authentication failed - no GUI password dialog available")
                                        app.log_signal.emit("This usually means you need to install a GUI authentication tool.")
                                        app.log_signal.emit("Please install: sudo pacman -S kdialog (or zenity/yad)")
                                    else:
                                        app.log_signal.emit("AUR installation cancelled by user")
                                    app.installation_progress.emit("cancelled", False)
                                    return
                                if source == 'npm' and ("EACCES" in error_output or "permission denied" in error_output.lower()):
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
                                                app.installation_progress.emit("cancelled", False)
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
                                            worker.error.emit(f"Error: {err2 or error_output}")
                                        continue
                                    except Exception as _e:
                                        worker.error.emit(f"Error: {str(_e)}")

                                error_text = f"Error: {error_output}"
                                if "Cannot change ownership" in error_output and "Value too large for defined data type" in error_output:
                                    error_text += "\n\nThis error occurs when tar tries to set file ownership to UIDs/GIDs that don't exist in the current environment.\n"
                                    error_text += "To fix this, you can modify packaging/PKGBUILD to add '--no-same-owner' to the tar command.\n"
                                    error_text += "For example, change 'tar -xzf file.tar.gz' to 'tar -xzf file.tar.gz --no-same-owner'"
                                worker.error.emit(error_text)
                finally:
                    pass

            if success and not app.install_cancel_event.is_set():
                try:
                    app.progress_update.emit("Installation complete!", 100)
                except Exception:
                    pass
                app.log_signal.emit("Install completed")
                app.show_message.emit("Installation Complete", f"Successfully installed {total_packages} package(s).")
                app.installation_progress.emit("success", False)
            elif not success and not app.install_cancel_event.is_set():
                app.log_signal.emit("Install failed")
                app.installation_progress.emit("failed", False)

        except Exception as e:
            app.log_signal.emit(f"Error in installation thread: {str(e)}")
            app.installation_progress.emit("failed", False)
        finally:
            try:
                if hasattr(app, 'force_sudo_install'):
                    app.force_sudo_install = False
            except Exception:
                pass
            if hasattr(app, 'install_cancel_event'):
                delattr(app, 'install_cancel_event')

    Thread(target=install, daemon=True).start()
