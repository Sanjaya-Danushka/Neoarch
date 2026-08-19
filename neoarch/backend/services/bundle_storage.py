"""Persistent bundle storage for multi-bundle management.

Bundles are stored as individual JSON files under ~/.config/neoarch/bundles/
with a manifest file tracking all bundles.
"""

import os
import json
import uuid

_BUNDLES_DIR = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "bundles")
_MANIFEST = os.path.join(_BUNDLES_DIR, "_manifest.json")


def _ensure_dir():
    os.makedirs(_BUNDLES_DIR, exist_ok=True)


def _safe_name(name):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name).strip("_") or "bundle"


def list_bundles():
    """Return list of {"key": str, "name": str, "count": int} sorted by name."""
    _ensure_dir()
    manifest = _load_manifest()
    bundles = []
    for key, meta in manifest.items():
        items = _load_items(key)
        bundles.append({"key": key, "name": meta.get("name", key), "count": len(items)})
    bundles.sort(key=lambda b: b["name"].lower())
    return bundles


def create_bundle(name="My Bundle", key=None):
    """Create a new bundle, return its key. If *key* is given, reuse it."""
    _ensure_dir()
    manifest = _load_manifest()
    if key is None:
        key = uuid.uuid4().hex[:12]
    manifest[key] = {"name": name}
    _save_manifest(manifest)
    _save_items(key, [])
    return key


def rename_bundle(key, new_name):
    """Rename a bundle. Returns True on success."""
    _ensure_dir()
    manifest = _load_manifest()
    if key not in manifest:
        return False
    manifest[key]["name"] = new_name
    _save_manifest(manifest)
    return True


def delete_bundle(key):
    """Delete a bundle. Returns True on success."""
    _ensure_dir()
    manifest = _load_manifest()
    if key not in manifest:
        return False
    del manifest[key]
    _save_manifest(manifest)
    path = os.path.join(_BUNDLES_DIR, f"{key}.json")
    if os.path.exists(path):
        os.remove(path)
    return True


def load_bundle(key):
    """Load items for a bundle key. Returns list of dicts."""
    _ensure_dir()
    return _load_items(key)


def save_bundle(key, items):
    """Save items for a bundle key."""
    _ensure_dir()
    _save_items(key, items)


def _load_manifest():
    if os.path.exists(_MANIFEST):
        try:
            with open(_MANIFEST, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_manifest(data):
    with open(_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_items(key):
    path = os.path.join(_BUNDLES_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "items" in data:
                return data["items"]
        except Exception:
            pass
    return []


def _save_items(key, items):
    path = os.path.join(_BUNDLES_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def export_bundle_json(key):
    """Export a bundle as a JSON string for file export."""
    manifest = _load_manifest()
    meta = manifest.get(key, {})
    items = _load_items(key)
    return json.dumps({
        "app": "NeoArch",
        "bundle_name": meta.get("name", key),
        "items": items,
    }, indent=2)


def import_bundle_json(json_str):
    """Import bundle items from a JSON string. Returns (name, items) or (None, [])."""
    try:
        data = json.loads(json_str)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return None, []
        name = data.get("bundle_name", "Imported Bundle")
        return name, items
    except Exception:
        return None, []
