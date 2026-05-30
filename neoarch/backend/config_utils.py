"""Configuration file utilities for persistent app settings.

Manages JSON-based config files in ~/.config/neoarch/ for ignored updates
and local update entries.
"""

import os
import json
from typing import Set, List, Dict, Any

__all__ = [
    "get_ignore_file_path", "load_ignored_updates", "save_ignored_updates",
    "get_local_updates_file_path", "load_local_update_entries",
]


def _ensure_config_dir() -> str:
    """Create and return the neoarch config directory path."""
    cfg = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        pass
    return cfg


def get_ignore_file_path() -> str:
    """Get path to the ignored-updates JSON file."""
    return os.path.join(_ensure_config_dir(), 'ignored_updates.json')


def load_ignored_updates() -> Set[str]:
    """Load the set of package names that are ignored for updates."""
    p = get_ignore_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def save_ignored_updates(items: Set[str]) -> None:
    """Save the set of ignored update package names to disk."""
    p = get_ignore_file_path()
    try:
        with open(p, 'w') as f:
            json.dump(sorted(list(items)), f)
    except Exception:
        pass


def get_local_updates_file_path() -> str:
    """Get path to the local updates JSON file."""
    return os.path.join(_ensure_config_dir(), 'local_updates.json')


def load_local_update_entries() -> List[Dict[str, Any]]:
    """Load locally-defined update entries from disk."""
    p = get_local_updates_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []
