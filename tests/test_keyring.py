"""Tests for the pacman keyring manager (Phase 4 roadmap)."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.keyring as keyring


def test_list_keyring_parses(monkeypatch):
    out = (
        "pub   ed25519 2020-12-31 [SC]\n"
        "ABCDEF1234567890ABCDEF1234567890ABCDEF12  [full] keyring\n"
        "uid                  Arch Linux Master Signing Key\n"
        "pub   rsa4096 2021-01-01 [SC]\n"
        "1234567890123456789012345678901234567890  [expired]\n"
    )
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 0, stdout=out, stderr=""))
    keys = keyring.list_keyring()
    assert len(keys) == 2
    assert keys[0]["fingerprint"] == "ABCDEF1234567890ABCDEF1234567890ABCDEF12"
    assert keys[0]["uid"] == "Arch Linux Master Signing Key"
    assert keys[0]["created"] == "2020-12-31"
    assert "expired" in keys[1]["validity"]


def test_list_keyring_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 1, stdout="", stderr="error"))
    assert keyring.list_keyring() == []


def test_normalize_fingerprint():
    assert keyring._normalize_fingerprint("ab cd ef 12") == "ABCDEF12"
    assert keyring._normalize_fingerprint("abcdef") == "ABCDEF"


def test_valid_key():
    assert keyring._valid_key("ABCDEF1234567890ABCDEF1234567890ABCDEF12") is True
    assert keyring._valid_key("; rm -rf /") is False
    assert keyring._valid_key("abc") is False


def test_key_details(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, 0, stdout="uid      Arch Maintainer\n", stderr=""))
    info = keyring.key_details("ABCDEF1234567890ABCDEF1234567890ABCDEF12")
    assert "Arch Maintainer" in info["list"]


def test_mutations_use_pacman_key(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=900, env=None, **kw):
        calls.append(cmd)
        assert cmd[0] == "sudo"
        assert cmd[2] == "pacman-key"
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(keyring, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(keyring, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert keyring.init_keyring() is True
    assert "--init" in calls[-1]

    assert keyring.populate_keyring() is True
    assert "--populate" in calls[-1]
    assert "archlinux" in calls[-1]

    assert keyring.refresh_keys() is True
    assert "--refresh-keys" in calls[-1]

    assert keyring.receive_key("ABCDEF1234567890ABCDEF1234567890ABCDEF12") is True
    assert "--recv-keys" in calls[-1]

    assert keyring.locally_sign("ABCDEF1234567890ABCDEF1234567890ABCDEF12") is True
    assert "--lsign-key" in calls[-1]


def test_mutations_validate_key():
    assert keyring.receive_key("bad; rm -rf") is False
    assert keyring.locally_sign("bad") is False


def test_populate_custom_keyrings(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=900, env=None, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(keyring, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(keyring, "get_askpass_env", lambda: {})
    monkeypatch.setattr(subprocess, "run", fake_run)
    keyring.populate_keyring(["archlinux"])
    assert calls[-1][-1] == "archlinux"
