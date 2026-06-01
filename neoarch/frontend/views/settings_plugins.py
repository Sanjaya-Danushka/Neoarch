import os
import shutil
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
                             QLabel, QPushButton, QDialog, QFormLayout, QLineEdit,
                             QTextEdit, QDialogButtonBox, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

from neoarch.resources.paths import PLUGINS_ITEMS_DIR


class UploadPluginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upload Plugin")
        self.setMinimumSize(500, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Upload Plugin")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #ffffff;")
        layout.addWidget(header)

        desc = QLabel("Upload a plugin to the community repository.\n"
                      "Others can browse and install your shared plugin.")
        desc.setStyleSheet("font-size: 12px; color: #aaa;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 8, 0, 8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., My Custom Plugin")
        form.addRow("Plugin Name:", self.name_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g., Your Name")
        form.addRow("Author:", self.author_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Optional email for contact")
        form.addRow("Email:", self.email_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Describe what this plugin does\u2026")
        self.desc_edit.setMaximumHeight(100)
        form.addRow("Description:", self.desc_edit)

        path_row = QHBoxLayout()
        self.plugin_path_edit = QLineEdit()
        self.plugin_path_edit.setPlaceholderText("Path to plugin script or directory")
        path_row.addWidget(self.plugin_path_edit)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_path)
        path_row.addWidget(browse_btn)
        form.addRow("Plugin File:", path_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        upload_btn = buttons.addButton("Upload", QDialogButtonBox.ButtonRole.AcceptRole)
        upload_btn.clicked.connect(self._on_upload)
        cancel_btn = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #111; color: #e0e0e0;
            }
            QLineEdit, QTextEdit {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 8px 12px;
                color: #e0e0e0; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0d7377;
            }
            QPushButton {
                background-color: rgba(13,115,119,0.8);
                color: #fff; border: none; border-radius: 6px;
                padding: 8px 16px; font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0d7377;
            }
            QLabel { color: #ccc; }
        """)

    def _browse_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Plugin File",
                                               os.path.expanduser("~"),
                                               "Plugins (*.py *.sh);;All Files (*)")
        if path:
            self.plugin_path_edit.setText(path)

    def _on_upload(self):
        name = self.name_edit.text().strip()
        author = self.author_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        plugin_path = self.plugin_path_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Info", "Please provide a plugin name.")
            return
        if not author:
            QMessageBox.warning(self, "Missing Info", "Please provide an author name.")
            return
        if not plugin_path or not os.path.exists(plugin_path):
            QMessageBox.warning(self, "Missing File", "Please select a valid plugin file.")
            return

        plugins_items = PLUGINS_ITEMS_DIR
        ext = os.path.splitext(plugin_path)[1]
        dest_name = f"{name.replace(' ', '_').lower()}{ext}"
        dest_path = os.path.join(str(plugins_items), dest_name)
        try:
            os.makedirs(str(plugins_items), exist_ok=True)
            shutil.copy2(plugin_path, dest_path)
        except (OSError, shutil.Error) as e:
            QMessageBox.critical(self, "Error", f"Failed to copy plugin file: {e}")
            return

        QMessageBox.information(
            self, "Upload Complete",
            f"Plugin '{name}' has been uploaded.\n\n"
            f"File saved to: {dest_path}\n\n"
            "Submit a pull request to the community repository to share it with everyone.")
        self.accept()


class PluginsSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        title = QLabel("Plugins")
        title.setStyleSheet("""
            font-size: 28px; font-weight: 700; color: #ffffff;
            margin-bottom: 4px; letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)

        subtitle = QLabel("Manage plugins and external scripts")
        subtitle.setStyleSheet("font-size: 13px; color: #888; margin-bottom: 20px;")
        self.layout.addWidget(subtitle)

        upload_box = QGroupBox("Community Upload")
        upload_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px; font-weight: 600; color: #ffffff;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px; margin-top: 16px; padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 16px;
                padding: 0 8px; background-color: transparent;
            }
            QPushButton {
                background-color: transparent; color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px; padding: 12px 20px;
                font-weight: 500; font-size: 14px; min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15); border-color: #0d7377;
            }
            QLabel { color: #b0b0b0; }
        """)
        upload_layout = QVBoxLayout(upload_box)
        upload_layout.setContentsMargins(16, 20, 16, 16)
        upload_layout.setSpacing(8)

        upload_label = QLabel("Share your plugin with the community by uploading it to the repository.")
        upload_label.setWordWrap(True)
        upload_layout.addWidget(upload_label)

        upload_btn = QPushButton("Upload Plugin")
        upload_btn.clicked.connect(self._open_upload_dialog)
        upload_layout.addWidget(upload_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        open_dir_btn = QPushButton("Open Plugins Directory")
        open_dir_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(PLUGINS_ITEMS_DIR))))
        upload_layout.addWidget(open_dir_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout.addWidget(upload_box)
        self.layout.addStretch()

    def _open_upload_dialog(self):
        dialog = UploadPluginDialog(self)
        dialog.exec()
