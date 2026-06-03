"""Settings management services for persisting and loading app configuration.

Manages user preferences stored in ~/.config/neoarch/settings.json with
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
    'bundle_autosave_path': os.path.join(os.path.expanduser('~'), '.config', 'neoarch', 'bundles', 'default.json'),
    'auto_refresh_updates_minutes': 0,
    'auto_update_enabled': False,
    'auto_update_interval_days': 7,
    'snapshot_before_update': False,
    'aur_helper': 'auto',
    # Appearance
    'theme': 'dark',
    'accent_color': '#00BFAE',
    'font_size': 13,
    'source_accent_colors': True,
    # Notifications
    'notify_desktop': True,
    'notify_inapp': True,
    'notify_sound': False,
    'notify_on_install': True,
    'notify_on_updates': True,
    'notify_on_errors': True,
    'notify_cooldown': 10,
    # Logging
    'log_level': 'INFO',
    'log_to_console': False,
    'log_file_path': '',
    'log_max_size_mb': 5,
    # Proxy / Network
    'proxy_type': 'none',
    'proxy_host': '',
    'proxy_port': 8080,
    'request_timeout': 30,
    'verify_ssl': True,
    'parallel_network': True,
}


def _get_settings_path() -> str:
    """Get the path to the settings JSON file."""
    base = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
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
