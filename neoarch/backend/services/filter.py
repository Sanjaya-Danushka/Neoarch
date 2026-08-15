"""Filter services for package tables.

Provides source and status filtering for the installed and updates views.
"""

import re

__all__ = ["apply_filters", "apply_update_filters"]


def _version_key(text):
    return [int(p) for p in re.findall(r"\d+", str(text))] or [0]


def _sort_installed(dataset, field, asc, sizes):
    try:
        if field == "size":
            def key(p): return sizes.get(p.get("name"), 0)
        elif field == "version":
            def key(p): return _version_key(p.get("version"))
        elif field == "source":
            def key(p): return (p.get("source") or "").lower()
        elif field == "status":
            def key(p): return (0 if p.get("has_update") else 1)
        elif field == "date":
            def key(p): return p.get("installed_date") or 0
        else:
            def key(p): return (p.get("name") or "").lower()
        return sorted(dataset, key=key, reverse=not asc)
    except Exception:
        return dataset


def apply_filters(app):
    """Apply source and status filters to the installed packages view."""
    if app.current_view != "installed":
        return
    base = getattr(app, 'installed_all', []) or []
    selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True, "Local": True}
    if hasattr(app, 'source_card') and app.source_card:
        try:
            selected_sources.update(app.source_card.get_selected_sources())
        except Exception:
            pass
    filtered_by_source = []
    for pkg in base:
        s = pkg.get('source')
        if s in selected_sources and selected_sources.get(s, True):
            filtered_by_source.append(pkg)
    selected_filters = {"Updates available": False}
    if hasattr(app, '_installed_filter_states'):
        try:
            selected_filters = app._installed_filter_states
        except Exception:
            pass
    show_updates_only = selected_filters.get("Updates available", False)
    final = []
    for pkg in filtered_by_source:
        if show_updates_only:
            if pkg.get('has_update'):
                final.append(pkg)
        else:
            final.append(pkg)
    try:
        query = (app.search_input.text() or '').strip().lower()
    except Exception:
        query = ''
    if query:
        final = [p for p in final
                 if query in (p.get('name') or '').lower()
                 or query in (p.get('id') or '').lower()]
    field, asc = 'name', True
    try:
        if hasattr(app, 'source_card') and app.source_card:
            field = app.source_card.get_sort()
            asc = app.source_card.get_sort_asc()
    except Exception:
        pass
    sizes = getattr(app, '_installed_sizes', None) or {}
    final = _sort_installed(final, field, asc, sizes)
    app.all_packages = final
    app.current_page = 0
    app.package_table.setRowCount(0)
    if hasattr(app, '_sync_installed_table'):
        app._sync_installed_table()
    else:
        app.display_page()
    try:
        if getattr(app, '_view_mode', 'table') == 'grid' and hasattr(app, '_populate_grid'):
            app._populate_grid()
    except Exception:
        pass


def apply_update_filters(app):
    """Apply source filters to the updates view."""
    if app.current_view != "updates" or not app.all_packages:
        return
    selected_sources = {}
    if hasattr(app, 'source_card') and app.source_card:
        try:
            selected_sources = app.source_card.get_selected_sources()
        except Exception:
            selected_sources = {}
    if not selected_sources:
        selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True, "Local": True}
    show_pacman = selected_sources.get("pacman", True)
    show_aur = selected_sources.get("AUR", True)
    show_flatpak = selected_sources.get("Flatpak", True)
    show_npm = selected_sources.get("npm", True)
    show_local = selected_sources.get("Local", True)
    filtered = []
    for pkg in app.all_packages:
        src = pkg.get('source')
        if src == 'pacman' and show_pacman:
            filtered.append(pkg)
        elif src == 'AUR' and show_aur:
            filtered.append(pkg)
        elif src == 'Flatpak' and show_flatpak:
            filtered.append(pkg)
        elif src == 'npm' and show_npm:
            filtered.append(pkg)
        elif src == 'Local' and show_local:
            filtered.append(pkg)
    app.all_packages = filtered
    app.current_page = 0
    app.package_table.setRowCount(0)
    app.display_page()
