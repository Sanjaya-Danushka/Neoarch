"""Curated package recommendations.

A headless feed for the Discover tab. Recommendations come from a
bundled curated list (local plugin data) merged with optional AUR
popularity scores loaded from a local cache written by the search
service. Never requires the network at recommendation time.
"""

import json
import os
from typing import Dict, List

__all__ = ["CURATED", "recommendations", "set_popularity_cache"]

POPULARITY_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "neoarch", "popularity.json")

# name -> (description, category). Clean-room curated data.
CURATED: Dict[str, tuple] = {
    "firefox": ("Privacy-focused web browser", "browser"),
    "chromium": ("Open-source web browser", "browser"),
    "kitty": ("Fast, featureful GPU-based terminal", "terminal"),
    "alacritty": ("GPU-accelerated terminal emulator", "terminal"),
    "code": ("Visual Studio Code editor", "editor"),
    "vim": ("Highly configurable text editor", "editor"),
    "neovim": ("Extensible Vim-based text editor", "editor"),
    "obsidian": ("Knowledge base on local markdown files", "notes"),
    "joplin": ("Open-source note-taking application", "notes"),
    "spotify": ("Commercial music streaming client", "media"),
    "vlc": ("Versatile media player", "media"),
    "gimp": ("GNU image manipulation program", "graphics"),
    "krita": ("Digital painting application", "graphics"),
    "blender": ("3D creation suite", "graphics"),
    "gparted": ("GNOME partition editor", "utilities"),
    "htop": ("Interactive process viewer", "utilities"),
    "btop": ("Resource monitor showing usage and stats", "utilities"),
    "syncthing": ("Continuous file synchronization", "utilities"),
    "keepassxc": ("Cross-platform password manager", "security"),
    "veracrypt": ("Disk encryption with strong privacy", "security"),
    "wireguard-tools": ("Modern VPN tunneling tools", "security"),
    "docker": ("Container management daemon", "development"),
    "podman": ("Daemonless container engine", "development"),
    "postgresql": ("Powerful open-source database", "development"),
    "nodejs": ("JavaScript runtime", "development"),
    "rust": ("Systems programming language", "development"),
    "texlive-most": ("Comprehensive TeX distribution", "productivity"),
    "libreoffice-fresh": ("Full-featured office suite", "productivity"),
    "thunderbird": ("Email and news client", "communication"),
    "discord": ("Voice, video and text chat", "communication"),
}


def set_popularity_cache(path: str) -> None:
    """Override the popularity cache location (used by tests)."""
    global POPULARITY_CACHE
    POPULARITY_CACHE = path


def _load_popularity() -> Dict[str, float]:
    """Load cached AUR popularity scores, or {} when unavailable."""
    try:
        with open(POPULARITY_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:
        return {}


def _installed() -> List[str]:
    import subprocess
    try:
        result = subprocess.run(["pacman", "-Qq"], capture_output=True,
                                text=True, timeout=30)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def recommendations(limit: int = 20, include_installed: bool = False) -> List[Dict]:
    """Return a curated recommendation feed.

    Each entry: {name, desc, category, popularity, installed}. Sorted by
    popularity (descending) when scores are available, otherwise by name.
    """
    popularity = _load_popularity()
    installed = set(_installed())

    entries: List[Dict] = []
    for name, (desc, category) in CURATED.items():
        entries.append({
            "name": name,
            "desc": desc,
            "category": category,
            "popularity": popularity.get(name),
            "installed": name in installed,
        })
    if not include_installed:
        entries = [e for e in entries if not e["installed"]]

    def sort_key(e: Dict):
        return -(e["popularity"] if e["popularity"] is not None else 0.0), e["name"]

    entries.sort(key=sort_key)
    if limit and limit > 0:
        entries = entries[:limit]
    return entries
