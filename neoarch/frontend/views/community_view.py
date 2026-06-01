"""
Community Plugins Browser
Allows users to discover, install, and share plugins from the community
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QLineEdit,
                             QMessageBox, QProgressBar, QGroupBox)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
import os

from neoarch.backend.stores.plugin_store import PluginStore


class CommunityPluginCard(QFrame):
    """Card displaying a community plugin"""

    def __init__(self, plugin_info: dict, on_install, on_view_details, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.on_install = on_install
        self.on_view_details = on_view_details

        self.setObjectName("communityPluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(self._style())
        self.setMinimumHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header with title, author, and version (no image)
        header = QHBoxLayout()
        title = QLabel(plugin_info.get('name', 'Unknown Plugin'))
        title.setObjectName("pluginTitle")
        header.addWidget(title)
        author = QLabel(f"by {plugin_info.get('author', 'Unknown')}")
        author.setObjectName("pluginAuthor")
        author.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(author)
        header.addStretch()
        ver = QLabel(f"v{plugin_info.get('version', '1.0.0')}")
        ver.setStyleSheet("color: #666; font-size: 10px;")
        header.addWidget(ver)
        layout.addLayout(header)

        # Description
        desc = QLabel(plugin_info.get('description', ''))
        desc.setObjectName("pluginDesc")
        desc.setWordWrap(True)
        desc.setMaximumHeight(32)
        layout.addWidget(desc)

        # Footer with actions
        footer = QHBoxLayout()
        footer.addStretch()

        # Buttons
        details_btn = QPushButton("Details")
        details_btn.setFixedWidth(54)
        details_btn.clicked.connect(lambda: self.on_view_details(self.plugin_info))
        footer.addWidget(details_btn)

        install_btn = QPushButton("Install")
        install_btn.setFixedWidth(54)
        install_btn.clicked.connect(lambda: self.on_install(self.plugin_info))
        footer.addWidget(install_btn)

        layout.addLayout(footer)

    def _style(self):
        return """
        QFrame#communityPluginCard {
            background-color: #1a1a1a;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        QLabel#pluginTitle {
            color: #F0F0F0;
            font-size: 10px;
            font-weight: 600;
        }
        QLabel#pluginDesc {
            color: #A0A0A0;
            font-size: 9px;
            line-height: 1.3;
        }
        QPushButton {
            background-color: transparent;
            color: #00BFAE;
            border: 1px solid #00BFAE;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 9px;
        }
        QPushButton:hover {
            background-color: rgba(0, 191, 174, 0.1);
        }
        """

class PluginDetailsDialog(QFrame):
    """Dialog showing detailed plugin information"""

    def __init__(self, plugin_info: dict, on_install, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.on_install = on_install

        self.setObjectName("pluginDetailsDialog")
        self.setStyleSheet(self._dialog_style())
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel(plugin_info.get('name', 'Plugin Details'))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Info grid
        info_layout = QGridLayout()
        info_layout.setSpacing(8)

        labels = ["Author:", "Version:", "Downloads:", "Last Updated:"]
        values = [
            plugin_info.get('author', 'Unknown'),
            plugin_info.get('version', '1.0.0'),
            str(plugin_info.get('downloads', 0)),
            plugin_info.get('last_updated', 'Unknown')
        ]

        for i, (label, value) in enumerate(zip(labels, values)):
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; color: #CCC;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #FFF;")

            info_layout.addWidget(label_widget, i, 0)
            info_layout.addWidget(value_widget, i, 1)

        layout.addLayout(info_layout)

        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        desc_text = QTextEdit()
        desc_text.setPlainText(plugin_info.get('description', 'No description available.'))
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(100)
        desc_layout.addWidget(desc_text)
        layout.addWidget(desc_group)

        # Features (if available)
        if plugin_info.get('features'):
            features_group = QGroupBox("Features")
            features_layout = QVBoxLayout(features_group)
            features_text = QLabel('\n'.join(f"• {f}" for f in plugin_info['features']))
            features_text.setWordWrap(True)
            features_layout.addWidget(features_text)
            layout.addWidget(features_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        install_btn = QPushButton("Install Plugin")
        install_btn.clicked.connect(lambda: self.on_install(self.plugin_info))
        button_layout.addWidget(install_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _dialog_style(self):
        return """
        QFrame#pluginDetailsDialog {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #444;
        }
        QLabel#dialogTitle {
            color: #FFF;
            font-size: 18px;
            font-weight: bold;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }
        QPushButton {
            background-color: #00BFAE;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #00A090;
        }
        """

class PluginCreatorDialog(QFrame):
    """Dialog for creating new plugins"""

    def __init__(self, plugin_store, on_plugin_created, parent=None):
        super().__init__(parent)
        self.plugin_store = plugin_store
        self.on_plugin_created = on_plugin_created

        self.setObjectName("pluginCreatorDialog")
        self.setStyleSheet(self._dialog_style())
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel("Create New Plugin")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel("Fill in the details below to create a plugin template")
        subtitle.setStyleSheet("color: #AAA;")
        layout.addWidget(subtitle)

        # Form
        form_layout = QGridLayout()
        form_layout.setSpacing(8)

        # Plugin name
        name_label = QLabel("Plugin Name:")
        name_label.setStyleSheet("font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Awesome Plugin")

        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setPlaceholderText("What does your plugin do?")

        form_layout.addWidget(name_label, 0, 0)
        form_layout.addWidget(self.name_input, 0, 1)
        form_layout.addWidget(desc_label, 1, 0)
        form_layout.addWidget(self.desc_input, 1, 1)

        layout.addLayout(form_layout)

        # Template preview
        template_group = QGroupBox("Generated Template")
        template_layout = QVBoxLayout(template_group)
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setFontFamily("Monospace")
        self.template_preview.setStyleSheet("font-size: 10px;")
        template_layout.addWidget(self.template_preview)
        layout.addWidget(template_group)

        # Update preview when inputs change
        self.name_input.textChanged.connect(self.update_preview)
        self.desc_input.textChanged.connect(self.update_preview)

        # Set initial preview
        self.update_preview()

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        create_btn = QPushButton("Create Plugin")
        create_btn.clicked.connect(self.create_plugin)
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.hide)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def update_preview(self):
        """Update the template preview"""
        name = self.name_input.text().strip() or "My Plugin"
        desc = self.desc_input.toPlainText().strip() or "A plugin that does amazing things"

        template = self.plugin_store.create_plugin_template(name, desc)
        self.template_preview.setPlainText(template)

    def create_plugin(self):
        """Create and save the plugin"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a plugin name.")
            return

        desc = self.desc_input.toPlainText().strip()
        template = self.plugin_store.create_plugin_template(name, desc)

        # Save to plugins directory
        filename = name.lower().replace(' ', '_').replace('-', '_') + '.py'
        plugin_path = self.plugin_store.plugins_dir / filename

        try:
            with open(plugin_path, 'w') as f:
                f.write(template)

            QMessageBox.information(self, "Success",
                                  f"Plugin template created!\n\nSaved to: {plugin_path}\n\n"
                                  "You can now edit the plugin and enable it in Settings \u2192 Plugins.")

            if self.on_plugin_created:
                self.on_plugin_created(plugin_path)

            self.hide()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create plugin: {e}")

    def _dialog_style(self):
        return """
        QFrame#pluginCreatorDialog {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #444;
        }
        QLabel#dialogTitle {
            color: #FFF;
            font-size: 18px;
            font-weight: bold;
        }
        QLineEdit, QTextEdit {
            background-color: #1a1a1a;
            border: 1px solid #555;
            border-radius: 4px;
            color: #FFF;
            padding: 4px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QPushButton {
            background-color: #00BFAE;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #00A090;
        }
        """

