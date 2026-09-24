"""Unit tests for the pacman repo-map service (package → repository)."""

from neoarch.backend.services import repo_map

_SAMPLE = """core acl 2.3.1-2
core attr 2.5.2-1
extra 7zip 24.08-1
extra acl 2.3.2-1
multilib lib32-acl 2.3.1-2
chaotic-aur somepkg 1.0-1
chaotic-aur acl 2.3.2-2
"""


def test_parse_repo_list_maps_name_to_repo():
    mapping = repo_map.parse_repo_list(_SAMPLE)
    assert mapping["acl"] == "core"
    assert mapping["attr"] == "core"
    assert mapping["7zip"] == "extra"
    assert mapping["lib32-acl"] == "multilib"
    assert mapping["somepkg"] == "chaotic-aur"


def test_parse_repo_list_first_match_wins():
    mapping = repo_map.parse_repo_list(_SAMPLE)
    assert mapping["acl"] == "core"
    assert "somepkg" in mapping


def test_parse_repo_list_skips_blank_and_short_lines():
    mapping = repo_map.parse_repo_list("core broken\n\n \nextra ok 1.0-1\n")
    assert "ok" in mapping
    assert "broken" not in mapping


def test_parse_repo_list_empty_input():
    assert repo_map.parse_repo_list("") == {}


def test_get_repo_map_starts_empty_and_refresh_fills(monkeypatch):
    repo_map._repo_map = {}

    def fake_sl(*args, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(args[0] or ["pacman"], 0, _SAMPLE, "")

    monkeypatch.setattr(repo_map.subprocess, "run", fake_sl)
    mapping = repo_map.refresh_repo_map()
    assert mapping["7zip"] == "extra"
    assert repo_map.get_repo_map() == mapping


def test_refresh_failure_clears_cache(monkeypatch):
    repo_map._repo_map = {"acl": "extra"}

    def fail(*args, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(args[0] or ["pacman"], 1, "", "error")

    monkeypatch.setattr(repo_map.subprocess, "run", fail)
    refresh = repo_map.refresh_repo_map()
    assert refresh == {}
    assert repo_map.get_repo_map() == {}