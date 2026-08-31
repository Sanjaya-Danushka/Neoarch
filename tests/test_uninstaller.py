"""Tests for neoarch.backend.package.uninstaller – thread-based uninstall."""
import threading

from tests.conftest import FakeCompletedProcess
from neoarch.backend.package import uninstaller as uninstaller_mod
from neoarch.backend.package.uninstaller import uninstall_packages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Emitter:
    def __init__(self):
        self.calls = []
        self.connected = None

    def emit(self, *args):
        self.calls.append(args)

    def connect(self, cb):
        self.connected = cb


class FakeApp:
    def __init__(self):
        self.logs = []
        self._last_operation = None
        self.progress_update = Emitter()
        self.show_message = Emitter()
        self.installation_progress = Emitter()

    def log(self, msg):
        self.logs.append(msg)

    def load_installed_packages(self):
        ...


_workers_captured = []


class FakeWorker:
    def __init__(self, cmd, sudo=False, env=None):
        self.cmd = cmd
        self.sudo = sudo
        self.env = env
        self.output = Emitter()
        self.error = Emitter()
        _workers_captured.append(self)

    def run(self):
        ...


class FakeQTimer:
    @staticmethod
    def singleShot(ms, cb):
        ...


def _install_patches(monkeypatch, done_event):
    def _single_shot(ms, cb):
        done_event.set()

    monkeypatch.setattr(uninstaller_mod, "CommandWorker", FakeWorker)
    monkeypatch.setattr(
        uninstaller_mod, "QTimer", type("Q", (), {"singleShot": staticmethod(_single_shot)})
    )


# ---------------------------------------------------------------------------
# pacman source
# ---------------------------------------------------------------------------

def test_pacman_source_builds_command(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"pacman": ["a", "b"]})
    assert done.wait(timeout=5)

    assert len(_workers_captured) == 1
    w = _workers_captured[0]
    assert w.cmd == ["pacman", "-R", "--noconfirm", "a", "b"]
    assert w.sudo is True


# ---------------------------------------------------------------------------
# Flatpak source
# ---------------------------------------------------------------------------

def test_flatpak_source_no_sudo(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"Flatpak": ["app.flatpak"]})
    assert done.wait(timeout=5)

    assert len(_workers_captured) == 1
    w = _workers_captured[0]
    assert w.cmd[0] == "flatpak"
    assert w.cmd[1] == "uninstall"
    assert "app.flatpak" in w.cmd
    assert w.sudo is False


# ---------------------------------------------------------------------------
# AUR source
# ---------------------------------------------------------------------------

def test_aur_source_uses_pacman_r(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"AUR": ["x"]})
    assert done.wait(timeout=5)

    assert len(_workers_captured) == 1
    w = _workers_captured[0]
    assert w.cmd == ["pacman", "-R", "--noconfirm", "x"]
    assert w.sudo is True


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

def test_unknown_source_skipped(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"foo": ["x"]})
    assert done.wait(timeout=5)

    assert len(_workers_captured) == 0


def test_empty_source_skipped(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"pacman": []})
    assert done.wait(timeout=5)

    assert len(_workers_captured) == 0


# ---------------------------------------------------------------------------
# completion signals
# ---------------------------------------------------------------------------

def test_emits_completion(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"pacman": ["pkg1"]})
    assert done.wait(timeout=5)

    assert app.show_message.calls == [
        ("Uninstallation Complete", "Successfully processed 1 package(s).")
    ]
    assert ("success", False) in app.installation_progress.calls


def test_success_result(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)

    app = FakeApp()
    uninstall_packages(app, {"pacman": ["pkg1"]})
    assert done.wait(timeout=5)
    assert app._last_operation == "uninstall"


# ---------------------------------------------------------------------------
# npm source (minimal)
# ---------------------------------------------------------------------------

def test_npm_source_builds_command(monkeypatch):
    done = threading.Event()
    _workers_captured.clear()
    _install_patches(monkeypatch, done)
    monkeypatch.setattr(
        uninstaller_mod.sys_utils, "npm_user_mode_enabled", lambda: False
    )

    def _fake_run(cmd, **kw):
        if "ls" in cmd:
            return FakeCompletedProcess(stdout="{}")
        return FakeCompletedProcess(stdout="")

    monkeypatch.setattr(uninstaller_mod.subprocess, "run", _fake_run)

    app = FakeApp()
    uninstall_packages(app, {"npm": ["pkg"]})
    assert done.wait(timeout=5)

    assert app._last_operation == "uninstall"
    assert len(_workers_captured) == 0
