"""Tests for neoarch.backend.auth – auth command and askpass env helpers."""
import os
import sys

import pytest

from neoarch.backend.auth import get_auth_command, prepare_askpass_env
import neoarch.backend.auth as auth_mod


def test_get_auth_command():
    assert get_auth_command() == ["sudo", "-A"]


def test_prepare_askpass_env_creates_script(monkeypatch):
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    env, script_path = prepare_askpass_env()

    assert os.path.exists(script_path)
    with open(script_path) as f:
        content = f.read()
    assert "askpass_gui" in content

    os.unlink(script_path)


def test_prepare_askpass_env_returns_env(monkeypatch):
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    env, script_path = prepare_askpass_env()

    assert "SUDO_ASKPASS" in env
    assert env["SUDO_ASKPASS"] == script_path

    os.unlink(script_path)


def test_prepare_askpass_env_script_has_pythonpath(monkeypatch):
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    env, script_path = prepare_askpass_env()

    assert "PYTHONPATH" in env
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(auth_mod.__file__)))
    )
    assert project_root in env["PYTHONPATH"]

    os.unlink(script_path)
