"""Tests for headless AUR builds (Phase 6 roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.aur_build as ab


def test_valid_name():
    assert ab._valid_name("yay") is True
    assert ab._valid_name("firefox-developer-edition") is True
    assert ab._valid_name("yay-bin") is True
    assert ab._valid_name("..") is False
    assert ab._valid_name("bad name") is False
    assert ab._valid_name("; rm -rf /") is False
    assert ab._valid_name("") is False


def test_build_command_plain():
    cmd = ab.build_command("/tmp/work")
    assert cmd == ["bash", "-lc", "cd '/tmp/work' && makepkg"]


def test_build_command_install_checks():
    cmd = ab.build_command("/tmp/work", run_checks=True, install=True)
    shell = cmd[-1]
    assert "makepkg" in shell
    assert "--check" in shell
    assert "-i --noconfirm" in shell


def test_build_command_chroot():
    cmd = ab.build_command("/tmp/work", chroot=True)
    assert "makechrootpkg -c" in cmd[-1]
    assert "makepkg" not in cmd[-1]


def test_build_aur_package_invalid_name():
    res = ab.build_aur_package("bad;name")
    assert res["ok"] is False


def test_build_aur_package_bad_commit():
    res = ab.build_aur_package("yay", commit="; rm -rf")
    assert res["ok"] is False


def test_build_aur_package_clone_fails(monkeypatch):
    monkeypatch.setattr(ab, "_run_clone", lambda name, dest: False)
    res = ab.build_aur_package("yay")
    assert res["ok"] is False
    assert "clone" in res["stderr"]


def test_build_aur_package_full_flow(monkeypatch):
    calls = []

    def fake_clone(name, dest):
        os.makedirs(dest, exist_ok=True)
        calls.append(("clone", name))
        return True

    def fake_checkout(dest, commit):
        calls.append(("checkout", commit))
        return True

    def fake_build(workdir, chroot, run_checks, install, progress_cb):
        calls.append(("build", chroot, run_checks, install))
        return subprocess.CompletedProcess([], 0, "built ok", "")

    monkeypatch.setattr(ab, "_run_clone", fake_clone)
    monkeypatch.setattr(ab, "_checkout_commit", fake_checkout)
    monkeypatch.setattr(ab, "_run_build", fake_build)

    res = ab.build_aur_package("yay", run_checks=True, commit="a" * 40)
    assert res["ok"] is True
    assert ("clone", "yay") in calls
    assert ("checkout", "a" * 40) in calls
    assert ("build", False, True, False) in calls


def test_build_aur_package_async(monkeypatch):
    def fake_clone(name, dest):
        return True

    def fake_build(workdir, chroot, run_checks, install, progress_cb):
        return subprocess.CompletedProcess([], 0, "ok", "")

    monkeypatch.setattr(ab, "_run_clone", fake_clone)
    monkeypatch.setattr(ab, "_run_build", fake_build)

    results = []
    ab.build_aur_package("yay", finished_cb=lambda r: results.append(r))
    import time
    for _ in range(50):
        if results:
            break
        time.sleep(0.01)
    assert results and results[0]["ok"] is True
