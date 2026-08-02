"""Built-in backup services.

Provides native BTRFS snapshots and package-list/config backups without
requiring the external timeshift utility. Timeshift remains available as
an optional advanced tool.

Backup layout on disk:

    ~/.cache/neoarch/backups/<timestamp>/
        package-list.json   (pacman + flatpak + npm exports)
        config.tar.gz       (app config dirs)
        snapshots.txt       (list of created btrfs snapshots, if any)

BTRFS snapshots are created as read-only subvolume snapshots of the root
filesystem and stored inside the top-level subvolume under a neoarch-owned
directory, so they do not clutter the running system.
"""

import json
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from threading import Thread
from typing import List, Dict, Optional

from neoarch.backend.auth import get_auth_command
from neoarch.backend.workers import CommandWorker

__all__ = [
    "get_backup_root", "get_filesystem_type", "list_backups",
    "create_backup", "restore_packages", "restore_config",
    "prune_backups", "list_snapshots",
]

BACKUP_SUBDIR = "backups"
BACKUP_KEEP_COUNT = 5
SNAPSHOT_DIR = "@neoarch-snapshots"


def get_backup_root() -> Path:
    """Return the directory where NeoArch backups are stored."""
    root = Path.home() / ".cache" / "neoarch" / BACKUP_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_filesystem_type() -> str:
    """Detect the filesystem type of the root mount."""
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "FSTYPE", "/"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _btrfs_root_subvolume() -> Optional[str]:
    """Return the btrfs root mount target, or None if btrfs is unavailable."""
    if not shutil.which("btrfs"):
        return None
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "TARGET", "/"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None


