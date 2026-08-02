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
        "scan", "downgrade", "marks", "appimage", "keyring", "purify",
        "restart", "parallel", "schedule", "recommend", "doctor",
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


def test_cmd_downgrade_parser_flags():
    p = _build_parser()
    a = p.parse_args(["downgrade", "firefox", "--list-only", "--pin", "--version", "1.0"])
    assert a.command == "downgrade"
    assert a.package == "firefox"
    assert a.list_only is True
    assert a.pin is True
    assert a.version == "1.0"


def test_cmd_downgrade_no_cached(tmp_path, monkeypatch, capsys):
    from neoarch.cli import cmd_downgrade
    from neoarch.backend.services import downgrade

    monkeypatch.setattr(downgrade, "list_cached_versions", lambda pkg: [])
    args = _build_parser().parse_args(["downgrade", "nope"])
    cmd_downgrade(args)
    assert "No cached versions" in capsys.readouterr().out


def test_cmd_marks_parser():
    p = _build_parser()
    a = p.parse_args(["marks", "list"])
    assert a.command == "marks"
    assert a.action == "list"
    b = p.parse_args(["marks", "reason", "firefox", "explicit"])
    assert b.action == "reason"
    assert b.package == "firefox"
    assert b.reason == "explicit"


def test_cmd_marks_list(monkeypatch, capsys):
    from neoarch.cli import cmd_marks
    from neoarch.backend.services import marks

    monkeypatch.setattr(marks, "get_ignorepkg", lambda: ["firefox"])
    monkeypatch.setattr(marks, "get_holdpkg", lambda: ["linux"])
    args = _build_parser().parse_args(["marks", "list"])
    cmd_marks(args)
    out = capsys.readouterr().out
    assert "IgnorePkg: firefox" in out
    assert "HoldPkg:    linux" in out


def test_cmd_marks_reason_read(monkeypatch, capsys):
    from neoarch.cli import cmd_marks
    from neoarch.backend.services import marks

    monkeypatch.setattr(marks, "get_install_reason", lambda pkg: "explicit")
    args = _build_parser().parse_args(["marks", "reason", "firefox"])
    cmd_marks(args)
    assert "firefox: explicit" in capsys.readouterr().out


def test_cmd_marks_reason_set(monkeypatch, capsys):
    from neoarch.cli import cmd_marks
    from neoarch.backend.services import marks

    monkeypatch.setattr(marks, "set_install_reason", lambda pkg, reason: True)
    args = _build_parser().parse_args(["marks", "reason", "firefox", "deps"])
    cmd_marks(args)
    assert "marked as deps" in capsys.readouterr().out


def test_cmd_appimage_parser_actions():
    p = _build_parser()
    assert p.parse_args(["appimage", "list"]).action == "list"
    a = p.parse_args(["appimage", "add", "x.AppImage"])
    assert a.file == "x.AppImage"
    b = p.parse_args(["appimage", "add-repo", "App", "owner/repo", "--host", "codeberg"])
    assert b.repo == "owner/repo" and b.host == "codeberg"
    c = p.parse_args(["appimage", "update", "app1"])
    assert c.id == "app1"
    assert p.parse_args(["appimage", "check"]).id is None


def test_cmd_appimage_list_empty(monkeypatch, capsys):
    from neoarch.cli import cmd_appimage
    from neoarch.backend.services import appimage as svc

    monkeypatch.setattr(svc, "list_appimages", lambda: [])
    args = _build_parser().parse_args(["appimage", "list"])
    cmd_appimage(args)
    assert "No managed AppImages" in capsys.readouterr().out


def test_cmd_appimage_add_missing_file(monkeypatch, capsys):
    from neoarch.cli import cmd_appimage

    args = _build_parser().parse_args(["appimage", "add", "/nope/App.AppImage"])
    with pytest.raises(SystemExit) as exc:
        cmd_appimage(args)
    assert exc.value.code == 1


def test_cmd_keyring_parser_actions():
    p = _build_parser()
    assert p.parse_args(["keyring", "list"]).action == "list"
    assert p.parse_args(["keyring", "sign", "ABCDEF1234567890ABCDEF1234567890ABCDEF12"]).key \
        == "ABCDEF1234567890ABCDEF1234567890ABCDEF12"
    assert p.parse_args(["keyring", "populate"]).keyrings == []


def test_cmd_keyring_sign(monkeypatch, capsys):
    from neoarch.cli import cmd_keyring
    from neoarch.backend.services import keyring

    monkeypatch.setattr(keyring, "locally_sign", lambda k: True)
    args = _build_parser().parse_args(["keyring", "sign", "ABCD"])
    cmd_keyring(args)
    assert "Locally signed" in capsys.readouterr().out


