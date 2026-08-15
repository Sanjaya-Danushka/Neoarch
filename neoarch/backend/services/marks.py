"""Package mark management.

Reads and writes the real pacman mark lists — `IgnorePkg`, `HoldPkg` in
`/etc/pacman.conf` — and manages per-package install reasons via
`pacman -D --asexplicit/--asdeps`.

These are the durable, pacman-native mechanisms (as opposed to NeoArch's
own ignored-updates tracking file). Editing requires root and uses the
app's standard elevation helpers.
"""

import os
import re
import subprocess
from typing import List, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = [
    "PACMAN_CONF",
    "get_ignorepkg", "add_ignorepkg", "remove_ignorepkg",
    "get_holdpkg", "add_holdpkg", "remove_holdpkg",
    "get_install_reason", "set_install_reason",
]

PACMAN_CONF = "/etc/pacman.conf"

# Names that are safe to embed in a shell command.
_SAFE_NAME_RE = re.compile(r"^[\w@.+:\-]+$")


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _run_sudo(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except Exception:
        return subprocess.CompletedProcess(auth + cmd, 1, "", "")


def _read_conf() -> str:
    try:
        with open(PACMAN_CONF, "r") as f:
            return f.read()
    except Exception:
        return ""


def _get_list(keyword: str) -> List[str]:
    entries: List[str] = []
    for line in _read_conf().splitlines():
        line = line.strip()
        if line.startswith(keyword):
            for name in re.split(r"[,\s]+", line.split("=", 1)[1].strip()):
                if name and name not in entries:
                    entries.append(name)
    return entries


def get_ignorepkg() -> List[str]:
    """Current IgnorePkg package names."""
    return _get_list("IgnorePkg")


def get_holdpkg() -> List[str]:
    """Current HoldPkg package names."""
    return _get_list("HoldPkg")


def _validate(pkg: str) -> bool:
    return bool(_SAFE_NAME_RE.match(pkg))


def _add_list(keyword: str, pkg: str) -> bool:
    if not _validate(pkg):
        return False
    if pkg in _get_list(keyword):
        return True
    result = _run_sudo(
        ["bash", "-c", f'echo "{keyword} = {pkg}" >> {PACMAN_CONF}'])
    return result.returncode == 0


def _remove_list(keyword: str, pkg: str) -> bool:
    if not _validate(pkg):
        return False
    if pkg not in _get_list(keyword):
        return True
    esc = re.escape(pkg)
    result = _run_sudo([
        "bash", "-c",
        f"sed -i -e \"s/[ \\t,]*{esc}[ \\t,]*/ /g\""
        f" -e \"/{keyword}[ \\t]*=[ \\t]*$/d\" {PACMAN_CONF}",
    ])
    return result.returncode == 0


def add_ignorepkg(pkg: str) -> bool:
    """Add `pkg` to IgnorePkg in /etc/pacman.conf (needs root)."""
    return _add_list("IgnorePkg", pkg)


def remove_ignorepkg(pkg: str) -> bool:
    """Remove `pkg` from IgnorePkg (needs root)."""
    return _remove_list("IgnorePkg", pkg)


def add_holdpkg(pkg: str) -> bool:
    """Add `pkg` to HoldPkg (needs root)."""
    return _add_list("HoldPkg", pkg)


def remove_holdpkg(pkg: str) -> bool:
    """Remove `pkg` from HoldPkg (needs root)."""
    return _remove_list("HoldPkg", pkg)


def get_install_reason(pkg: str) -> Optional[str]:
    """Return the install reason for `pkg`: 'explicit' or 'deps' (or None)."""
    result = _run(["pacman", "-Qi", pkg])
    if result.returncode != 0:
        return None
    m = re.search(r"Install Reason\s*:\s*(.+)", result.stdout)
    if not m:
        return None
    value = m.group(1).strip().lower()
    if "explicit" in value:
        return "explicit"
    if "dependency" in value:
        return "deps"
    return value or None


def set_install_reason(pkg: str, reason: str) -> bool:
    """Set `pkg` install reason to 'explicit' or 'deps' (needs root)."""
    if reason not in ("explicit", "deps"):
        return False
    if not _validate(pkg):
        return False
    flag = "--asexplicit" if reason == "explicit" else "--asdeps"
    result = _run_sudo(["pacman", "-D", flag, pkg])
    return result.returncode == 0
