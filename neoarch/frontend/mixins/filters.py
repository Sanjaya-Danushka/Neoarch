"""Filters and sources mixin for the main window."""

import os

from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QWidget, QCheckBox,
                             QScrollArea, QLabel, QSizePolicy)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QFont

from neoarch.resources.paths import PROJECT_ROOT
from neoarch.frontend.components.source_card import SourceCard, _ActionRow


class _BundleActionRow(_ActionRow):
    """ActionRow variant with white icon for bundles sidebar."""

    def __init__(self, title, icon_text="", parent=None):
        super().__init__(title, icon_text, parent)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
        from PyQt6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
            painter.setBrush(QColor(Colors.CARD_HOVER))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)

        icon_size = 16
        icon_x = 16
        icon_y = (h - icon_size) // 2
        font = painter.font()
        font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            QRectF(icon_x, icon_y, icon_size, icon_size),
            Qt.AlignmentFlag.AlignCenter,
            self.icon_text,
        )

        text_x = 40
        text_w = w - 40 - 24

        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT))
        painter.drawText(
            QRectF(text_x, 0, text_w, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        font.setPixelSize(15)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawText(
            QRectF(w - 21, 0, 13, h),
            Qt.AlignmentFlag.AlignCenter,
            "\u203A",
        )

        painter.end()
from neoarch.frontend.tokens import Colors, SourceColors

from neoarch.backend.services import filter as filters_service
from neoarch.frontend.components.updates_table import classify_update, _parse_size, _parse_version

_BASE_DIR = str(PROJECT_ROOT)


class _BundlesSourcePanel(QWidget):
    """Custom panel for bundles sidebar — matches SourceCard visual style."""

    source_toggled = pyqtSignal()
    export_clicked = pyqtSignal()
    import_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    load_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sources = {}
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Sources")
        header.setStyleSheet(f"""
            color: {Colors.TEXT}; font-size: 15px; font-weight: 700;
            background: transparent; border: none; padding: 12px 20px 4px 20px;
        """)
        layout.addWidget(header)

        src_widget = QWidget()
        src_layout = QVBoxLayout(src_widget)
        src_layout.setContentsMargins(12, 4, 12, 4)
        src_layout.setSpacing(2)
        self._src_layout = src_layout
        layout.addWidget(src_widget)

        self._src_container = src_widget

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep1)

        self._build_actions_section(layout)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep2)

        self._build_summary(layout)

    def _build_actions_section(self, layout):
        header = QLabel("ACTIONS")
        header.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 11px; font-weight: 600;
            letter-spacing: 1.0px; background: transparent; border: none;
            padding: 8px 20px 4px 20px;
        """)
        layout.addWidget(header)

        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(12, 0, 12, 0)
        actions_layout.setSpacing(0)

        defs = [
            ("Export", "\U0001f4e4", self.export_clicked),
            ("Import", "\U0001f4e5", self.import_clicked),
            ("Save to Cloud", "\u2601", self.save_clicked),
            ("Load from Cloud", "\u2601", self.load_clicked),
        ]
        for title, icon, signal in defs:
            row = _BundleActionRow(title, icon)
            row.clicked.connect(signal.emit)
            actions_layout.addWidget(row)

        layout.addWidget(actions_widget)

    def _build_summary(self, layout):
        summary_widget = QWidget()
        summary_widget.setObjectName("summaryWidget")
        s_layout = QVBoxLayout(summary_widget)
        s_layout.setContentsMargins(20, 8, 20, 12)
        s_layout.setSpacing(2)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(f"""
            color: {Colors.TEXT}; font-size: 22px; font-weight: 700;
            background: transparent; border: none; padding: 0;
        """)
        s_layout.addWidget(self._count_label)

        self._caption_label = QLabel("ITEMS IN BUNDLE")
        self._caption_label.setStyleSheet(f"""
            color: {Colors.TEXT_3}; font-size: 9px; font-weight: 600;
            letter-spacing: 0.5px; background: transparent; border: none; padding: 0;
        """)
        s_layout.addWidget(self._caption_label)

        summary_widget.setStyleSheet("""
            QWidget#summaryWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.04);
                background: rgba(255, 255, 255, 0.02);
            }
        """)
        layout.addWidget(summary_widget)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(9, 9, 10))
        painter.drawRect(r)
        glow = QRadialGradient(r.width() / 2.0, 0, r.width() * 0.9)
        glow.setColorAt(0.0, QColor(124, 58, 237, 16))
        glow.setColorAt(0.5, QColor(88, 40, 160, 8))
        glow.setColorAt(1.0, QColor(88, 40, 160, 0))
        painter.setBrush(glow)
        painter.drawRect(r)
        painter.setPen(QPen(QColor(255, 255, 255, 6), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(168, 85, 247, 8))
        painter.drawRect(QRectF(0, 0, r.width(), 1))
        painter.end()
        super().paintEvent(event)

    def add_source(self, name, icon_path, count=0):
        from neoarch.frontend.components.source_item import SourceItem
        item = SourceItem(name, icon_path, count=count)
        item.toggle.toggled.connect(lambda: self.source_toggled.emit())
        self._sources[name] = item
        self._src_layout.addWidget(item)

    def get_source_states(self):
        return {name: item.is_checked() for name, item in self._sources.items()}

    def set_source_count(self, name, count):
        item = self._sources.get(name)
        if item:
            item.set_count(count)

    def set_summary(self, total):
        self._count_label.setText(str(total))
        self._caption_label.setText(
            f"ITEM{'S' if total != 1 else ''} IN BUNDLE")


def _fmt_size(b):
    try:
        mb = float(b) / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GiB"
        return f"{mb:.1f} MiB"
    except Exception:
        return ""


class _FiltersMixin:
    def get_row_checkbox(self, row):
        cell = self.package_table.cellWidget(row, 0)
        if not cell:
            return None
        if isinstance(cell, QCheckBox):
            return cell
        try:
            chks = cell.findChildren(QCheckBox)
            return chks[0] if chks else None
        except Exception:
            return None

    def create_filters_panel(self):
        self.filters_panel = QFrame()
        self.filters_panel.setMinimumWidth(250)
        self.filters_panel.setMaximumWidth(268)
        self.filters_panel.setStyleSheet("""
            QFrame {
                background-color: #0C0C0E;
            }
        """)

        panel_layout = QVBoxLayout(self.filters_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        scroll = QScrollArea(self.filters_panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.10);
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.18);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sources_section = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_section)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setSpacing(0)

        layout.addWidget(self.sources_section, 1)

        self.filters_section = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_section)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(8)

        layout.addWidget(self.filters_section)

        scroll.setWidget(container)
        panel_layout.addWidget(scroll)

        return self.filters_panel

    def update_filters_panel(self, view_id):
        # Clear existing filters section
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Recreate filters based on view
        if view_id == "updates":
            self.update_updates_sources()
        elif view_id == "installed":
            pass
        else:
            filter_options = []

        # Update visibility
        if view_id == "installed":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_installed_sources()
        elif view_id == "updates":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
        elif view_id == "discover":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_discover_sources()
        elif view_id == "bundles":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_bundles_sources()
        elif view_id in ("git", "docker"):
            # No source or status filters for Git/Docker pages
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        elif view_id == "plugins":
            # Show a source panel like the updates/installed page
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_plugins_sources()
        elif view_id == "settings":
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        else:
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)

    def on_filter_selection_changed(self, filter_states):
        """Handle changes in filter selection"""
        # Apply filtering based on current view
        if self.current_view == "installed":
            self._installed_filter_states = filter_states.copy()
            self.apply_filters()
        elif self.current_view == "updates":
            self._recompute_updates()
        elif self.current_view == "plugins":
            # Apply plugin status filters (Available/Installed)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.apply_filters(filter_states)

    def update_discover_sources(self):
        """Update the discover sources using the new SourceCard component"""
        # Clear existing sources layout
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Always create a new SourceCard component
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_source_selection_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        self.source_card.sort_changed.connect(self.on_discover_sort_changed)
        self.source_card.installed_filter_changed.connect(self.on_discover_installed_filter_changed)

        # Add the four main sources (exclude Local from Discover)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg")),
        ]

        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)

        # Discover-specific sort options. "relevance" keeps the best-match
        # ordering produced by the search; the rest are plain field sorts.
        self.source_card.set_sort_methods([
            ("relevance", True, "Best Match"),
            ("name", True, "Name A-Z"),
            ("name", False, "Name Z-A"),
            ("version", True, "Version (Oldest)"),
            ("version", False, "Version (Latest)"),
            ("source", True, "Source A-Z"),
            ("source", False, "Source Z-A"),
            ("installed", False, "Not Installed First"),
            ("installed", True, "Installed First"),
        ])
        self.source_card.set_sort("relevance", True)

        self.sources_layout.addWidget(self.source_card)
        self.source_card.maintenance_action.connect(self.on_installed_maintenance_action)
        self.source_card.configure_sections(
            show_search=True, show_counts=True, show_sort=True, show_installed_filter=True,
            show_storage=True, show_summary=True)
        self._refresh_discover_storage_async()

    def _refresh_discover_storage_async(self):
        """Fetch disk usage and cache size in the background for Discover."""
        try:
            def _run_storage():
                try:
                    from neoarch.backend.services.hygiene import disk_usage, package_cache_size
                    disk = disk_usage("/")
                    cache = package_cache_size()
                except Exception:
                    disk, cache = {}, 0
                self.ui_call.emit(lambda: self._apply_discover_storage(disk, cache))

            from threading import Thread
            Thread(target=_run_storage, daemon=True).start()
        except Exception:
            pass

    def _apply_discover_storage(self, disk, cache):
        if self.current_view != "discover" or not getattr(self, 'source_card', None):
            return
        try:
            self.source_card.set_storage(disk=disk, cache_size=cache)
        except Exception:
            pass

    def update_updates_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg")),
            ("Local", os.path.join(_BASE_DIR, "assets", "icons", "discover", "local.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        self.source_card.source_changed.connect(self.on_updates_source_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        self.source_card.search_mode_changed.connect(self._recompute_updates)
        self.source_card.status_filter_changed.connect(self._recompute_updates)
        self.source_card.sort_changed.connect(self._recompute_updates)
        self.source_card.set_action_callbacks(
            update_all=self.perform_update_all,
            ignore_selected=self.ignore_selected,
            manage_ignored=self.manage_ignored,
        )
        self.source_card.configure_sections(
            show_status=True, show_sort=True, show_actions=True,
            show_summary=True, show_search=True, show_counts=True,
        )
        try:
            self.source_card.on_source_changed()
        except Exception:
            pass
        self._refresh_updates_summary()
        self._recompute_updates()

    def update_installed_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_installed_source_changed)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        self.source_card.health_action.connect(self.on_installed_health_action)
        self.source_card.sort_changed.connect(self.apply_filters)
        self.source_card.maintenance_action.connect(self.on_installed_maintenance_action)
        self.source_card.configure_sections(
            show_search=False, show_health=True, show_counts=True, show_summary=True, show_sort=True,
            show_quick_actions=True,
        )
        self._refresh_installed_sources()
        self._refresh_installed_health_async()

    def on_installed_maintenance_action(self, action):
        if action == "purge_cache":
            if not self.ensure_session_auth():
                self.log("Cache purge cancelled: authentication required.")
                return

            def _run():
                try:
                    from neoarch.backend.services.hygiene import purge_cache
                    ok = purge_cache(retain=2)
                except Exception:
                    ok = False
                self.ui_call.emit(lambda: self._on_cache_cleared(ok))
            try:
                from threading import Thread
                Thread(target=_run, daemon=True).start()
            except Exception:
                pass
        elif action == "update_all":
            try:
                self.perform_update_all()
            except Exception:
                pass
        elif action == "clean_orphans":
            try:
                self.cleanup_orphans()
            except Exception:
                pass

    def _on_cache_cleared(self, ok):
        if ok:
            self._notify("Cache cleared", "Old package versions were removed from the cache.",
                         level="success", event="install")
        else:
            self._notify("Cache clear failed", "Could not trim the package cache.",
                         level="error", event="errors")
        if self.current_view == "installed":
            self._refresh_installed_storage_async()
        elif self.current_view == "discover":
            self._refresh_discover_storage_async()

    def _refresh_installed_storage_async(self):
        """Fetch disk usage and cache size in the background."""
        try:
            def _run():
                try:
                    from neoarch.backend.services.hygiene import disk_usage, package_cache_size
                    disk = disk_usage("/")
                    cache = package_cache_size()
                except Exception:
                    disk, cache = {}, 0
                self.ui_call.emit(lambda: self._apply_installed_storage(disk, cache))
            from threading import Thread
            Thread(target=_run, daemon=True).start()
        except Exception:
            pass

    def _apply_installed_storage(self, disk, cache):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        try:
            self.source_card.set_storage(disk=disk, cache_size=cache)
        except Exception:
            pass

    def on_installed_health_action(self, action):
        if action == "orphans":
            self.cleanup_orphans()
        elif action == "pacnew":
            self.manage_pacnew()
        elif action == "outdated":
            self.switch_view("updates")

    def _refresh_installed_sources(self):
        """Populate the installed source card: counts, distribution, health, summary."""
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'installed_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = 0
            per[s] += 1
        try:
            for name, item in self.source_card.sources.items():
                item.set_count(per.get(name, 0))
        except Exception:
            pass
        try:
            self.source_card.set_distribution(per)
        except Exception:
            pass
        outdated = sum(1 for p in base if p.get('has_update'))
        sizes = getattr(self, '_installed_sizes', None) or {}
        total_b = sum(sizes.values())
        size_text = f"{_fmt_size(total_b)}" if total_b > 0 else ""
        try:
            self.source_card.set_health(
                orphans=len(getattr(self, '_orphans_list', None) or []),
                pacnew=len(getattr(self, '_pacnew_list', None) or []),
                outdated=outdated,
            )
        except Exception:
            pass
        try:
            self.source_card.set_summary(len(base), size_text, noun="packages installed", size_label="on disk")
        except Exception:
            pass

    def _refresh_installed_health_async(self):
        """Fetch orphan/pacnew counts first (fast), then sizes (slow) in background."""
        try:
            def _run_counts():
                try:
                    from neoarch.backend.services.hygiene import list_orphans, list_pacnew, list_explicit_packages
                    orphans = list_orphans()
                    pacnew = list_pacnew()
                    explicit = list_explicit_packages()
                except Exception:
                    orphans, pacnew, explicit = [], [], set()
                self.ui_call.emit(lambda: self._apply_installed_counts(orphans, pacnew, explicit))

            def _run_sizes():
                try:
                    from neoarch.backend.services.hygiene import list_installed_sizes
                    sizes = list_installed_sizes()
                except Exception:
                    sizes = {}
                self.ui_call.emit(lambda: self._apply_installed_sizes(sizes))

            from threading import Thread
            Thread(target=_run_counts, daemon=True).start()
            Thread(target=_run_sizes, daemon=True).start()
        except Exception:
            pass

    def _apply_installed_counts(self, orphans, pacnew, explicit=None):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        self._orphans_list = orphans or []
        self._pacnew_list = pacnew or []
        if explicit is not None:
            self._explicit_packages = explicit
        self._refresh_installed_sources()

    def _apply_installed_sizes(self, sizes=None):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        self._installed_sizes = sizes or {}
        self._refresh_installed_sources()

    def update_plugins_sources(self):
        """Update plugins sources using the SourceCard component (like updates/installed)."""
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_plugins_source_changed)
        self.source_card.sort_changed.connect(self.on_plugins_sort_changed)

        # Per-source counts from the curated catalog
        counts = {"pacman": 0, "AUR": 0, "Flatpak": 0, "npm": 0}
        plugins = []
        try:
            from neoarch.resources.plugin_data import get_all_plugins_data
            from neoarch.frontend.components.plugins_view import PluginsView, _canonical_source
            plugins = get_all_plugins_data()
            for p in plugins:
                src = _canonical_source(PluginsView._get_package_source(p))
                counts[src] = counts.get(src, 0) + 1
        except Exception:
            pass

        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "discover", "node.svg")),
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path, count=counts.get(source_name, 0))

        self.source_card.set_sort_methods([
            ("name_asc", True, "Name A-Z"),
            ("name_desc", True, "Name Z-A"),
            ("category", True, "Category"),
            ("source", True, "Source"),
            ("installed", True, "Installed First"),
        ])
        self.source_card.set_sort("name_asc", True)

        self.sources_layout.addWidget(self.source_card)
        self.source_card.category_changed.connect(self._on_plugins_category_changed)
        self.source_card.status_mode_changed.connect(self._on_plugins_status_mode_changed)
        cats = sorted({(p.get('category') or '') for p in plugins if p.get('category')})
        cat_counts = {}
        for p in plugins:
            cat = p.get('category') or ''
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        self.source_card.set_categories(cats, cat_counts)
        self._plugins_status_mode = "all"
        self._plugins_category = ""
        self.source_card.configure_sections(
            show_search=False, show_counts=True, show_sort=True, show_summary=True,
            show_categories=True, show_status_mode=True, show_stats=False)
        self._refresh_plugins_summary()

    def _on_plugins_category_changed(self, category):
        self._plugins_category = category or ""
        self._apply_plugins_filters()

    def _on_plugins_status_mode_changed(self, mode):
        self._plugins_status_mode = mode or "all"
        try:
            if not (hasattr(self, 'plugins_view') and self.plugins_view):
                return
            states = {
                "all": {"Available": True, "Installed": True},
                "available": {"Available": True, "Installed": False},
                "installed": {"Available": False, "Installed": True},
            }.get(self._plugins_status_mode, {"Available": True, "Installed": True})
            self.plugins_view.apply_filters(states)
            self._refresh_plugins_summary()
        except Exception:
            pass

    def _apply_plugins_filters(self):
        try:
            if not (hasattr(self, 'plugins_view') and self.plugins_view):
                return
            query = getattr(self, '_plugins_search_query', "")
            cats = [getattr(self, '_plugins_category', "")] if getattr(self, '_plugins_category', "") else []
            self.plugins_view.set_filter(query, False, cats)
            self._refresh_plugins_summary()
        except Exception:
            pass

    def _refresh_plugins_summary(self):
        """Update the bottom extension count and status counts on the plugins source card."""
        try:
            if not (hasattr(self, 'source_card') and self.source_card):
                return
            from neoarch.resources.plugin_data import get_all_plugins_data
            plugins = get_all_plugins_data()
            total = len(plugins)
            installed = 0
            if hasattr(self, 'plugins_view') and self.plugins_view:
                try:
                    cache = getattr(self.plugins_view, '_installed_cache', {})
                    installed = sum(1 for val in cache.values() if val)
                except Exception:
                    installed = 0
            count = total
            if hasattr(self, 'plugins_view') and self.plugins_view:
                try:
                    count = len(self.plugins_view._get_filtered_plugins()) or total
                except Exception:
                    count = total
            self.source_card.set_summary(count, noun="extensions")
            self.source_card.set_status_counts({
                "all": total,
                "available": max(0, total - installed),
                "installed": installed,
            })
        except Exception:
            pass

    def on_installed_source_changed(self, source_states):
        self.apply_filters()

    def on_plugins_source_changed(self, source_states):
        if hasattr(self, 'plugins_view') and self.plugins_view:
            self.plugins_view.apply_source_filters(source_states)
            self._refresh_plugins_summary()

    def on_updates_source_changed(self, source_states):
        self._recompute_updates()

    def _pkg_status(self, pkg):
        try:
            return pkg.get("status") or classify_update(pkg.get("version"), pkg.get("new_version"))
        except Exception:
            return "Maintenance"

    def _matches_query(self, pkg, query, mode):
        name = (pkg.get('name') or '').lower()
        pid = (pkg.get('id') or pkg.get('name') or '').lower()
        if mode == 'name':
            return query in name
        if mode == 'id':
            return query in pid
        return query in name or query in pid

    def _sort_updates(self, dataset, field, asc):
        try:
            if field == 'size':
                def key(p): return _parse_size(p.get('download_size') or '')
            elif field == 'version':
                def key(p): return (_parse_version(p.get('version')), _parse_version(p.get('new_version')))
            elif field == 'status':
                def key(p): return classify_update(p.get('version'), p.get('new_version'))
            elif field == 'date':
                def key(p): return p.get('installed_date') or 0
            elif field == 'source':
                def key(p): return (p.get('source') or '').lower()
            else:
                def key(p): return (p.get('name') or '').lower()
            return sorted(dataset, key=key, reverse=not asc)
        except Exception:
            return dataset

    def _refresh_updates_summary(self):
        """Refresh per-source counts and the total size summary from updates_all."""
        if self.current_view != "updates" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'updates_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = [0, 0.0]
            per[s][0] += 1
            per[s][1] += _parse_size(pkg.get('download_size') or '')
        try:
            for name, item in self.source_card.sources.items():
                n, b = per.get(name, (0, 0.0))
                item.set_count(n, _fmt_size(b))
        except Exception:
            pass
        total_b = sum(per[s][1] for s in per)
        known = sum(1 for p in base if _parse_size(p.get('download_size') or '') > 0)
        size_text = ""
        if total_b > 0:
            prefix = "~" if known < len(base) else ""
            size_text = f"{prefix}{_fmt_size(total_b)}"
        try:
            self.source_card.set_summary(len(base), size_text, noun="updates available", size_label="to download")
        except Exception:
            pass

    def _recompute_updates(self):
        """Compose source, status, search, and sort filters for the updates view."""
        if self.current_view != "updates":
            return
        self._refresh_updates_summary()
        dataset = list(getattr(self, 'updates_all', None) or [])
        states = {}
        try:
            states = self.source_card.get_selected_sources()
        except Exception:
            states = {}
        if states:
            dataset = [p for p in dataset if states.get(p.get('source'), True)]
        try:
            active = self.source_card.get_active_statuses()
            dataset = [p for p in dataset if self._pkg_status(p) in active]
        except Exception:
            pass
        query = ""
        try:
            query = (self.search_input.text() or '').strip().lower()
        except Exception:
            pass
        if query:
            mode = 'both'
            try:
                mode = self.source_card.get_search_mode()
            except Exception:
                pass
            dataset = [p for p in dataset if self._matches_query(p, query, mode)]
        field, asc = 'name', True
        try:
            field = self.source_card.get_sort()
            asc = self.source_card.get_sort_asc()
        except Exception:
            pass
        dataset = self._sort_updates(dataset, field, asc)
        self.all_packages = dataset
        self.current_page = 0
        try:
            self.load_more_btn.setVisible(False)
        except Exception:
            pass
        try:
            col_map = {"name": 1, "size": 3, "version": 2, "status": 5, "source": 4}
            self.updates_table.sort_by_column(col_map.get(field, 1), asc)
        except Exception:
            pass
        if query:
            total = len(getattr(self, 'updates_all', None) or [])
            self.header_info.setText(
                f"{total} packages were found, {len(dataset)} of which match the specified filters")
        else:
            self.update_updates_header_counts()
        try:
            self._sync_updates_table(dataset)
        except Exception:
            pass

    def on_source_selection_changed(self, source_states):
        """Handle changes in source selection"""
        if self.current_view == "discover" and hasattr(self, 'search_results') and self.search_results:
            self.display_discover_results(selected_sources=source_states)

    def apply_filters(self):
        return filters_service.apply_filters(self)

    def apply_update_filters(self):
        return filters_service.apply_update_filters(self)

    # ── Bundles source panel ──────────────────────────────────────────────

    def update_bundles_sources(self):
        """Build the bundles sidebar — custom panel matching SourceCard style."""
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        panel = _BundlesSourcePanel(self)
        self._bundle_panel = panel
        panel.source_toggled.connect(self._on_bundle_source_toggle)
        panel.export_clicked.connect(self.export_bundle)
        panel.import_clicked.connect(self.import_bundle)
        panel.save_clicked.connect(self._cloud_save_favourites)
        panel.load_clicked.connect(self._cloud_sync_favourites)

        src_icon = os.path.join(_BASE_DIR, "assets", "icons", "discover")
        for name, icon_file in [
            ("pacman", "pacman.svg"), ("AUR", "aur.svg"),
            ("Flatpak", "flatpack.svg"), ("npm", "node.svg"),
        ]:
            panel.add_source(name, os.path.join(src_icon, icon_file), count=0)

        self.sources_layout.addWidget(panel)
        self.sources_layout.addStretch(1)

    def _on_bundle_source_toggle(self):
        if self.current_view != "bundles":
            return
        states = self._bundle_panel.get_source_states()
        items = getattr(self, 'bundle_items', [])
        if not items:
            return
        filtered = [it for it in items if states.get(it.get('source', ''), True)]
        try:
            self.updates_table.set_bundles_mode(True)
            self.updates_table.set_packages(filtered)
        except Exception:
            pass

    def update_bundle_source_counts(self):
        items = getattr(self, 'bundle_items', [])
        counts = {"pacman": 0, "AUR": 0, "Flatpak": 0, "npm": 0}
        for it in items:
            src = it.get('source', '')
            if src in counts:
                counts[src] += 1
        panel = getattr(self, '_bundle_panel', None)
        if panel:
            for name, cnt in counts.items():
                panel.set_source_count(name, cnt)
            panel.set_summary(len(items))
