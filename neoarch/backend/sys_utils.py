"""System utility functions for detecting available tools and dependencies.

Provides helpers to check for AUR helpers, GUI authentication tools,
and required system dependencies.
"""

import shutil
import os
import importlib.util
from typing import List, Tuple, Optional

__all__ = [
    "cmd_exists", "get_available_aur_helpers", "get_aur_helper",
    "get_dependency_catalog", "get_missing_required",
    "get_missing_optional", "get_missing_dependencies",
    "get_missing_auth_tools", "check_aur_authentication_support",
]

# GUI-launched apps often inherit a trimmed PATH; probe these directly.
_GUI_FALLBACK_PATHS = [
    "/usr/local/bin", "/usr/bin", "/bin",
    "/usr/local/sbin", "/usr/sbin", "/sbin",
]


def cmd_exists(cmd: str) -> bool:
    """Check if a command is available, tolerating GUI-trimmed PATH."""
    if shutil.which(cmd):
        return True
    return any(
        os.path.isfile(os.path.join(d, cmd)) for d in _GUI_FALLBACK_PATHS
    )


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


def get_dependency_catalog() -> List[dict]:
    """Return the full dependency catalog with live presence checks.

    Each entry: {name, pkg, required, feature, present} where ``name``
    is the install-facing identifier (also used by the setup flow),
    ``pkg`` the pacman/pip package, ``feature`` what breaks without it.
    """
    cat: List[dict] = []

    def add(name, pkg, required, feature, present):
        cat.append({"name": name, "pkg": pkg, "required": required,
                    "feature": feature, "present": bool(present)})

    # Core — the app cannot function without these
    add("pacman", "pacman", True, "Package operations", cmd_exists("pacman"))
    add("git", "git", True, "AUR builds and Git projects", cmd_exists("git"))

    # Optional integrations — features degrade gracefully
    add("flatpak", "flatpak", False, "Flatpak page", cmd_exists("flatpak"))
    add("nodejs", "nodejs", False, "Discover page (npm)", cmd_exists("node"))
    add("npm", "npm", False, "Discover page (npm)", cmd_exists("npm"))
    add("docker", "docker", False, "Docker page", cmd_exists("docker"))
    add("gnome-keyring", "gnome-keyring", False,
        "Saving sudo password", cmd_exists("gnome-keyring-daemon"))
    add("curl", "curl", False, "Network downloads", cmd_exists("curl"))
    add("yay or paru", "yay", False, "AUR updates",
        bool(get_available_aur_helpers()))

    python_mods = {
        "keyring": ("python-keyring", "Saving sudo password"),
        "httpx": ("python-httpx", "Cloud sync"),
        "supabase": ("python-supabase", "Cloud sync"),
    }
    for module, (pkg, feature) in python_mods.items():
        add(pkg, pkg, False, feature,
            importlib.util.find_spec(module) is not None)

    # Test hook: NEOARCH_FAKE_MISSING="a,b" simulates absent dependencies
    fake = os.environ.get("NEOARCH_FAKE_MISSING", "")
    for name in [n.strip() for n in fake.split(",") if n.strip()]:
        add(name, name, False, "Simulated missing dependency (test)", False)

    return cat


def get_missing_required() -> List[str]:
    """Names of required dependencies that are missing."""
    return [d["name"] for d in get_dependency_catalog()
            if d["required"] and not d["present"]]


def fake_missing_active() -> bool:
    """True while the NEOARCH_FAKE_MISSING test hook injects entries."""
    return bool(os.environ.get("NEOARCH_FAKE_MISSING", "").strip())


def npm_user_mode_enabled() -> bool:
    """Setting ▸ General ▸ 'Use npm user mode for global installs'.

    When disabled, npm queries/operations skip the per-user prefix
    (~/.npm-global) and only touch the system-wide default prefix.
    """
    try:
        from neoarch.backend.services.settings import load_settings
        return bool(load_settings().get('npm_user_mode', True))
    except Exception:
        return True


def local_source_enabled() -> bool:
    """Setting ▸ General ▸ 'Include Local source (custom scripts)'."""
    try:
        from neoarch.backend.services.settings import load_settings
        return bool(load_settings().get('include_local_source', True))
    except Exception:
        return True


def get_missing_optional() -> List[str]:
    """Names of optional integrations that are missing."""
    return [d["name"] for d in get_dependency_catalog()
            if not d["required"] and not d["present"]]


def get_missing_dependencies() -> List[str]:
    """Check for missing system dependencies and return their names."""
    # Keyring needs a running SecretService backend to persist sudo creds.
    # A stopped/locked daemon cannot be fixed by pacman, so try starting it
    # quietly instead of flagging an installable package (that looped forever).
    if cmd_exists("gnome-keyring-daemon") and importlib.util.find_spec("keyring") is not None:
        if not _keyring_usable():
            _start_secret_service()

    return get_missing_required() + get_missing_optional()


def _keyring_usable() -> bool:
    """Return True if the keyring backend can actually store/retrieve secrets."""
    try:
        import keyring
        keyring.set_password("neoarch-selfcheck", "probe", "1")
        ok = keyring.get_password("neoarch-selfcheck", "probe") == "1"
        try:
            keyring.delete_password("neoarch-selfcheck", "probe")
        except Exception:
            pass
        return ok
    except Exception:
        return False


def _start_secret_service() -> None:
    """Best-effort start of the gnome-keyring secrets daemon."""
    import subprocess
    try:
        subprocess.run(
            ["gnome-keyring-daemon", "--start", "--components=secrets"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False)
    except Exception:
        pass


def get_missing_auth_tools() -> List[str]:
    """Deprecated: external GUI auth tools are no longer required.

    NeoArch authenticates via its built-in themed dialog and session cache.

    Returns:
        list: Always empty.
    """
    return []


def check_aur_authentication_support() -> Tuple[bool, str]:
    """Check if AUR authentication is properly configured.

    Returns:
        tuple: (is_supported, message)
    """
    return True, "NeoArch uses its built-in authentication dialog."
