"""Background worker QObject classes for asynchronous task execution.

Provides thread-safe workers that run subprocess commands in background
threads and communicate results via PyQt6 signals.
"""

import os
import pty
import re
import select
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

_ANSI_RE = re.compile(r'\033\[[0-9;?]*[a-zA-Z]|\033\].*?(\033\\|[\a])')

def strip_ansi(text):
    return _ANSI_RE.sub('', text)

from neoarch.backend.auth import get_auth_command, get_askpass_env, prepare_askpass_env

__all__ = ["PackageLoaderWorker", "CommandWorker"]


class PackageLoaderWorker(QObject):
    """Worker that runs a command to load package lists.

    Parses command output expecting lines of "name version" format.

    Signals:
        packages_loaded(list): Emitted with parsed package dictionaries.
        error_occurred(str): Emitted on failure.
        finished(): Emitted when work is complete (success or failure).
    """

    packages_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        """Execute the command and parse package output."""
        try:
            result = subprocess.run(self.command, capture_output=True, text=True, timeout=60)
            packages = []
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                'name': parts[0],
                                'version': parts[1],
                                'id': parts[0]
                            })
            self.packages_loaded.emit(packages)
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()


class CommandWorker(QObject):
    """Worker that executes a shell command with real-time output streaming.

    Uses a pseudo-terminal (PTY) to trick subprocesses (like pacman) into
    providing full terminal output including progress bars, download speeds,
    and ETA. Handles carriage-return progress updates from the PTY.

    Supports sudo elevation via get_auth_command() and runs the process
    in a separate process group for clean cancellation.

    Signals:
        finished(): Emitted when the command completes.
        output(str): Emitted for each complete line of stdout.
        line_update(str): Emitted for progress updates that should replace
                          the last line in the console (uses \r internally).
        error(str): Emitted on non-zero exit or exception.
    """

    finished = pyqtSignal()
    output = pyqtSignal(str)
    line_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, command, sudo=False, env=None, cancel_event=None):
        super().__init__()
        self.command = command
        self.sudo = sudo
        self.env = env if env is not None else os.environ.copy()
        self._cancel_event = cancel_event

    def run(self):
        """Execute the command, streaming output via PTY."""
        try:
            if self.sudo:
                auth_cmd = get_auth_command(self.env)
                self.command = auth_cmd + self.command
                if auth_cmd == ["sudo", "-A"]:
                    askpass = self.env.get('SUDO_ASKPASS', '')
                    if not askpass or not os.path.exists(askpass):
                        self.env = get_askpass_env(self.env)

            self._run_with_pty()
        except Exception as e:
            self.error.emit(f"Error running command: {str(e)}")
            self.finished.emit()

    def _run_with_pty(self):
        master_fd, slave_fd = pty.openpty()

        process = subprocess.Popen(
            self.command,
            stdout=slave_fd,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            text=True,
            preexec_fn=os.setsid,
            env=self.env
        )

        os.close(slave_fd)
        os.set_blocking(master_fd, False)
        poller = select.poll()
        poller.register(master_fd, select.POLLIN)

        buf = ""

        while True:
            if process.poll() is not None:
                break

            if self._cancel_event is not None and self._cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
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
                            buf = self._process_buf(buf)
            except OSError:
                break

        # Drain remaining data from master
        try:
            while True:
                data = os.read(master_fd, 4096)
                if not data:
                    break
                buf += data.decode('utf-8', errors='replace')
        except OSError:
            pass

        if buf:
            self._process_buf(buf, final=True)

        _, stderr = process.communicate()
        try:
            os.close(master_fd)
        except OSError:
            pass

        if stderr and process.returncode != 0:
            self.error.emit(f"Error: {stderr}")

        self.finished.emit()

    def _process_buf(self, buf, final=False):
        """Process buffer, emitting output/lines with \r handling.

        Splits on \n for complete lines and handles \r for progress
        updates. Returns remaining incomplete buffer.
        """
        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            self._emit_line(line)

        if '\r' in buf:
            parts = buf.split('\r')
            stripped = strip_ansi(parts[-1].strip())
            if stripped:
                self.line_update.emit(stripped)
            buf = parts[-1]

        if final and buf:
            stripped = strip_ansi(buf.strip())
            if stripped:
                self.output.emit(stripped)

        return buf

    def _emit_line(self, line):
        """Emit a complete line.

        For lines with \r progress sequences, only the last segment
        is emitted (the final state of the line).
        """
        if '\r' in line:
            parts = line.split('\r')
            stripped = strip_ansi(parts[-1].strip())
            if stripped:
                self.output.emit(stripped)
        else:
            stripped = strip_ansi(line.strip())
            if stripped:
                self.output.emit(stripped)

    def _command_exists(self, cmd):
        """Check if a command exists in PATH."""
        return subprocess.run(['which', cmd], capture_output=True).returncode == 0
