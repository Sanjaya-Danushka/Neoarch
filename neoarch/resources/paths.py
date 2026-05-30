"""Path constants for NeoArch project"""

import os
from pathlib import Path

__all__ = [
    "PROJECT_ROOT", "ASSETS_DIR", "ICONS_DIR", "CONFIG_DIR",
    "APP_NAME", "APP_VERSION", "APP_ICON",
    "PLUGINS_ITEMS_DIR", "DEFAULT_ICON_PATH",
]

# neoarch/resources/paths.py -> 3 levels up to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
CONFIG_DIR = Path.home() / ".config" / "neoarch"

APP_NAME = "NeoArch"
APP_VERSION = "2.0.0"
APP_ICON = str(ASSETS_DIR / "icons" / "app.png")

PLUGINS_ITEMS_DIR = str(PROJECT_ROOT / "assets" / "plugins" / "plugins-items")
DEFAULT_ICON_PATH = str(ASSETS_DIR / "icons" / "default.png")
