"""Filter services for package tables.

Provides source and status filtering for the installed and updates views.
"""

__all__ = ["apply_filters", "apply_update_filters"]


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
    app.all_packages = final
    app.current_page = 0
    app.package_table.setRowCount(0)
    app.display_page()


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
