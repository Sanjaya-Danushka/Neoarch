"""MongoDB-backed plugin store for community plugin discovery and installation.

Provides an alternative to the GitHub-based PluginStore, allowing plugins
to be stored and retrieved from a MongoDB collection with support for
inline code storage and URL-based fetching.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from pymongo import MongoClient as _MongoClient
    MONGO_AVAILABLE = True
except Exception:
    _MongoClient = None
    MONGO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    requests = None
    REQUESTS_AVAILABLE = False

__all__ = ["MongoPluginStore"]


class MongoPluginStore:
    """Manages community plugin discovery via MongoDB.

    Reads configuration from environment variables or a local config file:
        AURORA_MONGO_URI: Full MongoDB URI.
        AURORA_MONGO_DB: Database name (default: neoarch).
        AURORA_MONGO_COLLECTION: Collection name (default: community_plugins).

    Fallback: ~/.config/aurora/mongo_uri.txt
    """

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "aurora"
        self.plugins_dir = self.config_dir / "plugins"

        self.mongo_uri = os.environ.get("AURORA_MONGO_URI") or self._read_uri_from_file()
        self.db_name = os.environ.get("AURORA_MONGO_DB", "neoarch")
        self.collection_name = os.environ.get("AURORA_MONGO_COLLECTION", "community_plugins")

        self.client: Any = None
        self.db: Any = None
        self.col: Any = None

        if MONGO_AVAILABLE and self.mongo_uri:
            assert _MongoClient is not None
            try:
                self.client = _MongoClient(self.mongo_uri, serverSelectionTimeoutMS=4000)
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                self.col = self.db[self.collection_name]
            except Exception:
                self.client = None
                self.db = None
                self.col = None

    def _read_uri_from_file(self) -> Optional[str]:
        """Read MongoDB URI from the local config file."""
        try:
            p = self.config_dir / "mongo_uri.txt"
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return None

    def is_configured(self) -> bool:
        """Check if the MongoDB store is properly configured and connected."""
        return bool(MONGO_AVAILABLE and self.col is not None)

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins from MongoDB.

        Expected document shape:
        {
            id: str,            # unique identifier/slug
            name: str,          # display name
            author: str,        # developer
            version: str,       # semantic version
            description: str,   # short description
            code: str,          # optional: plugin script content
            url: str,           # optional: URL to raw .py
            downloads: int,     # optional
            updated_at: any     # optional (for sorting)
        }

        Returns:
            list: Plugin metadata dictionaries.
        """
        if not self.is_configured():
            return []
        try:
            cursor = self.col.find({}, {
                "_id": 1, "id": 1, "name": 1, "author": 1,
                "version": 1, "description": 1, "downloads": 1,
                "url": 1, "code": 1, "updated_at": 1,
            }).sort([
                ("downloads", -1),
                ("updated_at", -1),
                ("name", 1),
            ])
            items: List[Dict] = []
            for doc in cursor:
                pid = (doc.get("id") or str(doc.get("_id") or "")).strip()
                if not pid:
                    continue
                items.append({
                    "id": pid,
                    "name": doc.get("name") or pid,
                    "author": doc.get("author") or "Unknown",
                    "version": doc.get("version") or "1.0.0",
                    "description": doc.get("description") or "",
                    "downloads": int(doc.get("downloads") or 0),
                    "url": doc.get("url"),
                    "code": doc.get("code"),
                })
            return items
        except Exception:
            return []

    def install_community_plugin(self, plugin_id: str) -> bool:
        """Install a plugin by ID.

        Uses inline 'code' field if available, otherwise fetches from 'url'.
        Increments the download counter on success.

        Args:
            plugin_id: Unique identifier of the plugin.

        Returns:
            bool: True if installation succeeded.
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
                assert requests is not None
                resp = requests.get(doc.get("url").strip(), timeout=30)
                if resp.status_code == 200:
                    code_text = resp.text

            if not code_text:
                return False

            safe_id = self._safe_id(plugin_id)
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            plugin_path = self.plugins_dir / f"{safe_id}.py"
            with open(plugin_path, "w", encoding="utf-8") as f:
                f.write(code_text)

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
        """Generate a plugin template string (UI compatibility wrapper).

        Args:
            plugin_name: Name of the plugin.
            description: Short description.

        Returns:
            str: Plugin template source code.
        """
        return f'''"""
{plugin_name} - NeoArch Plugin
{description}

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """Called when NeoArch starts up. Use this to initialize your plugin."""
    try:
        print(f"Plugin {plugin_name} loaded!")
    except Exception as e:
        print(f"Error in {plugin_name} startup: {{e}}")

def on_tick(app):
    """Called periodically (every 60 seconds). Use this for background tasks."""
    try:
        pass
    except Exception as e:
        print(f"Error in {plugin_name} tick: {{e}}")

def on_view_changed(app, view_id):
    """Called when user switches between views."""
    try:
        if view_id == "discover":
            pass
        elif view_id == "plugins":
            pass
    except Exception as e:
        print(f"Error in {plugin_name} view change: {{e}}")

def my_custom_function(app, param=None):
    """Example custom function."""
    try:
        print(f"{plugin_name}: Custom function called with param: {{param}}")
    except Exception as e:
        print(f"Error in {plugin_name} custom function: {{e}}")
'''

    @staticmethod
    def _safe_id(s: str) -> str:
        """Sanitize a string for use as a safe filename."""
        return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in (s or "").strip())
