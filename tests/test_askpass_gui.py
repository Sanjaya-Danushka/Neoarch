"""Tests for neoarch.backend.askpass_gui – cached credential and main path."""
import os
from pathlib import Path

import pytest

from neoarch.backend.askpass_gui import _cached_credential, _marker_path, main
import neoarch.backend.askpass_gui as ag_mod


def test_cached_credential_no_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)
    assert _cached_credential() is None


def test_cached_credential_with_file(tmp_path, monkeypatch):
    cache = tmp_path / ".cache" / "neoarch"
    cache.mkdir(parents=True)
    (cache / "session.lock").touch()
    (cache / "sudo_credential").write_text("secret123")

    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)
    # keyring is imported locally inside _cached_credential, so patch the
    # module-level keyring.get_password to return None and force file fallback
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda svc, user: None)

    result = _cached_credential()
    assert result == "secret123"


def test_cached_credential_no_lock_file(tmp_path, monkeypatch):
    cache = tmp_path / ".cache" / "neoarch"
    cache.mkdir(parents=True)
    (cache / "sudo_credential").write_text("pw")
    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda svc, user: None)

    result = _cached_credential()
    assert result is None


def test_marker_path(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)
    p = _marker_path()
    assert str(p).endswith("auth_in_progress")


def test_main_fast_path(tmp_path, monkeypatch, capsys):
    cache = tmp_path / ".cache" / "neoarch"
    cache.mkdir(parents=True)
    (cache / "session.lock").touch()
    (cache / "sudo_credential").write_text("pw123")
    monkeypatch.setattr(Path, "home", lambda self=0: tmp_path)
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda svc, user: None)

    rc = main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "pw123" in captured.out
