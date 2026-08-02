"""Tests for the pacman.conf option service (Phase 5 roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.pacman_conf as pconf

CONF = (
    "# /etc/pacman.conf\n"
    "[options]\n"
    "HoldPkg = pacman glibc\n"
    "ParallelDownloads = 5\n"
    "Architecture = auto\n"
    "\n"
    "[core]\n"
    "Include = /etc/pacman.d/mirrorlist\n"
)


def test_get_parallel_downloads(monkeypatch, tmp_path):
    f = tmp_path / "pacman.conf"
    f.write_text(CONF)
    monkeypatch.setattr(pconf, "PACMAN_CONF", str(f))
    assert pconf.get_parallel_downloads() == 5


def test_get_option_unset(monkeypatch, tmp_path):
    f = tmp_path / "pacman.conf"
    f.write_text("[options]\nHoldPkg = pacman glibc\n")
    monkeypatch.setattr(pconf, "PACMAN_CONF", str(f))
    assert pconf.get_option("ParallelDownloads") is None
    assert pconf.get_parallel_downloads() is None


def test_get_option_ignores_comments(monkeypatch, tmp_path):
    f = tmp_path / "pacman.conf"
    f.write_text("[options]\n#ParallelDownloads = 9\nParallelDownloads = 5\n")
    monkeypatch.setattr(pconf, "PACMAN_CONF", str(f))
    assert pconf.get_option("ParallelDownloads") == "5"


def test_set_parallel_downloads_rewrites_existing(monkeypatch, tmp_path):
    f = tmp_path / "pacman.conf"
    f.write_text(CONF)
    monkeypatch.setattr(pconf, "PACMAN_CONF", str(f))

    written = {}

    def fake_tee(cmd, input="", **k):
        written["content"] = input
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(pconf, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(pconf, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_tee)

    assert pconf.set_parallel_downloads(10) is True
    content = written["content"]
    assert "ParallelDownloads = 10\n" in content
    # unrelated lines preserved
    assert "HoldPkg = pacman glibc\n" in content
    assert "[core]\n" in content


def test_set_parallel_downloads_appends(monkeypatch, tmp_path):
    f = tmp_path / "pacman.conf"
    f.write_text("[options]\nHoldPkg = pacman glibc\n")
    monkeypatch.setattr(pconf, "PACMAN_CONF", str(f))
    written = {}

    def fake_tee(cmd, input="", **k):
        written["content"] = input
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(pconf, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(pconf, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_tee)

    assert pconf.set_parallel_downloads(8) is True
    content = written["content"]
    assert content.index("ParallelDownloads = 8\n") < content.index("[options]") + 1


def test_set_parallel_downloads_validates():
    assert pconf.set_parallel_downloads(0) is False
    assert pconf.set_parallel_downloads(100) is False
    assert pconf.set_parallel_downloads("5") is False


def test_set_option_validates_name():
    assert pconf.set_option("Parallel; rm -rf", "5") is False
    assert pconf.set_option("Bad Name", "5") is False
