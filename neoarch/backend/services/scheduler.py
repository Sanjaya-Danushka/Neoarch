"""Scheduled task model.

A pure, Qt-free scheduler used by the tray/auto-update flows: computes
the next run time for a weekly days-of-week + time-of-day schedule and
tells callers whether a task is due. All functions take an explicit
`now` so they are deterministic and trivially testable.
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional

__all__ = ["next_run", "is_due", "parse_time", "validate_schedule", "DEFAULT_SCHEDULE"]

DEFAULT_SCHEDULE = {
    "schedule_enabled": False,
    "schedule_days": [0, 1, 2, 3, 4, 5, 6],  # Monday=0 .. Sunday=6
    "schedule_time": "03:00",
}

_TIME_RE = re.compile(r"^([0-1]?\d|2[0-3]):([0-5]\d)$")


def parse_time(value: str) -> Optional[tuple]:
    """Parse an 'HH:MM' time string into (hour, minute), or None."""
    if not isinstance(value, str):
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def validate_schedule(days: List[int], time_str: str) -> bool:
    """True when the schedule is well-formed."""
    if not isinstance(days, (list, tuple)) or not days:
        return False
    if not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
        return False
    return parse_time(time_str) is not None


def next_run(days: List[int], time_str: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Next scheduled datetime for a weekly schedule, or None if invalid.

    `now` defaults to the current local time. The result is strictly in
    the future: if today's slot is at/after the given time it returns
    today; otherwise the next matching weekday.
    """
    now = now or datetime.now()
    if not validate_schedule(days, time_str):
        return None
    hour, minute = parse_time(time_str)
    days = sorted(set(int(d) for d in days))
    for offset in range(8):
        candidate = now + timedelta(days=offset)
        candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate.weekday() in days and candidate > now:
            return candidate
    return None


def is_due(days: List[int], time_str: str, last_run: Optional[datetime],
           now: Optional[datetime] = None) -> bool:
    """True when a scheduled task should run now.

    True when today is a scheduled day, the current time has passed the
    schedule slot, and no run has happened since that slot. With no
    `last_run`, returns True only inside the slot window (so a freshly
    scheduled app does not fire immediately).
    """
    now = now or datetime.now()
    if not validate_schedule(days, time_str):
        return False
    if now.weekday() not in days:
        return False
    hour, minute = parse_time(time_str)
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < slot:
        return False
    if last_run is None:
        return False
    return last_run < slot
