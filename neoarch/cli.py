"""NeoArch command-line interface.

A scriptable frontend for the NeoArch package-management backend. Runs
without a display server and reuses the pure (Qt-free) service modules
so logic stays consistent with the GUI.

Usage:
    python -m neoarch.cli <command> [options]

Commands:
    search        Search pacman/AUR/Flatpak repositories
    install       Install packages (pacman with AUR/URL fallback)
    remove        Remove installed packages
    upgrade       Upgrade all sources or a specific source
    update        Update specific packages
    list          List installed packages
    list-updates  List available updates
    ignore        Manage the ignored-updates list
    news          Read the latest Arch Linux news
    backup        Create/list/restore system backups
    purge         Remove orphans, stale cache, and .pacnew files
    config        Get/set NeoArch configuration values
    marks         Manage IgnorePkg/HoldPkg marks and install reasons
    downgrade     Install an older cached version of a package
    appimage      Manage AppImage applications (add/update/remove)
    scan          Scan a PKGBUILD for security risks
    keyring       Manage the pacman keyring
    purify        Remove corrupted archives and unused runtimes
    restart       Check whether a reboot is recommended
    parallel      Show/set ParallelDownloads in /etc/pacman.conf
    schedule      Show/configure the weekly update schedule
    recommend     Curated package recommendations
    install-url   Install a package archive from an HTTP(S) URL
    aur-build     Clone and build an AUR package (chroot/check/commit)
    doctor        Check the system for missing prerequisites

Short aliases (also available as `neo`):
    updates = list-updates      down = downgrade    hold = marks
    keys  = keyring             reboot = restart    build = aur-build
    clean orphans/cache/corrupt/flatpak/merge  (purge/purify shortcuts)
    install <package> finds AUR packages automatically
    install <https://...> installs a package archive from a URL
    backup defaults to creating a backup      schedule defaults to show
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

from neoarch.resources.paths import APP_NAME, APP_VERSION
from neoarch.backend.services import search as search_service
from neoarch.backend import sys_utils
from neoarch.backend.config_utils import (
    get_ignore_file_path,
    load_ignored_updates,
    save_ignored_updates,
)

__all__ = ["main"]


# ──────────────────────────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────────────────────────

def _emit(data, as_json: bool):
    """Print data as JSON (--json) or in a readable table/text format."""
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    elif isinstance(data, list):
        if data and all(isinstance(item, dict) for item in data):
            print(_render_table(data))
        else:
            for item in data:
                if isinstance(item, dict):
                    print(_fmt_dict(item))
                else:
                    print(item)
    elif isinstance(data, dict):
        print(_fmt_dict(data))
    else:
        print(data)


_COLUMN_ORDER = (
    "name", "pkg", "id", "title",
    "version",
    "repo", "source", "provider", "category", "action", "status",
    "desc", "summary", "message", "updated", "published",
)

_LABELS = {
    "name": "NAME", "pkg": "PACKAGE", "id": "ID", "title": "TITLE",
    "version": "VERSION",
    "repo": "REPO", "source": "SOURCE", "provider": "PROVIDER",
    "category": "CATEGORY", "action": "ACTION", "status": "STATUS",
    "desc": "DESCRIPTION", "summary": "SUMMARY", "message": "MESSAGE",
    "updated": "UPDATED", "published": "PUBLISHED",
}


def _render_table(rows: List[Dict]) -> str:
    """Render a list of record dicts as aligned columns or compact lines.

    Wide terminals get a full aligned table with headers; narrow terminals get
    a compact, yay-style layout so lines never squeeze into single-word wraps.
    ANSI colors are added only when stdout is a TTY and NO_COLOR is unset.
    """
    def text(row, key) -> str:
        value = row.get(key)
        if value is None:
            return ""
        return str(value).replace("\t", " ").split("\n")[0].strip()

    def color(s: str, code: int) -> str:
        if (not sys.stdout.isatty()) or os.environ.get("NO_COLOR"):
            return s
        return f"\x1b[{code}m{s}\x1b[0m"

    present = {key for row in rows for key in row}
    present = {key for key in present if any(text(row, key) for row in rows)}
    keys = [k for k in _COLUMN_ORDER if k in present]
    keys += [k for k in sorted(present - set(_COLUMN_ORDER))]
    if not keys:
        return ""

    # Description-ish columns always land last so the wide column is the end one.
    desc_keys = {"desc", "summary", "message"}
    detail = next((k for k in keys if k in desc_keys), None)
    if detail:
        keys = [k for k in keys if k != detail] + [detail]

    term_cols = max(shutil.get_terminal_size((100, 24)).columns, 40)
    gap = 3
    padding = 2  # left indent

    meta = keys[:-1] if detail else keys

    # ── Compact layout for narrow terminals ──────────────────────────────
    if term_cols < 100:
        lines = []
        for row in rows:
            if meta:
                name = text(row, meta[0])
                cells = [color(name, 1)]
                for k in meta[1:]:
                    v = text(row, k)
                    if not v:
                        continue
                    cells.append(color(v, 36 if k == "version" else 33))
                head = "  " + "  ".join(cells)
                if len(head) <= term_cols:
                    lines.append(head)
                else:
                    lines.append(" " * padding + color(name, 1))
                    for k in meta[1:]:
                        v = text(row, k)
                        if v:
                            lines.append(" " * (padding + padding) + color(v, 36 if k == "version" else 33))
            else:
                lines.append(" " * padding + color(text(row, keys[0]), 1))
            if detail:
                desc = text(row, detail)
                if desc:
                    lines.extend(" " * 4 + segment for segment in textwrap.wrap(desc, width=max(term_cols - 4, 24)))
        return "\n".join(lines)

    # ── Full aligned table for wide terminals ─────────────────────────────
    widths = {}
    for key in meta:
        w = max((len(text(row, key)) for row in rows), default=0)
        widths[key] = min(w, 28)
    fixed = sum(widths.values()) + gap * (len(keys) - 1) + padding
    widths[detail or keys[-1]] = max(term_cols - fixed, 24)

    starts = {}
    offset = padding
    for key in keys:
        starts[key] = offset
        offset += widths[key] + gap

    def chop(s: str, width: int) -> List[str]:
        """Word-wrap to width, falling back to hard breaks for long tokens."""
        parts = textwrap.wrap(s, width=width)
        out = []
        for part in parts:
            if len(part) > width:
                out.extend(part[i : i + width] for i in range(0, len(part), width))
            else:
                out.append(part)
        return out or [s[:width]]

    def cell_color(key: str) -> int:
        if key == keys[0]:
            return 1
        if key == "version":
            return 36
        if key in ("source", "repo", "category"):
            return 33
        return 0

    lines = []
    if len(keys) > 1:
        head = [(_LABELS.get(k, k.upper())).ljust(widths[k]) for k in keys]
        lines.append(" " * padding + (" " * gap).join(head).rstrip())
    for row in rows:
        cells = []
        continuations: List[str] = []
        for key in keys:
            s = color(text(row, key), cell_color(key))
            w = widths[key]
            if len(s) > w:
                chunks = chop(text(row, key), w - 1)
                cells.append(color(chunks[0] + "…", cell_color(key)))
                for chunk in chunks[1:]:
                    continuations.append(" " * starts[key] + chunk)
            else:
                cells.append(s)
        lines.append(" " * padding + (" " * gap).join(c.ljust(widths[k]) for k, c in zip(keys, cells)).rstrip())
        lines.extend(continuations)
    return "\n".join(lines)


def _fmt_dict(d: Dict) -> str:
    parts = []
    for key in ("name", "pkg", "id", "title"):
        if d.get(key):
            parts.append(str(d[key]))
            break
    for key in ("version", "desc", "summary", "repo", "source", "published"):
        if d.get(key):
            parts.append(str(d[key]))
    return "  ".join(parts)


def _confirm(prompt: str, default_yes: bool = False) -> bool:
    """Ask for confirmation unless --yes/--no-confirm was passed."""
    if default_yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────────────────────────────────
# Command runners
# ──────────────────────────────────────────────────────────────────────────

def _run(cmd: List[str], timeout: int = 600, sudo: bool = False, check: bool = False) -> subprocess.CompletedProcess:
    """Run a command, optionally elevated, with captured output."""
    full = (["sudo"] if sudo else []) + cmd
    try:
        result = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        print(f"error: command not found: {cmd[0]}", file=sys.stderr)
        return subprocess.CompletedProcess(full, 127, "", "")
    if check and result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        print(f"error: {' '.join(cmd)} failed: {msg}", file=sys.stderr)
        sys.exit(result.returncode)
    return result


def _stream(cmd: List[str], sudo: bool = False, check: bool = False) -> int:
    """Run a command with live output; returns the exit code."""
    full = (["sudo"] if sudo else []) + cmd
    print(f"[neoarch] $ {' '.join(full)}", file=sys.stderr)
    try:
        result = subprocess.run(full)
        if check and result.returncode != 0:
            sys.exit(result.returncode)
        return result.returncode
    except FileNotFoundError:
        print(f"error: command not found: {cmd[0]}", file=sys.stderr)
        return 127


# ── search ────────────────────────────────────────────────────────────────

def cmd_search(args) -> None:
    query = " ".join(args.query)
    if not query.strip():
        print("error: search requires a query", file=sys.stderr)
        sys.exit(1)
    specs = search_service.search_live_packages(query, args.limit)
    if args.flatpak:
        specs = _search_flatpak(query, args.limit)
    elif args.aur:
        specs = search_service.search_aur(query, args.limit)
    elif args.pacman:
        specs = search_service.search_pacman(query, args.limit)
    if not specs:
        print("No results found.")
        return
    if args.json:
        _emit(specs, True)
        return
    rows = []
    for spec in specs:
        row = {
            "name": spec.get("name") or spec.get("pkg"),
            "source": spec.get("source"),
        }
        for key in ("version", "repo", "installed"):
            if spec.get(key) is not None:
                row[key] = spec[key]
        if spec.get("desc"):
            row["desc"] = spec["desc"]
        rows.append(row)
    _emit(rows, False)


def _search_flatpak(query: str, limit: int) -> List[Dict]:
    if not shutil.which("flatpak"):
        return []
    result = _run(["flatpak", "search", "--columns=application,version,description", query], timeout=60)
    specs = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            specs.append({
                "name": parts[0],
                "version": parts[1],
                "desc": parts[2] if len(parts) > 2 else "",
                "source": "flatpak",
            })
        if len(specs) >= limit:
            break
    return specs


# ── install ───────────────────────────────────────────────────────────────

def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def cmd_install(args) -> None:
    if not args.packages:
        print("error: install requires at least one package", file=sys.stderr)
        sys.exit(1)

    no_confirm = args.no_confirm or args.yes

    urls = [p for p in args.packages if _is_url(p)]
    packages = [p for p in args.packages if not _is_url(p)]

    for url in urls:
        from neoarch.backend.services import install_url
        if install_url.install_from_url(url):
            print(f"Installed {url}.")
        else:
            print(f"Failed to install from URL: {url}", file=sys.stderr)
            sys.exit(1)
    if not packages:
        return

    if not args.aur and not args.flatpak and not args.npm:
        target = "pacman"
    else:
        target = "aur" if args.aur else ("flatpak" if args.flatpak else "npm")

    if target == "pacman":
        cmd = ["pacman", "-S"] + (["--noconfirm"] if no_confirm else []) + packages
        code = _stream(cmd, sudo=True, check=False)
        if code != 0:
            helper = sys_utils.get_aur_helper()
            if helper:
                print("[neoarch] not found in official repos; trying AUR helper...",
                      file=sys.stderr)
                _stream([helper, "-S"] + (["--noconfirm"] if no_confirm else []) + packages,
                        check=True)
            else:
                sys.exit(code)
    elif target == "aur":
        helper = sys_utils.get_aur_helper()
        if not helper:
            print("error: no AUR helper available (install yay/paru)", file=sys.stderr)
            sys.exit(1)
        cmd = [helper, "-S"] + packages
        if no_confirm:
            cmd.insert(1, "--noconfirm")
        _stream(cmd, check=True)
    elif target == "flatpak":
        _stream(["flatpak", "install", "--user", "-y"] + packages, check=True)
    elif target == "npm":
        _stream(["npm", "install", "-g"] + packages, check=True)


# ── remove ────────────────────────────────────────────────────────────────

def cmd_remove(args) -> None:
    if not args.packages:
        print("error: remove requires at least one package", file=sys.stderr)
        sys.exit(1)
    if not args.yes and not args.no_confirm:
        if not _confirm(f"Remove {', '.join(args.packages)}?"):
            print("Aborted.")
            return
    cmd = ["pacman", "-R"]
    if args.cascade:
        cmd.append("-c")
    if args.keep_config:
        cmd.append("-n")
    cmd += ["--noconfirm"] if args.no_confirm or args.yes else []
    cmd += args.packages
    _stream(cmd, sudo=True, check=True)


# ── upgrade / update ──────────────────────────────────────────────────────

def cmd_upgrade(args) -> None:
    if args.flatpak:
        _stream(["flatpak", "update", "-y"], check=True)
        return
    if args.aur:
        helper = sys_utils.get_aur_helper()
        if not helper:
            print("error: no AUR helper available", file=sys.stderr)
            sys.exit(1)
        _stream([helper, "-Sua", "--noconfirm"], check=True)
        return
    if args.npm:
        _stream(["npm", "update", "-g"], check=True)
        return
    _stream(["pacman", "-Syu", "--noconfirm"], sudo=True, check=True)


def cmd_update(args) -> None:
    if not args.packages:
        print("error: update requires at least one package", file=sys.stderr)
        sys.exit(1)
    _stream(["pacman", "-S", "--noconfirm"] + args.packages, sudo=True, check=True)


# ── list ──────────────────────────────────────────────────────────────────

def _list_pacman(explicit_only: bool, foreign_only: bool, aur_only: bool) -> List[Dict]:
    if aur_only:
        cmd = ["pacman", "-Qqm"]
    elif explicit_only:
        cmd = ["pacman", "-Qqe"]
    elif foreign_only:
        cmd = ["pacman", "-Qm"]
    else:
        cmd = ["pacman", "-Q"]
    result = _run(cmd, timeout=60)
    packages = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            packages.append({"name": parts[0], "version": parts[1]})
    packages.sort(key=lambda p: p["name"])
    return packages


def cmd_list(args) -> None:
    if args.flatpak:
        result = _run(["flatpak", "list", "--app", "--columns=application,version"], timeout=60)
        items = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if parts:
                items.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else ""})
        _emit(items, args.json)
        return
    packages = _list_pacman(args.explicit, args.foreign, args.aur)
    if args.json:
        print(json.dumps(packages, indent=2))
    else:
        for p in packages:
            print(f"{p['name']} {p['version']}")


def cmd_list_updates(args) -> None:
    result = _run(["pacman", "-Qu"], timeout=60)
    updates = []
    for line in result.stdout.splitlines():
        if " -> " in line:
            left, right = line.split(" -> ", 1)
            parts = left.split()
            if parts:
                updates.append({
                    "name": parts[0],
                    "installed": parts[1] if len(parts) > 1 else "",
                    "available": right.strip(),
                    "source": "pacman",
                })
    if args.aur:
        helper = sys_utils.get_aur_helper()
        if helper:
            r = _run([helper, "-Qua"], timeout=60)
            for line in r.stdout.splitlines():
                if " -> " in line:
                    left, right = line.split(" -> ", 1)
                    parts = left.split()
                    if parts:
                        updates.append({
                            "name": parts[0],
                            "installed": parts[1] if len(parts) > 1 else "",
                            "available": right.strip(),
                            "source": "aur",
                        })
    if args.flatpak:
        r = _run(["flatpak", "list", "--app", "--updates", "--columns=application"], timeout=60)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line:
                updates.append({"name": line, "available": "", "source": "flatpak"})
    if args.json:
        print(json.dumps(updates, indent=2))
    elif updates:
        for u in updates:
            print(f"{u['name']}  {u['installed']} -> {u['available']}  [{u['source']}]")
    else:
        print("No updates available.")


# ── ignore ────────────────────────────────────────────────────────────────

def cmd_ignore(args) -> None:
    ignored = load_ignored_updates()
    if args.list or args.show:
        if args.json:
            print(json.dumps(sorted(ignored), indent=2))
        elif ignored:
            for name in sorted(ignored):
                print(name)
        else:
            print("No packages ignored.")
        return
    if args.remove:
        for name in args.remove:
            ignored.discard(name)
        save_ignored_updates(ignored)
        print(f"Unignored {len(args.remove)} package(s).")
        return
    if args.add:
        for name in args.add:
            ignored.add(name)
        save_ignored_updates(ignored)
        print(f"Ignored {len(args.add)} package(s).")
        return
    parser.print_help()


# ── news ──────────────────────────────────────────────────────────────────

_NEWS_URL = "https://archlinux.org/feeds/news/"
_NEWS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "news.xml")


def _fetch_news(limit: int) -> List[Dict]:
    xml_text = ""
    if os.path.exists(_NEWS_CACHE):
        try:
            with open(_NEWS_CACHE, "r", encoding="utf-8") as f:
                xml_text = f.read()
        except Exception:
            xml_text = ""
    try:
        import urllib.request
        req = urllib.request.Request(_NEWS_URL, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            fresh = resp.read().decode("utf-8")
        if fresh:
            xml_text = fresh
            try:
                os.makedirs(os.path.dirname(_NEWS_CACHE), exist_ok=True)
                with open(_NEWS_CACHE, "w", encoding="utf-8") as f:
                    f.write(fresh)
            except Exception:
                pass
    except Exception:
        pass
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.iter("item"):
        entry: Dict = {}
        for child in item:
            tag = child.tag.rsplit("}", 1)[-1]
            entry[tag] = (child.text or "").strip()
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


def cmd_news(args) -> None:
    from neoarch.backend.services import hygiene

    items = _fetch_news(args.limit)
    if not items:
        print("No news available (offline?).")
        return
    marked = hygiene.news_seen_status(items)
    if args.json:
        _emit(marked, True)
    else:
        for item in marked:
            tag = "[seen]" if item.get("seen") else "[new]"
            print(f"{tag} {item.get('title')}")
    if args.mark_read:
        for item in items:
            hygiene.mark_news_seen(item)
        print("Marked as read.")


# ── backup ────────────────────────────────────────────────────────────────

_BACKUP_DIR = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "backups")


def _list_backups() -> List[Dict]:
    if not os.path.isdir(_BACKUP_DIR):
        return []
    entries = []
    for name in sorted(os.listdir(_BACKUP_DIR), reverse=True):
        p = os.path.join(_BACKUP_DIR, name)
        if not os.path.isdir(p):
            continue
        info: Dict = {"path": p, "timestamp": name}
        pkg_file = os.path.join(p, "package-list.json")
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, "r") as f:
                    data = json.load(f)
                info["packages"] = {
                    k: len(v) for k, v in data.get("sources", {}).items()
                }
            except Exception:
                pass
        snap_file = os.path.join(p, "snapshots.txt")
        if os.path.exists(snap_file):
            snap = open(snap_file).read().strip()
            info["snapshot"] = None if snap == "none" else snap
        entries.append(info)
    return entries


def _create_backup() -> Dict:
    from neoarch.backend.services import backup as backup_service
    result = backup_service.create_backup()
    if isinstance(result, dict) and result.get("path"):
        return result
    raise RuntimeError("backup failed")


def cmd_backup(args) -> None:
    if args.create:
        print("Creating backup...")
        result = _create_backup()
        _emit(result, args.json)
        return
    if args.list or args.show:
        backups = _list_backups()
        if args.json:
            print(json.dumps(backups, indent=2))
        elif backups:
            for b in backups:
                pkgs = b.get("packages") or {}
                label = ", ".join(f"{k}={v}" for k, v in pkgs.items()) or "no package lists"
                print(f"{b['timestamp']}  {b['path']}  ({label})")
        else:
            print("No backups found.")
        return
    if args.restore:
        if not os.path.isdir(args.restore):
            print(f"error: backup not found: {args.restore}", file=sys.stderr)
            sys.exit(1)
        print("Restoring packages from backup...")
        from neoarch.backend.services import backup as backup_service
        ok = backup_service.restore_packages(args.restore)
        print("Restore completed." if ok else "Restore failed.")
        return
    parser.print_help()


# ── purge ─────────────────────────────────────────────────────────────────

def cmd_purge(args) -> None:
    from neoarch.backend.services import hygiene

    if args.orphans:
        orphans = hygiene.list_orphans()
        if not orphans:
            print("No orphaned packages.")
        else:
            print(f"{len(orphans)} orphaned package(s): {', '.join(orphans)}")
            if args.yes or args.no_confirm or _confirm("Remove orphans?"):
                _stream(["pacman", "-Rns", "--noconfirm"] + orphans, sudo=True, check=True)

    if args.cache:
        print("Cleaning package cache...")
        _stream(["pacman", "-Sc", "--noconfirm"], sudo=True, check=True)

    if args.pacnew:
        pacnews = hygiene.list_pacnew()
        if not pacnews:
            print("No .pacnew files.")
        elif args.json:
            _emit(pacnews, True)
        else:
            for p in pacnews:
                print(f"{p.get('package', 'unknown')}: {p.get('path')}")
            if args.yes or args.no_confirm or _confirm("Remove these .pacnew files?"):
                for p in pacnews:
                    hygiene.delete_pacnew(p.get("path", ""))
                print("Removed .pacnew files.")


# ── config ────────────────────────────────────────────────────────────────

_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "config.json")

_DEFAULTS = {
    "aur_helper": "auto",
    "force_sudo_flatpak": False,
    "force_sudo_npm": False,
    "check_updates_on_startup": True,
    "autoupdate_enabled": False,
    "autoupdate_interval_days": 7,
    "snapshot_before_update": False,
    "auto_clean_cache": False,
    "schedule_enabled": False,
    "schedule_days": [0, 1, 2, 3, 4, 5, 6],
    "schedule_time": "03:00",
    "culture": "en",
}


def _load_config() -> Dict:
    try:
        with open(_CONFIG_PATH, "r") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except Exception:
        return dict(_DEFAULTS)


def _save_config(data: Dict) -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def cmd_config(args) -> None:
    data = _load_config()
    if args.action == "get":
        if args.key is None:
            if args.json:
                _emit(data, True)
            else:
                for k, v in data.items():
                    print(f"{k} = {v}")
            return
        if args.key not in data:
            print(f"error: unknown key: {args.key}", file=sys.stderr)
            sys.exit(1)
        print(data[args.key])
    elif args.action == "set":
        if not args.key or args.value is None:
            print("usage: neoarch config set <key> <value>", file=sys.stderr)
            sys.exit(1)
        if args.key not in data:
            print(f"error: unknown key: {args.key}", file=sys.stderr)
            sys.exit(1)
        current = data[args.key]
        try:
            if isinstance(current, bool):
                data[args.key] = args.value.lower() in ("true", "1", "yes")
            elif isinstance(current, int):
                data[args.key] = int(args.value)
            elif isinstance(current, list):
                data[args.key] = [
                    int(t.strip()) for t in args.value.split(",") if t.strip()]
            else:
                data[args.key] = args.value
        except ValueError:
            print(f"error: cannot parse value for {args.key}", file=sys.stderr)
            sys.exit(1)
        _save_config(data)
        print(f"{args.key} = {data[args.key]}")
    elif args.action == "reset":
        _save_config(dict(_DEFAULTS))
        print("Configuration reset to defaults.")


# ── doctor ────────────────────────────────────────────────────────────────

def cmd_doctor(args) -> None:
    checks: List[Dict] = []
    missing = sys_utils.get_missing_dependencies()
    for dep in missing:
        checks.append({"check": f"dependency: {dep}", "ok": False, "message": "missing"})
    checks.append({"check": "pacman", "ok": sys_utils.cmd_exists("pacman"), "message": ""})
    for tool in ("git", "flatpak", "node", "npm", "docker"):
        checks.append({"check": tool, "ok": sys_utils.cmd_exists(tool), "message": ""})
    aur = sys_utils.get_aur_helper()
    checks.append({"check": "aur helper", "ok": aur is not None, "message": aur or "none installed"})
    pkgs = _list_pacman(False, False, False)
    checks.append({"check": "installed packages", "ok": True, "message": str(len(pkgs))})
    updates = _run(["pacman", "-Qu"], timeout=60).stdout.splitlines()
    checks.append({"check": "available updates", "ok": True, "message": str(len(updates))})
    backups = _list_backups()
    checks.append({"check": "backups", "ok": True, "message": str(len(backups))})

    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        all_ok = True
        for c in checks:
            mark = "ok" if c["ok"] else "FAIL"
            if not c["ok"]:
                all_ok = False
            extra = f" ({c['message']})" if c.get("message") else ""
            print(f"[{mark}] {c['check']}{extra}")
        print("System looks healthy." if all_ok else "Issues found — see FAIL entries above.")


# ── scan ──────────────────────────────────────────────────────────────────

def cmd_scan(args) -> None:
    from neoarch.backend.services import security_scan

    findings: List[Dict] = []
    for path in args.paths:
        result = security_scan.findings_for_file(path)
        if not result and not os.path.isfile(path):
            print(f"error: '{path}' is not a readable file", file=sys.stderr)
            raise SystemExit(1)
        for f in result:
            f["file"] = path
        findings.extend(result)

    if args.json:
        print(json.dumps(findings, indent=2))
        return

    if not findings:
        print("No security issues found.")
        return

    by_severity = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        by_severity[f.get("severity", "info")] = \
            by_severity.get(f.get("severity", "info"), 0) + 1
        loc = f.get("file", "?")
        if f.get("line"):
            loc += f":{f['line']}"
        print(f"[{f.get('severity', 'info'):>8}] {loc}")
        print(f"          {f['rule']}: {f['detail']}")
        if f.get("matched"):
            print(f"          > {f['matched']}")
    print(f"\n{len(findings)} finding(s): "
          f"{by_severity.get('critical', 0)} critical, "
          f"{by_severity.get('warning', 0)} warning, "
          f"{by_severity.get('info', 0)} info")

    if by_severity.get("critical"):
        raise SystemExit(2)


# ── downgrade ──────────────────────────────────────────────────────────────

def cmd_downgrade(args) -> None:
    from neoarch.backend.services import downgrade

    versions = downgrade.list_cached_versions(args.package)
    if not versions:
        print(f"No cached versions of '{args.package}' found.")
        return

    if args.json:
        _emit([
            {"name": v["name"], "version": v["version"], "epoch": v["epoch"],
             "release": v["release"], "arch": v["arch"], "file": v["file"]}
            for v in versions
        ], True)
        return

    print(f"Cached versions of {args.package}:")
    for i, v in enumerate(versions, start=1):
        print(f"  {i:>3}. {v['epoch']}:{v['version']}-{v['release']} "
              f"[{v['arch']}]")

    if args.pin:
        if downgrade.add_to_ignorepkg(args.package):
            print(f"Pinned '{args.package}' to IgnorePkg — pacman will keep "
                  "it at the downgraded version.")
        else:
            print("Failed to update IgnorePkg (need root).", file=sys.stderr)

    if args.list_only:
        return

    selected = None
    if args.version:
        selected = downgrade.resolve_cache_path(args.package, args.version)
        if not selected:
            print(f"Version '{args.version}' not in cache.", file=sys.stderr)
            raise SystemExit(1)
    else:
        print("\nChoose a version to install (or Ctrl-C to cancel):")
        try:
            choice = input(f"[1-{len(versions)}] ")
        except (EOFError, KeyboardInterrupt):
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(versions)):
            print("Invalid choice.", file=sys.stderr)
            raise SystemExit(1)
        selected = versions[int(choice) - 1]["path"]

    if args.yes or args.no_confirm or _confirm(
            f"Downgrade {args.package}? This may replace config files."):
        downgrade.install_version(args.package, path=selected)


# ── marks ─────────────────────────────────────────────────────────────────

def cmd_marks(args) -> None:
    from neoarch.backend.services import marks

    if args.action == "list":
        ignore = marks.get_ignorepkg()
        hold = marks.get_holdpkg()
        if args.json:
            print(json.dumps({"ignorepkg": ignore, "holdpkg": hold}, indent=2))
        else:
            print("IgnorePkg:", ", ".join(ignore) if ignore else "(none)")
            print("HoldPkg:   ", ", ".join(hold) if hold else "(none)")
        return

    pkg = args.package
    if args.action in ("ignore", "unignore", "hold", "unhold"):
        op = {
            "ignore": marks.add_ignorepkg,
            "unignore": marks.remove_ignorepkg,
            "hold": marks.add_holdpkg,
            "unhold": marks.remove_holdpkg,
        }[args.action]
        if op(pkg):
            print(f"{args.action.capitalize()}d '{pkg}'.")
        else:
            print(f"Failed to update marks for '{pkg}' (need root).", file=sys.stderr)
            raise SystemExit(1)
    elif args.action == "reason":
        if args.reason:
            if marks.set_install_reason(pkg, args.reason):
                print(f"'{pkg}' marked as {args.reason}.")
            else:
                print(f"Failed to set reason for '{pkg}' (need root).", file=sys.stderr)
                raise SystemExit(1)
        else:
            current = marks.get_install_reason(pkg)
            if args.json:
                print(json.dumps({"package": pkg, "reason": current}, indent=2))
            else:
                print(f"{pkg}: {current or 'not installed'}")


# ── appimage ──────────────────────────────────────────────────────────────

def cmd_appimage(args) -> None:
    from neoarch.backend.services import appimage as svc

    action = args.action
    if action == "list":
        entries = svc.list_appimages()
        if args.json:
            _emit(entries, True)
        elif not entries:
            print("No managed AppImages.")
        else:
            for e in entries:
                upd = ""
                if e.get("latest_version") and \
                        e.get("latest_version") != e.get("version"):
                    upd = f"  -> {e['latest_version']}"
                print(f"{e['id']:>20}  {e.get('name', '')}"
                      f"  {e.get('version', '')}{upd}")
        return

    if action == "add":
        try:
            e = svc.add_from_file(args.file)
            print(f"Installed '{e['name']}' ({e['id']}) "
                  f"v{e.get('version') or '?'}.")
        except FileNotFoundError:
            print(f"error: '{args.file}' not found", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "add-url":
        try:
            e = svc.add_from_url(args.name, args.url)
            print(f"Installed '{e['name']}' from URL (v{e.get('version') or '?'}).")
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "add-repo":
        owner, _, repo = args.repo.partition("/")
        if not owner or not repo:
            print("error: expected OWNER/REPO", file=sys.stderr)
            raise SystemExit(1)
        try:
            e = svc.add_from_repo(args.name, owner, repo, args.host)
            print(f"Installed '{e['name']}' from {args.host} "
                  f"({owner}/{repo}, v{e.get('version') or '?'}).")
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "remove":
        if svc.remove_appimage(args.id):
            print(f"Removed '{args.id}'.")
        else:
            print(f"error: no managed AppImage '{args.id}'", file=sys.stderr)
            raise SystemExit(1)
        return

    if action in ("check", "update"):
        targets = [args.id] if args.id else \
            [e["id"] for e in svc.list_appimages()]
        if args.action == "check":
            results = []
            for app_id in targets:
                updated = svc.check_update(app_id)
                if updated:
                    results.append(updated)
            if args.json:
                _emit(results, True)
            else:
                for u in results:
                    mark = "update" if (u.get("latest_version")
                                        and u["latest_version"] != u["version"]) \
                        else "current"
                    print(f"{u['id']:>20}  {u.get('version', '')}"
                          f"  -> {u.get('latest_version') or '-'}  [{mark}]")
        else:
            for app_id in targets:
                if svc.install_update(app_id):
                    print(f"Updated '{app_id}'.")
                else:
                    print(f"'{app_id}' is up to date or has no update source.")
        return

    if action == "sync":
        entries = svc.sync_from_disk()
        print(f"Synchronized: {len(entries)} managed AppImage(s).")


# ── keyring ──────────────────────────────────────────────────────────────

def cmd_keyring(args) -> None:
    from neoarch.backend.services import keyring

    action = args.action
    if action == "list":
        keys = keyring.list_keyring()
        if args.json:
            _emit(keys, True)
        elif not keys:
            print("No keys found (or pacman-key unavailable).")
        else:
            for k in keys:
                print(f"{k.get('fingerprint', ''):>40}  "
                      f"{k.get('uid', '') or k.get('validity', '')}"
                      f"{('  [' + k['created'] + ']') if k.get('created') else ''}")
        return

    if action == "details":
        info = keyring.key_details(args.key)
        if args.json:
            _emit(info, True)
        elif info:
            print(info.get("list", ""))
        else:
            print(f"error: invalid key id: {args.key}", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "init":
        if keyring.init_keyring():
            print("Keyring initialized.")
        else:
            print("Failed to initialize keyring (need root).", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "populate":
        keyrings = args.keyrings or None
        if keyring.populate_keyring(keyrings):
            names = ", ".join(keyrings) if keyrings else "default keyrings"
            print(f"Keyring populated with {names}.")
        else:
            print("Failed to populate keyring (need root).", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "refresh":
        if keyring.refresh_keys():
            print("Keyring refreshed.")
        else:
            print("Failed to refresh keyring (need root).", file=sys.stderr)
            raise SystemExit(1)
        return

    if action in ("receive", "sign"):
        ok = keyring.receive_key(args.key) if action == "receive" \
            else keyring.locally_sign(args.key)
        verb = "Received" if action == "receive" else "Locally signed"
        if ok:
            print(f"{verb} key '{args.key}'.")
        else:
            print(f"Failed to {action} key '{args.key}' (need root).", file=sys.stderr)
            raise SystemExit(1)
        return


# ── purify ───────────────────────────────────────────────────────────────

def cmd_purify(args) -> None:
    from neoarch.backend.services import hygiene

    action = args.action
    if action == "corrupt":
        corrupted = hygiene.list_corrupted_packages()
        if args.json:
            _emit(corrupted, True)
        elif not corrupted:
            print("No corrupted package archives found.")
        else:
            print(f"{len(corrupted)} corrupted archive(s):")
            for p in corrupted:
                print(f"  {p}")
            if args.yes or args.no_confirm or _confirm("Remove corrupted archives?"):
                hygiene.remove_corrupted_packages()
                print("Removed corrupted archives.")
        return

    if action == "cache":
        if hygiene.purge_cache(args.keep):
            print(f"Cache trimmed, keeping {args.keep} version(s) per package.")
        else:
            print("Failed to trim cache (need root).", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "flatpak":
        if hygiene.purge_flatpak_unused():
            print("Removed unused Flatpak runtimes.")
        else:
            print("Failed to clean up Flatpak (need root).", file=sys.stderr)
            raise SystemExit(1)
        return

    if action == "merge":
        result = hygiene.merge_pacnew(args.path, accept=args.accept)
        if result["conflicts"]:
            print(f"Conflicts in {result['merged']}; review and resolve manually.",
                  file=sys.stderr)
            raise SystemExit(2)
        if result["merged"]:
            print(f"Merged into {result['merged']} "
                  f"(backup: {result['backup'] or 'none'}).")
        else:
            print("error: merge failed.", file=sys.stderr)
            raise SystemExit(1)


# ── restart ──────────────────────────────────────────────────────────────

def cmd_restart(args) -> None:
    from neoarch.backend.services import restart_check

    items = restart_check.check_restart_required()
    if args.json:
        _emit(items, True)
    elif not items:
        print("No restart required.")
    else:
        print(f"{len(items)} item(s) need a restart:")
        for item in items:
            print(f"  [{item.get('category')}] {item.get('message')}")


# ── parallel ─────────────────────────────────────────────────────────────

def cmd_parallel(args) -> None:
    from neoarch.backend.services import pacman_conf

    if args.count is None:
        current = pacman_conf.get_parallel_downloads()
        if args.json:
            _emit({"parallel_downloads": current}, True)
        elif current is None:
            print("ParallelDownloads is not set.")
        else:
            print(f"ParallelDownloads = {current}")
        return

    if pacman_conf.set_parallel_downloads(args.count):
        print(f"ParallelDownloads = {args.count} written to /etc/pacman.conf.")
    else:
        print("Failed to set ParallelDownloads (need root).", file=sys.stderr)
        raise SystemExit(1)


# ── schedule ─────────────────────────────────────────────────────────────

def cmd_schedule(args) -> None:
    from neoarch.backend.services import scheduler
    data = _load_config()

    if args.action == "show":
        if args.json:
            _emit({k: data[k] for k in
                   ("schedule_enabled", "schedule_days", "schedule_time")}, True)
        else:
            print(f"enabled: {data.get('schedule_enabled', False)}")
            print(f"days:    {', '.join(str(d) for d in data.get('schedule_days', []))}")
            print(f"time:    {data.get('schedule_time', '03:00')}")
            nxt = scheduler.next_run(data.get("schedule_days", []),
                                     data.get("schedule_time", "03:00"))
            print(f"next:    {nxt.isoformat() if nxt else '(invalid schedule)'}")
        return

    if args.action == "set":
        days = data.get("schedule_days", [])
        if args.days:
            try:
                days = [int(d) for d in args.days.split(",") if d.strip()]
            except ValueError:
                print("error: --days expects a comma-separated list of 0-6",
                      file=sys.stderr)
                raise SystemExit(1)
        time_str = args.time or data.get("schedule_time", "03:00")
        if not scheduler.validate_schedule(days, time_str):
            print("error: invalid schedule", file=sys.stderr)
            raise SystemExit(1)
        data["schedule_days"] = days
        data["schedule_time"] = time_str
        if args.enable is not None:
            data["schedule_enabled"] = args.enable
        _save_config(data)
        print(f"Schedule set: days={days} time={time_str} "
              f"enabled={data['schedule_enabled']}.")


# ── recommend ────────────────────────────────────────────────────────────

def cmd_recommend(args) -> None:
    from neoarch.backend.services import recommend

    items = recommend.recommendations(
        limit=args.limit, include_installed=args.installed)
    if args.json:
        _emit(items, True)
    elif not items:
        print("No recommendations.")
    else:
        for item in items:
            installed = " [installed]" if item.get("installed") else ""
            pop = f"  (pop {item.get('popularity'):.1f})" \
                if item.get("popularity") is not None else ""
            print(f"{item['name']:>20}  [{item.get('category', '')}]  "
                  f"{item.get('desc', '')}{pop}{installed}")


# ── install-url ──────────────────────────────────────────────────────────

def cmd_install_url(args) -> None:
    from neoarch.backend.services import install_url

    if install_url.install_from_url(args.url):
        print("Installed.")
    else:
        print("Failed to install from URL.", file=sys.stderr)
        raise SystemExit(1)


# ── aur-build ────────────────────────────────────────────────────────────

def cmd_aur_build(args) -> None:
    from neoarch.backend.services import aur_build

    if args.commit and not aur_build._COMMIT_RE.match(args.commit):
        print("error: invalid commit reference", file=sys.stderr)
        raise SystemExit(1)
    result = aur_build.build_aur_package(
        args.name, chroot=args.chroot, run_checks=args.check,
        install=args.install, commit=args.commit)
    if result.get("ok"):
        print(f"Built '{args.name}' successfully.")
    else:
        err = (result.get("stderr") or result.get("stdout") or "").strip()
        print(f"error: build failed for '{args.name}': {err}", file=sys.stderr)
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neoarch",
        description="NeoArch CLI — manage Arch Linux packages from the terminal.",
    )
    p.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p.add_argument("-y", "--yes", action="store_true", help="assume yes for prompts")
    p.add_argument("--no-confirm", action="store_true", help="non-interactive safe defaults")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    common.add_argument("-y", "--yes", action="store_true", help="assume yes for prompts")
    common.add_argument("--no-confirm", action="store_true", help="non-interactive safe defaults")

    sub = p.add_subparsers(dest="command", required=True)

    # search
    sp = sub.add_parser("search", parents=[common], help="search repositories")
    sp.add_argument("query", nargs="+", help="search terms")
    sp.add_argument("--pacman", action="store_true", help="official repos only")
    sp.add_argument("--aur", action="store_true", help="AUR only")
    sp.add_argument("--flatpak", action="store_true", help="Flatpak only")
    sp.add_argument("-l", "--limit", type=int, default=8, help="max results")
    sp.set_defaults(func=cmd_search)

    # install
    sp = sub.add_parser("install", parents=[common], help="install packages")
    sp.add_argument("packages", nargs="+", help="package names")
    sp.add_argument("--aur", action="store_true", help="install from AUR")
    sp.add_argument("--flatpak", action="store_true", help="install Flatpak")
    sp.add_argument("--npm", action="store_true", help="install npm global")
    sp.set_defaults(func=cmd_install)

    # remove
    sp = sub.add_parser("remove", parents=[common], help="remove packages")
    sp.add_argument("packages", nargs="+", help="package names")
    sp.add_argument("-c", "--cascade", action="store_true", help="remove unneeded deps")
    sp.add_argument("-n", "--keep-config", action="store_true", help="keep config files")
    sp.set_defaults(func=cmd_remove)

    # upgrade
    sp = sub.add_parser("upgrade", parents=[common], help="upgrade all (or one source)")
    sp.add_argument("--aur", action="store_true", help="AUR packages only")
    sp.add_argument("--flatpak", action="store_true", help="Flatpak only")
    sp.add_argument("--npm", action="store_true", help="npm globals only")
    sp.set_defaults(func=cmd_upgrade)

    # update
    sp = sub.add_parser("update", parents=[common], help="update specific packages")
    sp.add_argument("packages", nargs="+", help="package names")
    sp.set_defaults(func=cmd_update)

    # list
    sp = sub.add_parser("list", parents=[common], help="list installed packages")
    sp.add_argument("-e", "--explicit", action="store_true", help="explicitly installed only")
    sp.add_argument("-m", "--foreign", action="store_true", help="foreign (AUR) only")
    sp.add_argument("--aur", action="store_true", help="AUR packages only")
    sp.add_argument("--flatpak", action="store_true", help="list Flatpaks")
    sp.set_defaults(func=cmd_list)

    # list-updates
    sp = sub.add_parser("list-updates", parents=[common], help="list available updates")
    sp.add_argument("--aur", action="store_true", help="include AUR updates")
    sp.add_argument("--flatpak", action="store_true", help="include Flatpak updates")
    sp.set_defaults(func=cmd_list_updates)

    # ignore
    sp = sub.add_parser("ignore", parents=[common], help="manage ignored updates")
    sp.add_argument("-a", "--add", nargs="+", help="add packages to ignore list")
    sp.add_argument("-r", "--remove", nargs="+", help="remove packages from ignore list")
    sp.add_argument("-l", "--list", action="store_true", help="list ignored packages")
    sp.add_argument("--show", action="store_true", help="alias for --list")
    sp.set_defaults(func=cmd_ignore)

    # news
    sp = sub.add_parser("news", parents=[common], help="read Arch Linux news")
    sp.add_argument("-l", "--limit", type=int, default=10)
    sp.add_argument("--mark-read", action="store_true", help="mark the listed entries as read")
    sp.set_defaults(func=cmd_news)

    # backup
    sp = sub.add_parser("backup", parents=[common], help="manage system backups")
    sp.add_argument("-c", "--create", action="store_true", help="create a backup")
    sp.add_argument("-l", "--list", action="store_true", help="list backups")
    sp.add_argument("--show", action="store_true", help="alias for --list")
    sp.add_argument("-r", "--restore", metavar="PATH", help="restore packages from a backup")
    sp.set_defaults(func=cmd_backup)

    # purge
    sp = sub.add_parser("purge", parents=[common], help="clean up the system")
    sp.add_argument("-o", "--orphans", action="store_true", help="remove orphaned packages")
    sp.add_argument("-c", "--cache", action="store_true", help="clean package cache")
    sp.add_argument("-p", "--pacnew", action="store_true", help="list/remove .pacnew files")
    sp.set_defaults(func=cmd_purge)

    # config
    sp = sub.add_parser("config", parents=[common], help="read/write configuration")
    sp.add_argument("action", choices=["get", "set", "reset"])
    sp.add_argument("key", nargs="?", help="config key")
    sp.add_argument("value", nargs="?", help="value to set")
    sp.set_defaults(func=cmd_config)

    sp = sub.add_parser("scan", parents=[common], help="scan PKGBUILD files for security risks")
    sp.add_argument("paths", nargs="+", help="PKGBUILD or .install files to scan")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("downgrade", parents=[common], help="install an older cached version")
    sp.add_argument("package", help="installed package name")
    sp.add_argument("--version", help="specific version (epoch:ver-rel, ver-rel, or ver)")
    sp.add_argument("-l", "--list-only", action="store_true", help="only list cached versions")
    sp.add_argument("-p", "--pin", action="store_true", help="add package to IgnorePkg after downgrade")
    sp.set_defaults(func=cmd_downgrade)

    sp = sub.add_parser("marks", parents=[common], help="manage IgnorePkg/HoldPkg marks")
    sp.add_argument("action", choices=["list", "ignore", "unignore", "hold", "unhold", "reason"])
    sp.add_argument("package", nargs="?", help="package name")
    sp.add_argument("reason", nargs="?", choices=["explicit", "deps"],
                    help="install reason (for 'reason')")
    sp.set_defaults(func=cmd_marks)

    sp = sub.add_parser("appimage", parents=[common], help="manage AppImage applications")
    asp = sp.add_subparsers(dest="action", required=True)
    asp.add_parser("list", parents=[common], help="list managed AppImages")
    asp.add_parser("sync", parents=[common], help="reconcile store with disk")
    _a = asp.add_parser("add", parents=[common], help="install from a local file")
    _a.add_argument("file", help="path to an .AppImage file")
    _a = asp.add_parser("add-url", parents=[common], help="install from a URL")
    _a.add_argument("name", help="application name")
    _a.add_argument("url", help="download URL ending in .AppImage")
    _a = asp.add_parser("add-repo", parents=[common], help="install latest release from a repo")
    _a.add_argument("name", help="application name")
    _a.add_argument("repo", help="OWNER/REPO")
    _a.add_argument("--host", default="github",
                    choices=["github", "gitlab", "codeberg", "forgejo"],
                    help="release host (default github)")
    _a = asp.add_parser("remove", parents=[common], help="remove a managed AppImage")
    _a.add_argument("id", help="managed app id")
    _a = asp.add_parser("check", parents=[common], help="check for updates")
    _a.add_argument("id", nargs="?", help="managed app id (default: all)")
    _a = asp.add_parser("update", parents=[common], help="install updates")
    _a.add_argument("id", nargs="?", help="managed app id (default: all)")
    sp.set_defaults(func=cmd_appimage)

    sp = sub.add_parser("keyring", parents=[common], help="manage the pacman keyring")
    ksp = sp.add_subparsers(dest="action", required=True)
    ksp.add_parser("list", parents=[common], help="list trusted keys")
    _k = ksp.add_parser("details", parents=[common], help="show key details")
    _k.add_argument("key", help="key id or fingerprint")
    ksp.add_parser("init", parents=[common], help="initialize the keyring")
    _k = ksp.add_parser("populate", parents=[common], help="populate with official keyrings")
    _k.add_argument("keyrings", nargs="*",
                    help="keyring names (default: archlinux, archlinux32, archlinuxarm)")
    ksp.add_parser("refresh", parents=[common], help="refresh keys from the keyserver")
    _k = ksp.add_parser("receive", parents=[common], help="receive a key from the keyserver")
    _k.add_argument("key", help="key id or fingerprint")
    _k = ksp.add_parser("sign", parents=[common], help="locally sign a key")
    _k.add_argument("key", help="key id or fingerprint")
    sp.set_defaults(func=cmd_keyring)

    sp = sub.add_parser("purify", parents=[common], help="deep system cleanup")
    psp = sp.add_subparsers(dest="action", required=True)
    psp.add_parser("corrupt", parents=[common], help="find/remove corrupted archives")
    _p = psp.add_parser("cache", parents=[common], help="trim package cache")
    _p.add_argument("--keep", type=int, default=3, help="versions to keep per package (default 3)")
    psp.add_parser("flatpak", parents=[common], help="remove unused Flatpak runtimes")
    _p = psp.add_parser("merge", parents=[common], help="three-way merge a .pacnew file")
    _p.add_argument("path", help="path to a .pacnew file")
    _p.add_argument("--accept", action="store_true",
                    help="apply the merge if it has no conflicts")
    sp.set_defaults(func=cmd_purify)

    sp = sub.add_parser("restart", parents=[common], help="check whether a reboot is recommended")
    sp.add_argument("action", choices=["check"], nargs="?", default="check")
    sp.set_defaults(func=cmd_restart)

    sp = sub.add_parser("parallel", parents=[common], help="show/set ParallelDownloads in /etc/pacman.conf")
    sp.add_argument("count", nargs="?", type=int, help="parallel download count (1-32)")
    sp.set_defaults(func=cmd_parallel)

    sp = sub.add_parser("schedule", parents=[common], help="show/configure the weekly update schedule")
    ssp = sp.add_subparsers(dest="action", required=True)
    ssp.add_parser("show", parents=[common], help="show the current schedule")
    _s = ssp.add_parser("set", parents=[common], help="set the schedule")
    _s.add_argument("--days", help="comma-separated weekdays (0=Monday..6=Sunday)")
    _s.add_argument("--time", help="time of day as HH:MM")
    _s.add_argument("--enable", dest="enable", action="store_true", default=None,
                    help="enable the schedule")
    _s.add_argument("--disable", dest="enable", action="store_false",
                    help="disable the schedule")
    sp.set_defaults(func=cmd_schedule)

    sp = sub.add_parser("recommend", parents=[common], help="curated package recommendations")
    sp.add_argument("-n", "--limit", type=int, default=20, help="max entries (default 20)")
    sp.add_argument("--installed", action="store_true", help="include installed packages")
    sp.set_defaults(func=cmd_recommend)

    sp = sub.add_parser("install-url", parents=[common], help="install a package archive from a URL")
    sp.add_argument("url", help="http(s) URL of a .pkg.tar.* / .pacman archive")
    sp.set_defaults(func=cmd_install_url)

    sp = sub.add_parser("aur-build", parents=[common], help="clone and build an AUR package")
    sp.add_argument("name", help="AUR package name")
    sp.add_argument("--chroot", action="store_true", help="use makechrootpkg clean chroot")
    sp.add_argument("--check", dest="check", action="store_true", help="run check() functions")
    sp.add_argument("--install", dest="install", action="store_true", help="install after building")
    sp.add_argument("--commit", help="build a specific upstream commit (sha)")
    sp.set_defaults(func=cmd_aur_build)

    sub.add_parser("doctor", parents=[common], help="check system health").set_defaults(func=cmd_doctor)

    return p


# ──────────────────────────────────────────────────────────────────────────
# Shorthand aliases
# ──────────────────────────────────────────────────────────────────────────

# Short names so the everyday commands are easy to type and remember.
# Both spellings work: `neoarch-cli <long>` and `neo <short>`.
_ALIASES = {
    "updates": "list-updates",
    "down": "downgrade",
    "keys": "keyring",
    "reboot": "restart",
    "build": "aur-build",
}

_HOLD_ACTIONS = ("list", "ignore", "unignore", "hold", "unhold", "reason")
_CLEAN_ACTIONS = {
    "orphans": ("purge", ("-o",)),
    "corrupt": ("purify", ("corrupt",)),
    "cache": ("purify", ("cache",)),
    "flatpak": ("purify", ("flatpak",)),
    "merge": ("purify", ("merge",)),
}


def _normalize_argv(argv: List[str]) -> List[str]:
    """Rewrite shorthand `neo` invocations into canonical commands."""
    argv = list(argv)

    # Skip leading global flags (--json/-y/--no-confirm) before the command.
    idx = 0
    while idx < len(argv) and argv[idx].startswith("-"):
        idx += 1
    prefix = argv[:idx]
    if idx >= len(argv):
        return argv
    first = argv[idx]
    rest = argv[idx + 1:]

    if first == "schedule":
        if not rest or rest[0].startswith("-"):
            rest = ["show"] + rest
        return prefix + ["schedule"] + rest

    if first == "backup":
        if not rest or rest[0].startswith("-"):
            if not any(flag in rest for flag in
                       ("-c", "--create", "-l", "--list", "-r", "--restore")):
                rest = ["-c"] + rest
        return prefix + ["backup"] + rest

    if first == "hold":
        if not rest or rest[0].startswith("-"):
            return prefix + ["marks", "list"] + rest
        action = rest[0]
        if action in _HOLD_ACTIONS:
            return prefix + ["marks"] + rest
        return prefix + ["marks", "hold"] + rest

    if first == "clean":
        action = rest[0] if rest else None
        if action in _CLEAN_ACTIONS:
            cmd, extra = _CLEAN_ACTIONS[action]
            return prefix + [cmd] + list(extra) + rest[1:]
        if action is None:
            return prefix + ["purify", "--help"]
        print(f"error: 'clean' takes one of: "
              f"{', '.join(sorted(_CLEAN_ACTIONS))}", file=sys.stderr)
        sys.exit(2)

    cmd = _ALIASES.get(first, first)
    if first == "reboot":
        return prefix + [cmd] + ["check" if t == "--check" else t for t in rest]
    return prefix + [cmd] + rest


parser = _build_parser()


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    argv = _normalize_argv(list(sys.argv[1:] if argv is None else argv))
    flags = _scan_global_flags(argv)
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.json = args.json or flags.get("json", False)
        args.yes = args.yes or flags.get("yes", False)
        args.no_confirm = args.no_confirm or args.yes
        args.func(args)
    else:
        parser.print_help()


def _scan_global_flags(argv: List[str]) -> Dict:
    """Detect --json/-y/--no-confirm anywhere in argv.

    The subparser shadows the top-level parser's attribute defaults, so we
    scan the raw arguments to merge flags placed before the subcommand.
    """
    found: Dict = {}
    for tok in argv:
        if tok == "--json":
            found["json"] = True
        elif tok in ("-y", "--yes"):
            found["yes"] = True
        elif tok == "--no-confirm":
            found["no_confirm"] = True
    return found


if __name__ == "__main__":
    main()
