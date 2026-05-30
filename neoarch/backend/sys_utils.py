"""System utility functions for detecting available tools and dependencies.

Provides helpers to check for AUR helpers, GUI authentication tools,
and required system dependencies.
"""

import shutil
import os
from typing import List, Tuple, Optional

__all__ = [
    "cmd_exists", "get_available_aur_helpers", "get_aur_helper",
    "get_missing_dependencies", "get_missing_auth_tools",
    "check_aur_authentication_support",
]


def cmd_exists(cmd: str) -> bool:
    """Check if a command is available in the system PATH."""
    return shutil.which(cmd) is not None


def get_available_aur_helpers() -> List[str]:
    """Get list of available AUR helpers in order of preference.

    Returns:
        list: Available helpers from ['yay', 'paru', 'trizen', 'pikaur']
    """
    helpers = ['yay', 'paru', 'trizen', 'pikaur']
    return [h for h in helpers if cmd_exists(h)]


def get_aur_helper(preferred: Optional[str] = None) -> Optional[str]:
    """Get the AUR helper to use.

    Args:
        preferred: Preferred AUR helper name. If None or not available,
                   returns the first available helper.

    Returns:
        Name of the AUR helper to use, or None if none available.
    """
    available = get_available_aur_helpers()
    if not available:
        return None
    if preferred and preferred in available:
        return preferred
    return available[0]


def get_missing_dependencies() -> List[str]:
    """Check for missing system dependencies and return their names."""
    missing = []
    if not cmd_exists("flatpak"):
        missing.append("flatpak")
    if not cmd_exists("git"):
        missing.append("git")
    if not cmd_exists("node"):
        missing.append("nodejs")
    if not cmd_exists("npm"):
        missing.append("npm")
    if not cmd_exists("docker"):
        missing.append("docker")
    if not get_available_aur_helpers():
        missing.append("yay or paru")
    return missing


def get_missing_auth_tools() -> List[str]:
    """Get list of missing GUI authentication tools.

    At least one of kdialog, zenity, or yad is needed for AUR
    package sudo password prompts.

    Returns:
        list: Missing tool names, or empty list if at least one is available.
    """
    auth_tools = ['kdialog', 'zenity', 'yad']
    available = [tool for tool in auth_tools if cmd_exists(tool)]
    if not available:
        return auth_tools
    return []


def check_aur_authentication_support() -> Tuple[bool, str]:
    """Check if AUR authentication is properly configured.

    Returns:
        tuple: (is_supported, message)
    """
    missing_auth = get_missing_auth_tools()
    if missing_auth:
        message = (
            "Warning: No GUI authentication tools found for AUR packages.\n"
            f"Please install one of: {', '.join(missing_auth)}\n"
            "Example: sudo pacman -S kdialog (or zenity/yad)"
        )
        return False, message
    return True, "AUR authentication is properly configured"
