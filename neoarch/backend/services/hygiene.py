"""System hygiene services.

Provides orphaned-package cleanup, .pacnew file management, and the
Arch Linux news feed. Each service is safe to call from the UI layer
and uses the same auth/elevation helpers as the rest of the app.
"""

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from threading import Thread
from typing import List, Dict, Optional

from neoarch.backend.auth import get_auth_command
from neoarch.resources.paths import APP_VERSION

__all__ = [
    "list_orphans", "remove_orphans",
    "list_pacnew", "diff_pacnew", "accept_pacnew", "delete_pacnew",
    "merge_pacnew",
    "list_installed_sizes",
    "list_explicit_packages", "package_info",
    "fetch_news", "news_cache", "news_cache_age",
    "mark_news_seen", "news_seen", "news_seen_status", "news_unseen_count",
    "list_corrupted_packages", "remove_corrupted_packages",
    "purge_cache", "purge_flatpak_unused",
    "disk_usage", "package_cache_size",
]

NEWS_URL = "https://archlinux.org/feeds/news/"
NEWS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "news.xml")
NEWS_SEEN_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "news_seen.json")
NEWS_CACHE_MAX_AGE = 60 * 60  # 1 hour


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command without elevation, tolerating failures."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _run_sudo(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    """Run a command with the app's preferred elevation."""
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        from neoarch.backend.auth import get_askpass_env
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except Exception:
        return subprocess.CompletedProcess(auth + cmd, 1, "", "")


# ──────────────────────────────────────────────────────────────────────────
# Orphaned packages
# ──────────────────────────────────────────────────────────────────────────

