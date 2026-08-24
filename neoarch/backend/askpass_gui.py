"""Standalone SUDO_ASKPASS helper rendering NeoArch's authentication dialog.

Invoked as ``python -m neoarch.backend.askpass_gui`` from the temporary
askpass script built by :func:`neoarch.backend.auth.prepare_askpass_env`.

Behaviour:
  1. If a cached session credential exists (keyring / 0600 cred file guarded
     by the session lock), it is printed to stdout silently — sudo proceeds
     without any prompt.
  2. Otherwise the SAME themed authentication dialog used by the in-app
     session setup is shown. A successfully validated password is cached for
     the session (so every later sudo — on any page — stays silent) and then
     printed to stdout for the current sudo invocation.

Exits non-zero when cancelled so the caller can fail gracefully.
"""

import os
import sys


def _cached_credential() -> str | None:
    """Return the cached sudo password, or None if unavailable.

    Mirrors neoarch/resources/askpass_helper.py: credentials are only valid
    while the session lock exists.
    """
    from pathlib import Path

    lock_file = Path.home() / ".cache" / "neoarch" / "session.lock"
    if not lock_file.exists():
        return None

    try:
        import keyring
        pw = keyring.get_password("NeoArch", "sudo_credential")
        if pw:
            return pw
    except Exception:
        pass

    try:
        cred_file = Path.home() / ".cache" / "neoarch" / "sudo_credential"
        if cred_file.exists():
            return cred_file.read_text('utf-8').strip()
    except Exception:
        pass
    return None


_AUTH_MARKER = None


def _marker_path():
    from pathlib import Path
    return Path.home() / ".cache" / "neoarch" / "auth_in_progress"


def main() -> int:
    # Fast path: cached credential -> completely silent.
    credential = _cached_credential()
    if credential:
        sys.stdout.write(credential + "\n")
        return 0

    import time
    from pathlib import Path

    # Single-flight: if another askpass process is already showing the
    # dialog (parallel sudo commands), wait for it to establish the cache
    # instead of stacking a second prompt. Stale markers from crashed
    # processes are detected via PID liveness and ignored.
    marker = _marker_path()
    waited = 0.0
    saw_other_auth = False
    while waited < 300.0:
        credential = _cached_credential()
        if credential:
            sys.stdout.write(credential + "\n")
            return 0
        live_pid = None
        try:
            raw = marker.read_text().strip()
            if raw.isdigit():
                os.kill(int(raw), 0)  # raises if the process is gone
                live_pid = int(raw)
        except (FileNotFoundError, ProcessLookupError, PermissionError,
                ValueError):
            live_pid = None
        except Exception:
            live_pid = None
        if not live_pid:
            try:
                marker.unlink(missing_ok=True)
            except Exception:
                pass
            break
        saw_other_auth = True
        time.sleep(0.3)
        waited += 0.3
    else:
        return 1  # waited 300s with no resolution

    if saw_other_auth:
        # The other dialog just closed without caching a password -> the
        # user cancelled authentication there. Do not nag again.
        time.sleep(0.5)
        credential = _cached_credential()
        if credential:
            sys.stdout.write(credential + "\n")
            return 0
        return 1

    from PyQt6.QtWidgets import QApplication
    from neoarch.backend import session_auth

    app = QApplication.instance() or QApplication(sys.argv[:1])

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(os.getpid()))
    except Exception:
        pass

    session_auth._atexit_registered = True
    ok = False
    try:
        ok = session_auth.setup_session_auth(None)
    except Exception:
        ok = False
    finally:
        try:
            marker.unlink(missing_ok=True)
        except Exception:
            pass

    if not ok:
        # Cancelled/failed — but a parallel askpass may have just cached the
        # credential while we were open; prefer silence over failure.
        credential = _cached_credential()
        if credential:
            sys.stdout.write(credential + "\n")
            return 0
        return 1

    credential = _cached_credential()
    if not credential:
        return 1
    sys.stdout.write(credential + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
