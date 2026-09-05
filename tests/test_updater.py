from unittest.mock import MagicMock

import neoarch.backend.package.updater as updater_module
from neoarch.backend.package.updater import parse_aur_failures, _classify_aur_hint
from neoarch.backend.package.updater import update_packages


class Emitter:
    """Simple stand-in for a pyqtSignal."""
    def __init__(self):
        self.calls = []
        self.handlers = []

    def connect(self, handler):
        self.handlers.append(handler)

    def emit(self, *args):
        self.calls.append(args)
        for handler in self.handlers:
            handler(*args)


class FakeWorker:
    """Synchronous CommandWorker stand-in; emits error for failing packages."""
    instances = []
    failing = set()

    def __init__(self, command, sudo=False, env=None, cancel_event=None):
        self.command = command
        self.sudo = sudo
        self.env = env or {}
        self.cancel_event = cancel_event
        self.output = Emitter()
        self.line_update = Emitter()
        self.error = Emitter()
        FakeWorker.instances.append(self)

    def run(self):
        pkg = self.command[-1]
        if pkg in FakeWorker.failing:
            self.error.emit(f"Error: error making: {pkg}: exit status 8")


class FakeApp:
    def __init__(self):
        self.settings = {"aur_helper": "auto"}
        self.log_lines = []
        self.progress_update = Emitter()
        self.installation_progress = Emitter()
        self.show_message = Emitter()
        self.ui_call = Emitter()
        self._ui_refreshed = []
        self.refresh_packages = lambda: self._ui_refreshed.append(True)

    def log(self, msg):
        self.log_lines.append(msg)

    def log_line_update(self, msg):
        self.log_lines.append(msg)


def _run_update_sync(app, packages_by_source, upgrade_all=False):
    """Run update_packages with a synchronous thread stand-in."""
    class SyncThread:
        def __init__(self, target, daemon=False):
            self._target = target

        def start(self):
            self._target()

    updater_module.Thread = SyncThread
    try:
        update_packages(app, packages_by_source, upgrade_all=upgrade_all)
    finally:
        updater_module.Thread = __import__("threading").Thread


def test_parse_yay_error_making_lines():
    msg = (
        "==> ERROR: A failure occurred in build().\n"
        " -> error making: docker-desktop: exit status 1\n"
        " -> error making: cursor-bin: exit status 1\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert set(failed) == {'docker-desktop', 'cursor-bin'}
    assert failed['docker-desktop'] == 'exit status 1'
    assert hint == 'a package failed to build'


def test_parse_paru_manual_intervention_section():
    msg = (
        "Failed to install the following packages. Manual intervention is required:\n"
        "cursor-bin - fork/exec /usr/bin/makepkg: no such file or directory\n"
        "nvidia-580xx-dkms - could not satisfy dependencies\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert set(failed) == {'cursor-bin', 'nvidia-580xx-dkms'}
    assert hint == 'a build tool is missing (install base-devel)'


def test_parse_colon_separated_paru_entries():
    msg = (
        "Failed to install the following packages. Manual intervention is required:\n"
        "foo: error making: exit status 1\n"
    )
    failed, _ = parse_aur_failures(msg)
    assert failed.get('foo') == 'error making: exit status 1'


def test_parse_empty_or_none():
    assert parse_aur_failures('') == ({}, None)
    assert parse_aur_failures(None) == ({}, None)


def test_parse_ignores_noise():
    msg = (
        "warning: w3m-0.5.6-1 is up to date -- reinstalling\n"
        "some unrelated progress line\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert failed == {}
    assert hint is None


def test_classify_hints():
    assert _classify_aur_hint('fork/exec /usr/bin/makepkg: no such file or directory') == 'a build tool is missing (install base-devel)'
    assert _classify_aur_hint('error: failed to prepare transaction (could not satisfy dependencies)') == 'there is a dependency conflict'
    assert _classify_aur_hint('==> ERROR: A failure occurred in build()') == 'a package failed to build'
    assert _classify_aur_hint('nothing wrong here') is None


def test_aur_update_runs_one_command_per_package(monkeypatch):
    FakeWorker.instances = []
    monkeypatch.setattr(updater_module, "CommandWorker", FakeWorker)
    monkeypatch.setattr(
        updater_module.sys_utils, "get_aur_helper", lambda preferred: "yay")
    monkeypatch.setattr(updater_module, "get_askpass_env", lambda: {})

    app = FakeApp()
    _run_update_sync(app, {"AUR": ["a", "b"]})

    commands = [w.command for w in FakeWorker.instances]
    assert commands == [
        ["yay", "-S", "--noconfirm", "a"],
        ["yay", "-S", "--noconfirm", "b"],
    ]


def test_aur_update_continues_after_single_package_failure(monkeypatch):
    FakeWorker.instances = []
    FakeWorker.failing = {"a"}
    monkeypatch.setattr(updater_module, "CommandWorker", FakeWorker)
    monkeypatch.setattr(
        updater_module.sys_utils, "get_aur_helper", lambda preferred: "yay")
    monkeypatch.setattr(updater_module, "get_askpass_env", lambda: {})

    app = FakeApp()
    _run_update_sync(app, {"AUR": ["a", "b", "c"]})

    # All three packages still ran despite "a" failing to build.
    commands = [w.command for w in FakeWorker.instances]
    assert len(commands) == 3
    assert commands[-1] == ["yay", "-S", "--noconfirm", "c"]

    status = app.installation_progress.calls[-1][0]
    assert status == "failed"
    partial = app.show_message.calls[-1][1]
    assert "a" in partial


def test_aur_update_success_when_no_failures(monkeypatch):
    FakeWorker.instances = []
    FakeWorker.failing = set()
    monkeypatch.setattr(updater_module, "CommandWorker", FakeWorker)
    monkeypatch.setattr(
        updater_module.sys_utils, "get_aur_helper", lambda preferred: "yay")
    monkeypatch.setattr(updater_module, "get_askpass_env", lambda: {})

    app = FakeApp()
    _run_update_sync(app, {"AUR": ["x"]})

    status = app.installation_progress.calls[-1][0]
    assert status == "success"
