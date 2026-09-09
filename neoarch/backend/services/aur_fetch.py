"""Fetch AUR package sources for pre-install scanning.

Pulls the raw ``PKGBUILD`` (and any ``<pkgbase>.install`` scriptlets) of an
AUR package straight from the AUR cgit plain-text endpoint — no AUR helper
or git clone required. Best-effort: returns ``None`` on any network/HTTP
error so a scan can degrade gracefully to no-op instead of blocking an
install.
"""

import re
from typing import Dict, Optional
from urllib.parse import quote

from neoarch.backend.services import network

__all__ = ["fetch_aur_pkgbuild"]

AUR_CGIT_PLAIN = "https://aur.archlinux.org/cgit/aur.git/plain/{path}"

# AUR package names: [a-z0-9][a-z0-9+_.-]*
_PKG_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9+_.\-]*$")

# Safety cap: a PKGBUILD / scriptlet never legitimately exceeds this.
_MAX_SCRIPTLET_BYTES = 2 * 1024 * 1024


def _valid_name(name: str) -> bool:
    return bool(name) and bool(_PKG_NAME_RE.match(name))


def _fetch_plain(path: str, timeout: Optional[int] = None) -> Optional[str]:
    """GET a single cgit plain-text file, or None on 404/error."""
    import urllib.request
    url = AUR_CGIT_PLAIN.format(path=path)
    try:
        with network.urlopen(
                urllib.request.Request(url), timeout=timeout) as r:
            if getattr(r, "status", 200) == 404:
                return None
            data = r.read(_MAX_SCRIPTLET_BYTES)
        return data.decode("utf-8", "replace")
    except Exception:
        return None


def fetch_aur_pkgbuild(name: str,
                       timeout: Optional[int] = None) -> Optional[Dict]:
    """Fetch ``PKGBUILD`` + ``.install`` scriptlets of an AUR package.
    Args:
        name: AUR package base name.
        timeout: Per-request timeout (seconds); falls back to the app-wide
            network default.

    Returns:
        ``{"name", "pkgbuild", "scriptlets": {fname: text}}`` or ``None``
        if the package does not exist / cannot be fetched.
    """
    if not _valid_name(name):
        return None
    quoted = quote(name, safe="")
    pkgbuild = _fetch_plain(f"PKGBUILD?h={quoted}", timeout=timeout)
    if pkgbuild is None:
        return None
    scriptlets: Dict[str, str] = {}
    install = _fetch_plain(f"{quoted}.install?h={quoted}", timeout=timeout)
    if install is not None:
        scriptlets[f"{name}.install"] = install
    return {"name": name, "pkgbuild": pkgbuild, "scriptlets": scriptlets}
