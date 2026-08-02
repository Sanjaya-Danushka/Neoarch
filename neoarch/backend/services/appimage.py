"""Managed AppImage store.

Installs AppImages into a NeoArch-managed directory, extracts name/icon/
desktop metadata from the archive, registers desktop entries, tracks
versions in a JSON database, and checks for updates from a static URL or
from GitHub/GitLab/Codeberg/Forgejo releases.

Everything is pure-stdlib so the service runs headless and is shared by
the GUI and the CLI.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from glob import glob
from typing import Dict, List, Optional

__all__ = [
    "APPIMAGE_DIR", "METADATA_PATH", "DESKTOP_DIR", "ICON_DIR",
    "list_appimages", "add_from_file", "add_from_url", "add_from_repo",
    "remove_appimage", "check_update", "check_all_updates",
    "install_update", "sync_from_disk",
]

BASE_STORE = os.path.join(os.path.expanduser("~"), ".local", "share", "neoarch")
APPIMAGE_DIR = os.path.join(BASE_STORE, "appimages")
ICON_DIR = os.path.join(APPIMAGE_DIR, "icons")
METADATA_PATH = os.path.join(APPIMAGE_DIR, "metadata.json")
DESKTOP_DIR = os.path.expanduser("~/.local/share/applications")

REPO_HOSTS = ("github", "gitlab", "codeberg", "forgejo")

_APPIMAGE_SUFFIXES = (".AppImage", ".appimage")
_UA = "neoarch-appimage-manager/2.2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────

def _load_db() -> List[Dict]:
    try:
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_db(entries: List[Dict]) -> None:
    os.makedirs(APPIMAGE_DIR, exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def _make_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "appimage"


def _parse_version_from_name(filename: str) -> Optional[str]:
    """Extract a semver-ish version from an AppImage filename."""
    m = re.search(r"(?i)(\d+\.\d+(?:\.\d+)*)", os.path.basename(filename))
    return m.group(1) if m else None


# ──────────────────────────────────────────────────────────────────────────
# AppImage introspection
# ──────────────────────────────────────────────────────────────────────────

def _extract_metadata(path: str, icon_dest_dir: str = "") -> Dict:
    """Read name/icon/desktop data from an AppImage without executing it.

    Uses the AppImage's `--appimage-extract` self-extraction into a
    scratch directory, then parses the embedded .desktop file. Returns
    {name, icon_inside, desktop}. Best effort — never raises.

    When `icon_dest_dir` is given and an icon is found, the icon is copied
    into that directory (the extraction scratch dir is deleted afterwards,
    so a returned path must live elsewhere) and the copied path returned.
    """
    result = {"name": None, "icon_inside": None, "desktop": None}
    workdir = tempfile.mkdtemp(prefix="neoarch_appimg_")
    try:
        subprocess.run([path, "--appimage-extract"], cwd=workdir,
                       capture_output=True, timeout=120)
        desktop_files = glob(os.path.join(workdir, "squashfs-root", "*.desktop"))
        desktop_files += glob(os.path.join(workdir, "squashfs-root", "**", "*.desktop"),
                              recursive=True)
        if not desktop_files:
            return result
        desktop = desktop_files[0]
        with open(desktop, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        name = re.search(r"(?m)^Name\s*=\s*(.+)$", text)
        icon = re.search(r"(?m)^Icon\s*=\s*(.+)$", text)
        result["desktop"] = text
        if name:
            result["name"] = name.group(1).strip()
        if icon:
            icon_path = _find_icon(workdir, icon.group(1).strip())
            if icon_path and icon_dest_dir:
                try:
                    os.makedirs(icon_dest_dir, exist_ok=True)
                    ext = os.path.splitext(icon_path)[1] or ".png"
                    dest = os.path.join(
                        icon_dest_dir,
                        f"appimg-{os.getpid()}-{int(time.time() * 1000)}{ext}")
                    shutil.copy2(icon_path, dest)
                    icon_path = dest
                except Exception:
                    icon_path = None
            result["icon_inside"] = icon_path
    except Exception:
        pass
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return result


def _find_icon(workdir: str, icon_name: str) -> Optional[str]:
    """Locate an icon file inside an extracted AppImage."""
    candidates = [
        os.path.join(workdir, "squashfs-root", "usr", "share", "icons",
                     "hicolor", "256x256", "apps", f"{icon_name}.png"),
        os.path.join(workdir, "squashfs-root", "usr", "share", "icons",
                     "hicolor", "128x128", "apps", f"{icon_name}.png"),
        os.path.join(workdir, "squashfs-root", "usr", "share", "icons",
                     "hicolor", "64x64", "apps", f"{icon_name}.png"),
        os.path.join(workdir, "squashfs-root", f"{icon_name}.png"),
        os.path.join(workdir, "squashfs-root", f"{icon_name}.svg"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    found = glob(os.path.join(workdir, "squashfs-root", "**",
                              f"{icon_name}.*"), recursive=True)
    return found[0] if found else None


def _desktop_entry_text(app_id: str, name: str, bin_path: str,
                        icon_path: str = "") -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={name}",
        f"Exec={bin_path}",
        "Terminal=false",
        "Categories=Utility;",
        "X-NeoArch-AppImage=true",
    ]
    if icon_path:
        lines.append(f"Icon={icon_path}")
    return "\n".join(lines) + "\n"


def _register_desktop(app_id: str, entry: Dict) -> Optional[str]:
    """Write a .desktop file for a managed AppImage. Returns its path."""
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    desktop_path = os.path.join(DESKTOP_DIR, f"neoarch-{app_id}.desktop")
    text = _desktop_entry_text(app_id, entry.get("name", app_id),
                               entry.get("bin_path", ""),
                               entry.get("icon_path", ""))
    try:
        with open(desktop_path, "w") as f:
            f.write(text)
        return desktop_path
    except Exception:
        return None


def _unregister_desktop(app_id: str) -> None:
    try:
        os.remove(os.path.join(DESKTOP_DIR, f"neoarch-{app_id}.desktop"))
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────
# Install
# ──────────────────────────────────────────────────────────────────────────

def _base_display_name(path: str) -> str:
    """Derive a clean name from an AppImage filename, stripping the
    trailing version/arch token (e.g. 'Obsidian-1.5.12-x86_64')."""
    base = os.path.splitext(os.path.basename(path))[0]
    for pattern in (r"^(.*)-\d+\.\d+(?:\.\d+)*-[A-Za-z0-9_]+$",
                    r"^(.*)-\d+\.\d+(?:\.\d+)*$"):
        m = re.search(pattern, base)
        if m and m.group(1):
            return m.group(1)
    return base


def add_from_file(path: str, name: Optional[str] = None) -> Dict:
    """Install an AppImage file into the managed store.

    Copies the binary, extracts metadata, registers a desktop entry, and
    records the entry in the database. Returns the new DB entry.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    base_name = name or _base_display_name(path)
    app_id = _make_id(base_name)
    os.makedirs(APPIMAGE_DIR, exist_ok=True)
    os.makedirs(ICON_DIR, exist_ok=True)

    bin_path = os.path.join(APPIMAGE_DIR, f"{app_id}.AppImage")
    shutil.copy2(path, bin_path)
    os.chmod(bin_path, os.stat(bin_path).st_mode | 0o111)

    os.makedirs(ICON_DIR, exist_ok=True)
    meta = _extract_metadata(bin_path, icon_dest_dir=ICON_DIR)
    display_name = meta.get("name") or base_name

    icon_path = ""
    if meta.get("icon_inside"):
        ext = os.path.splitext(meta["icon_inside"])[1] or ".png"
        final_icon = os.path.join(ICON_DIR, f"{app_id}{ext}")
        try:
            if os.path.abspath(meta["icon_inside"]) != os.path.abspath(final_icon):
                shutil.move(meta["icon_inside"], final_icon)
            icon_path = final_icon
        except Exception:
            icon_path = ""

    entries = [e for e in _load_db() if e.get("id") != app_id]
    entry = {
        "id": app_id,
        "name": display_name,
        "version": _parse_version_from_name(path) or "",
        "source_type": "file",
        "source": path,
        "host": None,
        "owner": None,
        "repo": None,
        "bin_path": bin_path,
        "icon_path": icon_path,
        "installed_at": _now(),
        "latest_version": None,
        "latest_url": None,
        "last_check": None,
    }
    entry["desktop_path"] = _register_desktop(app_id, entry)
    entries.append(entry)
    _save_db(entries)
    return entry


