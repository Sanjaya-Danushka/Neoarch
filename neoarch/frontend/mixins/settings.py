from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QWidget,
)

from neoarch.backend.services import settings as settings_service
from neoarch.resources.paths import APP_VERSION, APP_EDITION
from neoarch.frontend.views.settings_general import GeneralSettingsWidget
from neoarch.frontend.views.settings_auto_update import AutoUpdateSettingsWidget
from neoarch.frontend.views.settings_notifications import NotificationsSettingsWidget
from neoarch.frontend.views.settings_logging import LoggingSettingsWidget
from neoarch.frontend.views.settings_proxy import ProxySettingsWidget
from neoarch.frontend.views.settings_maintenance import MaintenanceSettingsWidget
from neoarch.frontend.views.settings_appearance import AppearanceSettingsWidget
from neoarch.frontend.tokens import Colors, Fonts, Fonts, Radii


class _SettingsMixin:
    def load_settings(self):
        return settings_service.load_settings()

    def save_settings(self):
        return settings_service.save_settings(self.settings, self.log)

    def build_settings_ui(self):
        # Clear existing widgets
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        self._settings_built = False

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(268)
        sidebar.setStyleSheet(f"""
            QFrame#settingsSidebar {{
                background-color: {Colors.BG};
                border-right: 1px solid {Colors.BORDER};
            }}
            QPushButton {{
                text-align: left;
                padding: 10px 16px;
                border: none;
                background-color: transparent;
                color: {Colors.TEXT_2};
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
                border-radius: {Radii.MD}px;
                margin: 1px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_SOFT};
                color: {Colors.ACCENT};
                font-weight: {Fonts.SEMI};
            }}
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(1)

        self.settings_nav_buttons = {}

        header_label = QLabel("SETTINGS")
        header_label.setStyleSheet(f"""
            color: {Colors.TEXT_3};
            font-size: {Fonts.SM};
            font-weight: {Fonts.BOLD};
            letter-spacing: 1.2px;
            padding: 6px 16px 8px 16px;
        """)
        sidebar_layout.addWidget(header_label)

        btn_general = QPushButton("General")
        btn_general.setCheckable(True)
        btn_general.setChecked(True)
        btn_general.clicked.connect(lambda: self.switch_settings_category("general"))
        self.settings_nav_buttons["general"] = btn_general
        sidebar_layout.addWidget(btn_general)

        btn_appearance = QPushButton("Appearance")
        btn_appearance.setCheckable(True)
        btn_appearance.clicked.connect(lambda: self.switch_settings_category("appearance"))
        self.settings_nav_buttons["appearance"] = btn_appearance
        sidebar_layout.addWidget(btn_appearance)

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

        btn_maintenance = QPushButton("Maintenance")
        btn_maintenance.setCheckable(True)
        btn_maintenance.clicked.connect(lambda: self.switch_settings_category("maintenance"))
        self.settings_nav_buttons["maintenance"] = btn_maintenance
        sidebar_layout.addWidget(btn_maintenance)

        sidebar_layout.addStretch()

        # Version badge with edition
        version_container = QHBoxLayout()
        version_container.setContentsMargins(16, 4, 16, 8)
        version_container.setSpacing(6)

        version_text = QLabel(f"NeoArch {APP_VERSION}")
        version_text.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; background: transparent;")
        version_container.addWidget(version_text)

        edition_badge = QLabel(APP_EDITION)
        edition_badge.setStyleSheet(f"""
            color: #0C0C0E;
            background-color: {Colors.ACCENT};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 2px 8px;
            border-radius: 10px;
        """)
        edition_badge.setFixedHeight(18)
        version_container.addWidget(edition_badge)
        version_container.addStretch()

        sidebar_layout.addLayout(version_container)

        # Content area
        content_area = QFrame()
        content_area.setObjectName("settingsContent")
        content_area.setStyleSheet(f"QFrame#settingsContent {{ background-color: #0C0C0E; }}")

        self.settings_content_layout = QVBoxLayout(content_area)
        self.settings_content_layout.setContentsMargins(24, 24, 24, 24)
        self.settings_content_layout.setSpacing(20)

        self.settings_widgets = {
            "general": GeneralSettingsWidget(self),
            "appearance": AppearanceSettingsWidget(self),
            "auto_update": AutoUpdateSettingsWidget(self),
            "notifications": NotificationsSettingsWidget(self),
            "logging": LoggingSettingsWidget(self),
            "proxy": ProxySettingsWidget(self),
            "maintenance": MaintenanceSettingsWidget(self),
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
