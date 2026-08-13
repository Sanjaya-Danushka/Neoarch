"""Unit tests for the Installed-section extras: size, install reason, reverse deps, sorting."""

import subprocess

import pytest


def _fake_result(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, "")


def test_list_explicit_packages(monkeypatch):
    from neoarch.backend.services import hygiene

    monkeypatch.setattr(
        hygiene,
        "_run",
        lambda cmd, timeout=60: _fake_result("linux\nfirefox 6.1-1\npython\n"),
    )
    assert hygiene.list_explicit_packages() == {"linux", "firefox", "python"}


def test_list_explicit_packages_error(monkeypatch):
    from neoarch.backend.services import hygiene

    monkeypatch.setattr(
        hygiene,
        "_run",
        lambda cmd, timeout=60: _fake_result("error: you cannot perform this operation", returncode=1),
    )
    assert hygiene.list_explicit_packages() == set()


def test_package_info_parses_qi(monkeypatch):
    from neoarch.backend.services import hygiene

    sample = (
        "Name            : firefox\n"
        "Version         : 128.0.1-1\n"
        "Description     : Standalone web browser\n"
        "Install Reason  : Explicitly installed\n"
        "Required By     : None\n"
        "Installed Size  : 273.34 MiB\n"
    )
    monkeypatch.setattr(hygiene, "_run", lambda cmd, timeout=30: _fake_result(sample))
    info = hygiene.package_info("firefox")
    assert info["install_reason"] == "Explicitly installed"
    assert info["required_by"] == []
    assert info["installed_size"] == int(273.34 * 1024 * 1024)
    assert info["description"] == "Standalone web browser"


def test_package_info_required_by(monkeypatch):
    from neoarch.backend.services import hygiene

    sample = (
        "Name            : qt5-base\n"
        "Install Reason  : Installed as a dependency for another package\n"
        "Required By     : firefox dolphin ark\n"
        "Installed Size  : 102.00 MiB\n"
    )
    monkeypatch.setattr(hygiene, "_run", lambda cmd, timeout=30: _fake_result(sample))
    info = hygiene.package_info("qt5-base")
    assert info["install_reason"] == "Installed as a dependency for another package"
    assert info["required_by"] == ["firefox", "dolphin", "ark"]


def test_package_info_missing(monkeypatch):
    from neoarch.backend.services import hygiene

    monkeypatch.setattr(
        hygiene,
        "_run",
        lambda cmd, timeout=30: _fake_result("error: package 'nope' was not found", returncode=1),
    )
    assert hygiene.package_info("nope") == {}


def test_sort_installed_by_size():
    from neoarch.backend.services.filter import _sort_installed

    pkgs = [{"name": "small"}, {"name": "big"}, {"name": "mid"}]
    sizes = {"big": 1000, "mid": 500, "small": 100}
    result = _sort_installed(pkgs, "size", False, sizes)
    assert [p["name"] for p in result] == ["big", "mid", "small"]
    result_asc = _sort_installed(pkgs, "size", True, sizes)
    assert [p["name"] for p in result_asc] == ["small", "mid", "big"]


def test_sort_installed_by_name():
    from neoarch.backend.services.filter import _sort_installed

    pkgs = [{"name": "zeta"}, {"name": "alpha"}, {"name": "Beta"}]
    result = _sort_installed(pkgs, "name", True, {})
    assert [p["name"] for p in result] == ["alpha", "Beta", "zeta"]


def test_sort_installed_updates_first_by_status():
    from neoarch.backend.services.filter import _sort_installed

    pkgs = [{"name": "a", "has_update": False}, {"name": "b", "has_update": True}]
    result = _sort_installed(pkgs, "status", True, {})
    assert [p["name"] for p in result] == ["b", "a"]
