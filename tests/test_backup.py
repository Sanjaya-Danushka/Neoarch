import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.backup as backup


def test_get_filesystem_type(monkeypatch):
    import subprocess
    fake = subprocess.CompletedProcess(["findmnt"], 0, stdout="btrfs\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    assert backup.get_filesystem_type() == "btrfs"


def test_export_package_list_structure(monkeypatch):
    import subprocess
    def fake_run(cmd, **kw):
        if cmd[0] == "pacman":
            mode = cmd[1]
            if mode == "-Qq":
                out = "pkg-a\npkg-b\n"
            elif mode == "-Qqen":
                out = "pkg-a\n"
            else:
                out = "pkg-b\n"
        elif cmd[0] == "npm":
            out = '{"foo": {}}'
        elif cmd[0] == "flatpak":
            out = "org.example.App\n"
        else:
            out = ""
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    data = backup._export_package_list()
    sources = data["sources"]
    assert sources["pacman_all"] == ["pkg-a", "pkg-b"]
    assert sources["pacman_explicit"] == ["pkg-a"]
    assert sources["pacman_foreign"] == ["pkg-b"]
    assert "flatpak" in sources
    assert "npm_global" in sources


def test_create_and_list_backup(tmp_path, monkeypatch):
    backup.get_backup_root = lambda: tmp_path
    backup._is_btrfs_root_snapshottable = lambda: False

    result = backup.create_backup()
    assert result["snapshot"] is None
    assert (tmp_path / result["timestamp"] / "package-list.json").exists()
    assert (tmp_path / result["timestamp"] / "config.tar.gz").exists()

    listed = backup.list_backups()
    assert len(listed) == 1
    assert listed[0]["timestamp"] == result["timestamp"]


def test_prune_backups_keeps_most_recent(tmp_path):
    backup.get_backup_root = lambda: tmp_path
    for i in range(4):
        d = tmp_path / f"20260101-{i:06d}"
        d.mkdir()
        (d / "package-list.json").write_text("{}")
    removed = backup.prune_backups(keep=2)
    assert len(removed) == 2
    remaining = [p.name for p in tmp_path.iterdir()]
    assert remaining == ["20260101-000003", "20260101-000002"]


def test_btrfs_detection_returns_none_without_btrfs(monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda name: None)
    assert backup._btrfs_root_subvolume() is None


def test_restore_packages_missing_file(tmp_path):
    assert backup.restore_packages(str(tmp_path)) is False


def test_restore_config_roundtrip(tmp_path, monkeypatch):
    backup.get_backup_root = lambda: tmp_path
    result = backup.create_backup()

    new_home = tmp_path / "home2"
    monkeypatch.setattr(Path, "home", lambda: new_home)
    ok = backup.restore_config(result["path"])
    assert ok is True
    assert (new_home / ".config" / "neoarch").exists()
