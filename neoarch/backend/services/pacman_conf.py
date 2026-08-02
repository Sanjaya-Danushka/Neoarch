"""pacman.conf helpers.

Reads and (with elevation) writes /etc/pacman.conf settings that the
app configures on behalf of the user — currently the parallel download
count (`ParallelDownloads`). The file is edited line-wise, preserving
comments, ordering, and unrelated directives.
"""

import os
import re
from typing import List, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = [
    "PACMAN_CONF",
    "get_parallel_downloads", "set_parallel_downloads",
    "get_option", "set_option",
]

PACMAN_CONF = "/etc/pacman.conf"

# Valid option name: alnum plus '_'. Guard against injection into the file.
_OPTION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
# An option line we can safely rewrite, e.g. "ParallelDownloads = 5".
_OPTION_LINE_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_]*)\s*=\s*(?P<value>[^\s#]*)")


def _run(cmd: List[str], timeout: int = 60) -> "subprocess.CompletedProcess":
    import subprocess
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _run_sudo(cmd: List[str], timeout: int = 120) -> "subprocess.CompletedProcess":
    import subprocess
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except Exception:
        return subprocess.CompletedProcess(auth + cmd, 1, "", "")


def _read_conf() -> List[str]:
    try:
        with open(PACMAN_CONF, "r") as f:
            return f.readlines()
    except Exception:
        return []


def get_option(name: str) -> Optional[str]:
    """Return the value of an option (first occurrence), or None."""
    if not _OPTION_RE.match(name):
        return None
    for line in _read_conf():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("[") or "=" not in stripped:
            continue
        m = _OPTION_LINE_RE.match(stripped)
        if m and m.group("key").lower() == name.lower():
            return m.group("value")
    return None


def get_parallel_downloads() -> Optional[int]:
    """Current ParallelDownloads count, or None when unset."""
    value = get_option("ParallelDownloads")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def set_option(name: str, value: str) -> bool:
    """Write an option into /etc/pacman.conf (needs root).

    Rewrites an existing line in place; appends one under the top-level
    section (before any '[' section header) when absent. Returns True on
    success.
    """
    if not _OPTION_RE.match(name) or value is None or "\n" in str(value):
        return False
    value = str(value)
    lines = _read_conf()
    if not lines:
        return False

    written = False
    out: List[str] = []
    for line in lines:
        stripped = line.strip()
        if (not written and not stripped.startswith("#")
                and "=" in stripped and "[" not in stripped):
            m = _OPTION_LINE_RE.match(stripped)
            if m and m.group("key").lower() == name.lower():
                out.append(f"{name} = {value}\n")
                written = True
                continue
        out.append(line)

    if not written:
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("["):
                insert_at = i
                break
        else:
            insert_at = len(lines)
        out.insert(insert_at, f"{name} = {value}\n")

    from neoarch.backend.auth import get_auth_command
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    import subprocess
    try:
        result = subprocess.run(
            auth + ["tee", PACMAN_CONF], input="".join(out),
            capture_output=True, text=True, timeout=120, env=env)
        return result.returncode == 0
    except Exception:
        return False


def set_parallel_downloads(count: int) -> bool:
    """Set the parallel download count (needs root)."""
    if not isinstance(count, int) or count < 1 or count > 32:
        return False
    return set_option("ParallelDownloads", str(count))
