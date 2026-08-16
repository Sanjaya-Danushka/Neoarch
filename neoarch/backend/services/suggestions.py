"""'Did you mean' package-name suggestions for the Discover search.

Builds a local, cached index of package names from pacman and Flatpak and
fuzzy-matches a query against it (difflib) so that a typo such as 'camtrix'
can suggest 'cmatrix'. The index is rebuilt at most once per day; the
expensive rebuild is expected to run in a background thread.
"""

import difflib
import json
import os
import shutil
import subprocess
import threading
import time

__all__ = ["suggest_names", "index_ready", "refresh_names_index", "set_cache_path"]

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "pkg_names.json")
CACHE_TTL = 24 * 60 * 60

_index = []
_index_lower = []
_index_ts = 0.0
_index_lock = threading.Lock()


def set_cache_path(path: str) -> None:
    """Override the cache location (used by tests)."""
    global CACHE_FILE
    CACHE_FILE = str(path)


def _run(cmd, timeout=20) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout or ""
    except Exception:
        return ""


def _collect_names():
    """Collect package names from the available local sources."""
    names = set()
    if shutil.which("pacman"):
        for line in _run(["pacman", "-Ssq"]).splitlines():
            line = line.strip()
            if line and not line.startswith("error:"):
                names.add(line)
    if shutil.which("flatpak"):
        for line in _run(["flatpak", "remote-ls", "--app", "--columns=application"]).splitlines():
            line = line.strip()
            if line and "/" not in line and " " not in line:
                names.add(line)
    return sorted(names)


def _load_cache():
    global _index, _index_lower, _index_ts
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict) or time.time() - data.get("ts", 0) >= CACHE_TTL:
            return False
        names = data.get("names") or []
        if not names:
            return False
        _index = list(names)
        _index_lower = [n.lower() for n in _index]
        _index_ts = data["ts"]
        return True
    except Exception:
        return False


def index_ready() -> bool:
    """True when a usable name index is available without a rebuild."""
    if _index and time.time() - _index_ts < CACHE_TTL:
        return True
    return _load_cache()


def refresh_names_index():
    """Rebuild the name index from pacman + Flatpak and persist it."""
    global _index, _index_lower, _index_ts
    with _index_lock:
        names = _collect_names()
        _index = names
        _index_lower = [n.lower() for n in _index]
        _index_ts = time.time()
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({"ts": _index_ts, "names": names}, f)
        except Exception:
            pass
        return names


def suggest_names(query, limit=3, cutoff=0.62):
    """Return close package-name matches for a (possibly mistyped) query."""
    query = (query or "").strip().lower()
    if len(query) < 3:
        return []
    if not _index or time.time() - _index_ts >= CACHE_TTL:
        if not _load_cache():
            return []
    matches = difflib.get_close_matches(query, _index_lower, n=limit, cutoff=cutoff)
    by_lower = {low: name for low, name in zip(_index_lower, _index)}
    return [by_lower[m] for m in matches if by_lower.get(m, "").lower() != query]
