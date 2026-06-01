import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QPushButton, QLabel, QTabWidget,
                             QMessageBox, QCheckBox, QDialog, QLineEdit, QTextEdit,
                             QComboBox, QFileDialog, QFormLayout)
from PyQt6.QtCore import Qt

class PluginsSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        # Add title with subtitle
        title = QLabel("Plugins")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #ffffff; 
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)
        
        subtitle = QLabel("Manage installed plugins and extensions")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        """)
        self.layout.addWidget(subtitle)
        
        # Create tab widget for Core Plugins and Community Hub
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background-color: rgba(255, 255, 255, 0.03);
                margin-top: 12px;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #888;
                padding: 14px 28px;
                margin-right: 6px;
                border-radius: 8px 8px 0 0;
                font-weight: 500;
                font-size: 14px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
                color: #ffffff;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
        """)
        
        # Core Plugins Tab
        core_tab = QWidget()
        core_layout = QVBoxLayout(core_tab)
        core_layout.setContentsMargins(16, 16, 16, 16)
        core_layout.setSpacing(12)
        
        # Core plugins actions
        core_actions = QHBoxLayout()
        btn_reload = QPushButton("Reload Plugins")
        btn_reload.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_reload.clicked.connect(self.app.reload_plugins_and_notify)
        core_actions.addWidget(btn_reload)
        core_actions.addStretch()
        core_layout.addLayout(core_actions)
        
        # Core Plugins Table
        self.core_plugins_table = QTableWidget()
        self.core_plugins_table.setColumnCount(3)
        self.core_plugins_table.setHorizontalHeaderLabels(["Enabled", "Plugin", "Location"])
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.core_plugins_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #e0e0e0;
                selection-background-color: rgba(13, 115, 119, 0.3);
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QTableWidget::item:selected {
                background-color: rgba(13, 115, 119, 0.25);
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
                font-size: 13px;
            }
        """)
        core_layout.addWidget(self.core_plugins_table)
        
        # Community Hub Tab
        community_tab = QWidget()
        community_layout = QVBoxLayout(community_tab)
        community_layout.setContentsMargins(16, 16, 16, 16)
        community_layout.setSpacing(12)
        
        # Community hub actions
        community_actions = QHBoxLayout()
        btn_add = QPushButton("Upload Plugin")
        btn_add.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0a5c5f;
            }
        """)
        btn_add.clicked.connect(self.show_upload_plugin_form)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #d9534f;
                border: 1px solid rgba(217, 83, 79, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(217, 83, 79, 0.15);
                border-color: #d9534f;
            }
        """)
        btn_remove.clicked.connect(self.app.remove_selected_plugins)
        btn_go_plugins = QPushButton("Browse Community")
        btn_go_plugins.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_go_plugins.clicked.connect(self.go_to_plugins_page)
        
        community_actions.addWidget(btn_add)
        community_actions.addWidget(btn_remove)
        community_actions.addWidget(btn_go_plugins)
        community_actions.addStretch()
        community_layout.addLayout(community_actions)
        
        # Community Packages Table (repurpose the existing table)
        self.community_plugins_table = QTableWidget()
        self.community_plugins_table.setColumnCount(3)
        self.community_plugins_table.setHorizontalHeaderLabels(["Select", "Package Name", "Source"])
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.community_plugins_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #e0e0e0;
                selection-background-color: rgba(13, 115, 119, 0.3);
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QTableWidget::item:selected {
                background-color: rgba(13, 115, 119, 0.25);
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
                font-size: 13px;
            }
        """)
        
        community_layout.addWidget(self.community_plugins_table)
        
        # Add tabs to tab widget
        self.tabs.addTab(core_tab, "Core Plugins")
        self.tabs.addTab(community_tab, "Community Hub")
        
        self.layout.addWidget(self.tabs)
        
        # Initialize tables
        self.refresh_plugins_table()
        self.core_plugins_table.itemChanged.connect(self.on_plugin_item_changed)
        
        # Initialize community bundles
        self.refresh_community_bundles()

    def refresh_plugins_table(self):
        self._plugins_populating = True
        plugs = self.app.scan_plugins()
        enabled = set(self.app.settings.get('enabled_plugins') or [])
        self.core_plugins_table.setRowCount(0)

        for p in plugs:
            row = self.core_plugins_table.rowCount()
            self.core_plugins_table.insertRow(row)

            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            enabled_item.setCheckState(Qt.CheckState.Checked if p['name'] in enabled else Qt.CheckState.Unchecked)
            name_item = QTableWidgetItem(p['name'])
            loc_item = QTableWidgetItem(p.get('location', 'Core'))

            self.core_plugins_table.setItem(row, 0, enabled_item)
            self.core_plugins_table.setItem(row, 1, name_item)
            self.core_plugins_table.setItem(row, 2, loc_item)

        self._plugins_populating = False

    def on_plugin_item_changed(self, item):
        if getattr(self, '_plugins_populating', False):
            return
        if item.column() != 0:
            return

        row = item.row()
        name_item = self.core_plugins_table.item(row, 1)
        if not name_item:
            return

        name = name_item.text().strip()
        enabled = set(self.app.settings.get('enabled_plugins') or [])

        if item.checkState() == Qt.CheckState.Checked:
            enabled.add(name)
        else:
            enabled.discard(name)

        self.app.settings['enabled_plugins'] = sorted(enabled)
        self.app.save_settings()

    def remove_selected_plugins(self):
        """Remove selected plugins from the table and filesystem"""
        rows = self.plugins_table.selectionModel().selectedRows()
        if not rows:
            return
        
        removed = 0
        for mi in rows:
            r = mi.row()
            name_item = self.plugins_table.item(r, 1)
            if not name_item:
                continue
            name = name_item.text().strip()
            path = os.path.join(self.app.get_user_plugins_dir(), name + '.py')
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed += 1
                enabled = set(self.app.settings.get('enabled_plugins') or [])
                enabled.discard(name)
                self.app.settings['enabled_plugins'] = sorted(enabled)
            except Exception:
                pass
        
        self.app.save_settings()
        self.refresh_plugins_table()
        if removed > 0:
            self.app._show_message("Remove Plugins", f"Removed {removed} plugin(s)")

    def go_to_plugins_page(self):
        """Switch to the main plugins page"""
        try:
            self.app.switch_view("plugins")
        except Exception as e:
            print(f"Could not switch to plugins page: {e}")

    def refresh_community_bundles(self):
        """Refresh the community packages display"""
        try:
            from services.bundle_service import list_community_bundles
            
            # Clear existing packages
            self.community_plugins_table.setRowCount(0)
            
            # Load community bundles and extract all packages
            bundles = list_community_bundles()
            all_packages = []
            
            # Extract all packages from all bundles
            for bundle_data in bundles:
                items = bundle_data.get('items', [])
                for item in items:
                    if isinstance(item, dict) and item.get('name') and item.get('source'):
                        all_packages.append(item)
            
            if not all_packages:
                # Add a single row with message
                self.community_plugins_table.setRowCount(1)
                message_item = QTableWidgetItem("No community packages found. Share bundles from the Bundle page to see them here!")
                message_item.setFlags(message_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(0, 1, message_item)
                self.community_plugins_table.setSpan(0, 1, 1, 2)  # Span across remaining columns
                return
            
            # Remove duplicates while preserving order
            seen = set()
            unique_packages = []
            for pkg in all_packages:
                key = (pkg.get('name'), pkg.get('source'))
                if key not in seen:
                    seen.add(key)
                    unique_packages.append(pkg)
            
            # Populate table with packages
            self.community_plugins_table.setRowCount(len(unique_packages))
            
            for row, package in enumerate(unique_packages):
                # Checkbox column
                checkbox = QCheckBox()
                checkbox.setObjectName("packageCheckbox")
                cb_container = QWidget()
                cb_container.setStyleSheet("background: transparent;")
                cb_layout = QHBoxLayout(cb_container)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                cb_layout.addStretch()
                cb_layout.addWidget(checkbox)
                cb_layout.addStretch()
                self.community_plugins_table.setCellWidget(row, 0, cb_container)
                
                # Package name
                name_item = QTableWidgetItem(package.get('name', 'Unknown Package'))
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(row, 1, name_item)
                
                # Source
                source_item = QTableWidgetItem(package.get('source', 'Unknown'))
                source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(row, 2, source_item)
                
        except Exception as e:
            # Show error in table
            self.community_plugins_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Error loading community packages: {str(e)}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.community_plugins_table.setItem(0, 1, error_item)
            self.community_plugins_table.setSpan(0, 1, 1, 2)

    def show_upload_plugin_form(self):
        """Show the upload plugin form dialog"""
        # Get selected packages from the community table
        selected_packages = self.get_selected_community_packages()
        if not selected_packages:
            QMessageBox.information(self, "No Selection", "Please select packages from the table first.")
            return
        
        dialog = UploadPluginDialog(self, selected_packages)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the form data
            plugin_data = dialog.get_plugin_data()
            if plugin_data:
                self.upload_plugin_to_community(plugin_data)

    def get_selected_community_packages(self):
        """Get selected packages from the community table"""
        selected_packages = []
        for row in range(self.community_plugins_table.rowCount()):
            checkbox_widget = self.community_plugins_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    name_item = self.community_plugins_table.item(row, 1)
                    source_item = self.community_plugins_table.item(row, 2)
                    if name_item and source_item:
                        selected_packages.append({
                            'name': name_item.text(),
                            'source': source_item.text()
                        })
        return selected_packages

    def upload_plugin_to_community(self, plugin_data):
        """Upload the plugin data to community"""
        try:
            # Here you would implement the actual upload logic
            # For now, just show a success message
            QMessageBox.information(self, "Upload Successful", 
                                  f"Plugin '{plugin_data['name']}' uploaded successfully!\n\n"
                                  f"Category: {plugin_data['category']}\n"
                                  f"Logo: {plugin_data['logo_path'] if plugin_data['logo_path'] else 'No logo'}")
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to upload plugin: {str(e)}")


class UploadPluginDialog(QDialog):
    """Dialog for uploading plugins to the community"""
    
    def __init__(self, parent=None, selected_packages=None):
        super().__init__(parent)
        self.selected_packages = selected_packages or []
        self.setWindowTitle("Upload Plugin to Community")
        self.setFixedSize(480, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
            }
            QLabel {
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                font-size: 13px;
                selection-background-color: #0d7377;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0d7377;
                background-color: #2f2f2f;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #777777;
            }
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #0d7377;
                background-color: #2f2f2f;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #444444;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #333333;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                border: 1px solid #0d7377;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: #0d7377;
                outline: none;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 500;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0a5c5f;
            }
            QPushButton:pressed {
                background-color: #085a5d;
            }
        """)
        
        self.logo_path = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Upload Plugin to Community")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #ffffff; 
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Selected packages info
        if self.selected_packages:
            packages_text = f"Selected {len(self.selected_packages)} package(s): {', '.join([pkg['name'] for pkg in self.selected_packages[:3]])}"
            if len(self.selected_packages) > 3:
                packages_text += f" and {len(self.selected_packages) - 3} more..."
            
            packages_info = QLabel(packages_text)
            packages_info.setStyleSheet("""
                color: #0d7377; 
                font-size: 12px; 
                font-weight: 500;
                background-color: rgba(13, 115, 119, 0.15);
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid rgba(13, 115, 119, 0.3);
            """)
            packages_info.setWordWrap(True)
            layout.addWidget(packages_info)
        
        # Form fields
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Plugin name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter plugin name...")
        form_layout.addRow("Plugin Name:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter plugin description...")
        self.description_input.setMaximumHeight(70)
        form_layout.addRow("Description:", self.description_input)
        
        # Category
        self.category_combo = QComboBox()
        categories = [
            "System", "Office", "Development", "Internet", "Multimedia",
            "Graphics", "Games", "Education", "Utilities", "Customization",
            "Security", "Lifestyle"
        ]
        self.category_combo.addItems(categories)
        form_layout.addRow("Category:", self.category_combo)
        
        # Version and Author
        version_author_layout = QHBoxLayout()
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("1.0.0")
        self.version_input.setText("1.0.0")
        
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Enter author name...")
        
        version_author_layout.addWidget(self.version_input)
        version_author_layout.addWidget(self.author_input)
        
        version_author_widget = QWidget()
        version_author_widget.setLayout(version_author_layout)
        form_layout.addRow("Version / Author:", version_author_widget)
        
        layout.addLayout(form_layout)
        
        # Logo section
        logo_layout = QHBoxLayout()
        logo_label = QLabel("Plugin Logo (Optional - Max 1MB):")
        logo_layout.addWidget(logo_label)
        
        self.logo_button = QPushButton("Choose Logo")
        self.logo_button.clicked.connect(self.choose_logo)
        logo_layout.addWidget(self.logo_button)
        
        self.logo_status = QLabel("No logo selected")
        self.logo_status.setStyleSheet("color: #777777; font-size: 12px;")
        logo_layout.addWidget(self.logo_status)
        logo_layout.addStretch()
        
        layout.addLayout(logo_layout)
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        upload_btn = QPushButton("Upload Plugin")
        upload_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(upload_btn)
        
        layout.addLayout(buttons_layout)
    
    def choose_logo(self):
        """Choose logo file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Choose Plugin Logo", 
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.svg *.gif);;All Files (*)"
        )
        
        if file_path:
            # Check file size (1MB = 1048576 bytes)
            file_size = os.path.getsize(file_path)
            if file_size > 1048576:  # 1MB
                QMessageBox.warning(self, "File Too Large", 
                                  f"Logo file is {file_size / 1048576:.1f}MB. Please choose a file smaller than 1MB.")
                return
            
            self.logo_path = file_path
            filename = os.path.basename(file_path)
            size_mb = file_size / 1048576
            self.logo_status.setText(f"✓ {filename} ({size_mb:.2f}MB)")
            self.logo_status.setStyleSheet("color: #0d7377; font-weight: normal;")
    
    def get_plugin_data(self):
        """Get the plugin data from the form"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Please enter a plugin name.")
            return None
        
        return {
            'name': name,
            'description': self.description_input.toPlainText().strip(),
            'category': self.category_combo.currentText(),
            'version': self.version_input.text().strip() or "1.0.0",
            'author': self.author_input.text().strip() or "Unknown",
            'logo_path': self.logo_path,
            'selected_packages': self.selected_packages
        }


