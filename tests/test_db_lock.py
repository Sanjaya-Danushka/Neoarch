"""Tests for the pacman DB lock detection helpers."""

import os
import subprocess

from neoarch.backend import sys_utils


def test_check_db_lock_no_lock(monkeypatch, tmp_path):
    lock = tmp_path / "db.lck"
    monkeypatch.setattr(sys_utils, "PACMAN_DB_LOCK", str(lock))
    assert not lock.exists()
    assert sys_utils.check_db_lock() is None


def test_check_db_lock_stale(monkeypatch, tmp_path):
    lock = tmp_path / "db.lck"
    lock.write_text("")
    monkeypatch.setattr(sys_utils, "PACMAN_DB_LOCK", str(lock))
    monkeypatch.setattr(sys_utils, "_lock_holder_pids", lambda: [])
    assert sys_utils.check_db_lock() == {"status": "stale"}


def test_check_db_lock_ours(monkeypatch, tmp_path):
    lock = tmp_path / "db.lck"
    lock.write_text("")
    monkeypatch.setattr(sys_utils, "PACMAN_DB_LOCK", str(lock))
    my_pid = os.getpid()
    monkeypatch.setattr(sys_utils, "_lock_holder_pids", lambda: [my_pid])
    assert sys_utils.check_db_lock() == {"status": "ours"}


def test_check_db_lock_other(monkeypatch, tmp_path):
    lock = tmp_path / "db.lck"
    lock.write_text("")
    monkeypatch.setattr(sys_utils, "PACMAN_DB_LOCK", str(lock))
    monkeypatch.setattr(sys_utils, "_lock_holder_pids", lambda: [999999])
    monkeypatch.setattr(sys_utils, "_is_neoarch_child", lambda p: False)
    monkeypatch.setattr(
        sys_utils, "_holder_is_other_package_manager", lambda p: True)
    assert sys_utils.check_db_lock() == {"status": "other"}


def test_check_db_lock_unknown(monkeypatch, tmp_path):
    lock = tmp_path / "db.lck"
    lock.write_text("")
    monkeypatch.setattr(sys_utils, "PACMAN_DB_LOCK", str(lock))
    monkeypatch.setattr(sys_utils, "_lock_holder_pids", lambda: [999999])
    monkeypatch.setattr(sys_utils, "_is_neoarch_child", lambda p: False)
    monkeypatch.setattr(
        sys_utils, "_holder_is_other_package_manager", lambda p: False)
    assert sys_utils.check_db_lock() == {"status": "unknown", "pid": 999999}


def test_holder_is_other_package_manager_sees_pacman(monkeypatch):
    class _FakeFile:
        def __init__(self, data):
            self._data = data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self._data

    def _fake_open(path, *_a, **_k):
        assert path == "/proc/12/cmdline"
        return _FakeFile(b"/usr/bin/pacman\x00--noconfirm\x00-Sy\x00")

    monkeypatch.setattr("builtins.open", _fake_open)
    assert sys_utils._holder_is_other_package_manager([12]) is True


def test_holder_is_other_package_manager_ignores_unknown(monkeypatch):
    class _FakeFile:
        def __init__(self, data):
            self._data = data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self._data

    def _fake_open(path, *_a, **_k):
        return _FakeFile(b"/usr/bin/something\x00else\x00")

    monkeypatch.setattr("builtins.open", _fake_open)
    assert sys_utils._holder_is_other_package_manager([12]) is False