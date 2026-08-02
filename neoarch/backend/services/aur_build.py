"""Headless AUR package builds.

Clones a PKGBUILD from the AUR and builds it with `makepkg`, with
opt-in support for clean chroot builds (`makechrootpkg`), running
`check()` functions, and pinning to a specific upstream commit. Pure
stdlib; drives subprocesses so it works from the CLI or the GUI worker
pipeline.
"""

import os
import re
import shutil
import subprocess
import tempfile
from threading import Thread
from typing import Callable, Dict, List, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = ["build_aur_package", "build_command", "AUR_BASE"]

AUR_BASE = "https://aur.archlinux.org/{name}.git"

# AUR package names: [a-z0-9][a-z0-9+_.-]*
_PKG_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9+_.\-]*$")
# Git commit-ish we allow: hex sha or a tag. Reject anything that could
# smuggle shell metacharacters into the clone path.
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _valid_name(name: str) -> bool:
    return bool(name) and bool(_PKG_NAME_RE.match(name))


def build_command(workdir: str, chroot: bool = False, run_checks: bool = False,
                  install: bool = False) -> List[str]:
    """Build the shell command that runs inside a cloned PKGBUILD dir."""
    tool = "makechrootpkg -c" if chroot else "makepkg"
    flags = ""
    if run_checks:
        flags += " --check"
    if install:
        flags += " -i --noconfirm"
    return ["bash", "-lc", f"cd '{workdir}' && {tool}{flags}"]


def _askpass_env() -> Optional[dict]:
    auth = get_auth_command()
    if auth == ["sudo", "-A"]:
        return get_askpass_env()
    return None


def _run_clone(name: str, dest: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", AUR_BASE.format(name=name), dest],
            capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception:
        return False


def _checkout_commit(dest: str, commit: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", dest, "checkout", commit],
            capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False


def _run_build(workdir: str, chroot: bool, run_checks: bool, install: bool,
               progress_cb: Optional[Callable]) -> subprocess.CompletedProcess:
    cmd = build_command(workdir, chroot, run_checks, install)
    env = _askpass_env()
    try:
        if progress_cb:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, env=env)
            for line in proc.stdout or ():
                line = line.rstrip()
                if line:
                    try:
                        progress_cb(line)
                    except Exception:
                        pass
            proc.wait()
            return subprocess.CompletedProcess(cmd, proc.returncode, "", "")
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=3600, env=env)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def build_aur_package(name: str, chroot: bool = False, run_checks: bool = False,
                      install: bool = False, commit: Optional[str] = None,
                      workdir: Optional[str] = None,
                      progress_cb: Optional[Callable] = None,
                      finished_cb: Optional[Callable] = None) -> Dict:
    """Clone and build an AUR package.

    Returns {name, ok, stdout, stderr} (with the async variant,
    `finished_cb` receives that dict and this call returns {} immediately).
    """
    def _do() -> Dict:
        if not _valid_name(name):
            return {"name": name, "ok": False, "stdout": "",
                    "stderr": "invalid package name"}
        if commit and not _COMMIT_RE.match(commit):
            return {"name": name, "ok": False, "stdout": "",
                    "stderr": "invalid commit reference"}
        tmp = workdir or tempfile.mkdtemp(prefix="neoarch-aur-")
        dest = os.path.join(tmp, name)
        try:
            if not _run_clone(name, dest):
                return {"name": name, "ok": False, "stdout": "",
                        "stderr": "clone failed"}
            if commit and not _checkout_commit(dest, commit):
                return {"name": name, "ok": False, "stdout": "",
                        "stderr": "commit checkout failed"}
            result = _run_build(dest, chroot, run_checks, install, progress_cb)
            return {"name": name, "ok": result.returncode == 0,
                    "stdout": result.stdout or "", "stderr": result.stderr or ""}
        finally:
            if not workdir:
                shutil.rmtree(tmp, ignore_errors=True)

    if finished_cb:
        Thread(target=lambda: finished_cb(_do()), daemon=True).start()
        return {}
    return _do()
