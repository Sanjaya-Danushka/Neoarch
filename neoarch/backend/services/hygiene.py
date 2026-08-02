"""System hygiene services.

Provides orphaned-package cleanup, .pacnew file management, and the
Arch Linux news feed. Each service is safe to call from the UI layer
and uses the same auth/elevation helpers as the rest of the app.
"""

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from threading import Thread
from typing import List, Dict, Optional

from neoarch.backend.auth import get_auth_command
from neoarch.backend.workers import CommandWorker

__all__ = [
    "list_orphans", "remove_orphans",
    "list_pacnew", "diff_pacnew", "accept_pacnew", "delete_pacnew",
    "fetch_news", "news_cache", "news_cache_age",
]

NEWS_URL = "https://archlinux.org/feeds/news/"
NEWS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "news.xml")
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
            shutil_copy(info["original"], backup)
        result = _run_sudo(["cp", path, info["original"]])
        if result.returncode == 0:
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def delete_pacnew(path: str) -> bool:
    """Delete a .pacnew file without touching the original."""
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def shutil_copy(src: str, dst: str):
    import shutil
    shutil.copy2(src, dst)


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
    req = urllib.request.Request(NEWS_URL, headers={"User-Agent": "neoarch/2.2"})
    with urllib.request.urlopen(req, timeout=15) as resp:
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
