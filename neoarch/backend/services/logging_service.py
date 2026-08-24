"""Central logging service backing the Settings ▸ Logging tab.

Every control on that tab maps to real behaviour here:
  - log_level        minimum severity written anywhere
  - log_to_console   mirror log lines to stdout
  - log_file_path    rotating log file location ('' disables file output)
  - log_max_size_mb  rollover threshold for the log file

app.log(message, level="info") feeds this service; untagged legacy callers
default to INFO.
"""

import os

__all__ = ["log_message", "reconfigure", "current_config"]

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
_state = {
    "level": "INFO",
    "console": False,
    "path": "",
    "max_mb": 5,
}


def current_config():
    return dict(_state)


def reconfigure(level=None, console=None, path=None, max_mb=None):
    """Apply new logging configuration (None keeps current value)."""
    if level is not None and str(level).upper() in LEVELS:
        _state["level"] = str(level).upper()
    if console is not None:
        _state["console"] = bool(console)
    if path is not None:
        _state["path"] = str(path or "")
    if max_mb is not None:
        try:
            _state["max_mb"] = max(1, int(max_mb))
        except (TypeError, ValueError):
            pass


def _classify(message: str) -> str:
    """Best-effort severity for plain-text legacy log lines."""
    m = message.lower()
    if "traceback" in m or m.startswith("error") or " failed" in m or ": error" in m:
        return "ERROR"
    if "warning" in m or "warn:" in m:
        return "WARNING"
    if "debug" in m:
        return "DEBUG"
    return "INFO"


def _rotate_if_needed(path: str):
    try:
        if os.path.exists(path) and \
                os.path.getsize(path) >= _state["max_mb"] * 1024 * 1024:
            backup = path + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.replace(path, backup)
    except Exception:
        pass


def log_message(message: str, level: str = "") -> None:
    """Route one line to file/stdout according to configuration."""
    lvl = (level or "").upper()
    if lvl not in LEVELS:
        lvl = _classify(message)
    if LEVELS[lvl] < LEVELS[_state["level"]]:
        return

    line = message
    try:
        if _state["path"]:
            os.makedirs(os.path.dirname(_state["path"]) or ".", exist_ok=True)
            _rotate_if_needed(_state["path"])
            from datetime import datetime
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(_state["path"], "a", encoding="utf-8") as f:
                f.write(f"[{stamp}] [{lvl}] {message}\n")
    except Exception:
        pass
    try:
        if _state["console"]:
            print(f"[neoarch] {line}", flush=True)
    except Exception:
        pass
