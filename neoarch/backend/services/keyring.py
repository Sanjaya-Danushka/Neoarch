"""Pacman keyring manager.

Wraps `pacman-key` operations: initialize/populate/refresh the keyring,
list trusted keys, and receive + locally-sign a key so packages signed
by it can be installed.

`pacman-key` must run as root, so every mutation goes through the app's
standard elevation helpers. Inspection commands run unprivileged.
"""

import re
import subprocess
from typing import Dict, List, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = [
    "list_keyring", "key_details",
    "init_keyring", "populate_keyring", "refresh_keys",
    "receive_key", "locally_sign", "locally_sign_key",
]

# Key IDs the keyring is populated with by default.
ARCH_KEYRING = ("archlinux", "archlinux32", "archlinuxarm")

# Fingerprint: 40 hex chars (optionally with spaces).
_FINGERPRINT_RE = re.compile(r"^[0-9A-Fa-f]{40}$")
# Accept 40-hex with separators collapsed.
_KEYID_RE = re.compile(r"^[0-9A-Fa-f]{8,40}$")


def _run(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _run_sudo(cmd: List[str], timeout: int = 900) -> subprocess.CompletedProcess:
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except Exception:
        return subprocess.CompletedProcess(auth + cmd, 1, "", "")


def _normalize_fingerprint(value: str) -> str:
    """Strip spaces and uppercase a key id/fingerprint."""
    return re.sub(r"[^0-9A-Fa-f]", "", value).upper()


def _valid_key(value: str) -> bool:
    return bool(_KEYID_RE.match(_normalize_fingerprint(value)))


def list_keyring() -> List[Dict]:
    """List trusted keys: {fingerprint, uid, validity, created}."""
    result = _run(["pacman-key", "--list-keys"])
    if result.returncode != 0:
        return []
    keys: List[Dict] = []
    current: Dict = {}
    pending_created = ""
    for line in result.stdout.splitlines():
        line = line.rstrip()
        m = re.match(r"^(?:pub|sec)\s+\S+\s+(\d{4}-\d{2}-\d{2})", line)
        if m:
            pending_created = m.group(1)
            continue
        m = re.match(r"^([0-9A-Fa-f]{40})\s+(.*)$", line)
        if m:
            if current:
                keys.append(current)
            created = ""
            cm = re.search(r"\[created:\s*(\d{4}-\d{2}-\d{2})", m.group(2))
            if cm:
                created = cm.group(1)
            current = {
                "fingerprint": m.group(1),
                "validity": m.group(2).strip(),
                "uid": "",
                "created": created or pending_created,
            }
            pending_created = ""
        elif line.strip().startswith("uid") and current:
            uid = line.strip()[3:].strip()
            current["uid"] = uid
    if current:
        keys.append(current)
    return keys


def key_details(fingerprint: str) -> Dict:
    """Return detailed info for a single key."""
    if not _valid_key(fingerprint):
        return {}
    result = _run(["pacman-key", "--finger", fingerprint])
    lines = result.stdout.splitlines()
    return {
        "fingerprint": _normalize_fingerprint(fingerprint),
        "list": "\n".join(l for l in lines if l.strip()),
    }


def init_keyring() -> bool:
    """Create/wipe and initialize the keyring (needs root)."""
    return _run_sudo(["pacman-key", "--init"]).returncode == 0


def populate_keyring(keyrings: Optional[List[str]] = None) -> bool:
    """Populate the keyring with Arch master/signing keys (needs root)."""
    names = keyrings or list(ARCH_KEYRING)
    return _run_sudo(["pacman-key", "--populate"] + names).returncode == 0


def refresh_keys() -> bool:
    """Refresh the keyring from the keyservers (needs root)."""
    return _run_sudo(["pacman-key", "--refresh-keys"]).returncode == 0


def receive_key(key_id: str) -> bool:
    """Receive a key from the keyserver (needs root)."""
    if not _valid_key(key_id):
        return False
    return _run_sudo(["pacman-key", "--recv-keys", _normalize_fingerprint(key_id)]
                     ).returncode == 0


def locally_sign(key_id: str) -> bool:
    """Locally sign a key so its packages can be installed (needs root)."""
    if not _valid_key(key_id):
        return False
    return _run_sudo(["pacman-key", "--lsign-key", _normalize_fingerprint(key_id)]
                     ).returncode == 0


# Backward-compatible alias used by some callers.
locally_sign_key = locally_sign
