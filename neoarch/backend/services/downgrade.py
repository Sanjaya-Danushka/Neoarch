"""Package downgrade service.

Lists cached versions of an installed package, installs a specific
version from the local pacman cache, and optionally pins the package to
IgnorePkg so pacman will not upgrade it back.

Version ordering follows pacman's `vercmp` semantics so results match
what the package manager itself would decide.
"""

import os
import re
import subprocess
from functools import cmp_to_key
from threading import Thread
from typing import Callable, Dict, List, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = [
    "cache_dirs", "list_cached_versions",
    "install_version", "add_to_ignorepkg", "vercmp",
]

DEFAULT_CACHE_DIR = "/var/cache/pacman/pkg"
PACMAN_CONF = "/etc/pacman.conf"

# <pkgname>-<epoch>:<pkgver>-<pkgrel>-<arch>.pkg.tar.<ext>
_PKG_FILE_RE = re.compile(r"-(?P<arch>\w+)\.pkg\.tar(?:\.\w+)?$")


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _run_sudo(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except Exception:
        return subprocess.CompletedProcess(auth + cmd, 1, "", "")


def cache_dirs() -> List[str]:
    """Return the pacman cache directories from /etc/pacman.conf.

    Falls back to the default location when unset.
    """
    dirs: List[str] = []
    try:
        with open(PACMAN_CONF, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CacheDir") and "=" in line:
                    for d in line.split("=", 1)[1].split():
                        if d.startswith("/"):
                            dirs.append(d)
    except Exception:
        pass
    return dirs or [DEFAULT_CACHE_DIR]


def vercmp(a: str, b: str) -> int:
    """Compare two full versions ('epoch:ver-rel') like pacman.

    Uses the `vercmp` binary when available; falls back to a
    segment-wise comparison otherwise. Returns -1, 0, or 1.
    """
    for fmt in ("{0} {1}", "{0}:{1}"):
        pass
    result = _run(["vercmp", a, b])
    if result.returncode == 0:
        out = result.stdout.strip()
        if out in ("-1", "0", "1"):
            return int(out)
    return _vercmp_fallback(a, b)


def _vercmp_fallback(a: str, b: str) -> int:
    """Approximate alpm_pkgvercmp when the `vercmp` binary is unavailable."""
    def split_epoch(v: str):
        if ":" in v:
            ep, _, rest = v.rpartition(":")
            return ep, rest
        return "0", v

    def split_rel(v: str):
        if "-" in v:
            ver, _, rel = v.rpartition("-")
            return ver, rel
        return v, "0"

    def segs(v: str):
        return re.findall(r"\d+|\D+", v)

    def cmp_seg(x: str, y: str) -> int:
        if x.isdigit() and y.isdigit():
            return (int(x) > int(y)) - (int(x) < int(y))
        if x.isdigit() != y.isdigit():
            return -1 if x.isdigit() else 1
        return (x > y) - (x < y)

    ea, va = split_epoch(a)
    eb, vb = split_epoch(b)
    if ea != eb:
        return -1 if int(ea) < int(eb) else 1
    va, ra = split_rel(va)
    vb, rb = split_rel(vb)
    for x, y in zip(segs(va), segs(vb)):
        c = cmp_seg(x, y)
        if c:
            return c
    for x, y in zip(segs(ra), segs(rb)):
        c = cmp_seg(x, y)
        if c:
            return c
    return (len(segs(va)) > len(segs(vb))) - (len(segs(va)) < len(segs(vb)))


def _parse_pkgfile(path: str) -> Optional[Dict]:
    """Parse a .pkg.tar.* filename into structured metadata."""
    base = os.path.basename(path)
    m = _PKG_FILE_RE.search(base)
    if not m:
        return None
    arch = m.group("arch")
    rest = base[: m.start()]
    parts = rest.rsplit("-", 2)
    if len(parts) != 3:
        return None
    name, ver, rel = parts
    epoch = "0"
    if ":" in ver:
        epoch, _, ver = ver.partition(":")
    return {
        "name": name,
        "epoch": epoch,
        "version": ver,
        "release": rel,
        "arch": arch,
        "full": f"{epoch}:{ver}-{rel}",
        "path": path,
        "file": base,
    }


def list_cached_versions(pkg: str, extra_dirs: Optional[List[str]] = None) -> List[Dict]:
    """List versions of `pkg` present in the pacman cache, newest first.

    Returns a list of dicts: {name, version, release, arch, full, path,
    file}. Duplicates (same version+arch) are collapsed.
    """
    seen: Dict[str, Dict] = {}
    for dirpath in extra_dirs or cache_dirs():
        try:
            entries = os.listdir(dirpath)
        except Exception:
            continue
        for entry in entries:
            if not entry.endswith(".pkg.tar") and ".pkg.tar." not in entry:
                continue
            info = _parse_pkgfile(os.path.join(dirpath, entry))
            if not info or info["name"] != pkg:
                continue
            key = (info["arch"], info["epoch"], info["version"], info["release"])
            seen.setdefault(key, info)

    result = sorted(seen.values(), key=cmp_to_key(
        lambda x, y: vercmp(x["full"], y["full"])))
    result.reverse()
    return result


def resolve_cache_path(pkg: str, version: Optional[str] = None) -> Optional[str]:
    """Return the cached .pkg.tar path for a version (newest if None)."""
    versions = list_cached_versions(pkg)
    if not versions:
        return None
    if version:
        for v in versions:
            if v["full"] == version or v["full"].lstrip("0:") == version \
               or v["version"] == version or f"{v['version']}-{v['release']}" == version:
                return v["path"]
        return None
    return versions[0]["path"]


def install_version(pkg: str, version: Optional[str] = None, path: Optional[str] = None,
                    progress_cb: Optional[Callable] = None,
                    finished_cb: Optional[Callable] = None) -> bool:
    """Install a specific cached version of `pkg`. Returns True on success.

    Either `version` (looked up in the cache) or an explicit `path` may
    be given. Runs `pacman -U --noconfirm` with elevation.
    """
    def _do() -> bool:
        pkg_path = path
        if pkg_path is None:
            pkg_path = resolve_cache_path(pkg, version)
        if not pkg_path or not os.path.isfile(pkg_path):
            if progress_cb:
                try:
                    progress_cb(f"No cached version of '{pkg}' to install.")
                except Exception:
                    pass
            if finished_cb:
                try:
                    finished_cb(False)
                except Exception:
                    pass
            return False
        if progress_cb:
            try:
                progress_cb(f"Downgrading {pkg} from {os.path.basename(pkg_path)}...")
            except Exception:
                pass
        result = _run_sudo(["pacman", "-U", "--noconfirm", pkg_path])
        ok = result.returncode == 0
        if progress_cb:
            try:
                progress_cb("Downgrade complete." if ok else
                            f"Downgrade failed: {result.stderr.strip()[:200]}")
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


def _ignorepkg_entries() -> List[str]:
    """Current IgnorePkg package names (delegates to the marks service)."""
    from neoarch.backend.services import marks
    return marks.get_ignorepkg()


def add_to_ignorepkg(pkg: str) -> bool:
    """Append `pkg` to IgnorePkg in /etc/pacman.conf (needs root)."""
    from neoarch.backend.services import marks
    return marks.add_ignorepkg(pkg)


def remove_from_ignorepkg(pkg: str) -> bool:
    """Remove `pkg` from IgnorePkg in /etc/pacman.conf (needs root)."""
    from neoarch.backend.services import marks
    return marks.remove_ignorepkg(pkg)