def _download(url: str, dest: str, timeout: int = 120) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, \
                open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)
        return True
    except Exception:
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except Exception:
            pass
        return False


def add_from_url(name: str, url: str) -> Dict:
    """Download an AppImage from a URL and install it."""
    if not url.lower().endswith(_APPIMAGE_SUFFIXES):
        raise ValueError(f"URL does not look like an AppImage: {url}")
    os.makedirs(APPIMAGE_DIR, exist_ok=True)
    tmp = os.path.join(APPIMAGE_DIR, f".download-{_make_id(name)}")
    try:
        if not _download(url, tmp):
            raise RuntimeError(f"Failed to download {url}")
        entry = add_from_file(tmp, name=name)
        entry.update({
            "source_type": "url",
            "source": url,
            "version": _parse_version_from_name(url) or entry.get("version"),
        })
        _update_entry(entry["id"], {
            "source_type": "url",
            "source": url,
            "version": entry["version"],
        })
        return entry
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────
# Repo releases (update source detection)
# ──────────────────────────────────────────────────────────────────────────

def _release_api(host: str, owner: str, repo: str) -> Optional[str]:
    if host == "github":
        return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    if host == "gitlab":
        return (f"https://gitlab.com/api/v4/projects/"
                f"{urllib.parse.quote(f'{owner}/{repo}', safe='')}"
                f"/releases/permalink/latest")
    if host in ("codeberg", "forgejo"):
        base = "codeberg.org" if host == "codeberg" else host
        return f"https://{base}/api/v1/repos/{owner}/{repo}/releases/latest"
    return None


