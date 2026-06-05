from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QWidget,
)

from neoarch.backend.services import settings as settings_service
from neoarch.frontend.views.settings_general import GeneralSettingsWidget
from neoarch.frontend.views.settings_auto_update import AutoUpdateSettingsWidget
from neoarch.frontend.views.settings_notifications import NotificationsSettingsWidget
from neoarch.frontend.views.settings_logging import LoggingSettingsWidget
from neoarch.frontend.views.settings_proxy import ProxySettingsWidget


class _SettingsMixin:
    def load_settings(self):
        return settings_service.load_settings()

    def save_settings(self):
        return settings_service.save_settings(self.settings, self.log)

    def build_settings_ui(self):
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            QFrame#settingsSidebar {
                background-color: rgba(22, 23, 26, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
            QPushButton {
                text-align: left;
                padding: 14px 20px;
                border: none;
                background-color: transparent;
                color: #8B8D97;
                font-size: 14px;
                font-weight: 500;
                border-radius: 8px;
                margin: 2px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
                color: #EDEDEF;
            }
            QPushButton:checked {
                background-color: rgba(0, 191, 174, 0.12);
                color: #00BFAE;
                font-weight: 600;
            }
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 24)
        sidebar_layout.setSpacing(2)

        self.settings_nav_buttons = {}

        header_label = QLabel("SETTINGS")
        header_label.setStyleSheet("""
            color: #5C5E66;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.2px;
            padding: 8px 20px 12px 20px;
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

        btn_notifications = QPushButton("Notifications")
        btn_notifications.setCheckable(True)
        btn_notifications.clicked.connect(lambda: self.switch_settings_category("notifications"))
        self.settings_nav_buttons["notifications"] = btn_notifications
        sidebar_layout.addWidget(btn_notifications)

        btn_logging = QPushButton("Logging")
        btn_logging.setCheckable(True)
        btn_logging.clicked.connect(lambda: self.switch_settings_category("logging"))
        self.settings_nav_buttons["logging"] = btn_logging
        sidebar_layout.addWidget(btn_logging)

        btn_proxy = QPushButton("Proxy & Network")
        btn_proxy.setCheckable(True)
        btn_proxy.clicked.connect(lambda: self.switch_settings_category("proxy"))
        self.settings_nav_buttons["proxy"] = btn_proxy
        sidebar_layout.addWidget(btn_proxy)

        sidebar_layout.addStretch()

        version_label = QLabel("NeoArch v2.0")
        version_label.setStyleSheet("""
            color: #5C5E66;
            font-size: 11px;
            padding: 12px 20px;
        """)
        sidebar_layout.addWidget(version_label)

        # Content area
        content_area = QFrame()
        content_area.setObjectName("settingsContent")
        content_area.setStyleSheet("QFrame#settingsContent { background-color: rgba(22, 23, 26, 0.6); }")

        self.settings_content_layout = QVBoxLayout(content_area)
        self.settings_content_layout.setContentsMargins(32, 32, 32, 32)
        self.settings_content_layout.setSpacing(24)

        self.settings_widgets = {
            "general": GeneralSettingsWidget(self),
            "auto_update": AutoUpdateSettingsWidget(self),
            "notifications": NotificationsSettingsWidget(self),
            "logging": LoggingSettingsWidget(self),
            "proxy": ProxySettingsWidget(self),
        }

        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == "general")
            self.settings_content_layout.addWidget(widget)

        self.settings_content_layout.addStretch()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, 1)

        container_widget = QWidget()
        container_widget.setLayout(main_layout)
        self.settings_layout.addWidget(container_widget)

    def switch_settings_category(self, category):
        for key, btn in self.settings_nav_buttons.items():
            btn.setChecked(key == category)
        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == category)

    def update_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def export_settings(self):
        return settings_service.export_settings(self)

    def import_settings(self):
        return settings_service.import_settings(self)
