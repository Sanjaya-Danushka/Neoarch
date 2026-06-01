"""Settings management services for persisting and loading app configuration.

Manages user preferences stored in ~/.config/aurora/settings.json with
sensible defaults. Supports export and import of settings to/from JSON files.
"""

import os
import json
from PyQt6.QtWidgets import QFileDialog

__all__ = ["load_settings", "save_settings", "export_settings", "import_settings"]

DEFAULT_SETTINGS = {
    'auto_check_updates': True,
    'npm_user_mode': True,
    'include_local_source': True,
    'enabled_plugins': [],
    'bundle_autosave': True,
    'bundle_autosave_path': os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json'),
    'auto_refresh_updates_minutes': 0,
    'auto_update_enabled': False,
    'auto_update_interval_days': 7,
    'snapshot_before_update': False,
    'aur_helper': 'auto',
}


def _get_settings_path() -> str:
    """Get the path to the settings JSON file."""
    base = os.path.join(os.path.expanduser('~'), '.config', 'aurora')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'settings.json')


def load_settings() -> dict:
    """Load app settings from disk, merged with defaults."""
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        defaults = dict(DEFAULT_SETTINGS)
        defaults.update(data if isinstance(data, dict) else {})
        return defaults
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict, log=None) -> None:
    """Save app settings to disk."""
    try:
        path = _get_settings_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        if log:
            log(f"Settings save error: {str(e)}")


def export_settings(app) -> None:
    """Export current settings to a user-chosen JSON file."""
    path, _ = QFileDialog.getSaveFileName(app, "Export Settings", os.path.expanduser('~'), "Settings JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(app.settings, f, indent=2)
        app._show_message("Export Settings", f"Saved to {path}")
    except Exception as e:
        app._show_message("Export Settings", f"Failed: {e}")


def import_settings(app) -> None:
    """Import settings from a user-chosen JSON file."""
    path, _ = QFileDialog.getOpenFileName(app, "Import Settings", os.path.expanduser('~'), "Settings JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            app.settings.update(data)
            save_settings(app.settings, app.log)
            app.build_settings_ui()
            app._show_message("Import Settings", "Imported")
    except Exception as e:
        app._show_message("Import Settings", f"Failed: {e}")
