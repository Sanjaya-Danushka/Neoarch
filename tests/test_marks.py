"""Tests for the package mark service (IgnorePkg/HoldPkg/reasons)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.marks as marks


def test_get_ignorepkg_parses(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text(
        "[options]\n"
        "IgnorePkg = firefox\n"
        "IgnorePkg = vim neovim\n"
        "#IgnorePkg = commented\n"
    )
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    assert marks.get_ignorepkg() == ["firefox", "vim", "neovim"]


def test_get_holdpkg_parses(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("HoldPkg = linux\nHoldPkg = linux-lts\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    assert marks.get_holdpkg() == ["linux", "linux-lts"]


def test_get_ignorepkg_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(marks, "PACMAN_CONF", str(tmp_path / "nope"))
    assert marks.get_ignorepkg() == []


def test_add_ignorepkg_appends(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("[options]\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        assert cmd[0] == "sudo"
        assert f'echo "IgnorePkg = firefox" >> {conf}' in " ".join(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(marks, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(marks, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.add_ignorepkg("firefox") is True
    assert len(calls) == 1


def test_add_ignorepkg_noop_if_present(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("IgnorePkg = firefox\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.add_ignorepkg("firefox") is True
    assert calls == []


def test_add_ignorepkg_rejects_injection():
    assert marks.add_ignorepkg("foo; rm -rf /") is False


def test_remove_ignorepkg_runs_sed(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("IgnorePkg = firefox vim\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        assert cmd[0] == "sudo"
        assert any("sed" in c for c in cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(marks, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(marks, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.remove_ignorepkg("vim") is True
    assert len(calls) == 1


def test_remove_ignorepkg_noop_if_absent(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("IgnorePkg = firefox\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.remove_ignorepkg("vim") is True
    assert calls == []


def test_holdpkg_roundtrip_dispatch(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text("[options]\n")
    monkeypatch.setattr(marks, "PACMAN_CONF", str(conf))
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        assert f"HoldPkg = linux" in " ".join(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(marks, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(marks, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.add_holdpkg("linux") is True
    assert len(calls) == 1


def test_get_install_reason_explicit(monkeypatch):
    out = ("Name : firefox\n"
           "Install Reason : Explicitly installed\n")
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 0, stdout=out, stderr=""))
    assert marks.get_install_reason("firefox") == "explicit"


def test_get_install_reason_deps(monkeypatch):
    out = "Install Reason : Installed as a dependency for another package\n"
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 0, stdout=out, stderr=""))
    assert marks.get_install_reason("libpng") == "deps"


def test_get_install_reason_missing(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 1, stdout="", stderr="error"))
    assert marks.get_install_reason("nope") is None


def test_set_install_reason_explicit(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(marks, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(marks, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.set_install_reason("firefox", "explicit") is True
    assert "--asexplicit" in calls[0]


def test_set_install_reason_deps(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(marks, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(marks, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert marks.set_install_reason("libpng", "deps") is True
    assert "--asdeps" in calls[0]


def test_set_install_reason_invalid():
    assert marks.set_install_reason("firefox", "sometimes") is False
    assert marks.set_install_reason("foo; rm -rf", "explicit") is False
