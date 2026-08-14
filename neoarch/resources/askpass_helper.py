#!/usr/bin/env python3
"""
Minimal script to retrieve the cached sudo password for the session.

Called by SUDO_ASKPASS when the session is active. Reads the credential from
the system keyring first, then falls back to the 0600 session credential file,
so passwordless sudo works even without a keyring daemon.
"""
import sys
from pathlib import Path


def _get_credential():
    """Return the cached sudo password, or None if unavailable."""
    # Guard: only return credentials while this session lock is present
    lock_file = Path.home() / ".cache" / "neoarch" / "session.lock"
    if not lock_file.exists():
        return None

    pw = None
    try:
        import keyring
        pw = keyring.get_password("NeoArch", "sudo_credential")
    except Exception:
        pw = None
    if pw:
        return pw

    try:
        cred_file = Path.home() / ".cache" / "neoarch" / "sudo_credential"
        if cred_file.exists():
            return cred_file.read_text('utf-8').strip()
    except Exception:
        pass
    return None


if __name__ == "__main__":
    credential = _get_credential()
    if credential:
        print(credential, end='')
        sys.exit(0)
    sys.exit(1)