def list_orphans() -> List[str]:
    """List orphaned (unneeded) packages installed as dependencies.

    Uses `pacman -Qtdq` which reports packages no longer required by any
    explicitly installed package.
    """
    result = _run(["pacman", "-Qtdq"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def remove_orphans(progress_cb=None, finished_cb=None) -> bool:
    """Remove all orphaned packages. Returns True on success."""
    def _do() -> bool:
        orphans = list_orphans()
        if not orphans:
            if progress_cb:
                try:
                    progress_cb("No orphaned packages to remove.")
                except Exception:
                    pass
            if finished_cb:
                try:
                    finished_cb(True)
                except Exception:
                    pass
            return True
        if progress_cb:
            try:
                progress_cb(f"Removing {len(orphans)} orphaned package(s)...")
            except Exception:
                pass
        result = _run_sudo(["pacman", "-Rns", "--noconfirm"] + orphans)
        ok = result.returncode == 0
        if progress_cb:
            try:
                progress_cb("Orphans removed." if ok else f"Failed to remove orphans: {result.stderr.strip()}")
            except Exception:
                pass
        if finished_cb:
            try:
                finished_cb(ok)
            except Exception:
                pass
        return ok

    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()


# ──────────────────────────────────────────────────────────────────────────
# .pacnew files
# ──────────────────────────────────────────────────────────────────────────

def list_pacnew() -> List[Dict]:
    """Find .pacnew files left by recent package upgrades.

    Searches the standard config tree and common package dirs. Returns a
    list of dicts: {path, original, package}.
    """
    targets = ["/etc"]
    for extra in ("/usr/share", "/usr/local/etc", "/var/lib"):
        if os.path.isdir(extra):
            targets.append(extra)
    found = []
    for root in targets:
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d != ".git"]
                for fn in filenames:
                    if fn.endswith(".pacnew"):
                        path = os.path.join(dirpath, fn)
                        found.append(_pacnew_info(path))
        except Exception:
            continue
    return found


def _pacnew_info(path: str) -> Dict:
    original = re.sub(r"\.pacnew$", "", path)
    pkg = "unknown"
    try:
        result = subprocess.run(
            ["pacman", "-Qo", original],
            capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            match = re.match(r"^([^\s]+)", result.stdout.strip())
            if match:
                pkg = match.group(1)
    except Exception:
        pass
    return {"path": path, "original": original, "package": pkg}


def diff_pacnew(path: str) -> str:
    """Return the diff between a .pacnew file and its current original."""
    info = _pacnew_info(path)
    result = subprocess.run(
        ["diff", "-u", info["original"], path],
        capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return "(no differences)"
    return result.stdout or result.stderr or "(unable to diff)"


def accept_pacnew(path: str) -> bool:
    """Replace the original file with the .pacnew version (needs root)."""
    info = _pacnew_info(path)
    backup = info["original"] + ".pacsave"
    try:
        if os.path.exists(info["original"]):
            _run_sudo(["cp", "-a", info["original"], backup])
        result = _run_sudo(["cp", path, info["original"]])
        if result.returncode == 0:
            _run_sudo(["rm", "-f", path])
            return True
    except Exception:
        pass
    return False


def delete_pacnew(path: str) -> bool:
    """Delete a .pacnew file without touching the original (needs root)."""
    result = _run_sudo(["rm", "-f", path])
    if result.returncode == 0 and not os.path.exists(path):
        return True
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def merge_pacnew(path: str, accept: bool = False) -> Dict:
    """Three-way merge a .pacnew against the current original.

    The base is taken from a cached package archive for the owning
    package (an earlier config), falling back to the current original
    when no archive is available. Uses `diff3 -m`.

    Returns {merged, conflicts, backup}. When conflicts exist the merged
    output (with conflict markers) is written next to the original as
    `<original>.merged` and the .pacnew is left in place. When clean and
    `accept=True` the original is replaced (backup to .pacsave) and the
    .pacnew is removed.
    """
    info = _pacnew_info(path)
    original = info["original"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            theirs = f.read()
    except Exception:
        return {"merged": "", "conflicts": True, "backup": ""}

    base = _extract_base(original, path, info["package"])
    try:
        with open(original, "r", encoding="utf-8") as f:
            ours = f.read()
    except Exception:
        ours = ""

    # diff3 -m ours base theirs
    import tempfile
    def _write(content: str) -> str:
        fd, name = tempfile.mkstemp(prefix="neoarch-merge-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return name

    tmp_ours, tmp_base, tmp_theirs = _write(ours), _write(base), _write(theirs)
    try:
        result = subprocess.run(
            ["diff3", "-m", tmp_ours, tmp_base, tmp_theirs],
            capture_output=True, text=True, timeout=30)
        merged = result.stdout
        conflicts = result.returncode != 0  # 1 = conflicts, 2 = trouble
    finally:
        for tmp in (tmp_ours, tmp_base, tmp_theirs):
            try:
                os.remove(tmp)
            except Exception:
                pass

    if not conflicts:
        if accept:
            backup = original + ".pacsave"
            try:
                if os.path.exists(original):
                    _run_sudo(["cp", "-a", original, backup])
                if _run_sudo(["cp", path, original]).returncode == 0:
                    _run_sudo(["rm", "-f", path])
                    return {"merged": original, "conflicts": False, "backup": backup}
            except Exception:
                pass
        return {"merged": merged, "conflicts": False, "backup": ""}

    merged_path = original + ".merged"
    try:
        with open(merged_path, "w", encoding="utf-8") as f:
            f.write(merged)
        return {"merged": merged_path, "conflicts": True, "backup": ""}
    except Exception:
        return {"merged": "", "conflicts": True, "backup": ""}


def _extract_base(original: str, pacnew: str, package: str) -> str:
    """Return the previous upstream version of `original`.

    Searches cached package archives for the owning package and extracts
    the same config path, preferring an archive whose content differs
    from the .pacnew (i.e. a genuinely older version). Falls back to the
    current original content when nothing suitable is cached.
    """
    rel = original.lstrip("/")
    try:
        with open(pacnew, "r", encoding="utf-8") as f:
            new_content = f.read()
    except Exception:
        new_content = None

    from neoarch.backend.services.downgrade import cache_dirs, _parse_pkgfile
    for cache_dir in cache_dirs():
        try:
            names = sorted(os.listdir(cache_dir))
        except Exception:
            continue
        for name in names:
            if not name.endswith(".pkg.tar.zst") and not name.endswith(".pkg.tar.xz"):
                continue
            parsed = _parse_pkgfile(os.path.join(cache_dir, name))
            if not parsed or parsed["name"] != package:
                continue
            archive = os.path.join(cache_dir, name)
            result = _run(["bsdtar", "-xOf", archive, rel], timeout=60)
            if result.returncode == 0 and result.stdout:
                if new_content is None or result.stdout != new_content:
                    return result.stdout
    # Fall back to the current original as base (two-way-ish merge).
    try:
        with open(original, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────
# Installed size intelligence
# ──────────────────────────────────────────────────────────────────────────

def list_installed_sizes() -> Dict[str, int]:
    """Map each installed package name to its installed size in bytes.

    Uses `pacman -Qik` which reports the on-disk size of every locally
    installed package. Returns a dict of {name: bytes} — an empty dict on
    failure.
    """
    result = _run(["pacman", "-Qik"], timeout=120)
    if result.returncode != 0 and not result.stdout.strip():
        return {}
    sizes: Dict[str, int] = {}
    name = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Name"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                name = parts[1].strip()
        elif stripped.startswith("Installed Size") and name:
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                value = _parse_size_text(parts[1].strip())
                if value:
                    sizes[name] = value
            name = None
    return sizes


def _parse_size_text(text: str) -> int:
    """Parse a human size string (e.g. '1.23 MiB') into bytes."""
    m = re.search(r"([\d.]+)\s*([KMGT]?)i?B", str(text), re.IGNORECASE)
    if not m:
        return 0
    num = float(m.group(1))
    mult = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    return int(num * mult.get(m.group(2).upper(), 1))


def list_explicit_packages() -> set:
    """Names of packages installed as explicit (not pulled in as a dependency)."""
    result = _run(["pacman", "-Qe"])
    if result.returncode != 0:
        return set()
    return {line.split()[0] for line in result.stdout.splitlines() if line.split()}


def package_info(name: str) -> Dict:
    """Detailed metadata for one installed package via `pacman -Qi`.

    Returns a dict with install reason, required-by (reverse dependencies),
    description, and installed size. Empty dict on failure or unknown pkg.
    """
    result = _run(["pacman", "-Qi", name], timeout=30)
    if result.returncode != 0:
        return {}
    info: Dict = {}
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "Description":
            info["description"] = value
        elif key == "Install Reason":
            info["install_reason"] = value
        elif key == "Required By":
            info["required_by"] = [x for x in value.split() if x and x != "None"]
        elif key == "Installed Size":
            info["installed_size"] = _parse_size_text(value)
    return info


# ──────────────────────────────────────────────────────────────────────────
# Cache retention / corrupted archives
# ──────────────────────────────────────────────────────────────────────────

def list_corrupted_packages() -> List[str]:
    """List package archives in the cache that fail archive verification.

    Each `.pkg.tar.*` archive is verified with `bsdtar -tf`; an archive
    that cannot be listed is treated as corrupted.
    """
    from neoarch.backend.services.downgrade import cache_dirs
    corrupted: List[str] = []
    for cache_dir in cache_dirs():
        try:
            names = os.listdir(cache_dir)
        except Exception:
            continue
        for name in names:
            if not re.search(r"\.pkg\.tar(?:\.\w+)?$", name):
                continue
            path = os.path.join(cache_dir, name)
            if not os.path.isfile(path):
                continue
            result = _run(["bsdtar", "-tf", path], timeout=120)
            if result.returncode != 0:
                corrupted.append(path)
    return corrupted


def remove_corrupted_packages(progress_cb=None, finished_cb=None) -> bool:
    """Delete corrupted archives from the cache. Returns True on success."""
    def _do() -> bool:
        corrupted = list_corrupted_packages()
        if not corrupted:
            if progress_cb:
                try:
                    progress_cb("No corrupted package archives found.")
                except Exception:
                    pass
            if finished_cb:
                try:
                    finished_cb(True)
                except Exception:
                    pass
            return True
        if progress_cb:
            try:
                progress_cb(f"Removing {len(corrupted)} corrupted archive(s)...")
            except Exception:
                pass
        result = _run_sudo(["rm", "-f"] + corrupted)
        ok = result.returncode == 0
        if finished_cb:
            try:
                finished_cb(ok)
            except Exception:
                pass
        return ok

    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()


def purge_cache(retain: int = 3) -> bool:
    """Trim the package cache, keeping `retain` versions per package.

    Runs `paccache -rk<N>` which also clears the transaction database
    temp directory. Returns True on success.
    """
    if retain < 0:
        return False
    result = _run_sudo(["paccache", "-r", "-k", str(retain)], timeout=900)
    return result.returncode == 0


def disk_usage(path: str = "/") -> Dict[str, int]:
    """Filesystem usage for a mount point as {total, used, free} bytes."""
    try:
        import shutil
        u = shutil.disk_usage(path)
        return {"total": u.total, "used": u.used, "free": u.free}
    except Exception:
        return {}


def package_cache_size() -> int:
    """Total size of the pacman package cache in bytes (0 on failure)."""
    total = 0
    cache_dir = "/var/cache/pacman/pkg"
    try:
        for root, _, files in os.walk(cache_dir):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def purge_flatpak_unused(progress_cb=None, finished_cb=None) -> bool:
    """Remove Flatpak runtimes left unused by installed apps."""
    def _do() -> bool:
        if progress_cb:
            try:
                progress_cb("Removing unused Flatpak runtimes...")
            except Exception:
                pass
        result = _run_sudo(["flatpak", "uninstall", "--unused", "-y"], timeout=900)
        ok = result.returncode == 0
        if progress_cb:
            try:
                progress_cb("Flatpak cleanup done." if ok else
                            f"Flatpak cleanup failed: {result.stderr.strip()}")
            except Exception:
                pass
        if finished_cb:
            try:
                finished_cb(ok)
            except Exception:
                pass
        return ok

    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()


# ──────────────────────────────────────────────────────────────────────────
# Arch Linux news feed
# ──────────────────────────────────────────────────────────────────────────

def news_cache() -> Optional[str]:
    """Path to the cached news feed, if it exists."""
    if os.path.exists(NEWS_CACHE):
        return NEWS_CACHE
    return None


def news_cache_age() -> float:
    """Age of the cached news feed in seconds (-1 if none)."""
    path = news_cache()
    if not path:
        return -1
    try:
        import time
        return time.time() - os.path.getmtime(path)
    except Exception:
        return -1


def _fetch_news_xml() -> str:
    """Download the Arch news feed XML, with a short timeout."""
    import urllib.request
    req = urllib.request.Request(NEWS_URL, headers={"User-Agent": f"neoarch/{APP_VERSION}"})
    from neoarch.backend.services.network import urlopen as _net_urlopen
    with _net_urlopen(req) as resp:
        return resp.read().decode("utf-8")


def _parse_news(xml_text: str, limit: int = 10) -> List[Dict]:
    """Parse an RSS feed into {title, link, published, summary} entries."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    for item in root.iter("item"):
        entry: Dict = {}
        for child in item:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("title", "link", "description", "pubDate", "dc:date", "guid"):
                entry[tag] = (child.text or "").strip()
        if entry.get("title") or entry.get("link"):
            items.append({
                "id": entry.get("link") or entry.get("guid") or entry.get("title", ""),
                "title": entry.get("title", "(untitled)"),
                "link": entry.get("link", ""),
                "published": entry.get("pubDate", ""),
                "summary": entry.get("description", ""),
            })
        if len(items) >= limit:
            break
    return items


def fetch_news(limit: int = 10, use_cache: bool = True) -> List[Dict]:
    """Return the latest Arch Linux news. Uses a cache when stale/no net.

    Falls back to cached data if the network request fails.
    """
    xml_text = ""
    if use_cache and os.path.exists(NEWS_CACHE):
        try:
            with open(NEWS_CACHE, "r", encoding="utf-8") as f:
                xml_text = f.read()
        except Exception:
            xml_text = ""
    try:
        fresh = _fetch_news_xml()
        if fresh:
            xml_text = fresh
            try:
                os.makedirs(os.path.dirname(NEWS_CACHE), exist_ok=True)
                with open(NEWS_CACHE, "w", encoding="utf-8") as f:
                    f.write(fresh)
            except Exception:
                pass
    except Exception:
        pass
    items = _parse_news(xml_text, limit)
    if not items and not xml_text:
        return []
    return items


# ──────────────────────────────────────────────────────────────────────────
# News read-tracking
# ──────────────────────────────────────────────────────────────────────────

def _load_seen() -> Dict[str, str]:
    """Load the seen map: entry id -> ISO timestamp."""
    try:
        with open(NEWS_SEEN_CACHE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_seen(data: Dict[str, str]) -> None:
    try:
        os.makedirs(os.path.dirname(NEWS_SEEN_CACHE), exist_ok=True)
        with open(NEWS_SEEN_CACHE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _news_id(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("id") or entry.get("link") or entry.get("title") or "")
    return str(entry)


def mark_news_seen(entry) -> bool:
    """Mark a news entry as read, persisting alongside the RSS cache."""
    import time as _time
    key = _news_id(entry)
    if not key:
        return False
    seen = _load_seen()
    seen[key] = _time.strftime("%Y-%m-%d %H:%M:%S")
    _save_seen(seen)
    return True


def news_seen(entry) -> bool:
    """True when a news entry has been marked as read."""
    key = _news_id(entry)
    if not key:
        return False
    return key in _load_seen()


def news_seen_status(entries: List[Dict]) -> List[Dict]:
    """Return `entries` with an added `seen` boolean on each."""
    seen = _load_seen()
    out = []
    for entry in entries:
        item = dict(entry)
        item["seen"] = _news_id(item) in seen
        out.append(item)
    return out


def news_unseen_count(limit: int = 50) -> int:
    """Number of recent news entries not yet read."""
    return sum(1 for e in fetch_news(limit) if not news_seen(e))