def _latest_release(host: str, owner: str, repo: str) -> Dict:
    """Return {tag, url} for the latest AppImage release asset."""
    api = _release_api(host, owner, repo)
    if not api:
        return {}
    req = urllib.request.Request(api, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}

    tag = data.get("tag_name", "")
    assets = data.get("assets", []) or []
    candidates = []
    for asset in assets:
        for key in ("browser_download_url", "url", "name"):
            value = asset.get(key)
            if isinstance(value, str) and value.lower().endswith(_APPIMAGE_SUFFIXES):
                url = value
                if key == "name":
                    url = (f"https://github.com/{owner}/{repo}/releases/"
                           f"download/{tag}/{value}")
                candidates.append(url)
    if host == "gitlab" and not candidates:
        for link in (data.get("assets", {}).get("links", []) or []):
            url = link.get("url", "")
            if url.lower().endswith(_APPIMAGE_SUFFIXES):
                candidates.append(url)
    return {"tag": tag, "url": candidates[0] if candidates else ""}


def add_from_repo(name: str, owner: str, repo: str, host: str = "github") -> Dict:
    """Install the latest AppImage release from a repo."""
    if host not in REPO_HOSTS:
        raise ValueError(f"Unsupported host: {host}")
    info = _latest_release(host, owner, repo)
    if not info.get("url"):
        raise RuntimeError(
            f"No AppImage asset found in latest release of {owner}/{repo}")
    entry = add_from_url(name, info["url"])
    _update_entry(entry["id"], {
        "source_type": "repo",
        "host": host,
        "owner": owner,
        "repo": repo,
        "version": _clean_tag(info.get("tag", "")) or entry.get("version"),
    })
    return next(e for e in _load_db() if e.get("id") == entry["id"])


