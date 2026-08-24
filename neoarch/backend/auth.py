"""Authentication utilities for package management operations.

All privilege elevation goes through 'sudo -A' with NeoArch's own themed
authentication dialog and session credential cache — one prompt per
session, silent afterwards.
"""

import os
import shutil
from typing import Tuple

from neoarch.backend import session_auth

__all__ = ["get_auth_command", "prepare_askpass_env", "get_askpass_env"]


def get_auth_command(env=None):
    """Return the privilege elevation command for internal operations.

    NeoArch always elevates via 'sudo -A' so authentication is handled by
    its own themed askpass dialog instead of the system polkit agent.
    When the session credential cache is active, the stored password is
    reused silently without any prompt.

    Args:
        env: Unused; kept for backward compatibility with callers.

    Returns:
        list: The authentication command prefix (["sudo", "-A"]).
    """
    return ["sudo", "-A"]


def prepare_askpass_env(env=None) -> Tuple[dict, str]:
    """Create a temporary SUDO_ASKPASS script and prepare environment.

    The script delegates entirely to NeoArch's own authentication flow
    (``python -m neoarch.backend.askpass_gui``): it serves any cached
    session credential silently, and otherwise shows the themed dialog,
    caches the password, and hands it to sudo. System tools (kdialog,
    zenity, yad) are no longer used — they were the old, inconsistent
    prompt design that re-asked on every command.

    Args:
        env: Base environment to extend. If None, uses os.environ copy.

    Returns:
        tuple: (env_dict, temp_script_path)
    """
    import sys
    import tempfile

    if env is None:
        env = os.environ.copy()
    else:
        env = env.copy()

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    python = sys.executable or "python3"

    script_content = "#!/bin/sh\n"
    script_content += (
        f"out=$('{python}' -m neoarch.backend.askpass_gui 2>/dev/null)\n"
        "if [ $? -eq 0 ] && [ -n \"$out\" ]; then\n"
        "  printf '%s\\n' \"$out\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n"
    )

    env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')

    fd, script_path = tempfile.mkstemp(prefix='neoarch_askpass_', suffix='.sh')
    with os.fdopen(fd, 'w') as f:
        f.write(script_content)
    os.chmod(script_path, 0o700)

    env['SUDO_ASKPASS'] = script_path
    return env, script_path


def get_askpass_env(base_env=None) -> dict:
    """Return an environment dict with SUDO_ASKPASS set.

    If the session auth manager has an active credential cache, its
    askpass script is preferred. Otherwise falls back to creating a
    temporary askpass via prepare_askpass_env().

    Args:
        base_env: Optional base environment to extend. If None, uses
                  a copy of os.environ.

    Returns:
        dict: Environment with SUDO_ASKPASS set.
    """
    if session_auth.is_session_active():
        return session_auth.get_askpass_env()
    if base_env is not None:
        env = base_env.copy()
    else:
        env = os.environ.copy()
    if "SUDO_ASKPASS" not in env:
        env, _ = prepare_askpass_env(env)
    return env
