"""Install package archives from HTTP(S) URLs.

Downloads a .pkg.tar.* / .pacman archive to a temporary file, verifies
it looks like an Arch package, and installs it with an elevated
`pacman -U`. The temp file is removed afterwards. Pure stdlib; safe to
drive from the CLI or a worker thread.
"""

import os
import re
import subprocess
import tempfile
import urllib.request
from threading import Thread
from typing import Callable, Optional

from neoarch.backend.auth import get_auth_command, get_askpass_env

__all__ = ["install_from_url", "is_package_url"]

# Extension must match so we never feed random content to pacman.
_PKG_EXT_RE = re.compile(r"\.(?:pkg\.tar\.(?:zst|xz|gz|lrz|lzo|zstd)|pacman)$",
                         re.IGNORECASE)
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB safety cap


def is_package_url(url: str) -> bool:
    """True when the URL is http(s) and its path looks like a package archive."""
    try:
        parsed = urllib.request.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        return bool(_PKG_EXT_RE.search(parsed.path))
    except Exception:
        return False


def _download(url: str, dest: str, progress_cb: Optional[Callable]) -> bool:
    """Download `url` to `dest`. Returns True on success."""
    try:
        parsed = urllib.request.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        req = urllib.request.Request(url, headers={"User-Agent": "neoarch/2.5"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            received = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_DOWNLOAD_BYTES:
                        return False
                    f.write(chunk)
                    if progress_cb and total:
                        try:
                            progress_cb(received / total)
                        except Exception:
                            pass
        return os.path.getsize(dest) > 0
    except Exception:
        return False


def _install(file_path: str) -> bool:
    """Install a package archive with elevated pacman -U."""
    auth = get_auth_command()
    env = None
    if auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        result = subprocess.run(
            auth + ["pacman", "-U", "--noconfirm", file_path],
            capture_output=True, text=True, timeout=1200, env=env)
        return result.returncode == 0
    except Exception:
        return False


def install_from_url(url: str, progress_cb: Optional[Callable] = None,
                     finished_cb: Optional[Callable] = None) -> bool:
    """Download and install a package archive from a URL.

    With `finished_cb` the work runs on a daemon thread and the call
    returns immediately. Returns success when run synchronously.
    """
    def _do() -> bool:
        fd, tmp = tempfile.mkstemp(prefix="neoarch-url-", suffix=".pkg")
        os.close(fd)
        try:
            if not is_package_url(url):
                if progress_cb:
                    try:
                        progress_cb("URL does not look like a package archive.")
                    except Exception:
                        pass
                if finished_cb:
                    try:
                        finished_cb(False)
                    except Exception:
                        pass
                return False
            if not _download(url, tmp, progress_cb):
                if progress_cb:
                    try:
                        progress_cb("Download failed.")
                    except Exception:
                        pass
                if finished_cb:
                    try:
                        finished_cb(False)
                    except Exception:
                        pass
                return False
            ok = _install(tmp)
            if progress_cb:
                try:
                    progress_cb("Installed." if ok else "Installation failed.")
                except Exception:
                    pass
            if finished_cb:
                try:
                    finished_cb(ok)
                except Exception:
                    pass
            return ok
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    if finished_cb:
        Thread(target=_do, daemon=True).start()
        return True
    return _do()
