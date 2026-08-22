"""Authentication utilities for package management operations.

Detects desktop environment and selects the appropriate privilege elevation
method (pkexec, sudo -A) for GUI password prompts.
"""

import os
import shutil
from typing import Tuple

from neoarch.backend import session_auth

__all__ = ["get_auth_command", "get_sudo_askpass", "prepare_askpass_env", "get_askpass_env"]


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


def get_sudo_askpass(env=None) -> str:
    """Get the path to a GUI askpass program for sudo password prompts.

    Searches for available GUI authentication tools in order of preference:
    kdialog, zenity, yad.

    Args:
        env: Environment dictionary to search in.

    Returns:
        str: Path to the askpass program, or empty string if none found.
    """
    if env is None:
        env = os.environ
    path_env = env.get('PATH', os.defpath)
    for cmd in ['kdialog', 'zenity', 'yad']:
        fp = shutil.which(cmd, path=path_env)
        if fp:
            return fp
    return ""


def prepare_askpass_env(env=None) -> Tuple[dict, str]:
    """Create a temporary SUDO_ASKPASS script and prepare environment.

    Generates a shell script that uses a GUI dialog (kdialog/zenity/yad)
    to ask for the sudo password, then returns the modified environment
    and the path to the cleanup file.

    Args:
        env: Base environment to extend. If None, uses os.environ copy.

    Returns:
        tuple: (env_dict, temp_script_path)
    """
    import shutil
    import tempfile

    if env is None:
        env = os.environ.copy()
    else:
        env = env.copy()

    askpass_path = get_sudo_askpass(env)

    # Prefer NeoArch's own dark dialog; fall back to system tools only if
    # it fails (e.g. no display) or the user cancels.
    import sys
    import tempfile

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
    )
    if askpass_path:
        if 'kdialog' in askpass_path:
            script_content += f'exec {askpass_path} --password "NeoArch requires administrative privileges" --title "Authentication Required"\n'
        elif 'zenity' in askpass_path:
            script_content += f'exec {askpass_path} --password --title="Authentication Required" --text="NeoArch requires administrative privileges:"\n'
        elif 'yad' in askpass_path:
            script_content += f'exec {askpass_path} --entry --hide-text --title="Authentication Required" --text="NeoArch requires administrative privileges:"\n'
        else:
            script_content += f'exec {askpass_path} "NeoArch requires administrative privileges"\n'
    else:
        script_content += "exit 1\n"

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
