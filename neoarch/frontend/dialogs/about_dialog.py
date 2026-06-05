import platform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTextBrowser, QWidget)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices

from neoarch.resources.paths import APP_NAME, APP_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(540, 620)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("aboutDialog")

        self._build()
        self._apply_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_pixmap = QPixmap("/usr/share/pixmaps/archlinux.png")
        if icon_pixmap.isNull():
            icon_pixmap = QPixmap(64, 64)
            icon_pixmap.fill(Qt.GlobalColor.transparent)
        icon_label.setPixmap(icon_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop |
                                Qt.AlignmentFlag.AlignLeft)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title_layout.addWidget(title)

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setObjectName("versionLabel")
        version_font = QFont()
        version_font.setPointSize(11)
        version_label.setFont(version_font)
        title_layout.addWidget(version_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        desc = QLabel(
            f"{APP_NAME} is an Arch Linux package management frontend "
            "built with Python and Qt6. It provides a modern, fast, "
            "and user-friendly interface for managing packages, AUR helpers, "
            "Flatpak, Snap, AppImage, and custom scripts all in one place.")
        desc.setObjectName("descLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        info_widget = QWidget()
        info_widget.setObjectName("infoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)

        sys_info = [
            f"Architecture: {platform.machine()}",
            f"System: {platform.system()} {platform.release()}",
            f"Python: {platform.python_version()}",
            f"Qt: 6",
        ]
        for line in sys_info:
            lbl = QLabel(line)
            lbl.setObjectName("infoLine")
            info_layout.addWidget(lbl)
        layout.addWidget(info_widget)

        links_widget = QWidget()
        links_widget.setObjectName("linksWidget")
        links_layout = QHBoxLayout(links_widget)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(12)

        website_btn = QPushButton("Website")
        website_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://neoarch.netlify.app/")))
        website_btn.setObjectName("linkBtn")
        links_layout.addWidget(website_btn)

        gh_btn = QPushButton("GitHub")
        gh_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/anomalyco/Neoarch")))
        gh_btn.setObjectName("linkBtn")
        links_layout.addWidget(gh_btn)

        report_btn = QPushButton("Report Issue")
        report_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/anomalyco/Neoarch/issues")))
        report_btn.setObjectName("linkBtn")
        links_layout.addWidget(report_btn)

        links_layout.addStretch()
        layout.addWidget(links_widget)

        license_label = QLabel(
            "Licensed under the MIT License. See LICENSE for details.")
        license_label.setObjectName("licenseLabel")
        license_label.setWordWrap(True)
        layout.addWidget(license_label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setObjectName("closeBtn")
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog#aboutDialog {
                background-color: #0f0f0f;
            }
            QLabel#appTitle {
                color: #FFFFFF;
            }
            QLabel#versionLabel {
                color: #0d7377;
            }
            QLabel#descLabel {
                color: #b0b0b0;
                font-size: 13px;
                line-height: 1.5;
            }
            QLabel#infoLine {
                color: #a0a0a0;
                font-size: 12px;
            }
            QLabel#licenseLabel {
                color: #666;
                font-size: 11px;
            }
            QWidget#infoWidget {
                background-color: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }
            QWidget#linksWidget {
                background: transparent;
            }
            QPushButton#linkBtn {
                background-color: rgba(255,255,255,0.05);
                color: #0d7377; border: 1px solid rgba(13,115,119,0.3);
                border-radius: 6px; padding: 8px 16px; font-size: 13px;
            }
            QPushButton#linkBtn:hover {
                background-color: rgba(13,115,119,0.12);
                border-color: #0d7377;
            }
            QPushButton#closeBtn {
                background-color: #0d7377; color: #ffffff;
                border: none; border-radius: 8px;
                padding: 10px 32px; font-size: 14px; font-weight: 600;
                min-width: 120px;
            }
            QPushButton#closeBtn:hover {
                background-color: #0f8a8f;
            }
        """)
