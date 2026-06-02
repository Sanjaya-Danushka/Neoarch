"""
Community Plugins Browser
Allows users to discover, install, and share plugins from the community
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QLineEdit,
                             QMessageBox, QProgressBar, QGroupBox, QGraphicsDropShadowEffect)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor
import os

from neoarch.backend.stores.plugin_store import PluginStore


def _shadow(widget: QWidget, blur=22, offset=(4, 5), alpha=140):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(*offset)
    widget.setGraphicsEffect(s)


class CommunityPluginCard(QFrame):
    """Card displaying a community plugin with modern glassmorphism design"""

    def __init__(self, plugin_info: dict, on_install, on_view_details, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.on_install = on_install
        self.on_view_details = on_view_details

        self.setObjectName("communityPluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(80)
        self.setStyleSheet(self._style())
        _shadow(self, blur=20, offset=(3, 5), alpha=150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header with title, author, and version
        header = QHBoxLayout()
        header.setSpacing(8)

        avatar = QLabel("\U0001f9e9")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "font-size: 18px; background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;"
        )
        header.addWidget(avatar)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(plugin_info.get('name', 'Unknown Plugin'))
        title.setObjectName("pluginTitle")
        title_col.addWidget(title)

        author = QLabel(f"by {plugin_info.get('author', 'Unknown')} \u00b7 v{plugin_info.get('version', '1.0.0')}")
        author.setObjectName("pluginAuthor")
        title_col.addWidget(author)
        header.addLayout(title_col, 1)

        layout.addLayout(header)

        # Description
        desc = QLabel(plugin_info.get('description', ''))
        desc.setObjectName("pluginDesc")
        desc.setWordWrap(True)
        desc.setMaximumHeight(34)
        layout.addWidget(desc)

        layout.addStretch()

        # Footer with actions
        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch()

        details_btn = QPushButton("Details")
        details_btn.setFixedHeight(28)
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B8D97;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 7px;
                font-weight: 600;
                font-size: 10px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.04);
                border-color: rgba(255, 255, 255, 0.12);
                color: #EDEDEF;
            }
        """)
        details_btn.clicked.connect(lambda: self.on_view_details(self.plugin_info))
        footer.addWidget(details_btn)

        install_btn = QPushButton("Install")
        install_btn.setFixedHeight(28)
        install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 207, 188, 0.9),
                    stop:1 rgba(0, 175, 160, 0.9));
                color: #0C0C0E;
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                border-bottom: 1px solid rgba(0, 0, 0, 0.25);
                border-left: 1px solid rgba(255, 255, 255, 0.08);
                border-right: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 7px;
                font-weight: 700;
                font-size: 10px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 220, 200, 0.95),
                    stop:1 rgba(0, 190, 174, 0.95));
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 155, 140, 0.95),
                    stop:1 rgba(0, 175, 160, 0.95));
            }
        """)
        install_btn.clicked.connect(lambda: self.on_install(self.plugin_info))
        footer.addWidget(install_btn)

        layout.addLayout(footer)

    def _style(self):
        return """
        QFrame#communityPluginCard {
            background-color: rgba(22, 23, 26, 0.85);
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.03);
            border-right: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 14px;
        }
        QFrame#communityPluginCard:hover {
            border-top: 1px solid rgba(255, 255, 255, 0.10);
            border-bottom: 1px solid rgba(0, 0, 0, 0.35);
            background-color: rgba(26, 28, 32, 0.85);
        }
        QLabel#pluginTitle {
            color: #EDEDEF;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#pluginAuthor {
            color: #5C5E66;
            font-size: 10px;
        }
        QLabel#pluginDesc {
            color: #8B8D97;
            font-size: 11px;
            line-height: 1.3;
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
            background-color: rgba(18, 19, 22, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
        }
        QLabel#dialogTitle {
            color: #EDEDEF;
            font-size: 18px;
            font-weight: 700;
        }
        QGroupBox {
            font-weight: 600;
            color: #8B8D97;
            font-size: 11px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            margin-top: 12px;
            padding: 12px 8px 8px 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QPushButton {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 207, 188, 0.9),
                stop:1 rgba(0, 175, 160, 0.9));
            color: #0C0C0E;
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 700;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 220, 200, 0.95),
                stop:1 rgba(0, 190, 174, 0.95));
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 155, 140, 0.95),
                stop:1 rgba(0, 175, 160, 0.95));
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
            background-color: rgba(18, 19, 22, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
        }
        QLabel#dialogTitle {
            color: #EDEDEF;
            font-size: 18px;
            font-weight: 700;
        }
        QLineEdit, QTextEdit {
            background-color: rgba(14, 14, 16, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            color: #EDEDEF;
            padding: 8px 12px;
            font-size: 12px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid rgba(0, 191, 174, 0.5);
        }
        QGroupBox {
            font-weight: 600;
            color: #8B8D97;
            font-size: 11px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            margin-top: 12px;
            padding: 12px 8px 8px 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QPushButton {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 207, 188, 0.9),
                stop:1 rgba(0, 175, 160, 0.9));
            color: #0C0C0E;
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 700;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 220, 200, 0.95),
                stop:1 rgba(0, 190, 174, 0.95));
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 155, 140, 0.95),
                stop:1 rgba(0, 175, 160, 0.95));
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
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header with title and action buttons
        header = QFrame()
        header.setObjectName("communityHeader")
        header.setStyleSheet("""
            QFrame#communityHeader {
                background-color: rgba(14, 14, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        header.setFixedHeight(44)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 8, 4)
        header_layout.setSpacing(6)

        title = QLabel("Community Plugins")
        title.setStyleSheet("color: #EDEDEF; font-size: 13px; font-weight: 600; border: none;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        def _header_btn_style():
            return """
            QPushButton {
                background-color: transparent;
                color: #8B8D97;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 7px;
                padding: 0 12px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.04);
                color: #EDEDEF;
                border-color: rgba(255, 255, 255, 0.12);
            }
            """

        create_btn = QPushButton("+ Create")
        create_btn.setFixedHeight(30)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(_header_btn_style())
        create_btn.clicked.connect(self.show_plugin_creator)
        header_layout.addWidget(create_btn)

        submit_btn = QPushButton("Submit")
        submit_btn.setFixedHeight(30)
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.setStyleSheet(_header_btn_style())
        submit_btn.clicked.connect(self.submit_plugin)
        header_layout.addWidget(submit_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(30)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(_header_btn_style())
        refresh_btn.clicked.connect(self.refresh_plugins)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        # Progress bar for loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: rgba(255, 255, 255, 0.03);
            }
            QProgressBar::chunk {
                background-color: #00BFAE;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none; background: transparent; width: 8px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(60, 60, 65, 0.5); border-radius: 4px;
                min-height: 24px; margin: 2px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(80, 80, 85, 0.7); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none; background: transparent; height: 0;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none; width: 0; height: 0; background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(14)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area, 1)

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
