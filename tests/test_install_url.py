"""Tests for installing package archives from URLs (Phase 6 roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.install_url as iu


def test_is_package_url():
    assert iu.is_package_url("https://example.com/pkg-1.0-1-x86_64.pkg.tar.zst") is True
    assert iu.is_package_url("https://example.com/pkg-1.0-1-x86_64.pacman") is True
    assert iu.is_package_url("https://example.com/pkg-1.0-1-x86_64.pkg.tar.xz") is True
    assert iu.is_package_url("https://example.com/README.txt") is False
    assert iu.is_package_url("pkg-1.0-1-x86_64.pkg.tar.zst") is False
    assert iu.is_package_url("") is False


def test_download_bad_scheme(monkeypatch, tmp_path):
    dest = str(tmp_path / "out")
    assert iu._download("file:///etc/passwd", dest, None) is False


def test_download_writes_file(monkeypatch, tmp_path):
    calls = []

    class FakeResp:
        headers = {"Content-Length": "6"}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, size):
            calls.append(True)
            return b"hello" if len(calls) == 1 else b""

    monkeypatch.setattr("neoarch.backend.services.network.urlopen",
                        lambda req, timeout=None: FakeResp())
    dest = str(tmp_path / "out.pkg")
    assert iu._download("https://example.com/a.pkg.tar.zst", dest, None) is True
    with open(dest, "rb") as f:
        assert f.read() == b"hello"


def test_download_failure(monkeypatch, tmp_path):
    def boom(req, timeout=None):
        raise OSError("no net")
    monkeypatch.setattr("neoarch.backend.services.network.urlopen", boom)
    assert iu._download("https://example.com/a.pkg.tar.zst",
                        str(tmp_path / "out"), None) is False


def test_install_runs_pacman(monkeypatch):
    calls = []

    def fake_run(cmd, **k):
        calls.append(cmd)
        assert cmd[0] == "sudo"
        assert "pacman" in cmd and "-U" in cmd and "--noconfirm" in cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(iu, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(iu, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert iu._install("/tmp/x.pkg.tar.zst") is True
    assert calls[-1][-1] == "/tmp/x.pkg.tar.zst"


def test_install_from_url_sync(monkeypatch, tmp_path):
    monkeypatch.setattr(iu, "is_package_url", lambda url: True)
    monkeypatch.setattr(iu, "_download", lambda url, dest, cb: True)
    monkeypatch.setattr(iu, "_install", lambda path: True)
    assert iu.install_from_url("https://example.com/a.pkg.tar.zst") is True


def test_install_from_url_rejects_non_package(monkeypatch):
    monkeypatch.setattr(iu, "is_package_url", lambda url: False)
    monkeypatch.setattr(iu, "_install", lambda path: (_ for _ in ()).throw(AssertionError))
    assert iu.install_from_url("https://example.com/README.txt") is False


def test_install_from_url_download_fail(monkeypatch):
    monkeypatch.setattr(iu, "is_package_url", lambda url: True)
    monkeypatch.setattr(iu, "_download", lambda url, dest, cb: False)
    monkeypatch.setattr(iu, "_install", lambda path: (_ for _ in ()).throw(AssertionError))
    assert iu.install_from_url("https://example.com/a.pkg.tar.zst") is False


def test_install_from_url_async(monkeypatch):
    monkeypatch.setattr(iu, "is_package_url", lambda url: True)
    monkeypatch.setattr(iu, "_download", lambda url, dest, cb: True)
    monkeypatch.setattr(iu, "_install", lambda path: True)
    results = []
    ok = iu.install_from_url("https://example.com/a.pkg.tar.zst",
                             finished_cb=lambda r: results.append(r))
    assert ok is True  # launched on a thread
    import time
    for _ in range(50):
        if results:
            break
        time.sleep(0.01)
    assert results == [True]
