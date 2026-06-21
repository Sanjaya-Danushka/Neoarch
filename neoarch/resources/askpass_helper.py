#!/usr/bin/env python3
"""
Minimal script to retrieve cached sudo password from keyring.
Called by SUDO_ASKPASS when session is active.
No secrets stored on disk — only keyring access.
"""
import sys
import os
from pathlib import Path

try:
    import keyring
    CACHE_DIR = Path.home() / ".cache" / "neoarch"
    SERVICE_NAME = "NeoArch"
    USERNAME = "sudo_credential"

    # Check session lock exists (prevents unauthorized retrieval)
    LOCK_FILE = os.path.expanduser(CACHE_DIR / "session.lock")
    if not os.path.exists(LOCK_FILE):
        sys.exit(1)

    pw = keyring.get_password(SERVICE_NAME, USERNAME)
    if pw:
        print(pw, end='')
        sys.exit(0)

    sys.exit(1)
except Exception:
    sys.exit(1)