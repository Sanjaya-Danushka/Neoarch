"""
Community Plugins Browser
Allows users to discover, install, and share plugins from the community
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QLineEdit,
                             QMessageBox, QProgressBar, QGroupBox, QListWidget, QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QTimer
from PyQt6.QtGui import QGuiApplication
import os

from stores.plugin_store import PluginStore
 
try:
    from supabase_store import SupabasePluginStore
except Exception:
    SupabasePluginStore = None  # type: ignore
try:
    from stores.mongo_store import MongoPluginStore
except Exception:
    MongoPluginStore = None  # type: ignore

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
                                  "You can now edit the plugin and enable it in Settings → Plugins.")

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
        self.plugin_store = None
        self._is_supabase = False
        self._is_mongo = False
        try:
            if MongoPluginStore is not None:
                m = MongoPluginStore()
                if m.is_configured():
                    self.plugin_store = m
                    self._is_mongo = True
        except Exception:
            self.plugin_store = None
        if self.plugin_store is None:
            try:
                if SupabasePluginStore is not None:
                    s = SupabasePluginStore()
                    if s.is_configured():
                        self.plugin_store = s
                        self._is_supabase = True
            except Exception:
                self.plugin_store = None
        if self.plugin_store is None:
            self.plugin_store = PluginStore()
        self.community_plugins = []
        self.details_dialog = None
        self.creator_dialog = None
        self.my_plugins = []
        self._selected_my_id = None
        self._setup_status = None

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

        if self._is_supabase:
            self.onboarding_group = QGroupBox("Supabase Setup Required")
            ob_layout = QVBoxLayout(self.onboarding_group)
            self.ob_text = QLabel("Your Supabase project is missing required objects. Use the buttons below to copy SQL and run it in the Supabase SQL editor, and create two storage buckets: plugin-icons and plugin-files.")
            self.ob_text.setWordWrap(True)
            ob_layout.addWidget(self.ob_text)
            btns = QHBoxLayout()
            self.btn_copy_sql = QPushButton("Copy Table + RLS SQL")
            self.btn_copy_sql.clicked.connect(self._copy_sql_setup)
            self.btn_copy_storage = QPushButton("Copy Storage Policies SQL")
            self.btn_copy_storage.clicked.connect(self._copy_storage_policies)
            btns.addWidget(self.btn_copy_sql)
            btns.addWidget(self.btn_copy_storage)
            btns.addStretch()
            ob_layout.addLayout(btns)
            layout.addWidget(self.onboarding_group)
            self.onboarding_group.setVisible(False)
            auth_row = QHBoxLayout()
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText("Email")
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("Password")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_login = QPushButton("Login")
            self.btn_signup = QPushButton("Sign up")
            self.btn_logout = QPushButton("Logout")
            self.btn_login.clicked.connect(self.sign_in)
            self.btn_signup.clicked.connect(self.sign_up)
            self.btn_logout.clicked.connect(self.sign_out)
            auth_row.addWidget(self.email_input)
            auth_row.addWidget(self.password_input)
            auth_row.addWidget(self.btn_login)
            auth_row.addWidget(self.btn_signup)
            auth_row.addWidget(self.btn_logout)
            auth_row.addStretch()
            layout.addLayout(auth_row)

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

        if self._is_supabase:
            self.my_group = QGroupBox("My Plugins")
            my_layout = QHBoxLayout(self.my_group)
            self.my_list = QListWidget()
            self.my_list.currentTextChanged.connect(self._on_my_select)
            my_layout.addWidget(self.my_list, 1)

            form_col = QVBoxLayout()
            form_grid = QGridLayout()
            form_grid.setSpacing(6)
            self.input_id = QLineEdit()
            self.input_name = QLineEdit()
            self.input_version = QLineEdit()
            self.input_author = QLineEdit()
            self.input_desc = QTextEdit()
            self.input_desc.setMaximumHeight(80)
            self.input_cats = QLineEdit()
            self.icon_path = QLineEdit()
            self.file_path = QLineEdit()
            btn_browse_icon = QPushButton("Browse Icon")
            btn_browse_icon.clicked.connect(self._browse_icon)
            btn_browse_file = QPushButton("Browse File")
            btn_browse_file.clicked.connect(self._browse_file)
            form_grid.addWidget(QLabel("ID"), 0, 0)
            form_grid.addWidget(self.input_id, 0, 1)
            form_grid.addWidget(QLabel("Name"), 1, 0)
            form_grid.addWidget(self.input_name, 1, 1)
            form_grid.addWidget(QLabel("Version"), 2, 0)
            form_grid.addWidget(self.input_version, 2, 1)
            form_grid.addWidget(QLabel("Author"), 3, 0)
            form_grid.addWidget(self.input_author, 3, 1)
            form_grid.addWidget(QLabel("Categories (comma)"), 4, 0)
            form_grid.addWidget(self.input_cats, 4, 1)
            form_grid.addWidget(QLabel("Description"), 5, 0)
            form_grid.addWidget(self.input_desc, 5, 1)
            form_grid.addWidget(QLabel("Icon"), 6, 0)
            row6 = QHBoxLayout()
            row6.addWidget(self.icon_path, 1)
            row6.addWidget(btn_browse_icon)
            form_col.addLayout(form_grid)
            form_col.addLayout(row6)
            form_grid2 = QGridLayout()
            form_grid2.addWidget(QLabel("Plugin File (.py)"), 0, 0)
            rowf = QHBoxLayout()
            rowf.addWidget(self.file_path, 1)
            rowf.addWidget(btn_browse_file)
            form_col.addLayout(form_grid2)
            form_col.addLayout(rowf)
            btn_row = QHBoxLayout()
            self.btn_new = QPushButton("New")
            self.btn_save = QPushButton("Save")
            self.btn_delete = QPushButton("Delete")
            self.btn_reload_my = QPushButton("Reload")
            self.btn_new.clicked.connect(self._reset_my_form)
            self.btn_save.clicked.connect(self._save_my_plugin)
            self.btn_delete.clicked.connect(self._delete_my_plugin)
            self.btn_reload_my.clicked.connect(self._load_my_plugins)
            btn_row.addWidget(self.btn_new)
            btn_row.addWidget(self.btn_save)
            btn_row.addWidget(self.btn_delete)
            btn_row.addWidget(self.btn_reload_my)
            btn_row.addStretch()
            form_col.addLayout(btn_row)
            my_layout.addLayout(form_col, 2)
            layout.addWidget(self.my_group)
            self._update_auth_ui()
            self._update_onboarding_panel()

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

        if self._is_supabase:
            QTimer.singleShot(150, self._load_my_plugins)
            QTimer.singleShot(50, self._update_onboarding_panel)

    def _load_plugins_async(self):
        """Load plugins asynchronously"""
        try:
            self.community_plugins = self.plugin_store.discover_plugins()
            self._display_plugins()
        except Exception as e:
            self._show_error(f"Failed to load community plugins: {e}")
            self.progress_bar.setVisible(False)

    def _update_auth_ui(self):
        if not self._is_supabase:
            return
        try:
            uid = self.plugin_store.current_user_id()
        except Exception:
            uid = None
        logged_in = bool(uid)
        self.btn_logout.setVisible(logged_in)
        self.btn_login.setVisible(not logged_in)
        self.btn_signup.setVisible(not logged_in)
        self.email_input.setVisible(not logged_in)
        self.password_input.setVisible(not logged_in)
        if hasattr(self, "my_group"):
            self.my_group.setVisible(logged_in)

    def _update_onboarding_panel(self):
        if not self._is_supabase:
            return
        try:
            status = self.plugin_store.get_setup_status()
        except Exception:
            status = None
        self._setup_status = status
        if not status:
            if hasattr(self, 'onboarding_group'):
                self.onboarding_group.setVisible(False)
            return
        missing = (not status.get('has_plugins_table')) or (not status.get('has_increment_fn'))
        if hasattr(self, 'onboarding_group'):
            self.onboarding_group.setVisible(bool(missing))
            if missing:
                parts = []
                if not status.get('has_plugins_table'):
                    parts.append("plugins table")
                if not status.get('has_increment_fn'):
                    parts.append("increment_downloads function")
                self.ob_text.setText("Missing: " + ", ".join(parts) + ". Copy SQL and run in Supabase SQL editor, and create buckets plugin-icons and plugin-files.")

    def _copy_sql_setup(self):
        try:
            QGuiApplication.clipboard().setText(self._get_sql_setup())
            QMessageBox.information(self, "Copied", "SQL copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _copy_storage_policies(self):
        try:
            QGuiApplication.clipboard().setText(self._get_sql_storage())
            QMessageBox.information(self, "Copied", "Storage SQL copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _get_sql_setup(self) -> str:
        return (
            "create table if not exists public.plugins (\n"
            "  id text primary key,\n"
            "  name text not null,\n"
            "  description text,\n"
            "  version text default '1.0.0' not null,\n"
            "  author text not null,\n"
            "  categories text[] default '{}',\n"
            "  icon_url text,\n"
            "  file_url text not null,\n"
            "  downloads bigint default 0 not null,\n"
            "  created_by uuid not null references auth.users(id) on delete cascade,\n"
            "  created_at timestamptz not null default now(),\n"
            "  updated_at timestamptz not null default now(),\n"
            "  constraint id_slug check (id ~ '^[a-z0-9_]+$')\n"
            ");\n\n"
            "create or replace function public.set_updated_at() returns trigger language plpgsql as $$\n"
            "begin new.updated_at = now(); return new; end; $$;\n"
            "drop trigger if exists trg_plugins_set_updated_at on public.plugins;\n"
            "create trigger trg_plugins_set_updated_at before update on public.plugins for each row execute function public.set_updated_at();\n\n"
            "alter table public.plugins enable row level security;\n"
            "drop policy if exists \"plugins_select_all\" on public.plugins;\n"
            "create policy \"plugins_select_all\" on public.plugins for select to public using (true);\n"
            "drop policy if exists \"plugins_insert_owner\" on public.plugins;\n"
            "create policy \"plugins_insert_owner\" on public.plugins for insert to authenticated with check (created_by = auth.uid());\n"
            "drop policy if exists \"plugins_update_owner\" on public.plugins;\n"
            "create policy \"plugins_update_owner\" on public.plugins for update to authenticated using (created_by = auth.uid()) with check (created_by = auth.uid());\n"
            "drop policy if exists \"plugins_delete_owner\" on public.plugins;\n"
            "create policy \"plugins_delete_owner\" on public.plugins for delete to authenticated using (created_by = auth.uid());\n\n"
            "create or replace function public.increment_downloads(p_id text) returns void language plpgsql security definer as $$\n"
            "begin update public.plugins set downloads = downloads + 1, updated_at = now() where id = p_id; end; $$;\n"
            "revoke all on function public.increment_downloads(text) from public;\n"
            "grant execute on function public.increment_downloads(text) to anon, authenticated;\n"
        )

    def _get_sql_storage(self) -> str:
        return (
            "create policy if not exists \"icons_read_public\" on storage.objects for select to public using (bucket_id = 'plugin-icons');\n"
            "create policy if not exists \"files_read_public\" on storage.objects for select to public using (bucket_id = 'plugin-files');\n"
            "create policy if not exists \"icons_insert_auth\" on storage.objects for insert to authenticated with check (bucket_id = 'plugin-icons');\n"
            "create policy if not exists \"files_insert_auth\" on storage.objects for insert to authenticated with check (bucket_id = 'plugin-files');\n"
            "create policy if not exists \"icons_update_owner\" on storage.objects for update to authenticated using (bucket_id = 'plugin-icons' and owner = auth.uid()) with check (bucket_id = 'plugin-icons' and owner = auth.uid());\n"
            "create policy if not exists \"icons_delete_owner\" on storage.objects for delete to authenticated using (bucket_id = 'plugin-icons' and owner = auth.uid());\n"
            "create policy if not exists \"files_update_owner\" on storage.objects for update to authenticated using (bucket_id = 'plugin-files' and owner = auth.uid()) with check (bucket_id = 'plugin-files' and owner = auth.uid());\n"
            "create policy if not exists \"files_delete_owner\" on storage.objects for delete to authenticated using (bucket_id = 'plugin-files' and owner = auth.uid());\n"
        )

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
                                      "Go to Settings → Plugins to enable it.")
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

    def sign_in(self):
        if not self._is_supabase:
            return
        email = (self.email_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        if not email or not password:
            QMessageBox.warning(self, "Login", "Enter email and password")
            return
        res = self.plugin_store.sign_in(email, password)
        if not res.get("ok"):
            QMessageBox.critical(self, "Login", str(res.get("error")))
            return
        self._update_auth_ui()
        self._load_my_plugins()

    def sign_up(self):
        if not self._is_supabase:
            return
        email = (self.email_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        if not email or not password:
            QMessageBox.warning(self, "Sign up", "Enter email and password")
            return
        res = self.plugin_store.sign_up(email, password)
        if not res.get("ok"):
            QMessageBox.critical(self, "Sign up", str(res.get("error")))
            return
        QMessageBox.information(self, "Sign up", "Check your email to confirm (if required). Now login.")

    def sign_out(self):
        if not self._is_supabase:
            return
        self.plugin_store.sign_out()
        self._update_auth_ui()

    def _load_my_plugins(self):
        if not self._is_supabase:
            return
        try:
            self.my_plugins = self.plugin_store.list_my_plugins() or []
        except Exception:
            self.my_plugins = []
        try:
            self.my_list.blockSignals(True)
            self.my_list.clear()
            for p in self.my_plugins:
                name = p.get('name') or p.get('id')
                self.my_list.addItem(name)
        finally:
            self.my_list.blockSignals(False)

    def _find_my_by_name(self, name):
        for p in self.my_plugins:
            if (p.get('name') or p.get('id')) == name:
                return p
        return None

    def _on_my_select(self, text):
        p = self._find_my_by_name(text)
        if not p:
            return
        self._selected_my_id = p.get('id')
        self.input_id.setText(p.get('id') or "")
        self.input_id.setEnabled(False)
        self.input_name.setText(p.get('name') or "")
        self.input_version.setText(p.get('version') or "")
        self.input_author.setText(p.get('author') or "")
        self.input_desc.setPlainText(p.get('description') or "")
        cats = p.get('categories') or []
        self.input_cats.setText(','.join(cats))
        self.icon_path.setText("")
        self.file_path.setText("")

    def _reset_my_form(self):
        self._selected_my_id = None
        self.input_id.setEnabled(True)
        self.input_id.clear()
        self.input_name.clear()
        self.input_version.clear()
        self.input_author.clear()
        self.input_desc.clear()
        self.input_cats.clear()
        self.icon_path.clear()
        self.file_path.clear()

    def _save_my_plugin(self):
        if not self._is_supabase:
            return
        pid = (self.input_id.text() or "").strip()
        name = (self.input_name.text() or "").strip()
        version = (self.input_version.text() or "").strip() or "1.0.0"
        author = (self.input_author.text() or "").strip() or "Unknown"
        desc = self.input_desc.toPlainText().strip()
        cats = [c.strip() for c in (self.input_cats.text() or "").split(',') if c.strip()]
        iconp = (self.icon_path.text() or "").strip() or None
        filep = (self.file_path.text() or "").strip() or None
        if not pid or not name:
            QMessageBox.warning(self, "Save", "ID and Name are required")
            return
        if self._selected_my_id:
            res = self.plugin_store.update_plugin(self._selected_my_id, name=name, description=desc, version=version, author=author, categories=cats, icon_path=iconp, file_path=filep)
        else:
            res = self.plugin_store.create_plugin(pid, name, desc, version, author, cats, iconp, filep)
        if not res.get('ok'):
            QMessageBox.critical(self, "Save", str(res.get('error')))
            return
        QMessageBox.information(self, "Save", "Saved")
        self._reset_my_form()
        self._load_my_plugins()
        self.refresh_plugins()

    def _delete_my_plugin(self):
        if not self._is_supabase or not self._selected_my_id:
            return
        res = self.plugin_store.delete_plugin(self._selected_my_id)
        if not res.get('ok'):
            QMessageBox.critical(self, "Delete", str(res.get('error')))
            return
        QMessageBox.information(self, "Delete", "Deleted")
        self._reset_my_form()
        self._load_my_plugins()
        self.refresh_plugins()

    def _browse_icon(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Icon", os.path.expanduser('~'), "Images (*.png *.svg *.jpg *.jpeg)")
        if p:
            self.icon_path.setText(p)

    def _browse_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Plugin File", os.path.expanduser('~'), "Python (*.py)")
        if p:
            self.file_path.setText(p)

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
                              "You can now edit it and enable it in Settings → Plugins.")

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
