"""Tests for neoarch.backend.workers.strip_ansi and
   neoarch.backend.package.installer pure/mockable helpers."""
from unittest.mock import MagicMock

from tests.conftest import FakeCompletedProcess
from neoarch.backend.workers import strip_ansi
from neoarch.backend.package.installer import _process_pty_buf, _clean_pacman_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Emitter:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class WorkerStub:
    def __init__(self):
        self.output = Emitter()
        self.line_update = Emitter()


# ---------------------------------------------------------------------------
# strip_ansi
# ---------------------------------------------------------------------------

def test_strip_ansi_color_codes():
    assert strip_ansi("\033[31mhello\033[0m") == "hello"


def test_strip_ansi_osc():
    assert strip_ansi("\033]0;title\033\\") == ""


def test_strip_ansi_plain():
    assert strip_ansi("no ansi here") == "no ansi here"


def test_strip_ansi_empty():
    assert strip_ansi("") == ""


# ---------------------------------------------------------------------------
# _process_pty_buf
# ---------------------------------------------------------------------------

def test_process_single_line():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "pkg done\n", lambda l: parse_calls.append(l), worker
    )

    assert result == ""
    assert parse_calls == ["pkg done"]
    assert worker.output.calls == [("pkg done",)]
    assert worker.line_update.calls == []


def test_process_multiple_lines():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "a\nb\n", lambda l: parse_calls.append(l), worker
    )

    assert result == ""
    assert parse_calls == ["a", "b"]
    assert worker.output.calls == [("a",), ("b",)]


def test_process_skips_blank():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "\n\n", lambda l: parse_calls.append(l), worker
    )

    assert result == ""
    assert parse_calls == []
    assert worker.output.calls == []
    assert worker.line_update.calls == []


def test_process_progress_cr():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "pre\r50%", lambda l: parse_calls.append(l), worker, final=False
    )

    assert parse_calls == ["50%"]
    assert worker.line_update.calls == [("50%",)]
    assert worker.output.calls == []
    assert result == "50%"


def test_process_partial_line_not_final():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "half", lambda l: parse_calls.append(l), worker, final=False
    )

    assert result == "half"
    assert parse_calls == []
    assert worker.output.calls == []
    assert worker.line_update.calls == []


def test_process_partial_line_final():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "half", lambda l: parse_calls.append(l), worker, final=True
    )

    assert result == ""
    assert parse_calls == ["half"]
    assert worker.output.calls == [("half",)]
    assert worker.line_update.calls == []


def test_process_crlf_progress_with_ansi():
    parse_calls = []
    worker = WorkerStub()
    buf = "\033[31m50%\033[0m\r\033[32m60%\033[0m"

    result = _process_pty_buf(
        buf, lambda l: parse_calls.append(l), worker, final=False
    )

    assert parse_calls == ["60%"]
    assert worker.line_update.calls == [("60%",)]


def test_process_cr_within_newline():
    parse_calls = []
    worker = WorkerStub()

    result = _process_pty_buf(
        "first\rsecond\n", lambda l: parse_calls.append(l), worker
    )

    assert result == ""
    assert parse_calls == ["second"]
    assert worker.output.calls == [("second",)]


# ---------------------------------------------------------------------------
# _clean_pacman_cache
# ---------------------------------------------------------------------------

def test_clean_pacman_cache_calls_sudo_sc(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.installer.get_askpass_env",
        lambda: {"SUDO_ASKPASS": "/usr/bin/askpass"},
    )
    recorded = []
    monkeypatch.setattr(
        "neoarch.backend.package.installer.subprocess.run",
        lambda cmd, **kw: recorded.append(cmd) or FakeCompletedProcess(),
    )

    _clean_pacman_cache(MagicMock())

    assert recorded == [["sudo", "-A", "pacman", "-Sc", "--noconfirm"]]


def test_clean_pacman_cache_suppresses_error(monkeypatch):
    monkeypatch.setattr(
        "neoarch.backend.package.installer.get_askpass_env",
        lambda: {},
    )

    def _raise(*a, **kw):
        raise RuntimeError("no sudo")

    monkeypatch.setattr(
        "neoarch.backend.package.installer.subprocess.run", _raise
    )

    _clean_pacman_cache(MagicMock())
