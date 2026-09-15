"""Tests for the snapper (BTRFS) snapshot service."""

import os
import sys
import subprocess
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.snapper as snapper
import neoarch.backend.services.snapshot as snapshot_mod


SAMPLE_LIST = """\
  # | Type   | Pre # | Date             | User | Cleanup | Description
----+--------+-------+------------------+------+---------+------------
  0 | single |       |                  | root |        | current
  1 | single |       | 2026-09-10 09:00 | root | number  | pkg install
  2 | single |       | 2026-09-11 08:00 | root | number  | old daily
  3 | single |       | 2026-09-12 21:30 | root |        | NeoArch pre-update
"""


class _Sig:
    """Mimics a Qt Signal: supports .emit(*args)."""

    def __init__(self, sink):
        self._sink = sink

    def emit(self, *args):
        self._sink.append(args)


class _StubApp:
    def __init__(self):
        self.logs = []
        self.messages = []
        self.show_message = _Sig(self.messages)

    def log(self, msg):
        self.logs.append(msg)


def _make_configs(tmp_path, names, monkeypatch):
    d = tmp_path / "configs"
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / n).write_text("SUBVOLUME=/\n")
    monkeypatch.setattr(snapper, "SNAPPER_CONFIGS_DIR", d)


def test_parse_snapshot_list():
    snaps = snapper.parse_snapshot_list(SAMPLE_LIST)
    assert [s["num"] for s in snaps] == [0, 1, 2, 3]
    assert snaps[3]["description"] == "NeoArch pre-update"
    assert snaps[1]["type"] == "single"


def test_default_config_prefers_root(tmp_path, monkeypatch):
    _make_configs(tmp_path, ["root", "home"], monkeypatch)
    assert snapper.default_config() == "root"


def test_default_config_first_alpha(tmp_path, monkeypatch):
    _make_configs(tmp_path, ["data"], monkeypatch)
    assert snapper.default_config() == "data"


def test_default_config_empty_when_no_configs(tmp_path, monkeypatch):
    _make_configs(tmp_path, [], monkeypatch)
    assert snapper.default_config() is None


def test_snapper_available_configs_ignores_hidden(tmp_path, monkeypatch):
    _make_configs(tmp_path, [".template", "user"], monkeypatch)
    assert snapper.snapper_available_configs() == ["user"]


def test_snapper_supported_requires_btrfs_and_config(tmp_path, monkeypatch):
    _make_configs(tmp_path, ["root"], monkeypatch)
    monkeypatch.setattr(snapper, "get_filesystem_type", lambda: "btrfs")
    monkeypatch.setattr(snapper, "_btrfs_root_subvolume", lambda: "/")
    monkeypatch.setattr(
        snapper.shutil, "which", lambda _name: "/usr/bin/snapper")
    assert snapper.snapper_supported() is True
    monkeypatch.setattr(snapper, "get_filesystem_type", lambda: "ext4")
    assert snapper.snapper_supported() is False


def test_snapper_supported_missing_binary(tmp_path, monkeypatch):
    _make_configs(tmp_path, ["root"], monkeypatch)
    monkeypatch.setattr(snapper, "get_filesystem_type", lambda: "btrfs")
    monkeypatch.setattr(snapper, "_btrfs_root_subvolume", lambda: "/")
    monkeypatch.setattr(snapper.shutil, "which", lambda _name: None)
    assert snapper.snapper_supported() is False


def test_pre_update_snapshot_creates_and_cleans(tmp_path, monkeypatch):
    _make_configs(tmp_path, ["root"], monkeypatch)
    calls = []
    auth_calls = []

    def fake_run(cmd, **kw):
        if cmd[0].split("/")[-1] == "date":
            return subprocess.CompletedProcess(
                cmd, 0, stdout="2026-09-15_10-00-00\n", stderr="")
        calls.append(cmd)
        if "list" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=SAMPLE_LIST, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fake_auth_cmd(cmd, timeout=None, input=None):
        auth_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(snapper.subprocess, "run", fake_run)
    monkeypatch.setattr(snapper, "run_auth_cmd", fake_auth_cmd)

    app = _StubApp()
    snapper.pre_update_snapshot(app)

    create = [c for c in auth_calls if "--description" in c]
    assert create, auth_calls
    create_cmd = create[-1]
    assert "root" in create_cmd
    assert "NeoArch pre-update snapshot 2026-09-15_10-00-00" in create_cmd
    assert "single" in create_cmd
    assert any("delete" in c for c in auth_calls)
    assert any(("Cleaned up old snapper snapshots" in m) for m in app.logs)
    assert any(("Pre-update snapshot created" in m) for m in app.logs)
    assert app.messages
    assert snapshot_mod.snapshot_op_active() is False


def test_snapshot_op_guard_serializes():
    assert snapshot_mod.acquire_snapshot_op() is True
    try:
        assert snapshot_mod.acquire_snapshot_op() is False
    finally:
        snapshot_mod.release_snapshot_op()
    assert snapshot_mod.acquire_snapshot_op() is True
    snapshot_mod.release_snapshot_op()


def test_run_auth_cmd_cancel_terminates_child(monkeypatch):
    monkeypatch.setattr(snapshot_mod, "get_auth_command", lambda *a, **k: [])
    monkeypatch.setattr(snapshot_mod, "get_askpass_env", lambda *a, **k: {})
    result = {}

    def _run():
        result["value"] = snapshot_mod.run_auth_cmd(
            ["sh", "-c", "sleep 30; echo done"], timeout=60)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(0.6)
    start = time.monotonic()
    snapshot_mod.request_snapshot_cancel()
    t.join(timeout=10)
    elapsed = time.monotonic() - start
    assert not t.is_alive(), "cancel must return promptly"
    assert result["value"].returncode is None
    assert elapsed < 12, "cancel must not wait on the child's shell"
    snapshot_mod.clear_snapshot_cancel()


def test_run_auth_cmd_cancel_bounded_even_if_term_ignored(monkeypatch):
    monkeypatch.setattr(snapshot_mod, "get_auth_command", lambda *a, **k: [])
    monkeypatch.setattr(snapshot_mod, "get_askpass_env", lambda *a, **k: {})
    result = {}

    def _run():
        result["value"] = snapshot_mod.run_auth_cmd(
            ["sh", "-c", 'trap "" TERM; sleep 30; echo done'], timeout=60)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(0.6)
    start = time.monotonic()
    snapshot_mod.request_snapshot_cancel()
    t.join(timeout=15)
    elapsed = time.monotonic() - start
    snapshot_mod.clear_snapshot_cancel()
    assert not t.is_alive(), "cancel must fall back to SIGKILL"
    assert result["value"].returncode is None
    assert elapsed < 12, "SIGKILL fallback must keep teardown bounded"


def test_pre_update_snapshot_skips_without_config(tmp_path, monkeypatch):
    _make_configs(tmp_path, [], monkeypatch)
    app = _StubApp()
    snapper.pre_update_snapshot(app)
    assert any("not configured" in m for m in app.logs)
    assert not app.messages
