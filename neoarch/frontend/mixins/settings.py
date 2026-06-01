"""Settings UI mixin for the main window."""

import os

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QGroupBox, QGridLayout, QCheckBox, QLineEdit, QFileDialog, QSpinBox,
)

from neoarch.backend.services import settings as settings_service
from neoarch.frontend.views.settings_general import GeneralSettingsWidget
from neoarch.frontend.views.settings_auto_update import AutoUpdateSettingsWidget
from neoarch.frontend.views.settings_plugins import PluginsSettingsWidget


class _SettingsMixin:
    def load_settings(self):
        return settings_service.load_settings()

    def save_settings(self):
        return settings_service.save_settings(self.settings, self.log)

    def build_settings_ui(self):
        # Clear existing layout
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create main horizontal layout for sidebar + content
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create left sidebar for navigation
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("""
            QFrame#settingsSidebar {
                background-color: #1a1a1a;
                border: none;
            }
            QPushButton {
                text-align: left;
                padding: 18px 24px;
                border: none;
                background-color: transparent;
                color: #a0a0a0;
                font-size: 15px;
                font-weight: 500;
                border-radius: 8px;
                margin: 3px 20px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: rgba(13, 115, 119, 0.2);
                color: #0d7377;
                font-weight: 600;
                border: 1px solid rgba(13, 115, 119, 0.3);
            }
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(6)

        # Create navigation buttons
        self.settings_nav_buttons = {}

        # Add a header label
        header_label = QLabel("SETTINGS")
        header_label.setStyleSheet("""
            color: #777;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.2px;
            padding: 12px 24px;
            margin-top: 12px;
            margin-bottom: 8px;
        """)
        sidebar_layout.addWidget(header_label)

        btn_general = QPushButton("General")
        btn_general.setCheckable(True)
        btn_general.setChecked(True)
        btn_general.clicked.connect(lambda: self.switch_settings_category("general"))
        self.settings_nav_buttons["general"] = btn_general
        sidebar_layout.addWidget(btn_general)

        btn_auto_update = QPushButton("Auto Update")
        btn_auto_update.setCheckable(True)
        btn_auto_update.clicked.connect(lambda: self.switch_settings_category("auto_update"))
        self.settings_nav_buttons["auto_update"] = btn_auto_update
        sidebar_layout.addWidget(btn_auto_update)

        btn_plugins = QPushButton("Plugins")
        btn_plugins.setCheckable(True)
        btn_plugins.clicked.connect(lambda: self.switch_settings_category("plugins"))
        self.settings_nav_buttons["plugins"] = btn_plugins
        sidebar_layout.addWidget(btn_plugins)

        sidebar_layout.addStretch()

        # Add version info at bottom
        version_label = QLabel("NeoArch v1.0")
        version_label.setStyleSheet("""
            color: #555;
            font-size: 11px;
            padding: 12px 20px;
        """)
        sidebar_layout.addWidget(version_label)

        # Create right content area
        content_area = QFrame()
        content_area.setObjectName("settingsContent")
        content_area.setStyleSheet("""
            QFrame#settingsContent {
                background-color: #1e1e1e;
                border-radius: 12px;
                margin: 24px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

        self.settings_content_layout = QVBoxLayout(content_area)
        self.settings_content_layout.setContentsMargins(24, 24, 24, 24)
        self.settings_content_layout.setSpacing(16)

        # Create and store settings widgets
        self.settings_widgets = {
            "general": GeneralSettingsWidget(self),
            "auto_update": AutoUpdateSettingsWidget(self),
            "plugins": PluginsSettingsWidget(self)
        }

        # Add widgets to content area (initially show general)
        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == "general")
            self.settings_content_layout.addWidget(widget)

        self.settings_content_layout.addStretch()

        # Add sidebar and content to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, 1)

        # Add main layout to settings layout
        container_widget = QWidget()
        container_widget.setLayout(main_layout)
        self.settings_layout.addWidget(container_widget)

    def switch_settings_category(self, category):
        """Switch between settings categories"""
        # Update button states
        for key, btn in self.settings_nav_buttons.items():
            btn.setChecked(key == category)

        # Show/hide appropriate widget
        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == category)

    def build_general_settings(self, layout):
        box = QGroupBox("General Settings")
        grid = QGridLayout(box)
        cb_auto = QCheckBox("Auto check updates on launch")
        cb_auto.setChecked(bool(self.settings.get('auto_check_updates')))
        cb_auto.toggled.connect(lambda v: self.update_setting('auto_check_updates', v))
        grid.addWidget(cb_auto, 0, 0, 1, 2)
        cb_local = QCheckBox("Include Local source (custom scripts)")
        cb_local.setChecked(bool(self.settings.get('include_local_source')))
        cb_local.toggled.connect(lambda v: self.update_setting('include_local_source', v))
        grid.addWidget(cb_local, 1, 0, 1, 2)
        cb_npm = QCheckBox("Use npm user mode for global installs")
        cb_npm.setChecked(bool(self.settings.get('npm_user_mode')))
        cb_npm.toggled.connect(lambda v: self.update_setting('npm_user_mode', v))
        grid.addWidget(cb_npm, 2, 0, 1, 2)
        layout.addWidget(box)

        path_box = QGroupBox("Bundle Autosave")
        pgrid = QGridLayout(path_box)
        cb_bsave = QCheckBox("Autosave bundle to file")
        cb_bsave.setChecked(bool(self.settings.get('bundle_autosave', True)))
        cb_bsave.toggled.connect(lambda v: self.update_setting('bundle_autosave', v))
        pgrid.addWidget(cb_bsave, 0, 0, 1, 3)
        from_path = self.settings.get('bundle_autosave_path') or os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass
        path_edit = QLineEdit(from_path)
        browse_btn = QPushButton("Browse\u2026")
        def on_browse():
            path, _ = QFileDialog.getSaveFileName(self, "Select Bundle Autosave Path", from_path, "Bundle JSON (*.json)")
            if path:
                path_edit.setText(path)
                self.update_setting('bundle_autosave_path', path)
        browse_btn.clicked.connect(on_browse)
        pgrid.addWidget(QLabel("Autosave path:"), 1, 0)
        pgrid.addWidget(path_edit, 1, 1)
        pgrid.addWidget(browse_btn, 1, 2)
        layout.addWidget(path_box)

        # Auto Update Settings
        auto_update_box = QGroupBox("Auto Update")
        auto_grid = QGridLayout(auto_update_box)
        cb_auto_update = QCheckBox("Enable automatic updates")
        cb_auto_update.setChecked(bool(self.settings.get('auto_update_enabled')))
        cb_auto_update.toggled.connect(lambda v: self.update_setting('auto_update_enabled', v))
        auto_grid.addWidget(cb_auto_update, 0, 0, 1, 2)

        auto_grid.addWidget(QLabel("Update interval (hours):"), 1, 0)
        interval_spin = QSpinBox()
        interval_spin.setRange(1, 168)  # 1 hour to 1 week
        interval_spin.setValue(int(self.settings.get('auto_update_interval_hours', 24)))
        interval_spin.valueChanged.connect(lambda v: self.update_setting('auto_update_interval_hours', v))
        auto_grid.addWidget(interval_spin, 1, 1)

        layout.addWidget(auto_update_box)

        # Snapshot Settings
        snapshot_box = QGroupBox("Snapshots")
        snap_grid = QGridLayout(snapshot_box)
        cb_snapshot = QCheckBox("Create snapshot before updates")
        cb_snapshot.setChecked(bool(self.settings.get('snapshot_before_update')))
        cb_snapshot.toggled.connect(lambda v: self.update_setting('snapshot_before_update', v))
        snap_grid.addWidget(cb_snapshot, 0, 0, 1, 2)

        snap_btns = QHBoxLayout()
        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.clicked.connect(self.create_snapshot)
        snap_btns.addWidget(create_snap_btn)

        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.clicked.connect(self.revert_to_snapshot)
        snap_btns.addWidget(revert_snap_btn)

        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.clicked.connect(self.delete_snapshots)
        snap_btns.addWidget(delete_snap_btn)

        snap_btns.addStretch()
        snap_grid.addLayout(snap_btns, 1, 0, 1, 2)

        layout.addWidget(snapshot_box)

        btns = QHBoxLayout()
        btn_export = QPushButton("Export Settings")
        btn_export.clicked.connect(self.export_settings)
        btn_import = QPushButton("Import Settings")
        btn_import.clicked.connect(self.import_settings)
        btns.addWidget(btn_export)
        btns.addWidget(btn_import)
        btns.addStretch()

    def update_setting(self, key, value):
        """Public method for updating a setting value."""
        self.settings[key] = value
        self.save_settings()

    def export_settings(self):
        return settings_service.export_settings(self)

    def import_settings(self):
        return settings_service.import_settings(self)
