"""Tests for the Discover 'did you mean' name-suggestion service."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.suggestions as sugg


def test_suggest_typo_matches(monkeypatch, tmp_path):
    sugg.set_cache_path(str(tmp_path / "names.json"))
    monkeypatch.setattr(sugg, "_collect_names", lambda: ["cmatrix", "gimp", "vlc", "htop"])
    sugg.refresh_names_index()
    got = sugg.suggest_names("camtrix")
    assert "cmatrix" in got


def test_suggest_returns_empty_for_short_query(monkeypatch, tmp_path):
    sugg.set_cache_path(str(tmp_path / "names.json"))
    monkeypatch.setattr(sugg, "_collect_names", lambda: ["cmatrix"])
    sugg.refresh_names_index()
    assert sugg.suggest_names("cm") == []


def test_suggest_excludes_exact_match(monkeypatch, tmp_path):
    sugg.set_cache_path(str(tmp_path / "names.json"))
    monkeypatch.setattr(sugg, "_collect_names", lambda: ["cmatrix", "gimp"])
    sugg.refresh_names_index()
    got = sugg.suggest_names("cmatrix")
    assert "cmatrix" not in got


def test_refresh_persists_cache(monkeypatch, tmp_path):
    cache = str(tmp_path / "names.json")
    sugg.set_cache_path(cache)
    monkeypatch.setattr(sugg, "_collect_names", lambda: ["firefox", "vim"])
    sugg.refresh_names_index()
    with open(cache) as f:
        data = json.load(f)
    assert data["names"] == ["firefox", "vim"]
    assert "ts" in data


def test_index_ready_loads_fresh_cache(monkeypatch, tmp_path):
    cache = str(tmp_path / "names.json")
    sugg.set_cache_path(cache)
    sugg._index = []
    sugg._index_ts = 0.0
    with open(cache, "w") as f:
        json.dump({"ts": sugg.time.time(), "names": ["firefox"]}, f)
    assert sugg.index_ready() is True
    assert sugg.suggest_names("firefox") == []


def test_index_ready_stale_cache(monkeypatch, tmp_path):
    cache = str(tmp_path / "names.json")
    sugg.set_cache_path(cache)
    sugg._index = []
    sugg._index_ts = 0.0
    with open(cache, "w") as f:
        json.dump({"ts": sugg.time.time() - sugg.CACHE_TTL - 1, "names": ["firefox"]}, f)
    assert sugg.index_ready() is False


def test_run_handles_failure(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError
    monkeypatch.setattr(sugg.subprocess, "run", boom)
    assert sugg._run(["pacman", "-Ssq"]) == ""


def test_collect_uses_available_sources(monkeypatch):
    calls = []
    monkeypatch.setattr(sugg, "shutil", type("Sh", (), {"which": lambda p: "/usr/bin/" + p}))
    monkeypatch.setattr(sugg, "_run", lambda cmd, timeout=20: calls.append(cmd) or "cmatrix\ngimp\n")
    names = sugg._collect_names()
    assert "cmatrix" in names and "gimp" in names
    assert calls == [
        ["pacman", "-Ssq"],
        ["flatpak", "remote-ls", "--app", "--columns=application"],
    ]
