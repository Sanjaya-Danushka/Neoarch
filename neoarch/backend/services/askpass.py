"""Askpass script generation for GUI sudo password prompts.

Creates temporary shell scripts that use kdialog, zenity, or yad to
present a graphical password dialog for sudo elevation.
"""

import os
import shutil
import tempfile

__all__ = ["get_sudo_askpass", "prepare_askpass_env"]


def get_sudo_askpass() -> str:
    """Find an available SSH askpass program.

    Returns:
        str: Path to askpass program, or None if not found.
    """
    candidates = ["ksshaskpass", "ssh-askpass", "qt5-askpass", "lxqt-openssh-askpass"]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return None


def prepare_askpass_env() -> tuple:
    """Create a temporary SUDO_ASKPASS script and prepare environment.

    Generates a shell script that uses kdialog/zenity/yad to ask for the
    sudo password, then returns the modified environment and cleanup path.

    Returns:
        tuple: (env dict, temp script path or None)
    """
    env = os.environ.copy()
    cleanup_path = None

    # If SUDO_ASKPASS is already set (e.g. by session auth), use as-is
    if env.get("SUDO_ASKPASS") and os.path.exists(env["SUDO_ASKPASS"]):
        return env, cleanup_path

    available_tools = []
    for tool in ["kdialog", "zenity", "yad"]:
        if shutil.which(tool):
            available_tools.append(tool)

    if not available_tools:
        print("Warning: No GUI authentication tools found (kdialog, zenity, yad)")
        return env, None

    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"

    try:
        script = """#!/bin/sh
title=${NEOARCH_ASKPASS_TITLE:-"NeoArch - AUR Install"}
text=${NEOARCH_ASKPASS_TEXT:-"AUR packages are community-maintained and may be unsafe.\\nEnter your password to proceed."}
icon=${NEOARCH_ASKPASS_ICON:-"dialog-password"}

echo "NeoArch askpass called: $title" >> /tmp/neoarch-askpass.log

export DISPLAY="${DISPLAY:-:0}"

if command -v kdialog >/dev/null 2>&1; then
  echo "Using kdialog for password prompt" >> /tmp/neoarch-askpass.log
  result=$(kdialog --title "$title" --icon "$icon" --password "$text" 2>/dev/null)
  exit_code=$?
elif command -v zenity >/dev/null 2>&1; then
  echo "Using zenity for password prompt" >> /tmp/neoarch-askpass.log
  result=$(zenity --password --title="$title" --text="$text" --window-icon="$icon" 2>/dev/null)
  exit_code=$?
elif command -v yad >/dev/null 2>&1; then
  echo "Using yad for password prompt" >> /tmp/neoarch-askpass.log
  result=$(yad --title="$title" --text="$text" --entry --hide-text --window-icon="$icon" 2>/dev/null)
  exit_code=$?
else
  echo "Using terminal fallback for password prompt" >> /tmp/neoarch-askpass.log
  echo "$text" >&2
  read -s -p "Password: " result
  echo >&2
  exit_code=$?
fi

echo "Password prompt result: exit_code=$exit_code, has_result=$([ -n "$result" ] && echo yes || echo no)" >> /tmp/neoarch-askpass.log

if [ $exit_code -ne 0 ] || [ -z "$result" ]; then
  echo "Password prompt cancelled or failed" >> /tmp/neoarch-askpass.log
  exit 1
fi

echo "Password prompt successful" >> /tmp/neoarch-askpass.log
echo "$result"
exit 0
"""
        temp_dir = os.path.expanduser("~/.cache")
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                temp_dir = None

        if temp_dir and os.access(temp_dir, os.W_OK):
            fd, path = tempfile.mkstemp(prefix="neoarch-askpass-", suffix=".sh", dir=temp_dir)
        else:
            fd, path = tempfile.mkstemp(prefix="neoarch-askpass-", suffix=".sh")

        with os.fdopen(fd, "w") as f:
            f.write(script)
        os.chmod(path, 0o700)
        cleanup_path = path
        env["SUDO_ASKPASS"] = path
        env["SSH_ASKPASS"] = path
        env["SUDO_ASKPASS_REQUIRE"] = "force"
    except Exception as e:
        print(f"Warning: Could not create askpass script: {e}")

    return env, cleanup_path