def _clean_tag(tag: str) -> str:
    return tag.lstrip("vV") if tag else ""


# ──────────────────────────────────────────────────────────────────────────
# Update checks
# ──────────────────────────────────────────────────────────────────────────

def _update_entry(app_id: str, fields: Dict) -> None:
    entries = _load_db()
    for e in entries:
        if e.get("id") == app_id:
            e.update(fields)
            break
    _save_db(entries)


def _check_static_url(entry: Dict) -> Dict:
    """Best-effort version check for a static URL source."""
    version = _parse_version_from_name(entry.get("source", "")) or ""
    return {
        "latest_version": version or None,
        "latest_url": entry.get("source"),
        "last_check": _now(),
    }


def check_update(app_id: str) -> Optional[Dict]:
    """Check for a newer version of a managed AppImage.

    Repo sources query the latest release; static URLs parse the
    filename. Returns the updated entry, or None if unknown.
    """
    entry = next((e for e in _load_db() if e.get("id") == app_id), None)
    if not entry:
        return None
    if entry.get("source_type") == "repo" and entry.get("owner"):
        info = _latest_release(entry["host"], entry["owner"], entry["repo"])
        latest = _clean_tag(info.get("tag", ""))
        fields = {
            "latest_version": latest or None,
            "latest_url": info.get("url") or None,
            "last_check": _now(),
        }
    else:
        fields = _check_static_url(entry)
    _update_entry(app_id, fields)
    entry.update(fields)
    return entry


def check_all_updates() -> List[Dict]:
    """Run update checks for every managed AppImage."""
    results = []
    for entry in _load_db():
        updated = check_update(entry["id"])
        if updated:
            results.append(updated)
    return results


def _is_newer(latest: str, current: str) -> bool:
    """Compare two versions; returns True if latest > current."""
    def segs(v: str):
        return [int(p) for p in re.findall(r"\d+", v) or ["0"]]

    la, ca = segs(latest), segs(current)
    for x, y in zip(la, ca):
        if x != y:
            return x > y
    return len(la) > len(ca)


def install_update(app_id: str) -> bool:
    """Download and install the newest version of a managed AppImage."""
    entry = check_update(app_id)
    if not entry or not entry.get("latest_url"):
        return False
    if not _is_newer(entry.get("latest_version", ""), entry.get("version", "")):
        return False
    tmp = os.path.join(APPIMAGE_DIR, f".update-{app_id}")
    try:
        if not _download(entry["latest_url"], tmp):
            return False
        shutil.copy2(tmp, entry["bin_path"])
        os.chmod(entry["bin_path"], os.stat(entry["bin_path"]).st_mode | 0o111)
        _update_entry(app_id, {
            "version": entry.get("latest_version") or entry.get("version"),
            "latest_version": None,
            "latest_url": None,
        })
        return True
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────
# Removal & sync
# ──────────────────────────────────────────────────────────────────────────

def remove_appimage(app_id: str) -> bool:
    """Remove an AppImage, its desktop entry, icon, and DB record."""
    entries = _load_db()
    entry = next((e for e in entries if e.get("id") == app_id), None)
    if not entry:
        return False
    _unregister_desktop(app_id)
    for p in (entry.get("bin_path"), entry.get("icon_path")):
        if p:
            try:
                os.remove(p)
            except Exception:
                pass
    _save_db([e for e in entries if e.get("id") != app_id])
    return True


def sync_from_disk() -> List[Dict]:
    """Reconcile the DB with the filesystem.

    Removes records whose binary has vanished and returns the current
    list. (Binaries present but unregistered are not auto-imported —
    use add_from_file for those.)
    """
    entries = [e for e in _load_db()
               if os.path.isfile(e.get("bin_path", "/nonexistent"))]
    _save_db(entries)
    return entries


def list_appimages() -> List[Dict]:
    """Return the managed AppImage database."""
    return _load_db()
