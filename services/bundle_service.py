import os
import json
import subprocess
from threading import Thread
from utils.workers import CommandWorker
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QLabel, QInputDialog, QMessageBox
from . import install_service


def add_selected_to_bundle(app):
    items = []
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
    if app.current_view == "bundles":
        refresh_bundles_table(app)


def refresh_bundles_table(app):
    if app.current_view != "bundles":
        return
    app.package_table.setRowCount(0)
    app.package_table.setUpdatesEnabled(False)
    for it in app.bundle_items:
        pkg = {
            'name': it.get('name', ''),
            'id': it.get('id') or it.get('name', ''),
            'version': it.get('version', ''),
            'source': it.get('source', ''),
        }
        app.add_discover_row(pkg)
    app.package_table.setUpdatesEnabled(True)
    try:
        app.package_table.clearSelection()
    except Exception:
        pass
    app.load_more_btn.setVisible(False)
    try:
        app.package_table.setVisible(True)
    except Exception:
        pass


def export_bundle(app):
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
        if app.current_view == "bundles":
            refresh_bundles_table(app)
    except Exception as e:
        app.display_message("Import Bundle", f"Failed: {e}")


def remove_selected_from_bundle(app):
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
    refresh_bundles_table(app)


def clear_bundle(app):
    if not app.bundle_items:
        return
    app.bundle_items = []
    refresh_bundles_table(app)


def install_bundle(app):
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
    install_service.install_packages(app, by_src)


def add_selected_to_community(app):
    """Add selected bundle items to community hub"""
    if app.current_view != "bundles":
        app.display_message("Add to Community", "This feature is only available in bundles view")
        return
    
    # Get selected items
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
    
    # Get bundle name from user
    bundle_name, ok = QInputDialog.getText(
        app, 
        "Share Bundle with Community", 
        f"Enter a name for this bundle ({len(selected_items)} items):",
        text=f"My Bundle ({len(selected_items)} packages)"
    )
    
    if not ok or not bundle_name.strip():
        return
    
    bundle_name = bundle_name.strip()
    
    # Get bundle description from user
    description, ok = QInputDialog.getText(
        app,
        "Bundle Description",
        "Enter a description for this bundle (optional):",
        text=f"A collection of {len(selected_items)} useful packages"
    )
    
    if not ok:
        return
    
    description = description.strip() if description else f"A bundle containing {len(selected_items)} packages"
    
    try:
        # Create bundle data structure
        bundle_data = {
            "name": bundle_name,
            "description": description,
            "items": selected_items,
            "item_count": len(selected_items),
            "created_by": "NeoArch User",
            "bundle_type": "community_shared",
            "version": "1.0.0"
        }
        
        # Save to community bundles directory
        community_dir = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "community_bundles")
        os.makedirs(community_dir, exist_ok=True)
        
        # Create safe filename
        safe_name = "".join(c for c in bundle_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        bundle_file = os.path.join(community_dir, f"{safe_name}.json")
        
        # Check if file already exists
        counter = 1
        original_file = bundle_file
        while os.path.exists(bundle_file):
            name_part = os.path.splitext(original_file)[0]
            bundle_file = f"{name_part}_{counter}.json"
            counter += 1
        
        # Save bundle file
        with open(bundle_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_data, f, indent=2, ensure_ascii=False)
        
        # Show success message with option to open community hub
        reply = QMessageBox.question(
            app,
            "Bundle Shared Successfully",
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
    """List all community shared bundles"""
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
    """Import a community bundle into the current bundle"""
    if not isinstance(bundle_data, dict) or 'items' not in bundle_data:
        app.display_message("Import Community Bundle", "Invalid bundle data")
        return
    
    items = bundle_data.get('items', [])
    if not items:
        app.display_message("Import Community Bundle", "Bundle contains no items")
        return
    
    # Add items to current bundle
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
