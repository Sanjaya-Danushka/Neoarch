"""Background worker QObject classes for asynchronous task execution.

Provides thread-safe workers that run subprocess commands in background
threads and communicate results via PyQt6 signals.
"""

import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

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

    Supports sudo elevation via get_auth_command() and runs the process
    in a separate process group for clean cancellation.

    Signals:
        finished(): Emitted when the command completes.
        output(str): Emitted for each line of stdout.
        error(str): Emitted on non-zero exit or exception.
    """

    finished = pyqtSignal()
    output = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, command, sudo=False, env=None):
        super().__init__()
        self.command = command
        self.sudo = sudo
        self.env = env if env is not None else os.environ.copy()

    def run(self):
        """Execute the command, streaming output line by line."""
        try:
            if self.sudo:
                auth_cmd = get_auth_command(self.env)
                self.command = auth_cmd + self.command
                if auth_cmd == ["sudo", "-A"]:
                    askpass = self.env.get('SUDO_ASKPASS', '')
                    if not askpass or not os.path.exists(askpass):
                        self.env = get_askpass_env(self.env)

            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
                env=self.env
            )

            assert process.stdout is not None
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.output.emit(line.strip())

            _, stderr = process.communicate()
            if stderr and process.returncode != 0:
                self.error.emit(f"Error: {stderr}")

            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Error running command: {str(e)}")
            self.finished.emit()

    def _command_exists(self, cmd):
        """Check if a command exists in PATH."""
        return subprocess.run(['which', cmd], capture_output=True).returncode == 0
