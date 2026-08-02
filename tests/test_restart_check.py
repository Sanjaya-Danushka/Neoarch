"""Tests for restart-required detection (Phase 4 roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time

import neoarch.backend.services.restart_check as restart


def test_running_kernel(monkeypatch):
    monkeypatch.setattr(restart, "_run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 0, stdout="6.9.1-arch1-1\n", stderr=""))
    assert restart.running_kernel() == "6.9.1-arch1-1"


def test_installed_kernels(monkeypatch, tmp_path):
    (tmp_path / "6.9.1-arch1-1").mkdir()
    (tmp_path / "6.10.2-arch1-1").mkdir()
    (tmp_path / ".keep").mkdir()
    monkeypatch.setattr(restart, "KERNEL_MODULES_DIR", str(tmp_path))
    assert restart.installed_kernels() == ["6.10.2-arch1-1", "6.9.1-arch1-1"]


def test_new_kernels(monkeypatch):
    monkeypatch.setattr(restart, "running_kernel", lambda: "6.9.1-arch1-1")
    monkeypatch.setattr(restart, "installed_kernels",
                        lambda: ["6.9.1-arch1-1", "6.10.2-arch1-1"])
    assert restart.new_kernels() == ["6.10.2-arch1-1"]


def test_new_kernels_none(monkeypatch):
    monkeypatch.setattr(restart, "running_kernel", lambda: "6.10.2-arch1-1")
    monkeypatch.setattr(restart, "installed_kernels",
                        lambda: ["6.10.2-arch1-1"])
    assert restart.new_kernels() == []


def test_boot_time_parses_uptime(monkeypatch, tmp_path):
    uptime_file = tmp_path / "uptime"
    uptime_file.write_text("3600.00 1800.00\n")
    import builtins
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open",
                        lambda p, *a, **k: real_open(uptime_file, *a, **k)
                        if str(p) == "/proc/uptime" else real_open(p, *a, **k))
    before = time.time()
    boot = restart.boot_time()
    assert boot is not None
    assert abs((time.time() - 3600) - boot) < 2
    assert boot < before


def test_check_restart_required_kernel(monkeypatch):
    monkeypatch.setattr(restart, "new_kernels", lambda: ["6.10.2-arch1-1"])
    monkeypatch.setattr(restart, "boot_time", lambda: None)
    items = restart.check_restart_required()
    assert items and items[0]["category"] == "kernel"


def test_check_restart_required_libs(monkeypatch):
    monkeypatch.setattr(restart, "new_kernels", lambda: [])
    monkeypatch.setattr(restart, "boot_time", lambda: 1000.0)
    # libc newer than boot, libsystemd older than boot.
    monkeypatch.setattr(restart, "_file_newer_than_boot",
                        lambda path, boot: path.endswith("libc.so.6"))
    items = restart.check_restart_required()
    cats = [i["category"] for i in items]
    assert cats == ["glibc"]


def test_file_newer_than_boot(monkeypatch, tmp_path):
    f = tmp_path / "libc.so.6"
    f.write_text("x")
    now = time.time()
    assert restart._file_newer_than_boot(str(f), now - 1000) is True
    assert restart._file_newer_than_boot(str(f), now + 1000) is False
    assert restart._file_newer_than_boot(str(tmp_path / "missing"), now) is False


def test_restart_required_flag(monkeypatch):
    monkeypatch.setattr(restart, "check_restart_required", lambda: [{"category": "kernel"}])
    assert restart.restart_required() is True
    monkeypatch.setattr(restart, "check_restart_required", lambda: [])
    assert restart.restart_required() is False
