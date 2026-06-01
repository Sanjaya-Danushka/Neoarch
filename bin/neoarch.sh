#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root (bin/..)
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

# Ensure proper environment for GUI applications
export DISPLAY="${DISPLAY:-:0}"

# Ensure authentication agents are available
if command -v kdialog >/dev/null 2>&1; then
    export SUDO_ASKPASS_PREFER="kdialog"
elif command -v zenity >/dev/null 2>&1; then
    export SUDO_ASKPASS_PREFER="zenity"
elif command -v yad >/dev/null 2>&1; then
    export SUDO_ASKPASS_PREFER="yad"
fi

# Activate local venv if present
if [[ -f "$REPO_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_DIR/.venv/bin/activate"
fi

cd "$REPO_DIR"
exec python aurora_home.py "$@"
