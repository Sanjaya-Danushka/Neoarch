#!/usr/bin/env python3
"""
NeoArch Scheduled Update Script
Runs independently to check for updates and prompt user when app is not running
"""

import time
import subprocess
import os
import json
import sys
from pathlib import Path
from utils import sys_utils

class ScheduledUpdater:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'aurora'
        self.settings_file = self.config_dir / 'settings.json'
        self.last_update_file = self.config_dir / 'last_update.json'

        self.settings = self.load_settings()
        self.last_update_data = self.load_last_update_data()

    def load_settings(self):
        """Load settings from config file"""
        default_settings = {
            'auto_update_enabled': False,
            'auto_update_interval_days': 7,
            'snapshot_before_update': False
        }

        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                default_settings.update(loaded)
            except Exception as e:
                print(f"Warning: Could not load settings: {e}")

        return default_settings

    def load_last_update_data(self):
        """Load last update tracking data"""
        default_data = {
            'last_update': 0,
            'last_check': 0
        }

        if self.last_update_file.exists():
            try:
                with open(self.last_update_file, 'r') as f:
                    loaded = json.load(f)
                default_data.update(loaded)
            except Exception as e:
                print(f"Warning: Could not load last update data: {e}")

        return default_data

    def save_last_update_data(self):
        """Save last update tracking data"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.last_update_file, 'w') as f:
                json.dump(self.last_update_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save last update data: {e}")

    def cmd_exists(self, cmd):
        """Check if command exists"""
        return subprocess.run(['which', cmd], capture_output=True).returncode == 0

    def check_for_updates(self):
        """Main update check logic"""
        if not self.settings.get('auto_update_enabled', False):
            return False

        days = int(self.settings.get('auto_update_interval_days', 7))
        interval_seconds = days * 24 * 3600

        now = time.time()

        # Check once per hour
        if self.last_update_data.get('last_check', 0) > 0:
            if now - self.last_update_data['last_check'] < 3600:
                return False

        self.last_update_data['last_check'] = now

        # Check if it's time for update
        if self.last_update_data.get('last_update', 0) > 0:
            if now - self.last_update_data['last_update'] < interval_seconds:
                return False

        # Ask user permission
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.attributes('-topmost', True)  # Bring to front

            result = messagebox.askyesno(
                "NeoArch - Scheduled Update",
                f"It's been {days} days since the last update.\n\n"
                "Would you like to update your system now?\n\n"
                "This will update packages and create snapshots if enabled.",
                default=messagebox.YES
            )

            root.destroy()

            if not result:
                return False

        except ImportError:
            # Fallback to zenity if tkinter not available
            try:
                result = subprocess.run([
                    'zenity', '--question',
                    '--title', 'NeoArch - Scheduled Update',
                    '--text', f"It's been {days} days since the last update.\n\nWould you like to update your system now?\n\nThis will update packages and create snapshots if enabled.",
                    '--default-cancel'
                ], capture_output=True)

                if result.returncode != 0:
                    return False
            except Exception:
                print("No GUI available for user interaction")
                return False

        # User approved - perform update
        self.last_update_data['last_update'] = now
        self.save_last_update_data()

        return self.perform_update()

    def perform_update(self):
        """Perform the actual system update"""
        print("Starting scheduled system updates...")

        # Create snapshot before updates if enabled
        if self.settings.get('snapshot_before_update', False):
            self.create_snapshot()

        update_success = False

        # Update pacman packages
        if self.cmd_exists("pacman"):
            print("Updating pacman packages...")
            # Import here to avoid circular imports
            from utils.workers import get_auth_command
            from services.askpass_service import prepare_askpass_env
            
            env, _ = prepare_askpass_env()
            auth_cmd = get_auth_command(env)
            cmd = auth_cmd + ["pacman", "-Syu", "--noconfirm"]
            print(f"Using {auth_cmd[0]} for pacman authentication")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
            if result.returncode == 0:
                print("Pacman updates completed successfully")
                update_success = True
            else:
                print(f"Pacman update failed: {result.stderr}")

        # Update AUR packages if an AUR helper is available
        aur_helper = sys_utils.get_aur_helper()
        if aur_helper:
            print(f"Updating AUR packages using {aur_helper}...")
            try:
                env = os.environ.copy()
                result = subprocess.run([aur_helper, "-Syu", "--noconfirm", "--sudoflags", "-A"],
                                      capture_output=True, text=True, timeout=1800, env=env)
                if result.returncode == 0:
                    print("AUR updates completed successfully")
                    update_success = True
                else:
                    print(f"AUR update failed: {result.stderr}")
            except Exception as e:
                print(f"AUR update error: {e}")

        # Update Flatpak
        if self.cmd_exists("flatpak"):
            print("Updating Flatpak packages...")
            scopes = [["--user"], ["--system"]] if self.cmd_exists("sudo") else [["--user"]]
            for scope in scopes:
                try:
                    result = subprocess.run(["flatpak"] + scope + ["update", "-y"],
                                          capture_output=True, text=True, timeout=900)
                    if result.returncode == 0:
                        print(f"Flatpak {scope[0]} updates completed")
                        update_success = True
                    else:
                        print(f"Flatpak {scope[0]} update failed: {result.stderr}")
                except Exception as e:
                    print(f"Flatpak {scope[0]} update error: {e}")

        # Update npm global packages
        if self.cmd_exists("npm"):
            print("Updating npm global packages...")
            try:
                env = os.environ.copy()
                npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                os.makedirs(npm_prefix, exist_ok=True)
                env['npm_config_prefix'] = npm_prefix
                env['NPM_CONFIG_PREFIX'] = npm_prefix
                env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')

                result = subprocess.run(["npm", "update", "-g"],
                                      capture_output=True, text=True, timeout=600, env=env)
                if result.returncode == 0:
                    print("NPM global packages updated")
                    update_success = True
                else:
                    print(f"NPM update failed: {result.stderr}")
            except Exception as e:
                print(f"NPM update error: {e}")

        if update_success:
            print(f"System update completed successfully! Next check in {self.settings.get('auto_update_interval_days', 7)} days.")

            # Show notification
            try:
                subprocess.run(["notify-send", "NeoArch Update", "System update completed successfully!"],
                             capture_output=True)
            except Exception:
                pass
        else:
            print("Some updates failed. Check the logs for details.")

        return update_success

    def create_snapshot(self):
        """Create a system snapshot"""
        if not self.cmd_exists("timeshift"):
            print("Timeshift not installed - skipping snapshot")
            return False

        # Count existing snapshots and clean up if needed
        try:
            result = subprocess.run(["timeshift", "--list"], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                snapshot_count = sum(1 for line in lines if line.strip() and not line.startswith('Num') and not line.startswith('---'))

                # Keep at most 2 snapshots: delete all but the 2 most recent
                if snapshot_count > 2:
                    delete_result = subprocess.run(["pkexec", "timeshift", "--delete-all", "--skip", "2"],
                                                 capture_output=True, text=True, timeout=300)
                    if delete_result.returncode == 0:
                        print("Cleaned up old snapshots (kept latest 2)")
                    else:
                        print(f"Failed to clean up snapshots: {delete_result.stderr}")
        except Exception as e:
            print(f"Error checking snapshots: {e}")

        # Create new snapshot
        timestamp = subprocess.run(["date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True).stdout.strip()
        comment = f"NeoArch pre-update snapshot {timestamp}"

        result = subprocess.run(["pkexec", "timeshift", "--create", "--comments", comment],
                              capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"Pre-update snapshot created: {comment}")
            return True
        else:
            print(f"Failed to create pre-update snapshot: {result.stderr}")
            return False


def main():
    """Main function"""
    updater = ScheduledUpdater()

    if updater.check_for_updates():
        print("Update process completed")
    else:
        print("No update needed or user declined")


if __name__ == "__main__":
    main()
