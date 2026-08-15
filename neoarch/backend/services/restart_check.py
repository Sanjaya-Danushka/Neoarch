"""Restart-required detection.

Flags upgrades that cannot take effect until the system is rebooted:
new kernels installed but not yet booted, plus critical shared
libraries (glibc, systemd, openssl, nss) replaced after boot time.
Used by the update flow to prompt the user.
"""

import os
import re
import subprocess
import time
from typing import Dict, List, Optional

from neoarch.backend.services.downgrade import vercmp

__all__ = [
    "boot_time", "running_kernel", "installed_kernels", "new_kernels",
    "check_restart_required", "restart_required",
]

KERNEL_MODULES_DIR = "/usr/lib/modules"

# Shared libraries whose replacement usually warrants a reboot.
RESTART_PATHS: Dict[str, str] = {
    "glibc": "/usr/lib/libc.so.6",
    "systemd": "/usr/lib/libsystemd.so.0",
    "openssl": "/usr/lib/libcrypto.so.3",
    "nss": "/usr/lib/libnss3.so",
}


def _run(cmd: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def boot_time() -> Optional[float]:
    """Wall-clock time of the last boot, or None if unknown."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime = float(f.read().split()[0])
        return time.time() - uptime
    except Exception:
        return None


def running_kernel() -> str:
    """Version of the currently booted kernel (uname -r)."""
    return _run(["uname", "-r"]).stdout.strip()


def installed_kernels() -> List[str]:
    """Kernel versions present on disk under /usr/lib/modules.

    Newest first, following pacman version ordering.
    """
    try:
        names = os.listdir(KERNEL_MODULES_DIR)
    except Exception:
        return []
    candidates = [n for n in names if n and not n.startswith(".")]
    from functools import cmp_to_key
    return sorted(candidates, key=cmp_to_key(
        lambda a, b: vercmp(b, a)))


def new_kernels() -> List[str]:
    """Installed kernel versions newer than the running one."""
    running = running_kernel()
    if not running:
        return []
    return [v for v in installed_kernels()
            if v != running and vercmp(v, running) > 0]


def _file_newer_than_boot(path: str, boot: float) -> bool:
    try:
        return os.path.getmtime(path) > boot
    except Exception:
        return False


def check_restart_required() -> List[Dict]:
    """Return a list of restart recommendations.

    Each entry is a dict: {category, message, ...} sorted with the most
    serious first (kernel first, then library upgrades).
    """
    items: List[Dict] = []
    kernels = new_kernels()
    if kernels:
        items.append({
            "category": "kernel",
            "message": "New kernel(s) installed but not yet booted: "
                       + ", ".join(kernels),
            "kernels": kernels,
        })

    boot = boot_time()
    if boot is not None:
        for category, path in RESTART_PATHS.items():
            if _file_newer_than_boot(path, boot):
                items.append({
                    "category": category,
                    "message": f"{category} was updated after boot; "
                               "a restart is recommended for the change to take effect",
                })
    return items


def restart_required() -> bool:
    """True when any restart recommendation is active."""
    return bool(check_restart_required())
