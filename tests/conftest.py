"""Shared fixtures for the NeoArch test suite."""
import os
import subprocess
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeCompletedProcess:
    """Reusable stand-in for subprocess.CompletedProcess."""
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.args = []


@pytest.fixture
def fake_run(monkeypatch):
    """Monkeypatch subprocess.run; returns list to append side_effects."""
    calls = []

    def _fake(cmd, timeout=60, env=None, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake)
    return calls


@pytest.fixture
def session_dirs(tmp_path, monkeypatch):
    """Redirect session_auth paths to tmp to avoid touching real ~/.cache."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr("neoarch.backend.session_auth.Path.home", lambda: tmp_path)
    return cache
