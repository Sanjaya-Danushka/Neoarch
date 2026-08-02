import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neoarch.cli import (
    _build_parser,
    _scan_global_flags,
    _list_pacman,
    _fmt_dict,
    _load_config,
    _save_config,
)


def test_parser_has_all_commands():
    p = _build_parser()
    subs = {}
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            subs.update(action.choices)
    for expected in (
        "search", "install", "remove", "upgrade", "update", "list",
        "list-updates", "ignore", "news", "backup", "purge", "config",
        "scan", "doctor",
    ):
        assert expected in subs, f"missing command {expected}"


def test_global_flags_accepted_before_and_after_subcommand():
    p = _build_parser()
    a = p.parse_args(["--json", "search", "code", "--limit", "1"])
    assert a.command == "search"
    flags = _scan_global_flags(["--json", "search", "code", "--limit", "1"])
    assert flags.get("json") is True
    b = p.parse_args(["search", "--json", "code"])
    assert b.command == "search"
    flags2 = _scan_global_flags(["search", "--json", "code"])
    assert flags2.get("json") is True


def test_global_flags_scan():
    assert _scan_global_flags([]) == {}
    assert _scan_global_flags(["-y", "install", "foo"]) == {"yes": True}
    assert _scan_global_flags(["--no-confirm", "remove", "x"]) == {"no_confirm": True}
    assert _scan_global_flags(["--json", "--yes", "search", "x"]) == {"json": True, "yes": True}


def test_fmt_dict_picks_name_field():
    assert _fmt_dict({"name": "firefox", "version": "1.0", "desc": "browser"}) == "firefox  1.0  browser"


def test_list_pacman_parses_installed(tmp_path):
    os.chdir(tmp_path)
    pkgs = _list_pacman(False, False, False)
    assert isinstance(pkgs, list)
    assert all("name" in p and "version" in p for p in pkgs)


def test_config_roundtrip(tmp_path, monkeypatch):
    cfg = str(tmp_path / "config.json")
    monkeypatch.setattr("neoarch.cli._CONFIG_PATH", cfg)
    _save_config({"aur_helper": "auto", "autoupdate_interval_days": 5})
    data = _load_config()
    assert data["aur_helper"] == "auto"
    assert data["autoupdate_interval_days"] == 5
    assert "check_updates_on_startup" in data


def test_config_defaults(tmp_path, monkeypatch):
    cfg = str(tmp_path / "missing.json")
    monkeypatch.setattr("neoarch.cli._CONFIG_PATH", cfg)
    data = _load_config()
    assert data["autoupdate_enabled"] is False
    assert data["snapshot_before_update"] is False


def test_cmd_scan_flags_json(tmp_path):
    p = _build_parser()
    a = p.parse_args(["scan", "--json", "PKGBUILD"])
    assert a.command == "scan"
    assert a.json is True
    assert a.paths == ["PKGBUILD"]
    a2 = p.parse_args(["--json", "scan", "PKGBUILD"])
    assert _scan_global_flags(["--json", "scan", "PKGBUILD"]).get("json") is True


def test_cmd_scan_reports_clean(tmp_path, capsys):
    from neoarch.cli import cmd_scan

    p = tmp_path / "PKGBUILD"
    p.write_text("pkgname=ok\npkgver=1.0\nsource=('ok.tar.gz')\n")
    args = _build_parser().parse_args(["scan", str(p)])
    cmd_scan(args)
    out = capsys.readouterr().out
    assert "No security issues found." in out


def test_cmd_scan_reports_findings(tmp_path, capsys):
    from neoarch.cli import cmd_scan

    p = tmp_path / "PKGBUILD"
    p.write_text(
        "pkgname=x\npost_install() {\n  sudo systemctl enable x\n}\n"
    )
    args = _build_parser().parse_args(["scan", str(p)])
    with pytest.raises(SystemExit) as exc:
        cmd_scan(args)
    assert exc.value.code == 2
    out = capsys.readouterr().out
    assert "critical" in out
    assert "privilege elevation" in out
