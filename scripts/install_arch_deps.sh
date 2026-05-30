#!/usr/bin/env bash
set -euo pipefail
if ! command -v pacman >/dev/null 2>&1; then
  echo "This installer is for Arch-based systems (pacman not found)." >&2
  exit 1
fi
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
