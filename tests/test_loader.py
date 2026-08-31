"""Tests for neoarch.backend.package.loader – pure functions and mocked checkers."""
import json

from tests.conftest import FakeCompletedProcess
from neoarch.backend.package.loader import (
    _parse_qu_output,
    _installed_ts,
    _check_pacman_updates,
    _check_aur_updates,
    _check_flatpak_updates,
    _check_npm_updates,
)


# ---------------------------------------------------------------------------
# Pure function tests — no mocking needed
# ---------------------------------------------------------------------------

def test_parse_qu_output_basic():
    stdout = "pkg 1.0 -> 2.0\nother 2.3 -> 2.4"
    result = _parse_qu_output(stdout)
    assert len(result) == 2
    assert result[0]["name"] == "pkg"
    assert result[0]["version"] == "1.0"
    assert result[0]["new_version"] == "2.0"
    assert result[0]["source"] == "pacman"
    assert result[1]["name"] == "other"
    assert result[1]["version"] == "2.3"
    assert result[1]["new_version"] == "2.4"


def test_parse_qu_output_empty():
    assert _parse_qu_output(None) == []
    assert _parse_qu_output("") == []


def test_parse_qu_output_malformed():
    assert _parse_qu_output("pkg 1.0") == []
    assert _parse_qu_output("a 1 -> 2 -> 3") == []


def test_parse_qu_output_single_line():
    result = _parse_qu_output("foo 0.1 -> 0.2")
    assert len(result) == 1
    assert result[0]["name"] == "foo"


def test_parse_qu_output_surrounding_whitespace():
    result = _parse_qu_output("  bar  3.0  ->  4.0  ")
    assert len(result) == 1
    assert result[0]["name"] == "bar"
    assert result[0]["version"] == "3.0"
    assert result[0]["new_version"] == "4.0"


# ---------------------------------------------------------------------------
# _check_pacman_updates
# ---------------------------------------------------------------------------

def test_pacman_prefers_checkupdates(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    calls = []
    def fake_run_cmd(cmd, **kw):
        calls.append(cmd)
        return FakeCompletedProcess(stdout="pkg 1.0 -> 2.0")
    monkeypatch.setattr("neoarch.backend.package.loader._run_cmd", fake_run_cmd)

    result = _check_pacman_updates()
    assert calls[0] == ["checkupdates", "--nocolor"]
    assert len(result) == 1
    assert result[0]["name"] == "pkg"


def test_pacman_fallback(monkeypatch):
    monkeypatch.setattr(
        "shutil.which",
        lambda name: None if name == "checkupdates" else "/usr/bin/fakeroot",
    )
    calls = []
    def fake_run_cmd(cmd, **kw):
        calls.append(cmd)
        return FakeCompletedProcess(stdout="a 1 -> 2")
    monkeypatch.setattr("neoarch.backend.package.loader._run_cmd", fake_run_cmd)

    result = _check_pacman_updates()
    assert calls[0] == ["pacman", "-Qu"]
    assert len(result) == 1


def test_pacman_retry_once(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr("time.sleep", lambda _: None)
    results = iter([
        FakeCompletedProcess(returncode=1),
        FakeCompletedProcess(stdout="pkg 1.0 -> 2.0"),
    ])
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: next(results),
    )
    assert len(_check_pacman_updates()) == 1


def test_pacman_all_fail(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr("time.sleep", lambda _: None)
    results = iter([
        FakeCompletedProcess(returncode=1),
        FakeCompletedProcess(returncode=1),
        FakeCompletedProcess(returncode=1),
    ])
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: next(results),
    )
    assert _check_pacman_updates() == []


def test_pacman_no_updates(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(returncode=0, stdout=""),
    )
    assert _check_pacman_updates() == []


# ---------------------------------------------------------------------------
# _check_aur_updates
# ---------------------------------------------------------------------------

def test_aur_no_helpers(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda h: None)
    assert _check_aur_updates() == []


def test_aur_picks_best(monkeypatch):
    monkeypatch.setattr(
        "shutil.which",
        lambda h: f"/usr/bin/{h}" if h in ("yay", "paru") else None,
    )
    monkeypatch.setattr("time.sleep", lambda _: None)

    def fake_run_cmd(cmd, timeout=60, env=None):
        helper = cmd[0]
        if helper == "yay":
            return FakeCompletedProcess(stdout="a 1 -> 2\nb 2 -> 3\nc 3 -> 4")
        elif helper == "paru":
            return FakeCompletedProcess(stdout="x 1 -> 2")
        return FakeCompletedProcess(returncode=1)

    monkeypatch.setattr("neoarch.backend.package.loader._run_cmd", fake_run_cmd)
    result = _check_aur_updates()
    assert len(result) == 3
    assert all(p["source"] == "AUR" for p in result)


def test_aur_retry_all_empty(monkeypatch):
    monkeypatch.setattr(
        "shutil.which",
        lambda h: f"/usr/bin/{h}" if h == "yay" else None,
    )
    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, timeout=60, env=None: FakeCompletedProcess(stdout=""),
    )
    assert _check_aur_updates() == []


# ---------------------------------------------------------------------------
# _check_flatpak_updates
# ---------------------------------------------------------------------------

def test_flatpak_dedupes(monkeypatch):
    def fake_run_cmd(cmd, **kw):
        if "--updates" not in cmd:
            return FakeCompletedProcess(stdout="com.app.Test\t1.0")
        return FakeCompletedProcess(stdout="com.app.Test\t2.0")
    monkeypatch.setattr("neoarch.backend.package.loader._run_cmd", fake_run_cmd)

    result = _check_flatpak_updates()
    names = [p["name"] for p in result]
    assert names.count("com.app.Test") == 1


def test_flatpak_empty(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(stdout=""),
    )
    assert _check_flatpak_updates() == []


# ---------------------------------------------------------------------------
# _check_npm_updates
# ---------------------------------------------------------------------------

def test_npm_json_output(monkeypatch):
    data = {
        "typescript": {"current": "4.9.0", "latest": "5.0.0"},
        "prettier": {"current": "2.8.0", "latest": "3.0.0"},
    }
    monkeypatch.setattr(
        "neoarch.backend.package.loader.sys_utils.npm_user_mode_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(stdout=json.dumps(data)),
    )
    result = _check_npm_updates()
    assert len(result) == 2
    names = {p["name"] for p in result}
    assert names == {"typescript", "prettier"}
    assert all(p["source"] == "npm" for p in result)


def test_npm_empty_json(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.loader.sys_utils.npm_user_mode_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(stdout="{}"),
    )
    assert _check_npm_updates() == []


def test_npm_array_json(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.loader.sys_utils.npm_user_mode_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(stdout="[]"),
    )
    assert _check_npm_updates() == []


def test_npm_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.loader.sys_utils.npm_user_mode_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "neoarch.backend.package.loader._run_cmd",
        lambda cmd, **kw: FakeCompletedProcess(stdout="not json"),
    )
    assert _check_npm_updates() == []


# ---------------------------------------------------------------------------
# _installed_ts
# ---------------------------------------------------------------------------

def test_installed_ts_existing(monkeypatch):
    monkeypatch.setattr("neoarch.backend.package.loader.os.path.getmtime", lambda p: 12345.0)
    assert _installed_ts("pkg", "1.0") == 12345.0


def test_installed_ts_missing(monkeypatch):
    def raise_err(p):
        raise FileNotFoundError
    monkeypatch.setattr("neoarch.backend.package.loader.os.path.getmtime", raise_err)
    assert _installed_ts("pkg", "1.0") == 0
