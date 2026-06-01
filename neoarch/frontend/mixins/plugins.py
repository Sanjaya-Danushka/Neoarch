"""Plugin system mixin for the main window."""

import os
import importlib
import traceback
import shutil

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog, QTabWidget


class _PluginsMixin:
    def get_user_plugins_dir(self):
        p = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'plugins')
        try:
            os.makedirs(p, exist_ok=True)
        except Exception:
            pass
        return p

    def scan_plugins(self):
        plugs = []
        try:
            user_dir = self.get_user_plugins_dir()
            for fn in sorted(os.listdir(user_dir)):
                if fn.endswith('.py'):
                    plugs.append({'name': os.path.splitext(fn)[0], 'path': os.path.join(user_dir, fn), 'location': 'User'})
        except Exception:
            pass
        return plugs

    def initialize_plugins(self):
        try:
            self.ensure_default_plugins(force_enable=True)
            self.reload_plugins()
            self.run_plugin_hook('on_startup')
            try:
                self.plugin_timer.start()
            except Exception:
                pass
            # Start session auth and update loading only if auto-check is enabled
            if self.settings.get('auto_check_updates', True):
                QTimer.singleShot(0, self._startup_auth_and_sync)
        except Exception as e:
            self.log(f"Plugin init error: {e}")

    def ensure_default_plugins(self, force_enable=False):
        user_dir = self.get_user_plugins_dir()
        defaults = {
            'auto_check_updates.py': (
                """
def on_startup(app):
    pass
                """.strip()
            ),
            'flathub_remote.py': (
                """
def on_startup(app):
    try:
        app.ensure_flathub_user_remote()
    except Exception as e:
        try:
            app.log(f"flathub_remote plugin: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'bundle_autoload.py': (
                """
from PyQt6.QtCore import QTimer
import os, json

def on_view_changed(app, view_id):
    if view_id != "bundles":
        return
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles')
        path = os.path.join(base, 'default.json')
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list):
            return
        existing = {(i.get('source'), (i.get('id') or i.get('name'))) for i in app.bundle_items}
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            src = (it.get('source') or '').strip()
            nm = (it.get('name') or '').strip()
            pid = (it.get('id') or nm).strip()
            if not src or not nm:
                continue
            key = (src, pid or nm)
            if key not in existing:
                app.bundle_items.append({'name': nm, 'id': pid or nm, 'version': (it.get('version') or '').strip(), 'source': src})
                existing.add(key)
                added += 1
        if added:
            try:
                app.refresh_bundles_table()
            except Exception:
                pass
            try:
                app._show_message("Bundle", f"Loaded {added} items from default bundle")
            except Exception:
                pass
    except Exception as e:
        try:
            app.log(f"bundle_autoload plugin: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'notify_install.py': (
                """
from PyQt6.QtWidgets import QMessageBox

def on_startup(app):
    try:
        app.installation_progress.connect(lambda status, can_cancel: _on_status(app, status))
    except Exception:
        pass

def _on_status(app, status):
    try:
        if status == "success":
            QMessageBox.information(app, "Install", "Installation complete.")
        elif status == "failed":
            QMessageBox.warning(app, "Install", "Installation failed. See console for details.")
        elif status == "cancelled":
            QMessageBox.information(app, "Install", "Installation cancelled.")
    except Exception:
        try:
            app._show_message("Install", status)
        except Exception:
            pass
                """.strip()
            ),
            'bundle_autosave.py': (
                """
import os, json, hashlib

_last_hash = None

def _hash_items(items):
    try:
        s = json.dumps(items or [], sort_keys=True)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()
    except Exception:
        return None

def _save(app):
    try:
        if not app.settings.get('bundle_autosave', True):
            return
        path = app.settings.get('bundle_autosave_path')
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        items = list(app.bundle_items)
        global _last_hash
        h = _hash_items(items)
        if h and h == _last_hash:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'app': 'NeoArch', 'items': items}, f, indent=2)
        _last_hash = h
        try:
            app._show_message('Bundle', f'Autosaved bundle to {path}')
        except Exception:
            pass
    except Exception as e:
        try:
            app.log(f"bundle_autosave plugin: {e}")
        except Exception:
            pass

def on_view_changed(app, view_id):
    if view_id == 'bundles':
        _save(app)

def on_tick(app):
    _save(app)
                """.strip()
            ),
            'auto_refresh_updates.py': (
                """
import time

_last = 0

def on_tick(app):
    global _last
    try:
        minutes = int(app.settings.get('auto_refresh_updates_minutes') or 0)
    except Exception:
        minutes = 0
    if minutes <= 0:
        return
    now = time.time()
    if _last and now - _last < minutes * 60:
        return
    _last = now
    try:
        if app.current_view == 'updates':
            app.load_updates()
    except Exception as e:
        try:
            app.log(f"auto_refresh_updates: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'auto_update.py': (
                """
import time
import subprocess
import os
import json

_last_update = 0
_last_check = 0
_state_file = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'last_update.json')

def _load_state():
    try:
        with open(_state_file, 'r') as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _save_state(data):
    try:
        os.makedirs(os.path.dirname(_state_file), exist_ok=True)
        with open(_state_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

_state = _load_state()
_last_update = float(_state.get('last_update', 0) or 0)
_last_check = float(_state.get('last_check', 0) or 0)

def on_tick(app):
    global _last_update, _last_check, _state
    try:
        if not app.settings.get('auto_update_enabled', False):
            return
        days = int(app.settings.get('auto_update_interval_days', 7))
        interval_seconds = days * 24 * 3600
        now = time.time()
        if _last_check and now - _last_check < 3600:
            return
        _last_check = now
        _state['last_check'] = _last_check
        _save_state(_state)
        if _last_update and now - _last_update < interval_seconds:
            return
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(app, "Scheduled Update",
            f"It's been {days} days since the last update.\\n\\n"
            "Would you like to update your system now?\\n\\n"
            "This will update packages and create snapshots if enabled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if reply != QMessageBox.StandardButton.Yes:
            return
        _last_update = now
        _state['last_update'] = _last_update
        _save_state(_state)
        if app.settings.get('snapshot_before_update', False):
            try:
                if app.cmd_exists("timeshift"):
                    try:
                        result = subprocess.run(["timeshift", "--list"], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\\n')
                            snapshot_count = sum(1 for line in lines if line.strip() and not line.startswith('Num') and not line.startswith('---'))
                            if snapshot_count > 2:
                                delete_result = subprocess.run(["pkexec", "timeshift", "--delete-all", "--skip", "2"], capture_output=True, text=True, timeout=300)
                                if delete_result.returncode == 0:
                                    app.log("Auto-update: Cleaned up old snapshots (kept latest 2)")
                                else:
                                    app.log(f"Auto-update: Failed to clean up snapshots: {delete_result.stderr}")
                    except Exception as e:
                        app.log(f"Auto-update: Error checking snapshots: {e}")
                    timestamp = subprocess.run(["date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True).stdout.strip()
                    comment = f"NeoArch pre-update snapshot {timestamp}"
                    result = subprocess.run(["pkexec", "timeshift", "--create", "--comments", comment], capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        app.log(f"Auto-update: Pre-update snapshot created: {comment}")
                        app.show_message.emit("Snapshot", f"Pre-update snapshot created: {comment}")
                    else:
                        app.log(f"Auto-update: Failed to create pre-update snapshot: {result.stderr}")
            except Exception as e:
                app.log(f"Auto-update: Pre-update snapshot creation failed: {e}")
        update_success = False
        try:
            app.log("Auto-update: Starting scheduled system updates...")
            if app.cmd_exists("pacman"):
                pass  # inlined
                env, _ = app.prepare_askpass_env()
                auth_cmd = get_auth_command(env)
                cmd = auth_cmd + ["pacman", "-Syu", "--noconfirm"]
                app.log(f"Auto-update: Using {auth_cmd[0]} for pacman")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
                if result.returncode == 0:
                    app.log("Auto-update: Pacman updates completed successfully")
                    update_success = True
                    app.show_message.emit("Auto Update", "System packages updated successfully")
                else:
                    app.log(f"Auto-update: Pacman update failed: {result.stderr}")
                    app.show_message.emit("Auto Update", f"Pacman update failed: {result.stderr}")
            # Update AUR packages using any available AUR helper
            aur_helper = sys_utils.get_aur_helper(app.settings.get('aur_helper', 'auto') if app.settings.get('aur_helper', 'auto') != 'auto' else None)
            if aur_helper:
                try:
                    env, _ = app.prepare_askpass_env()
                    result = subprocess.run([aur_helper, "-Syu", "--noconfirm", "--sudoflags", "-A"], capture_output=True, text=True, timeout=1800, env=env)
                    if result.returncode == 0:
                        app.log(f"Auto-update: AUR updates completed successfully using {aur_helper}")
                        update_success = True
                    else:
                        app.log(f"Auto-update: AUR update failed: {result.stderr}")
                except Exception as e:
                    app.log(f"Auto-update: AUR update error: {e}")
            if app.cmd_exists("flatpak"):
                scopes = [["--user"], ["--system"]] if app.cmd_exists("sudo") else [["--user"]]
                for scope in scopes:
                    try:
                        result = subprocess.run(["flatpak"] + scope + ["update", "-y"], capture_output=True, text=True, timeout=900)
                        if result.returncode == 0:
                            app.log(f"Auto-update: Flatpak {scope[0]} updates completed")
                            update_success = True
                        else:
                            app.log(f"Auto-update: Flatpak {scope[0]} update failed: {result.stderr}")
                    except Exception as e:
                        app.log(f"Auto-update: Flatpak {scope[0]} update error: {e}")
            if app.cmd_exists("npm"):
                try:
                    env = os.environ.copy()
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env['npm_config_prefix'] = npm_prefix
                    env['NPM_CONFIG_PREFIX'] = npm_prefix
                    env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
                    result = subprocess.run(["npm", "update", "-g"], capture_output=True, text=True, timeout=600, env=env)
                    if result.returncode == 0:
                        app.log("Auto-update: NPM global packages updated")
                        update_success = True
                    else:
                        app.log(f"Auto-update: NPM update failed: {result.stderr}")
                except Exception as e:
                    app.log(f"Auto-update: NPM update error: {e}")
        except Exception as e:
            app.log(f"Auto-update: General error: {e}")
        if update_success:
            app.show_message.emit("Auto Update", f"System update completed successfully! Next check in {days} days.")
        else:
            app.show_message.emit("Auto Update", "Some updates failed. Check the console for details.")
    except Exception:
        pass
                """.strip()
            ),
        }
        for fname, code in defaults.items():
            fpath = os.path.join(user_dir, fname)
            write_needed = True
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        existing = f.read()
                    write_needed = existing.strip() != (code + "\n").strip()
                except Exception:
                    write_needed = True
            if write_needed:
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(code + "\n")
                except Exception as e:
                    self.log(f"Default plugin write failed {fname}: {e}")
            if force_enable:
                name = os.path.splitext(fname)[0]
                enabled = set(self.settings.get('enabled_plugins') or [])
                if name not in enabled:
                    enabled.add(name)
                    self.settings['enabled_plugins'] = sorted(enabled)
        if force_enable:
            self.save_settings()

    def load_enabled_plugins(self):
        loaded = []
        plugs = {p['name']: p for p in self.scan_plugins()}
        enabled = self.settings.get('enabled_plugins') or []
        for name in enabled:
            p = plugs.get(name)
            if not p:
                continue
            path = p.get('path')
            try:
                spec = importlib.util.spec_from_file_location(name, path)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                loaded.append(mod)
            except Exception as e:
                self.log(f"Failed to load plugin {name}: {e}\n{traceback.format_exc()}")
        return loaded

    def reload_plugins(self):
        self.plugins = self.load_enabled_plugins()

    def reload_plugins_and_notify(self):
        self.reload_plugins()
        self._show_message("Plugins", f"Reloaded {len(self.plugins)} plugin(s)")

    def install_default_plugins(self):
        self.ensure_default_plugins(force_enable=True)
        self.refresh_plugins_table()
        self.reload_plugins()
        self._show_message("Plugins", "Default plugins installed and enabled")

    def run_plugin_hook(self, hook_name, *args, **kwargs):
        for mod in self.plugins:
            try:
                func = getattr(mod, hook_name, None)
                if callable(func):
                    func(self, *args, **kwargs)
            except Exception as e:
                self.log(f"Plugin hook {hook_name} error: {e}\n{traceback.format_exc()}")

    def run_plugin_tick(self):
        try:
            self.run_plugin_hook('on_tick')
        except Exception:
            pass

    def install_plugin(self):
        path, _ = QFileDialog.getOpenFileName(self, "Install Plugin", os.path.expanduser('~'), "Python Plugin (*.py)")
        if not path:
            return
        try:
            dst = os.path.join(self.get_user_plugins_dir(), os.path.basename(path))
            shutil.copy2(path, dst)
            self._show_message("Install Plugin", f"Installed: {os.path.basename(path)}")
            # Refresh plugins table if it exists
            try:
                # Find the plugins widget and refresh it
                if hasattr(self, 'settings_container'):
                    tabs = self.settings_container.widget().findChild(QTabWidget)
                    if tabs:
                        for i in range(tabs.count()):
                            widget = tabs.widget(i)
                            if hasattr(widget, 'refresh_plugins_table'):
                                widget.refresh_plugins_table()
                                break
            except Exception:
                # Handle UI widget access errors gracefully
                pass
        except Exception as e:
            self._show_message("Install Plugin", f"Failed: {e}")

    def remove_selected_plugins(self):
        # This method needs to be called from the plugins settings widget
        # We'll implement it to work with the current table selection
        try:
            # Find the plugins widget and call its remove method
            if hasattr(self, 'settings_container'):
                tabs = self.settings_container.widget().findChild(QTabWidget)
                if tabs:
                    for i in range(tabs.count()):
                        widget = tabs.widget(i)
                        if hasattr(widget, 'remove_selected_plugins'):
                            widget.remove_selected_plugins()
                            break
        except Exception as e:
            self._show_message("Remove Plugins", f"Error: {e}")

    def refresh_plugins_table(self):
        # This method is used internally by the main class
        # The component will call this if needed
        pass
