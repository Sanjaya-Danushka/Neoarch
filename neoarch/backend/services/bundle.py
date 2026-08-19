"""Bundle management services for creating, importing, and installing package bundles.

Bundles are JSON-based collections of packages from any source that can be
exported, imported, shared with the community, and installed in batches.
"""

import os
import json
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from neoarch.backend.package.installer import install_packages

__all__ = [
    "add_selected_to_bundle", "refresh_bundles_table", "export_bundle",
    "import_bundle", "remove_selected_from_bundle", "clear_bundle",
    "install_bundle", "add_selected_to_community", "list_community_bundles",
    "import_community_bundle",
]


def _auto_save(app):
    """Persist the active bundle to disk if multi-bundle mode is active."""
    key = getattr(app, '_active_bundle_key', '')
    if not key:
        return
    try:
        from neoarch.backend.services.bundle_storage import save_bundle, list_bundles
        name = "My Bundle"
        for b in list_bundles():
            if b["key"] == key:
                name = b["name"]
                break
        save_bundle(key, app.bundle_items)
    except Exception:
        pass


def add_selected_to_bundle(app):
    """Add currently selected packages from the main table to the bundle."""
    items = []
    # Modern table (Discover/Updates/Installed views)
    if hasattr(app, 'updates_table') and app.updates_table and hasattr(app.updates_table, 'checked_packages'):
        for pkg in app.updates_table.checked_packages():
            if pkg.get("name") and pkg.get("source"):
                items.append(pkg)
    # Legacy table fallback
    if not items:
        for row in range(app.package_table.rowCount()):
            checkbox = app.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                info = app.get_row_info(row)
                if info.get("name") and info.get("source"):
                    items.append(info)
    if not items:
        app.log("No selected rows to add to bundle")
        return
    existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
    added = 0
    for it in items:
        key = (it.get('source'), it.get('id') or it.get('name'))
        if key not in existing:
            app.bundle_items.append(it)
            existing.add(key)
            added += 1
    app.log(f"Added {added} item(s) to bundle")
    _auto_save(app)
    if app.current_view == "bundles":
        refresh_bundles_table(app)


def refresh_bundles_table(app):
    """Refresh the updates table to show current bundle items."""
    if app.current_view != "bundles":
        return
    if not hasattr(app, 'updates_table') or not app.updates_table:
        return
    if not app.bundle_items:
        key = getattr(app, '_active_bundle_key', '')
        if key:
            from neoarch.backend.services.bundle_storage import load_bundle
            app.bundle_items = load_bundle(key)
    table = app.updates_table
    table.set_bundles_mode(True)
    table.set_loading(False)
    table.set_empty_text(
        "No packages in bundle",
        "Add packages from Discover, Updates, or Installed views")
    mapped = []
    for it in app.bundle_items:
        mapped.append({
            'name': it.get('name', ''),
            'id': it.get('id') or it.get('name', ''),
            'version': it.get('version', '—'),
            'new_version': '',
            'source': it.get('source', ''),
            'description': it.get('desc') or it.get('description') or '',
            'download_size': '—',
            'installed_date': 0,
            'status': 'Installed' if it.get('_installed') else 'Available',
            '_installed': it.get('_installed', False),
            '_src': it,
        })
    table.set_enrich(False)
    table.set_packages(mapped)
    try:
        app._update_bundle_buttons()
    except Exception:
        pass


def export_bundle(app):
    """Export the current bundle items to a JSON file."""
    if not app.bundle_items:
        app.display_message("Export Bundle", "Bundle is empty")
        return
    path, _ = QFileDialog.getSaveFileName(app, "Export Bundle", os.path.expanduser("~"), "Bundle JSON (*.json)")
    if not path:
        return
    data = {"app": "NeoArch", "items": app.bundle_items}
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        app.display_message("Export Bundle", f"Saved {len(app.bundle_items)} items to {path}")
    except Exception as e:
        app.display_message("Export Bundle", f"Failed: {e}")


