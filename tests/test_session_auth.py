"""Tests for neoarch.backend.session_auth – credential management helpers."""
import os
import stat
from pathlib import Path

from neoarch.backend.session_auth import (
    is_session_active,
    get_askpass_env,
    cleanup_session,
    get_sudo_password,
    store_sudo_password,
    delete_sudo_password,
    _read_cred_file,
    _write_cred_file,
    _delete_cred_file,
    secure_string,
    SecureBytes,
)
import neoarch.backend.session_auth as sa_mod


# ---------------------------------------------------------------------------
# is_session_active
# ---------------------------------------------------------------------------

def test_is_session_active_default(monkeypatch):
    monkeypatch.setattr(sa_mod, "_session_active", False)
    assert is_session_active() is False


def test_is_session_active_true(monkeypatch):
    monkeypatch.setattr(sa_mod, "_session_active", True)
    assert is_session_active() is True


# ---------------------------------------------------------------------------
# get_askpass_env
# ---------------------------------------------------------------------------

def test_get_askpass_env_active(monkeypatch):
    monkeypatch.setattr(sa_mod, "_session_active", True)
    monkeypatch.setattr(sa_mod, "_session_askpass_script", "/tmp/helper")
    env = get_askpass_env()
    assert env["SUDO_ASKPASS"] == "/tmp/helper"
    assert env["SSH_ASKPASS"] == "/tmp/helper"


def test_get_askpass_env_inactive(monkeypatch):
    monkeypatch.setattr(sa_mod, "_session_active", False)
    env = get_askpass_env()
    assert "SUDO_ASKPASS" not in env


# ---------------------------------------------------------------------------
# secure_string / SecureBytes
# ---------------------------------------------------------------------------

def test_secure_string_roundtrip():
    ss = secure_string("hello")
    assert ss.get_bytes() == b"hello"


def test_secure_string_zero():
    ss = secure_string("hello")
    ss.zero()
    # ctypes .value returns b"" after zeroing (stops at null terminator)
    assert ss.get_bytes() == b""


# ---------------------------------------------------------------------------
# _write_cred_file / _read_cred_file / _delete_cred_file
# ---------------------------------------------------------------------------

def test_write_and_read_cred_file(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    assert _write_cred_file(b"mypass") is True
    assert _read_cred_file() == "mypass"


def test_write_cred_file_permissions(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    _write_cred_file(b"pw")
    mode = stat.S_IMODE(os.stat(str(cred)).st_mode)
    assert mode == 0o600


def test_read_cred_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sa_mod, "_CRED_FILE", tmp_path / "nonexistent")
    assert _read_cred_file() is None


def test_delete_cred_file(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    cred.write_text("secret")
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    _delete_cred_file()
    assert not cred.exists()


# ---------------------------------------------------------------------------
# store_sudo_password / get_sudo_password / delete_sudo_password
# ---------------------------------------------------------------------------

def test_store_sudo_password_writes_file(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    monkeypatch.setattr(sa_mod, "_load_keyring", lambda: None)

    pw = secure_string("testpw")
    assert store_sudo_password(pw) is True
    assert cred.read_text() == "testpw"


def test_store_sudo_password_returns_true(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    monkeypatch.setattr(sa_mod, "_load_keyring", lambda: None)

    pw = secure_string("x")
    assert store_sudo_password(pw) is True


def test_delete_sudo_password_removes_file(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    monkeypatch.setattr(sa_mod, "_load_keyring", lambda: None)

    pw = secure_string("abc")
    store_sudo_password(pw)
    assert cred.exists()
    delete_sudo_password()
    assert not cred.exists()


def test_cleanup_session_removes_lock_and_cred(tmp_path, monkeypatch):
    cache = tmp_path / ".cache" / "neoarch"
    cache.mkdir(parents=True)
    lock = cache / "session.lock"
    lock.touch()
    cred = cache / "sudo_credential"
    cred.write_text("pw")
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    monkeypatch.setattr(sa_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(sa_mod, "_session_active", True)
    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)

    cleanup_session()

    assert not lock.exists()
    assert not cred.exists()


def test_get_sudo_password_reads_file(tmp_path, monkeypatch):
    cred = tmp_path / "cred"
    cred.write_text("savedpw")
    monkeypatch.setattr(sa_mod, "_CRED_FILE", cred)
    monkeypatch.setattr(sa_mod, "_load_keyring", lambda: None)

    result = get_sudo_password()
    assert isinstance(result, SecureBytes)
    assert result.get_bytes() == b"savedpw"


def test_get_sudo_password_no_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(sa_mod, "_CRED_FILE", tmp_path / "nonexistent")
    monkeypatch.setattr(sa_mod, "_load_keyring", lambda: None)

    assert get_sudo_password() is None
