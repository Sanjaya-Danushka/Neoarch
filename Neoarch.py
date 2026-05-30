#!/usr/bin/env python3
# cSpell:disable
"""
NeoArch - Backward-compatible wrapper.

All functionality has been refactored into the neoarch/ package.
This file provides backward compatibility for direct imports and usage.

Usage:
    python Neoarch.py          # Launch the application
    python -m neoarch           # Launch via the new entry point
"""

import sys
import types

from neoarch.main import main
from neoarch.frontend.main_window import ArchPkgManagerUniGetUI

from neoarch.resources.paths import APP_NAME, APP_VERSION, APP_ICON, PLUGINS_ITEMS_DIR, PROJECT_ROOT
from neoarch.resources.plugin_data import get_plugins_data, get_all_plugins_data

# Backend utilities
from neoarch.backend.sys_utils import (
    cmd_exists, get_aur_helper, get_available_aur_helpers,
    check_aur_authentication_support, get_missing_auth_tools, get_missing_dependencies,
)
from neoarch.backend.config_utils import (
    get_ignore_file_path, get_local_updates_file_path,
    load_ignored_updates, load_local_update_entries, save_ignored_updates,
)
from neoarch.backend.auth import get_sudo_askpass, prepare_askpass_env
from neoarch.backend.workers import CommandWorker

# Package operations
from neoarch.backend.package.installer import install_packages
from neoarch.backend.package.uninstaller import uninstall_packages
from neoarch.backend.package.updater import update_core_tools, update_packages
from neoarch.backend.package.loader import load_installed_packages, load_updates

# Service modules
from neoarch.backend.services.bundle import (
    add_selected_to_bundle, add_selected_to_community, clear_bundle,
    export_bundle, import_bundle, import_community_bundle, install_bundle,
    list_community_bundles, refresh_bundles_table, remove_selected_from_bundle,
)
from neoarch.backend.services.filter import apply_filters, apply_update_filters
from neoarch.backend.services.ignore import ignore_selected, manage_ignored
from neoarch.backend.services.help import show_about, show_help
from neoarch.backend.services.settings import (
    export_settings, import_settings, load_settings, save_settings,
)
from neoarch.backend.services.snapshot import (
    create_snapshot, delete_snapshots, restore_snapshot, revert_to_snapshot,
)


# === Module aliases for backward compatibility ===

config_utils = types.SimpleNamespace()
config_utils.get_ignore_file_path = get_ignore_file_path
config_utils.get_local_updates_file_path = get_local_updates_file_path
config_utils.load_ignored_updates = load_ignored_updates
config_utils.load_local_update_entries = load_local_update_entries
config_utils.save_ignored_updates = save_ignored_updates

sys_utils = types.SimpleNamespace()
sys_utils.check_aur_authentication_support = check_aur_authentication_support
sys_utils.cmd_exists = cmd_exists
sys_utils.get_aur_helper = get_aur_helper
sys_utils.get_available_aur_helpers = get_available_aur_helpers
sys_utils.get_missing_auth_tools = get_missing_auth_tools
sys_utils.get_missing_dependencies = get_missing_dependencies

install_service = types.SimpleNamespace()
install_service.install_packages = install_packages

bundle_service = types.SimpleNamespace()
bundle_service.add_selected_to_bundle = add_selected_to_bundle
bundle_service.add_selected_to_community = add_selected_to_community
bundle_service.clear_bundle = clear_bundle
bundle_service.export_bundle = export_bundle
bundle_service.import_bundle = import_bundle
bundle_service.import_community_bundle = import_community_bundle
bundle_service.install_bundle = install_bundle
bundle_service.list_community_bundles = list_community_bundles
bundle_service.refresh_bundles_table = refresh_bundles_table
bundle_service.remove_selected_from_bundle = remove_selected_from_bundle

filters_service = types.SimpleNamespace()
filters_service.apply_filters = apply_filters
filters_service.apply_update_filters = apply_update_filters

help_service = types.SimpleNamespace()
help_service.show_about = show_about
help_service.show_help = show_help

ignore_service = types.SimpleNamespace()
ignore_service.ignore_selected = ignore_selected
ignore_service.manage_ignored = manage_ignored

packages_service = types.SimpleNamespace()
packages_service.load_installed_packages = load_installed_packages
packages_service.load_updates = load_updates

settings_service = types.SimpleNamespace()
settings_service.export_settings = export_settings
settings_service.import_settings = import_settings
settings_service.load_settings = load_settings
settings_service.save_settings = save_settings

snapshot_service = types.SimpleNamespace()
snapshot_service.create_snapshot = create_snapshot
snapshot_service.delete_snapshots = delete_snapshots
snapshot_service.restore_snapshot = restore_snapshot
snapshot_service.revert_to_snapshot = revert_to_snapshot

uninstall_service = types.SimpleNamespace()
uninstall_service.uninstall_packages = uninstall_packages

update_service = types.SimpleNamespace()
update_service.update_core_tools = update_core_tools
update_service.update_packages = update_packages

askpass_service = types.SimpleNamespace()
askpass_service.get_sudo_askpass = get_sudo_askpass
askpass_service.prepare_askpass_env = prepare_askpass_env

if __name__ == "__main__":
    main()