def test_cmd_purify_parser_actions():
    p = _build_parser()
    assert p.parse_args(["purify", "corrupt"]).action == "corrupt"
    c = p.parse_args(["purify", "cache", "--keep", "5"])
    assert c.action == "cache" and c.keep == 5
    m = p.parse_args(["purify", "merge", "/etc/foo.pacnew", "--accept"])
    assert m.path == "/etc/foo.pacnew" and m.accept is True


def test_cmd_purify_corrupt_clean(monkeypatch, capsys):
    from neoarch.cli import cmd_purify
    from neoarch.backend.services import hygiene

    monkeypatch.setattr(hygiene, "list_corrupted_packages", lambda: [])
    args = _build_parser().parse_args(["purify", "corrupt"])
    cmd_purify(args)
    assert "No corrupted package archives" in capsys.readouterr().out


def test_cmd_purify_merge_conflicts(monkeypatch, capsys):
    from neoarch.cli import cmd_purify
    from neoarch.backend.services import hygiene

    monkeypatch.setattr(hygiene, "merge_pacnew",
                        lambda path, accept=False: {"merged": "/etc/foo.merged",
                                                    "conflicts": True, "backup": ""})
    args = _build_parser().parse_args(["purify", "merge", "/etc/foo.pacnew"])
    with pytest.raises(SystemExit) as exc:
        cmd_purify(args)
    assert exc.value.code == 2


def test_cmd_restart_check(monkeypatch, capsys):
    from neoarch.cli import cmd_restart
    from neoarch.backend.services import restart_check

    monkeypatch.setattr(restart_check, "check_restart_required",
                        lambda: [{"category": "kernel",
                                  "message": "reboot now"}])
    args = _build_parser().parse_args(["restart", "check"])
    cmd_restart(args)
    assert "kernel" in capsys.readouterr().out

    monkeypatch.setattr(restart_check, "check_restart_required", lambda: [])
    args = _build_parser().parse_args(["restart", "check"])
    cmd_restart(args)
    assert "No restart required" in capsys.readouterr().out


def test_cmd_parallel_show(monkeypatch, capsys):
    from neoarch.cli import cmd_parallel
    from neoarch.backend.services import pacman_conf

    monkeypatch.setattr(pacman_conf, "get_parallel_downloads", lambda: 5)
    args = _build_parser().parse_args(["parallel"])
    cmd_parallel(args)
    assert "ParallelDownloads = 5" in capsys.readouterr().out


def test_cmd_parallel_set(monkeypatch, capsys):
    from neoarch.cli import cmd_parallel
    from neoarch.backend.services import pacman_conf

    monkeypatch.setattr(pacman_conf, "set_parallel_downloads", lambda n: n == 8)
    args = _build_parser().parse_args(["parallel", "8"])
    cmd_parallel(args)
    assert "written to" in capsys.readouterr().out


def test_cmd_schedule_set(monkeypatch, tmp_path, capsys):
    from neoarch.cli import cmd_schedule, _CONFIG_PATH

    cfg = tmp_path / "config.json"
    monkeypatch.setattr("neoarch.cli._CONFIG_PATH", str(cfg))
    args = _build_parser().parse_args(
        ["schedule", "set", "--days", "1,3,5", "--time", "05:30", "--enable"])
    cmd_schedule(args)
    out = capsys.readouterr().out
    assert "05:30" in out

    args = _build_parser().parse_args(["schedule", "show", "--json"])
    cmd_schedule(args)
    import json as _json
    data = _json.loads(capsys.readouterr().out)
    assert data["schedule_days"] == [1, 3, 5]
    assert data["schedule_enabled"] is True


def test_cmd_schedule_set_invalid(monkeypatch, tmp_path):
    from neoarch.cli import cmd_schedule

    cfg = tmp_path / "config.json"
    monkeypatch.setattr("neoarch.cli._CONFIG_PATH", str(cfg))
    args = _build_parser().parse_args(["schedule", "set", "--time", "25:99"])
    with pytest.raises(SystemExit) as exc:
        cmd_schedule(args)
    assert exc.value.code == 1


def test_cmd_recommend(monkeypatch, capsys):
    from neoarch.cli import cmd_recommend
    from neoarch.backend.services import recommend

    monkeypatch.setattr(recommend, "recommendations",
                        lambda limit=20, include_installed=False:
                        [{"name": "htop", "desc": "top", "category": "utilities",
                          "popularity": None, "installed": False}])
    args = _build_parser().parse_args(["recommend"])
    cmd_recommend(args)
    assert "htop" in capsys.readouterr().out
