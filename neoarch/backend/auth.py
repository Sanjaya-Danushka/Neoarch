"""Authentication utilities for package management operations.

Detects desktop environment and selects the appropriate privilege elevation
method (pkexec, sudo -A) for GUI password prompts.
"""

import os
import subprocess
from typing import Tuple

__all__ = ["get_auth_command", "get_sudo_askpass", "prepare_askpass_env"]


def get_auth_command(env=None):
    """Determine the appropriate authentication command based on desktop environment.

    Detects Hyprland, Wayland, GNOME, KDE, XFCE and selects pkexec or sudo -A
    accordingly. Ensures GUI password dialogs work properly.

    Args:
        env: Environment dictionary to check for desktop variables.

    Returns:
        list: Authentication command as a list (e.g., ["pkexec"] or ["sudo", "-A"])
    """
    if env is None:
        env = os.environ

    desktop = env.get('XDG_CURRENT_DESKTOP', '').lower()
    session_type = env.get('XDG_SESSION_TYPE', '').lower()
    wayland_display = env.get('WAYLAND_DISPLAY', '')
    hyprland_instance = env.get('HYPRLAND_INSTANCE_SIGNATURE', '')

    try:
        polkit_agent_running = subprocess.run(['pgrep', '-f', 'polkit.*agent'], capture_output=True).returncode == 0
    except Exception:
        polkit_agent_running = False

    is_hyprland = (
        'hyprland' in desktop
        or hyprland_instance
        or (session_type == 'wayland' and 'hypr' in wayland_display.lower())
    )

    if is_hyprland:
        return ["sudo", "-A"]

    elif session_type == 'wayland' and not polkit_agent_running:
        if 'SUDO_ASKPASS' in env:
            return ["sudo", "-A"]
        else:
            return ["pkexec"]

    elif polkit_agent_running:
        try:
            test_result = subprocess.run(['pkexec', '--version'],
                                         capture_output=True, timeout=5)
            if test_result.returncode == 0:
                if desktop in ['gnome', 'kde', 'xfce']:
                    return ["pkexec"]
                else:
                    return ["pkexec", "--disable-internal-agent"]
            else:
                if 'SUDO_ASKPASS' in env:
                    return ["sudo", "-A"]
                else:
                    return ["sudo", "-A"]
        except Exception:
            if 'SUDO_ASKPASS' in env:
                return ["sudo", "-A"]
            else:
                return ["sudo", "-A"]

    elif 'SUDO_ASKPASS' in env:
        return ["sudo", "-A"]

    else:
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
    if not askpass_path:
        return env, ""

    # Create askpass script
    script_content = "#!/bin/sh\n"
    if 'kdialog' in askpass_path:
        script_content += f'exec {askpass_path} --password "NeoArch requires administrative privileges" --title "Authentication Required"\n'
    elif 'zenity' in askpass_path:
        script_content += f'exec {askpass_path} --password --title="Authentication Required" --text="NeoArch requires administrative privileges:"\n'
    elif 'yad' in askpass_path:
        script_content += f'exec {askpass_path} --entry --hide-text --title="Authentication Required" --text="NeoArch requires administrative privileges:"\n'
    else:
        script_content += f'exec {askpass_path} "NeoArch requires administrative privileges"\n'

    fd, script_path = tempfile.mkstemp(prefix='neoarch_askpass_', suffix='.sh')
    with os.fdopen(fd, 'w') as f:
        f.write(script_content)
    os.chmod(script_path, 0o700)

    env['SUDO_ASKPASS'] = script_path
    return env, script_path
