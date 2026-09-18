"""System utility functions for detecting available tools and dependencies.

Provides helpers to check for AUR helpers, GUI authentication tools,
and required system dependencies.
"""

import shutil
import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple, Optional

__all__ = [
    "cmd_exists", "get_available_aur_helpers", "get_aur_helper",
    "get_dependency_catalog", "get_missing_required",
    "get_missing_optional", "get_missing_dependencies",
    "get_missing_auth_tools", "check_aur_authentication_support",
    "check_db_lock", "suppress_missing", "clear_suppressed_missing",
    "ensure_cloud_venv", "is_cloud_venv_ready", "add_cloud_venv_to_path",
    "c_locale_env",
]

# Dependencies that a recent install attempt failed to fix. Re-offering the
# same install every re-check (Diagnostics / first-run setup) loops forever
# when pip/pacman cannot possibly succeed this session — e.g. pip targeting
# a different interpreter, an offline source, or a broken helper. The set is
# per-session only; a restart re-evaluates them fresh.
_SUPPRESSED_MISSING = set()

# GUI-launched apps often inherit a trimmed PATH; probe these directly.
_GUI_FALLBACK_PATHS = [
    "/usr/local/bin", "/usr/bin", "/bin",
    "/usr/local/sbin", "/usr/sbin", "/sbin",
]

# App-owned virtualenv for cloud-sync dependencies (supabase + httpx).
# Kept isolated from system site-packages to avoid PEP 668 conflicts
# (supabase pins httpx<0.26 while Arch ships httpx>=0.28).
CLOUD_VENV_DIR = Path.home() / ".local/share/neoarch/venv"


def c_locale_env() -> dict:
    """Environment dict that forces C locale for subprocesses.

    gettext-based tools (pacman, …) localize their field labels
    (e.g. 'Install Reason' → 'Motif d'installation'); parsers match the
    English labels, so such queries must run under LC_ALL=C to stay stable
    for every user language.
    """
    env = os.environ.copy()
    env.pop("LANG", None)
    env.pop("LANGUAGE", None)
    env["LC_ALL"] = "C"
    env["LC_MESSAGES"] = "C"
    return env


