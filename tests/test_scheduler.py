"""Tests for the weekly scheduler model (Phase 5 roadmap)."""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.scheduler as sched


def test_parse_time():
    assert sched.parse_time("03:00") == (3, 0)
    assert sched.parse_time("9:05") == (9, 5)
    assert sched.parse_time("24:00") is None
    assert sched.parse_time("3:60") is None
    assert sched.parse_time("junk") is None


def test_validate_schedule():
    assert sched.validate_schedule([0, 1], "03:00") is True
    assert sched.validate_schedule([], "03:00") is False
    assert sched.validate_schedule([7], "03:00") is False
    assert sched.validate_schedule([0], "nope") is False


def test_next_run_today_later():
    now = datetime(2026, 8, 2, 12, 0)  # Sunday (weekday 6)
    run = sched.next_run([6], "18:00", now)
    assert run == datetime(2026, 8, 2, 18, 0)


def test_next_run_rolls_to_next_day():
    now = datetime(2026, 8, 2, 20, 0)  # Sunday evening
    run = sched.next_run([0], "03:00", now)  # next Monday
    assert run == datetime(2026, 8, 3, 3, 0)


def test_next_run_rolls_week():
    now = datetime(2026, 8, 2, 20, 0)
    run = sched.next_run([6], "03:00", now)  # next Sunday
    assert run == datetime(2026, 8, 9, 3, 0)


def test_next_run_invalid():
    assert sched.next_run([], "03:00") is None
    assert sched.next_run([0], "bad") is None


def test_next_run_not_in_past():
    now = datetime(2026, 8, 2, 12, 0)
    run = sched.next_run([6], "11:00", now)
    assert run is not None and run > now


def test_is_due_window():
    now = datetime(2026, 8, 2, 12, 0)
    last_run = datetime(2026, 8, 2, 11, 0)
    assert sched.is_due([6], "11:30", last_run, now) is True
    # Not due if we already ran after the slot.
    later = datetime(2026, 8, 2, 11, 31)
    assert sched.is_due([6], "11:30", later, now) is False
    # Not due when today's slot is in the future.
    assert sched.is_due([6], "15:00", last_run, now) is False
    # No last_run history -> never fires immediately.
    assert sched.is_due([6], "11:30", None, now) is False
