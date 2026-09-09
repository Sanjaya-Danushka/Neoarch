#!/usr/bin/env python3
"""NeoArch scheduled update runner.

Standalone entry point for the ``neoarch-update.timer`` / ``neoarch-update.service``
systemd units. Evaluates the weekly schedule configured in the GUI
(``schedule_enabled`` / ``schedule_days`` / ``schedule_time`` in
``~/.config/neoarch/settings.json``) and runs ``python -m neoarch.cli upgrade``
when one is due.

Qt-free: runs headless under systemd and reuses the pure scheduler service.
A last-run marker under ``~/.cache/neoarch/`` guarantees the upgrade fires at
most once per schedule slot, even after the system was asleep or off.

Usage:
    python3 /opt/neoarch/Neoarch/scheduled_update.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = Path.home() / ".config" / "neoarch" / "settings.json"
MARKER_PATH = Path.home() / ".cache" / "neoarch" / "scheduled_update.last"

DEFAULT_SCHEDULE = {
    "schedule_enabled": False,
    "schedule_days": [0, 1, 2, 3, 4, 5, 6],  # Monday=0 .. Sunday=6
    "schedule_time": "03:00",
}


def _log(msg: str) -> None:
    print(f"[neoarch-update] {msg}", flush=True)


def _load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SCHEDULE)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log(f"cannot read settings ({exc}); aborting")
        return dict(DEFAULT_SCHEDULE)
    merged = dict(DEFAULT_SCHEDULE)
    for key in DEFAULT_SCHEDULE:
        if key in data:
            merged[key] = data[key]
    return merged


def _due(data: dict, now: datetime) -> bool:
    """True when the weekly slot has arrived and was not run since."""
    if not data.get("schedule_enabled"):
        return False
    days = data.get("schedule_days") or []
    if now.weekday() not in days:
        return False
    time_str = str(data.get("schedule_time") or "03:00")
    try:
        hour, minute = map(int, time_str.split(":", 1))
    except (TypeError, ValueError):
        return False
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < slot:
        return False
    last = None
    if MARKER_PATH.exists():
        try:
            last = datetime.fromtimestamp(float(MARKER_PATH.read_text().strip()))
        except (OSError, ValueError):
            pass
    return last is None or last < slot


def _run_upgrade() -> int:
    if not sys.path[0]:
        os.chdir(BASE_DIR)
    cmd = [sys.executable, "-m", "neoarch.cli", "upgrade"]
    _log("running: " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(BASE_DIR)).returncode


def main() -> int:
    now = datetime.now()
    data = _load_settings()

    if not data.get("schedule_enabled"):
        _log("scheduled updates disabled; nothing to do")
        return 0
    if not _due(data, now):
        _log(f"not due today at {data.get('schedule_time')}; nothing to do")
        return 0

    try:
        MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    code = _run_upgrade()
    if code == 0:
        try:
            MARKER_PATH.write_text(str(now.timestamp()))
        except OSError:
            pass
        _log("scheduled update completed")
    else:
        _log(f"scheduled update failed (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())