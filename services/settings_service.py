import os
import json
from PyQt6.QtWidgets import QFileDialog

def load_settings():
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora')
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, 'settings.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        default = {
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
            'aur_helper': 'auto'  # auto, yay, paru, trizen, or pikaur
        }
        default.update(data if isinstance(data, dict) else {})
        return default
    except Exception:
        return {
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
            'aur_helper': 'auto'  # auto, yay, paru, trizen, or pikaur
        }


def save_settings(settings, log=None):
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora')
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, 'settings.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        if log:
            log(f"Settings save error: {str(e)}")


def export_settings(app):
    path, _ = QFileDialog.getSaveFileName(app, "Export Settings", os.path.expanduser('~'), "Settings JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(app.settings, f, indent=2)
        app._show_message("Export Settings", f"Saved to {path}")
    except Exception as e:
        app._show_message("Export Settings", f"Failed: {e}")


def import_settings(app):
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