def _run_sudo(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a command with the app's preferred elevation."""
    auth = get_auth_command()
    if auth == ["sudo", "-A"]:
        from neoarch.backend.auth import get_askpass_env
        env = get_askpass_env()
    else:
        env = None
    full = auth + cmd
    return subprocess.run(full, capture_output=True, text=True, timeout=timeout, env=env)


def _export_package_list() -> Dict:
    """Export installed package lists from pacman/flatpak/npm."""
    data: Dict = {"timestamp": int(time.time()), "sources": {}}

    def _cmd(cmd: List[str]) -> List[str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return [l.strip() for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            return []

    data["sources"]["pacman_all"] = _cmd(["pacman", "-Qq"])
    data["sources"]["pacman_explicit"] = _cmd(["pacman", "-Qqen"])
    data["sources"]["pacman_foreign"] = _cmd(["pacman", "-Qqem"])
    if shutil.which("flatpak"):
        data["sources"]["flatpak"] = _cmd(
            ["flatpak", "list", "--app", "--columns=application"])
    if shutil.which("npm"):
        data["sources"]["npm_global"] = _cmd(["npm", "ls", "-g", "--depth=0", "--json"])
    return data


def _export_config(backup_dir: Path) -> Path:
    """Tar the app config directory into the backup dir."""
    config_dir = Path.home() / ".config" / "neoarch"
    archive = backup_dir / "config.tar.gz"
    if not config_dir.exists():
        with tarfile.open(archive, "w:gz"):
            pass
        return archive
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(config_dir, arcname="neoarch-config")
    return archive


def _is_btrfs_root_snapshottable() -> bool:
    """Return True if we can snapshot the root subvolume."""
    if get_filesystem_type() != "btrfs":
        return False
    if not shutil.which("btrfs"):
        return False
    return _btrfs_root_subvolume() is not None


def _create_btrfs_snapshot(backup_dir: Path) -> Optional[str]:
    """Create a read-only btrfs snapshot of the root filesystem.

    Returns the snapshot name on success, None on failure.
    """
    mount = _btrfs_root_subvolume()
    if not mount:
        return None
    snapshot_name = f"neoarch-snap-{time.strftime('%Y%m%d-%H%M%S')}"
    snap_target = os.path.join(mount, SNAPSHOT_DIR, snapshot_name)
    try:
        _run_sudo(["mkdir", "-p", os.path.join(mount, SNAPSHOT_DIR)])
        result = _run_sudo(["btrfs", "subvolume", "snapshot", "-r", mount, snap_target], timeout=600)
        if result.returncode != 0:
            return None
        return snap_target
    except Exception:
        return None


def create_backup(progress_cb=None, finished_cb=None) -> Dict:
    """Create a full backup (btrfs snapshot when possible + package/config export).

    Args:
        progress_cb: Optional callable(str) for progress messages.
        finished_cb: Optional callable(dict) invoked with the result on completion.

    Returns:
        dict: Backup metadata (path, snapshot, counts) on success.
    """
    def _log(msg: str):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    def _do() -> Dict:
        _log("Starting backup...")
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = get_backup_root() / ts
        backup_dir.mkdir(parents=True, exist_ok=True)

        snapshot = None
        if _is_btrfs_root_snapshottable():
            _log("Creating BTRFS snapshot...")
            snapshot = _create_btrfs_snapshot(backup_dir)
            if snapshot:
                _log(f"Snapshot created: {snapshot}")
            else:
                _log("BTRFS snapshot failed; continuing with package/config backup.")

        _log("Exporting package lists...")
        pkg_data = _export_package_list()
        with open(backup_dir / "package-list.json", "w") as f:
            json.dump(pkg_data, f, indent=2)

        _log("Backing up config...")
        config_archive = _export_config(backup_dir)

        result = {
            "path": str(backup_dir),
            "timestamp": ts,
            "snapshot": snapshot,
            "packages": {
                k: len(v) for k, v in pkg_data["sources"].items()
            },
            "config": str(config_archive),
            "filesystem": get_filesystem_type(),
        }
        with open(backup_dir / "snapshots.txt", "w") as f:
            f.write((snapshot or "none") + "\n")

        _log(f"Backup complete: {backup_dir}")
        if finished_cb:
            try:
                finished_cb(result)
            except Exception:
                pass
        return result

    if progress_cb or finished_cb:
        thread = Thread(target=_do, daemon=True)
        thread.start()
        return {}
    return _do()


def list_backups() -> List[Dict]:
    """Return metadata for all stored backups, newest first."""
    root = get_backup_root()
    entries = []
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        info: Dict = {"path": str(entry), "timestamp": entry.name}
        pkg_file = entry / "package-list.json"
        if pkg_file.exists():
            try:
                data = json.loads(pkg_file.read_text())
                info["packages"] = data.get("sources", {})
                info["exported_at"] = data.get("timestamp")
            except Exception:
                pass
        snap_file = entry / "snapshots.txt"
        if snap_file.exists():
            snap = snap_file.read_text().strip()
            info["snapshot"] = None if snap == "none" else snap
        info["filesystem"] = _get_fs_from_path(str(entry))
        entries.append(info)
    return entries


def _get_fs_from_path(_path: str) -> str:
    """Best-effort filesystem label for a backup entry."""
    try:
        return get_filesystem_type()
    except Exception:
        return "unknown"


def prune_backups(keep: int = BACKUP_KEEP_COUNT) -> List[str]:
    """Delete oldest backups beyond the keep count. Returns removed paths."""
    removed = []
    backups = sorted(get_backup_root().iterdir(), reverse=True)
    for old in backups[keep:]:
        if old.is_dir():
            try:
                shutil.rmtree(old, ignore_errors=True)
                removed.append(str(old))
            except Exception:
                pass
    return removed


def list_snapshots() -> List[str]:
    """List neoarch-managed btrfs snapshots (best effort)."""
    mount = _btrfs_root_subvolume()
    if not mount:
        return []
    snap_root = os.path.join(mount, SNAPSHOT_DIR)
    if not os.path.isdir(snap_root):
        return []
    return sorted(os.listdir(snap_root), reverse=True)


def restore_packages(backup_path: str, progress_cb=None, finished_cb=None) -> bool:
    """Restore installed packages from a backup's package-list.json."""
    def _do() -> bool:
        pkg_file = Path(backup_path) / "package-list.json"
        if not pkg_file.exists():
            if finished_cb:
                finished_cb(False)
            return False
        try:
            data = json.loads(pkg_file.read_text())
        except Exception:
            if finished_cb:
                finished_cb(False)
            return False
        explicit = data.get("sources", {}).get("pacman_explicit", [])
        foreign = data.get("sources", {}).get("pacman_foreign", [])
        if not explicit and not foreign:
            if finished_cb:
                finished_cb(False)
            return False

        ok = True
        if explicit:
            try:
                worker = CommandWorker(
                    ["pacman", "-S", "--needed", "--noconfirm"] + explicit, sudo=True)
                worker.output.connect(lambda s: progress_cb(s) if progress_cb else None)
                worker.error.connect(lambda s: progress_cb(s) if progress_cb else None)
                worker.run()
            except Exception:
                ok = False
        if ok and foreign:
            from neoarch.backend import sys_utils
            helper = sys_utils.get_aur_helper()
            if helper:
                try:
                    worker = CommandWorker(
                        [helper, "-S", "--needed", "--noconfirm"] + foreign, sudo=True)
                    worker.output.connect(lambda s: progress_cb(s) if progress_cb else None)
                    worker.error.connect(lambda s: progress_cb(s) if progress_cb else None)
                    worker.run()
                except Exception:
                    ok = False
        if finished_cb:
            finished_cb(ok)
        return ok

    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()


def restore_config(backup_path: str, finished_cb=None) -> bool:
    """Restore the app config tar from a backup."""
    archive = Path(backup_path) / "config.tar.gz"
    if not archive.exists():
        if finished_cb:
            finished_cb(False)
        return False
    def _do() -> bool:
        try:
            config_dir = Path.home() / ".config" / "neoarch"
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    target = config_dir / member.name.replace("neoarch-config/", "", 1)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        extracted = tar.extractfile(member)
                        if extracted:
                            target.write_bytes(extracted.read())
            if finished_cb:
                finished_cb(True)
            return True
        except Exception:
            if finished_cb:
                finished_cb(False)
            return False
    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()