class CommunityPluginsTab(QWidget):
    """Community plugins discovery and sharing tab"""

    plugin_installed = pyqtSignal(str)  # plugin_id

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.plugin_store = PluginStore()
        self.community_plugins = []
        self.details_dialog = None
        self.creator_dialog = None

        self._init_ui()
        self.refresh_plugins()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with title and refresh button
        header = QHBoxLayout()

        title = QLabel("Community Plugins")
        title.setObjectName("sectionLabel")
        header.addWidget(title)

        header.addStretch()

        # Action buttons
        create_btn = QPushButton("Create Plugin")
        create_btn.clicked.connect(self.show_plugin_creator)
        header.addWidget(create_btn)

        submit_btn = QPushButton("Submit Plugin")
        submit_btn.clicked.connect(self.submit_plugin)
        header.addWidget(submit_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_plugins)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Progress bar for loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setSpacing(6)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)

    def refresh_plugins(self):
        """Refresh the list of community plugins"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Clear existing plugins
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add loading message
        loading_label = QLabel("Loading community plugins...")
        loading_label.setStyleSheet("color: #AAA; font-style: italic;")
        self.grid_layout.addWidget(loading_label, 0, 0, 1, 5, Qt.AlignmentFlag.AlignCenter)

        # Load plugins in background
        QTimer.singleShot(100, self._load_plugins_async)

    def _load_plugins_async(self):
        """Load plugins asynchronously"""
        try:
            self.community_plugins = self.plugin_store.discover_plugins()
            self._display_plugins()
        except Exception as e:
            self._show_error(f"Failed to load community plugins: {e}")
            self.progress_bar.setVisible(False)

    def _display_plugins(self):
        """Display the loaded plugins"""
        # Clear loading message
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.community_plugins:
            no_plugins_label = QLabel("No community plugins found.\n\nBe the first to share a plugin!")
            no_plugins_label.setStyleSheet("color: #AAA; text-align: center;")
            no_plugins_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(no_plugins_label, 0, 0, 1, 5, Qt.AlignmentFlag.AlignCenter)
            return

        # Display plugins in grid (three columns for readability)
        col_count = 3
        for idx, plugin_info in enumerate(self.community_plugins):
            card = CommunityPluginCard(
                plugin_info,
                on_install=self.install_plugin,
                on_view_details=self.show_plugin_details,
                parent=self
            )
            row = idx // col_count
            col = idx % col_count
            self.grid_layout.addWidget(card, row, col)

    def install_plugin(self, plugin_info):
        """Install a community plugin"""
        plugin_id = plugin_info.get('id')
        if not plugin_id:
            QMessageBox.warning(self, "Error", "Invalid plugin information.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        try:
            if self.plugin_store.install_community_plugin(plugin_id):
                QMessageBox.information(self, "Success",
                                      f"Plugin '{plugin_info.get('name')}' installed successfully!\n\n"
                                      "Go to Settings \u2192 Plugins to enable it.")
                self.plugin_installed.emit(plugin_id)
                self.main_app.reload_plugins_and_notify()
            else:
                QMessageBox.warning(self, "Installation Failed",
                                  f"Failed to install plugin '{plugin_info.get('name')}'.\n\n"
                                  "Please check your internet connection and try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Installation error: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def show_plugin_details(self, plugin_info):
        """Show detailed information about a plugin"""
        if self.details_dialog:
            self.details_dialog.close()

        self.details_dialog = PluginDetailsDialog(plugin_info, self.install_plugin, self)
        self.details_dialog.show()

    def show_plugin_creator(self):
        """Show the plugin creation dialog"""
        if self.creator_dialog:
            self.creator_dialog.close()

        self.creator_dialog = PluginCreatorDialog(
            self.plugin_store,
            self.on_plugin_created,
            self
        )
        self.creator_dialog.show()

    def on_plugin_created(self, plugin_path):
        """Called when a new plugin is created"""
        QMessageBox.information(self, "Plugin Created",
                              f"Your plugin template has been created!\n\n"
                              f"Location: {plugin_path}\n\n"
                              "You can now edit it and enable it in Settings \u2192 Plugins.")

    def submit_plugin(self):
        """Launch the plugin submission tool"""
        try:
            import subprocess
            import sys
            script_path = os.path.join(os.path.dirname(__file__), "..", "submit_plugin.py")
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch submission tool: {e}")

    def _show_error(self, message):
        """Show error message"""
        error_label = QLabel(f"Error: {message}")
        error_label.setStyleSheet("color: #F44336;")
        self.grid_layout.addWidget(error_label, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