def is_cloud_venv_ready() -> bool:
    """Check if the cloud venv exists and has supabase installed."""
    venv_python = CLOUD_VENV_DIR / "bin" / "python"
    if not venv_python.exists():
        return False
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import supabase"],
            capture_output=True, timeout=30, check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_cloud_venv(log_fn=None) -> None:
    """Create the app venv and install supabase if not already present.

    Raises RuntimeError on failure so the caller can decide how to handle it.

    Args:
        log_fn: Optional callable for progress messages (str -> None).
    """
    if is_cloud_venv_ready():
        return

    if log_fn:
        log_fn("Creating cloud-sync virtual environment...")

    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(CLOUD_VENV_DIR)],
            check=True, capture_output=True, timeout=60,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create venv: {e.stderr.decode(errors='ignore')}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Venv creation timed out") from e

    venv_pip = CLOUD_VENV_DIR / "bin" / "pip"
    if log_fn:
        log_fn("Installing supabase in virtual environment...")

    try:
        subprocess.run(
            [str(venv_pip), "install", "--quiet", "supabase"],
            check=True, capture_output=True, timeout=180,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pip install supabase failed: {e.stderr.decode(errors='ignore')}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("pip install supabase timed out") from e

    if not is_cloud_venv_ready():
        raise RuntimeError("Venv created but supabase import still fails")


def add_cloud_venv_to_path() -> None:
    """Add the cloud venv's site-packages to sys.path if available."""
    import glob
    for sp in sorted(glob.glob(str(CLOUD_VENV_DIR / "lib" / "python*" / "site-packages"))):
        if sp not in sys.path:
            sys.path.insert(0, sp)


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

    # Dependencies of bundled parsers — required at runtime
    add("python-defusedxml", "python-defusedxml", True,
        "Secure XML parsing (news feed)",
        importlib.util.find_spec("defusedxml") is not None)

    # Optional integrations — features degrade gracefully
    add("flatpak", "flatpak", False, "Flatpak page", cmd_exists("flatpak"))
    add("nodejs", "nodejs", False, "Discover page (npm)", cmd_exists("node"))
    add("npm", "npm", False, "Discover page (npm)", cmd_exists("npm"))
    add("docker", "docker", False, "Docker page", cmd_exists("docker"))
    add("fwupdmgr", "fwupd", False, "Firmware updates", cmd_exists("fwupdmgr"))
    add("gnome-keyring", "gnome-keyring", False,
        "Saving sudo password", cmd_exists("gnome-keyring-daemon"))
    add("curl", "curl", False, "Network downloads", cmd_exists("curl"))
    add("yay or paru", "yay", False, "AUR updates",
        bool(get_available_aur_helpers()))

    python_mods = {
        "keyring": ("python-keyring", "Saving sudo password"),
    }
    for module, (pkg, feature) in python_mods.items():
        add(pkg, pkg, False, feature,
            importlib.util.find_spec(module) is not None)

    # Cloud sync: supabase lives in an app-owned venv (PEP 668 safe).
    add("python-supabase", "python-supabase", False, "Cloud sync",
        is_cloud_venv_ready())

    # Test hook: NEOARCH_FAKE_MISSING="a,b" simulates absent dependencies
    fake = os.environ.get("NEOARCH_FAKE_MISSING", "")
    for name in [n.strip() for n in fake.split(",") if n.strip()]:
        add(name, name, False, "Simulated missing dependency (test)", False)

    return cat


def suppress_missing(name: str) -> None:
    """Stop reporting a dependency as missing for the rest of this session."""
    _SUPPRESSED_MISSING.add(name)


def clear_suppressed_missing() -> None:
    """Re-enable reporting for all previously-suppressed dependencies."""
    _SUPPRESSED_MISSING.clear()


def resolve_pkg_names(names):
    """Map dependency catalog names to their actual pacman package names.

    The setup flow uses catalog ``name`` identifiers (e.g. ``fwupdmgr``),
    but pacman needs the real package name (``fwupd``).
    """
    cat = {e['name']: e['pkg'] for e in get_dependency_catalog()}
    return [cat.get(n, n) for n in names]


def get_missing_required() -> List[str]:
    """Names of required dependencies that are missing."""
    return [d["name"] for d in get_dependency_catalog()
            if d["required"] and not d["present"]
            and d["name"] not in _SUPPRESSED_MISSING]


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
        return bool(load_settings().get('include_local_source', False))
    except Exception:
        return False


def firmware_source_enabled() -> bool:
    """Setting ▸ General ▸ 'Check for firmware updates'."""
    try:
        from neoarch.backend.services.settings import load_settings
        return bool(load_settings().get('include_firmware_updates', True))
    except Exception:
        return True


def pipx_source_enabled() -> bool:
    """Setting ▸ General ▸ 'Check for pipx updates'."""
    try:
        from neoarch.backend.services.settings import load_settings
        return bool(load_settings().get('check_pipx_updates', True))
    except Exception:
        return True


def get_missing_optional() -> List[str]:
    """Names of optional integrations that are missing."""
    return [d["name"] for d in get_dependency_catalog()
            if not d["required"] and not d["present"]
            and d["name"] not in _SUPPRESSED_MISSING]


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
            [shutil.which("gnome-keyring-daemon") or "gnome-keyring-daemon", "--start", "--components=secrets"],
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


PACMAN_DB_LOCK = "/var/lib/pacman/db.lck"

# AUR helpers and wrappers also take the pacman DB lock when they run
# pacman underneath. A process with any of these in its argv is "another
# package manager" holding the lock.
_OTHER_PM_NAMES = (
    "pacman", "yay", "paru", "trizen", "pikaur", "aur", "pamac", "octopi",
    "pkgfile", "checkupdates", "pacaur",
)


def check_db_lock():
    """Inspect the pacman DB lock and report who holds it.

    Returns one of::

        None                              -> no lock file present
        {"status": "ours"}                -> lock held by this app's process
        {"status": "other"}               -> lock held by another package manager
        {"status": "stale"}               -> lock file exists but nobody holds it
        {"status": "unknown", "pid": n}   -> lock file exists, holder unknown

    This lets callers distinguish "pacman is legitimately busy elsewhere"
    from "a leftover db.lck is blocking everything" (the common case after a
    crash, a killed terminal, or a ctrl-C'd pacman).
    """
    if not os.path.exists(PACMAN_DB_LOCK):
        return None

    holder_pids = _lock_holder_pids()
    if not holder_pids:
        return {"status": "stale"}

    my_pid = os.getpid()
    if my_pid in holder_pids:
        return {"status": "ours"}

    # A child pacman spawned by us shares our identity through env/argv.
    if _is_neoarch_child(holder_pids):
        return {"status": "ours"}

    if _holder_is_other_package_manager(holder_pids):
        return {"status": "other"}

    return {"status": "unknown", "pid": holder_pids[0]}


def _lock_holder_pids() -> List[int]:
    """Return PIDs currently holding the pacman DB lock (best-effort)."""
    candidates = []

    # fuser(1) is the most direct way to find lock holders.
    if cmd_exists("fuser"):
        try:
            import subprocess
            out = subprocess.run(
                [shutil.which("fuser") or "fuser", PACMAN_DB_LOCK],
                capture_output=True, text=True, timeout=5, check=False
            )
            for tok in out.stdout.replace(":", " ").split():
                try:
                    candidates.append(int(tok))
                except ValueError:
                    continue
        except Exception:
            pass
        else:
            if candidates:
                return list(dict.fromkeys(candidates))

    # Fallback: scan /proc for processes with the lock path open.
    try:
        import subprocess
        out = subprocess.run(
            [shutil.which("lsof") or "lsof", PACMAN_DB_LOCK],
            capture_output=True, text=True, timeout=5, check=False
        )
        for line in out.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    candidates.append(int(parts[1]))
                except ValueError:
                    continue
    except Exception:
        pass

    return list(dict.fromkeys(candidates))


def _is_neoarch_child(holder_pids: List[int]) -> bool:
    """True if any lock holder is a pacman child of this app."""
    import subprocess
    try:
        out = subprocess.run(
            [shutil.which("pgrep") or "pgrep", "-P", str(os.getpid())],
            capture_output=True, text=True, timeout=5, check=False
        )
        direct_children = {
            int(p) for p in out.stdout.split() if p.isdigit()
        }
    except Exception:
        return False
    if direct_children & set(holder_pids):
        return True
    # Grandchildren (pacman -> a helper script) too.
    for pid in holder_pids:
        if _descends_from(pid, os.getpid()):
            return True
    return False


def _descends_from(pid: int, ancestor: int) -> bool:
    """Walk /proc == pid parent chain to see if `ancestor` is an ancestor."""
    seen = set()
    cur = pid
    while cur and cur not in seen:
        seen.add(cur)
        try:
            with open(f"/proc/{cur}/stat", "rb") as f:
                data = f.read()
            ppid = int(data.split(b")")[1].split()[1])
        except Exception:
            return False
        if ppid == ancestor:
            return True
        cur = ppid
    return False


def _holder_is_other_package_manager(holder_pids: List[int]) -> bool:
    """True if a lock holder is another package manager (not this app)."""
    for pid in holder_pids:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                argv = f.read().replace(b"\x00", b" ").decode(errors="ignore")
        except Exception:
            continue
        name = argv.split()[0].rsplit("/", 1)[-1] if argv.strip() else ""
        if name in _OTHER_PM_NAMES:
            return True
    return False
