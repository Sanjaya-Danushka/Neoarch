"""NeoArch command-line interface.

A scriptable frontend for the NeoArch package-management backend. Runs
without a display server and reuses the pure (Qt-free) service modules
so logic stays consistent with the GUI.

Usage:
    python -m neoarch.cli <command> [options]

Commands:
    search        Search pacman/AUR/Flatpak repositories
    install       Install packages (pacman/AUR/Flatpak/npm)
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
    downgrade     Install an older cached version of a package
    scan          Scan a PKGBUILD for security risks
    doctor        Check the system for missing prerequisites
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
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
        for item in data:
            if isinstance(item, dict):
                print(_fmt_dict(item))
            else:
                print(item)
    elif isinstance(data, dict):
        print(_fmt_dict(data))
    else:
        print(data)


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
    _emit(specs, args.json)


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

def cmd_install(args) -> None:
    if not args.packages:
        print("error: install requires at least one package", file=sys.stderr)
        sys.exit(1)
    no_confirm = args.no_confirm or args.yes
    if not args.aur and not args.flatpak and not args.npm:
        target = "pacman"
    else:
        target = "aur" if args.aur else ("flatpak" if args.flatpak else "npm")

    if target == "pacman":
        cmd = ["pacman", "-S"] + (["--noconfirm"] if no_confirm else []) + args.packages
        _stream(cmd, sudo=True, check=True)
    elif target == "aur":
        helper = sys_utils.get_aur_helper()
        if not helper:
            print("error: no AUR helper available (install yay/paru)", file=sys.stderr)
            sys.exit(1)
        cmd = [helper, "-S"] + args.packages
        if no_confirm:
            cmd.insert(1, "--noconfirm")
        _stream(cmd, check=True)
    elif target == "flatpak":
        _stream(["flatpak", "install", "--user", "-y"] + args.packages, check=True)
    elif target == "npm":
        _stream(["npm", "install", "-g"] + args.packages, check=True)


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
            "title": entry.get("title", "(untitled)"),
            "link": entry.get("link", ""),
            "published": entry.get("pubDate", ""),
            "summary": entry.get("description", ""),
        })
        if len(items) >= limit:
            break
    return items


def cmd_news(args) -> None:
    items = _fetch_news(args.limit)
    if not items:
        print("No news available (offline?).")
        return
    _emit(items, args.json)


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

    sub.add_parser("doctor", parents=[common], help="check system health").set_defaults(func=cmd_doctor)

    return p


parser = _build_parser()


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    argv = list(sys.argv[1:] if argv is None else argv)
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
