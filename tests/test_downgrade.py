"""Tests for the package downgrade service (Phase 3a roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.downgrade as downgrade


def _make_pkg(tmp_path, name, ver, rel="1", arch="x86_64", ext="zst"):
    fname = f"{name}-{ver}-{rel}-{arch}.pkg.tar.{ext}"
    path = tmp_path / fname
    path.write_bytes(b"\x1f\x8b")
    return str(path)


def test_parse_pkgfile_basic(tmp_path):
    path = _make_pkg(tmp_path, "firefox", "140.0")
    info = downgrade._parse_pkgfile(path)
    assert info["name"] == "firefox"
    assert info["version"] == "140.0"
    assert info["release"] == "1"
    assert info["arch"] == "x86_64"
    assert info["full"] == "0:140.0-1"


def test_parse_pkgfile_epoch(tmp_path):
    path = _make_pkg(tmp_path, "systemd", "2:249.0")
    info = downgrade._parse_pkgfile(path)
    assert info["epoch"] == "2"
    assert info["full"] == "2:249.0-1"


def test_parse_pkgfile_name_with_dashes(tmp_path):
    path = _make_pkg(tmp_path, "lib32-foo", "1.0")
    info = downgrade._parse_pkgfile(path)
    assert info["name"] == "lib32-foo"


def test_parse_pkgfile_garbage():
    assert downgrade._parse_pkgfile("README.txt") is None
    assert downgrade._parse_pkgfile("firefox.pkg.tar.zst") is None


def test_list_cached_versions_sorted_desc(tmp_path):
    _make_pkg(tmp_path, "firefox", "138.0")
    _make_pkg(tmp_path, "firefox", "140.0")
    _make_pkg(tmp_path, "firefox", "139.0")
    _make_pkg(tmp_path, "firefox", "1:1.0")   # higher epoch wins
    _make_pkg(tmp_path, "chromium", "120.0")  # different package
    versions = downgrade.list_cached_versions("firefox", extra_dirs=[str(tmp_path)])
    assert [v["version"] for v in versions] == ["1.0", "140.0", "139.0", "138.0"]
    assert [v["epoch"] for v in versions] == ["1", "0", "0", "0"]


def test_list_cached_versions_dedupes(tmp_path):
    _make_pkg(tmp_path, "foo", "1.0", arch="x86_64")
    _make_pkg(tmp_path, "foo", "1.0", arch="any")
    versions = downgrade.list_cached_versions("foo", extra_dirs=[str(tmp_path)])
    assert len(versions) == 2
    assert {v["arch"] for v in versions} == {"x86_64", "any"}


def test_list_cached_versions_no_match(tmp_path):
    assert downgrade.list_cached_versions("nope", extra_dirs=[str(tmp_path)]) == []


def test_resolve_cache_path(tmp_path, monkeypatch):
    _make_pkg(tmp_path, "foo", "1.0")
    _make_pkg(tmp_path, "foo", "2.0")
    monkeypatch.setattr(downgrade, "cache_dirs", lambda: [str(tmp_path)])
    assert os.path.basename(downgrade.resolve_cache_path("foo")) == "foo-2.0-1-x86_64.pkg.tar.zst"
    assert os.path.basename(downgrade.resolve_cache_path("foo", "1.0")) == "foo-1.0-1-x86_64.pkg.tar.zst"
    assert downgrade.resolve_cache_path("foo", "99.0") is None
    assert downgrade.resolve_cache_path("missing") is None


def test_vercmp_matches_pacman(monkeypatch):
    fake = subprocess.CompletedProcess(["vercmp", "1.0", "2.0"], 0, stdout="-1\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    assert downgrade.vercmp("1.0", "2.0") == -1


def test_vercmp_fallback():
    assert downgrade._vercmp_fallback("1.0", "2.0") == -1
    assert downgrade._vercmp_fallback("2.0", "1.9") == 1
    assert downgrade._vercmp_fallback("1.0", "1.0") == 0
    assert downgrade._vercmp_fallback("1:1.0", "2.0") == 1  # epoch dominates
    assert downgrade._vercmp_fallback("2:1.0", "1:9.9") == 1


def test_install_version_calls_pacman(tmp_path, monkeypatch):
    _make_pkg(tmp_path, "foo", "1.0")
    calls = []

    def fake_sudo(cmd, timeout=600, **kw):
        calls.append(cmd)
        assert cmd[0] == "sudo" or cmd[0] == "pacman"
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(downgrade, "cache_dirs", lambda: [str(tmp_path)])
    monkeypatch.setattr(downgrade, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(downgrade, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_sudo)

    ok = downgrade.install_version("foo", version="1.0")
    assert ok is True
    assert any(cmd and "pacman" in cmd and "-U" in cmd for cmd in calls)
    assert calls[0][0] == "sudo"


def test_install_version_missing_version(tmp_path, monkeypatch):
    monkeypatch.setattr(downgrade, "cache_dirs", lambda: [str(tmp_path)])
    assert downgrade.install_version("missing") is False


def test_install_version_explicit_path(tmp_path, monkeypatch):
    pkg = _make_pkg(tmp_path, "foo", "1.0")
    calls = []

    def fake_run(cmd, timeout=600, env=None, **kw):
        calls.append(cmd)
        assert cmd[0] == "sudo"
        assert cmd[2:4] == ["pacman", "-U"]
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(downgrade, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(downgrade, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert downgrade.install_version("foo", path=pkg) is True
    assert calls[0][5] == pkg


def test_add_to_ignorepkg_delegates(monkeypatch):
    from neoarch.backend.services import marks

    calls = []

    def fake_add(pkg):
        calls.append(pkg)
        return True

    monkeypatch.setattr(marks, "add_ignorepkg", fake_add)
    assert downgrade.add_to_ignorepkg("firefox") is True
    assert calls == ["firefox"]


def test_add_to_ignorepkg_already_present(monkeypatch):
    from neoarch.backend.services import marks

    monkeypatch.setattr(marks, "add_ignorepkg", lambda pkg: True)
    assert downgrade.add_to_ignorepkg("firefox") is True


def test_ignorepkg_shell_injection_rejected():
    assert downgrade.add_to_ignorepkg("foo; rm -rf /") is False


def test_ignorepkg_entries_parse_delegates(monkeypatch):
    from neoarch.backend.services import marks

    monkeypatch.setattr(marks, "get_ignorepkg",
                        lambda: ["firefox", "vim", "neovim"])
    entries = downgrade._ignorepkg_entries()
    assert entries == ["firefox", "vim", "neovim"]