def import_bundle(app):
    """Import bundle items from a JSON file into the current bundle."""
    path, _ = QFileDialog.getOpenFileName(app, "Import Bundle", os.path.expanduser("~"), "Bundle JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list):
            app.display_message("Import Bundle", "Invalid bundle file")
            return
        existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            src = (it.get('source') or '').strip()
            nm = (it.get('name') or '').strip()
            pkg_id = (it.get('id') or nm).strip()
            if not src or not nm:
                continue
            key = (src, pkg_id or nm)
            if key not in existing:
                app.bundle_items.append({
                    'name': nm,
                    'id': pkg_id or nm,
                    'version': (it.get('version') or '').strip(),
                    'source': src,
                })
                existing.add(key)
                added += 1
        app.display_message("Import Bundle", f"Added {added} items")
        _auto_save(app)
        if app.current_view == "bundles":
            refresh_bundles_table(app)
    except Exception as e:
        app.display_message("Import Bundle", f"Failed: {e}")


def remove_selected_from_bundle(app):
    """Remove selected items from the current bundle."""
    if app.current_view != "bundles":
        return
    keys_to_remove = []
    for row in range(app.package_table.rowCount()):
        chk = app.get_row_checkbox(row)
        if chk is not None and chk.isChecked():
            info = app.get_row_info(row, view_id='bundles')
            keys_to_remove.append((info.get('source'), info.get('id') or info.get('name')))
    if not keys_to_remove:
        app.log("No selected items to remove from bundle")
        return
    before = len(app.bundle_items)
    app.bundle_items = [it for it in app.bundle_items if (it.get('source'), it.get('id') or it.get('name')) not in keys_to_remove]
    removed = before - len(app.bundle_items)
    app.log(f"Removed {removed} items from bundle")
    _auto_save(app)
    refresh_bundles_table(app)


def clear_bundle(app):
    """Clear all items from the current bundle."""
    if not app.bundle_items:
        return
    app.bundle_items = []
    _auto_save(app)
    refresh_bundles_table(app)


def install_bundle(app):
    """Install all packages in the current bundle."""
    if not app.bundle_items:
        app.display_message("Install Bundle", "Bundle is empty")
        return
    by_src = {}
    for it in list(app.bundle_items):
        src = it.get('source') or 'pacman'
        name = it.get('name') or ''
        pkg_id = it.get('id') or name
        if not name:
            continue
        token = pkg_id if src == 'Flatpak' else name
        by_src.setdefault(src, []).append(token)
    if not by_src:
        app.display_message("Install Bundle", "No valid items to install")
        return
    install_packages(app, by_src)


def add_selected_to_community(app):
    """Share selected bundle items with the community hub."""
    if app.current_view != "bundles":
        app.display_message("Add to Community", "This feature is only available in bundles view")
        return
    selected_items = []
    for row in range(app.package_table.rowCount()):
        checkbox = app.get_row_checkbox(row)
        if checkbox is not None and checkbox.isChecked():
            info = app.get_row_info(row, view_id='bundles')
            if info.get("name") and info.get("source"):
                selected_items.append(info)
    if not selected_items:
        app.display_message("Add to Community", "No items selected. Please select items to share with the community.")
        return
    bundle_name, ok = QInputDialog.getText(
        app, "Share Bundle with Community",
        f"Enter a name for this bundle ({len(selected_items)} items):",
        text=f"My Bundle ({len(selected_items)} packages)"
    )
    if not ok or not bundle_name.strip():
        return
    bundle_name = bundle_name.strip()
    description, ok = QInputDialog.getText(
        app, "Bundle Description",
        "Enter a description for this bundle (optional):",
        text=f"A collection of {len(selected_items)} useful packages"
    )
    if not ok:
        return
    description = description.strip() if description else f"A bundle containing {len(selected_items)} packages"
    try:
        bundle_data = {
            "name": bundle_name,
            "description": description,
            "items": selected_items,
            "item_count": len(selected_items),
            "created_by": "NeoArch User",
            "bundle_type": "community_shared",
            "version": "1.0.0"
        }
        community_dir = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "community_bundles")
        os.makedirs(community_dir, exist_ok=True)
        safe_name = "".join(c for c in bundle_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        bundle_file = os.path.join(community_dir, f"{safe_name}.json")
        counter = 1
        original_file = bundle_file
        while os.path.exists(bundle_file):
            name_part = os.path.splitext(original_file)[0]
            bundle_file = f"{name_part}_{counter}.json"
            counter += 1
        with open(bundle_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_data, f, indent=2, ensure_ascii=False)
        reply = QMessageBox.question(
            app, "Bundle Shared Successfully",
            f"Bundle '{bundle_name}' has been shared with the community!\n\n"
            f"Items shared: {len(selected_items)}\n"
            f"Saved to: {bundle_file}\n\n"
            "Would you like to open the Community Hub to see shared bundles?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            app.show_community_hub()
        app.log(f"Successfully shared bundle '{bundle_name}' with {len(selected_items)} items to community")
    except Exception as e:
        app.display_message("Add to Community", f"Failed to share bundle: {str(e)}")
        app.log(f"Error sharing bundle to community: {e}")


def list_community_bundles():
    """List all community shared bundles from the local directory."""
    community_dir = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "community_bundles")
    bundles = []
    if not os.path.exists(community_dir):
        return bundles
    try:
        for filename in os.listdir(community_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(community_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        bundle_data = json.load(f)
                        bundle_data['file_path'] = filepath
                        bundle_data['file_name'] = filename
                        bundles.append(bundle_data)
                except Exception as e:
                    print(f"Error reading bundle file {filename}: {e}")
    except Exception as e:
        print(f"Error listing community bundles: {e}")
    return bundles


def import_community_bundle(app, bundle_data):
    """Import a community bundle into the current bundle."""
    if not isinstance(bundle_data, dict) or 'items' not in bundle_data:
        app.display_message("Import Community Bundle", "Invalid bundle data")
        return
    items = bundle_data.get('items', [])
    if not items:
        app.display_message("Import Community Bundle", "Bundle contains no items")
        return
    existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
    added = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        src = (item.get('source') or '').strip()
        name = (item.get('name') or '').strip()
        pkg_id = (item.get('id') or name).strip()
        if not src or not name:
            continue
        key = (src, pkg_id or name)
        if key not in existing:
            app.bundle_items.append({
                'name': name,
                'id': pkg_id or name,
                'version': (item.get('version') or '').strip(),
                'source': src,
            })
            existing.add(key)
            added += 1
    bundle_name = bundle_data.get('name', 'Community Bundle')
    app.display_message("Import Community Bundle", f"Added {added} items from '{bundle_name}' to your bundle")
    if app.current_view == "bundles":
        refresh_bundles_table(app)
    app.log(f"Imported {added} items from community bundle '{bundle_name}'")
