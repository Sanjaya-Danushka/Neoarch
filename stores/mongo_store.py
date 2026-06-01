#!/usr/bin/env python3
"""
MongoDB-backed Plugin Store for Aurora/NeoArch
- Discovers plugins from a MongoDB collection
- Installs plugin code either from a stored "code" field or a URL (if available)
- No icon handling

Config:
- AURORA_MONGO_URI: full MongoDB URI (recommended)
- AURORA_MONGO_DB: database name (default: neoarch)
- AURORA_MONGO_COLLECTION: collection name (default: community_plugins)

Fallback config file if env var is not set:
- ~/.config/aurora/mongo_uri.txt containing the URI

Dependencies:
- pymongo (required)
- requests (optional, only if plugins provide a URL to fetch code)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Optional

# Optional imports
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except Exception:
    MongoClient = None  # type: ignore
    MONGO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    requests = None  # type: ignore
    REQUESTS_AVAILABLE = False


class MongoPluginStore:
    """Manages community plugin discovery via MongoDB."""

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "aurora"
        self.plugins_dir = self.config_dir / "plugins"

        self.mongo_uri = os.environ.get("AURORA_MONGO_URI") or self._read_uri_from_file()
        self.db_name = os.environ.get("AURORA_MONGO_DB", "neoarch")
        self.collection_name = os.environ.get("AURORA_MONGO_COLLECTION", "community_plugins")

        self.client: Optional[MongoClient] = None
        self.db = None
        self.col = None

        if MONGO_AVAILABLE and self.mongo_uri:
            try:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=4000)
                # Trigger a simple ping to validate connection
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                self.col = self.db[self.collection_name]
            except Exception:
                self.client = None
                self.db = None
                self.col = None

    def _read_uri_from_file(self) -> Optional[str]:
        try:
            p = self.config_dir / "mongo_uri.txt"
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return None

    def is_configured(self) -> bool:
        return bool(MONGO_AVAILABLE and self.col is not None)

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins from MongoDB.

        Expected document shape (flexible):
        {
          id: str,            # required unique id/slug
          name: str,          # display name
          author: str,        # developer/maintainer
          version: str,       # semantic version
          description: str,   # short description
          code: str,          # optional: plugin script content
          url: str,           # optional: URL to raw .py
          downloads: int,     # optional
          updated_at: any     # optional (for sorting)
        }
        """
        if not self.is_configured():
            return []
        try:
            # Prefer most popular/recent first
            cursor = self.col.find({}, {
                "_id": 1,
                "id": 1,
                "name": 1,
                "author": 1,
                "version": 1,
                "description": 1,
                "downloads": 1,
                "url": 1,
                "code": 1,
                "updated_at": 1,
            }).sort([
                ("downloads", -1),
                ("updated_at", -1),
                ("name", 1),
            ])
            items: List[Dict] = []
            for doc in cursor:
                pid = (doc.get("id") or str(doc.get("_id") or "")).strip()
                if not pid:
                    # Skip records without a stable id
                    continue
                items.append({
                    "id": pid,
                    "name": doc.get("name") or pid,
                    "author": doc.get("author") or "Unknown",
                    "version": doc.get("version") or "1.0.0",
                    "description": doc.get("description") or "",
                    "downloads": int(doc.get("downloads") or 0),
                    # keep url/code for install stage
                    "url": doc.get("url"),
                    "code": doc.get("code"),
                })
            return items
        except Exception:
            return []

    def install_community_plugin(self, plugin_id: str) -> bool:
        """Install a plugin by id.
        - If a 'code' field exists, write it directly.
        - Else if a 'url' exists, fetch it (requires requests).
        """
        if not self.is_configured():
            return False
        try:
            doc = self.col.find_one({"id": plugin_id}) or self.col.find_one({"_id": plugin_id})
            if not doc:
                return False

            code_text: Optional[str] = None
            if isinstance(doc.get("code"), str) and doc.get("code").strip():
                code_text = doc.get("code").strip()
            elif isinstance(doc.get("url"), str) and doc.get("url").strip():
                if not REQUESTS_AVAILABLE:
                    return False
                resp = requests.get(doc.get("url").strip(), timeout=30)
                if resp.status_code == 200:
                    code_text = resp.text

            if not code_text:
                return False

            # Write the plugin file
            safe_id = self._safe_id(plugin_id)
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            plugin_path = self.plugins_dir / f"{safe_id}.py"
            with open(plugin_path, "w", encoding="utf-8") as f:
                f.write(code_text)

            # Increment downloads counter (best-effort)
            try:
                if doc.get("_id") is not None:
                    self.col.update_one({"_id": doc["_id"]}, {"$inc": {"downloads": 1}})
                else:
                    self.col.update_one({"id": plugin_id}, {"$inc": {"downloads": 1}})
            except Exception:
                pass
            return True
        except Exception:
            return False

    def create_plugin_template(self, plugin_name: str, description: str = "") -> str:
        """Generate a plugin template (kept for UI compatibility)."""
        # Define template variables to avoid undefined variable errors
        e = "example_error"
        param = "example_param"
        
        template = f'''"""
{plugin_name} - NeoArch Plugin
{description}

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """
    Called when NeoArch starts up
    Use this to initialize your plugin
    """
    try:
        print(f"🚀 {plugin_name} plugin loaded!")
        # Add your startup code here

    except Exception as e:
        print(f"Error in {plugin_name} startup: {e}")

def on_tick(app):
    """
    Called periodically (every 60 seconds)
    Use this for background tasks
    """
    try:
        # Add your periodic tasks here
        pass
    except Exception as e:
        print(f"Error in {plugin_name} tick: {e}")

def on_view_changed(app, view_id):
    """
    Called when user switches between views
    view_id can be: "discover", "updates", "installed", "bundles", "plugins", "settings"
    """
    try:
        if view_id == "discover":
            # User switched to discover page
            pass
        elif view_id == "plugins":
            # User switched to plugins page
            pass
    except Exception as e:
        print(f"Error in {plugin_name} view change: {e}")

# Add your custom functions below
def my_custom_function(app, param=None):
    """
    Example custom function
    You can call this from other parts of your plugin
    """
    try:
        print(f"{plugin_name}: Custom function called with param: {param}")
        # Add your custom logic here
    except Exception as e:
        print(f"Error in {plugin_name} custom function: {e}")
'''

        return template

    def _safe_id(self, s: str) -> str:
        return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in (s or "").strip())
