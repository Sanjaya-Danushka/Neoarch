import os
import shutil
import tempfile


def get_sudo_askpass():
    candidates = [
        "ksshaskpass",
        "ssh-askpass",
        "qt5-askpass",
        "lxqt-openssh-askpass",
    ]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return None


def prepare_askpass_env():
    env = os.environ.copy()
    cleanup_path = None
    
    # Check if any GUI dialog tools are available
    available_tools = []
    for tool in ["kdialog", "zenity", "yad"]:
        if shutil.which(tool):
            available_tools.append(tool)
    
    # If no GUI tools available, return None to indicate failure
    if not available_tools:
        print("Warning: No GUI authentication tools found (kdialog, zenity, yad)")
        return env, None
    
    # Ensure DISPLAY is set for GUI dialogs
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    
    try:
        script = """#!/bin/sh
# Single-attempt password dialog - no retries
title=${NEOARCH_ASKPASS_TITLE:-"NeoArch - AUR Install"}
text=${NEOARCH_ASKPASS_TEXT:-"AUR packages are community-maintained and may be unsafe.\nEnter your password to proceed."}
icon=${NEOARCH_ASKPASS_ICON:-"dialog-password"}

# Debug logging
echo "NeoArch askpass called: $title" >> /tmp/neoarch-askpass.log

# Ensure DISPLAY is set
export DISPLAY="${DISPLAY:-:0}"

# Try different dialog tools, exit immediately on cancellation
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
  # Fallback to terminal-based password prompt if no GUI available
  echo "Using terminal fallback for password prompt" >> /tmp/neoarch-askpass.log
  echo "$text" >&2
  read -s -p "Password: " result
  echo >&2
  exit_code=$?
fi

# Log result
echo "Password prompt result: exit_code=$exit_code, has_result=$([ -n "$result" ] && echo yes || echo no)" >> /tmp/neoarch-askpass.log

# If cancelled or failed, exit with error code
if [ $exit_code -ne 0 ] || [ -z "$result" ]; then
  echo "Password prompt cancelled or failed" >> /tmp/neoarch-askpass.log
  exit 1
fi

# Output the password and exit successfully
echo "Password prompt successful" >> /tmp/neoarch-askpass.log
echo "$result"
exit 0
"""
        # Try to create temp file in user's temp directory first
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
        # If we can't create the askpass script, log the error but continue
        print(f"Warning: Could not create askpass script: {e}")
    
    return env, cleanup_path
