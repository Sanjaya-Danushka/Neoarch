"""Live package search against pacman and AUR.

Used as a fallback when a user's search term has no match in the curated
NeoArch catalog. Returns specs compatible with the plugins view so results
can be installed directly.
"""

import subprocess
import json
import os
from typing import List, Dict

from neoarch.resources.paths import APP_VERSION

__all__ = ["search_live_packages", "search_pacman", "search_aur"]

_UA_VERSION = APP_VERSION


def _run(cmd: List[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout or ""
    except Exception:
        return ""


def _parse_pacman_ss(out: str, limit: int = 8) -> List[Dict]:
    """Parse `pacman -Ss` output into installable specs."""
    specs = []
    name = None
    for line in out.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if name:
                desc = line.strip()
                specs[-1]["desc"] = desc
                name = None
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pkg = parts[0]
        repo = "official"
        if "/" in pkg:
            repo, pkg = pkg.split("/", 1)
        desc = " ".join(parts[1:]) if len(parts) > 1 else ""
        specs.append({
            "id": f"pacman-{pkg}",
            "name": pkg,
            "desc": desc,
            "pkg": pkg,
            "cmd": None,
            "icon": None,
            "category": "Live Search",
            "source": "pacman",
            "repo": repo,
            "installed": "installed" in desc,
        })
        name = pkg
        if len(specs) >= limit:
            break
    return specs


def merge_results(pacman: List[Dict], aur: List[Dict]) -> List[Dict]:
    """Combine pacman + AUR results, preferring the pacman entry for a pkg."""
    seen = {s["pkg"] for s in pacman}
    merged = list(pacman)
    for s in aur:
        if s["pkg"] not in seen:
            merged.append(s)
            seen.add(s["pkg"])
    return merged


def search_pacman(query: str, limit: int = 8) -> List[Dict]:
    """Search the official pacman repositories."""
    out = _run(["pacman", "-Ss", query])
    return _parse_pacman_ss(out, limit)


def search_aur(query: str, limit: int = 8) -> List[Dict]:
    """Search the Arch User Repository via its RPC API."""
    import urllib.parse
    import urllib.request
    specs = []
    try:
        url = "https://aur.archlinux.org/rpc/?v=5&type=search&arg=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": f"neoarch/{_UA_VERSION}"})
        from neoarch.backend.services.network import urlopen as _net_urlopen
        with _net_urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for r in data.get("results", []):
            pkg = r.get("Name", "")
            specs.append({
                "id": f"aur-{pkg}",
                "name": pkg,
                "desc": r.get("Description") or "",
                "pkg": f"aur/{pkg}",
                "cmd": None,
                "icon": None,
                "category": "Live Search",
                "source": "aur",
            })
            if len(specs) >= limit:
                break
    except Exception:
        pass
    return specs


def search_live_packages(query: str, limit: int = 8) -> List[Dict]:
    """Search pacman first, then AUR, returning combined installable specs."""
    query = (query or "").strip()
    if not query:
        return []
    specs = search_pacman(query, limit)
    return merge_results(specs, search_aur(query, limit))
