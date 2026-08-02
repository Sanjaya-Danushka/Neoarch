"""Tests for the curated recommendations feed (Phase 5 roadmap)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.recommend as rec


def test_recommendations_basic(monkeypatch, tmp_path):
    monkeypatch.setattr(rec, "set_popularity_cache", lambda p: None)
    rec.POPULARITY_CACHE = str(tmp_path / "pop.json")
    monkeypatch.setattr(rec, "_installed", lambda: ["firefox"])
    items = rec.recommendations(include_installed=True)
    names = [i["name"] for i in items]
    assert "firefox" in names
    assert "htop" in names
    entry = next(i for i in items if i["name"] == "htop")
    assert entry["desc"] and entry["category"] == "utilities"
    assert entry["installed"] is False


def test_recommendations_excludes_installed(monkeypatch, tmp_path):
    rec.POPULARITY_CACHE = str(tmp_path / "pop.json")
    monkeypatch.setattr(rec, "_installed", lambda: ["htop", "vlc"])
    items = rec.recommendations()
    names = [i["name"] for i in items]
    assert "htop" not in names
    assert "vlc" not in names
    assert "firefox" in names


def test_recommendations_limit(monkeypatch, tmp_path):
    rec.POPULARITY_CACHE = str(tmp_path / "pop.json")
    monkeypatch.setattr(rec, "_installed", lambda: [])
    items = rec.recommendations(limit=3)
    assert len(items) == 3


def test_recommendations_sorts_by_popularity(monkeypatch, tmp_path):
    pop = str(tmp_path / "pop.json")
    with open(pop, "w") as f:
        json.dump({"htop": 9.9, "vim": 2.0}, f)
    rec.POPULARITY_CACHE = pop
    monkeypatch.setattr(rec, "_installed", lambda: [])
    items = rec.recommendations()
    assert items[0]["name"] == "htop"
    assert items[0]["popularity"] == 9.9
    vim = next(i for i in items if i["name"] == "vim")
    assert vim["popularity"] == 2.0


def test_recommendations_missing_cache(monkeypatch, tmp_path):
    rec.POPULARITY_CACHE = str(tmp_path / "missing.json")
    monkeypatch.setattr(rec, "_installed", lambda: [])
    items = rec.recommendations()
    assert items and all(i["popularity"] is None for i in items)


def test_load_popularity_invalid(monkeypatch, tmp_path):
    bad = tmp_path / "pop.json"
    bad.write_text("not json")
    monkeypatch.setattr(rec, "POPULARITY_CACHE", str(bad))
    assert rec._load_popularity() == {}
