import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
                             QLabel, QCheckBox, QSpinBox, QPushButton)
from PyQt6.QtCore import Qt

class AutoUpdateSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        # Add title with subtitle
        title = QLabel("Auto Update")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #ffffff; 
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)
        
        subtitle = QLabel("Manage automatic updates and system snapshots")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        """)
        self.layout.addWidget(subtitle)
        
        # Auto Update Settings
        update_box = QGroupBox("Auto Update")
        update_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 12px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QSpinBox:focus {
                border-color: #0d7377;
            }
            QLabel {
                color: #b0b0b0;
            }
        """)
        auto_grid = QGridLayout(update_box)
        auto_grid.setContentsMargins(16, 20, 16, 16)
        auto_grid.setSpacing(12)

        self.cb_auto_update = QCheckBox("Enable automatic updates")
        self.cb_auto_update.setChecked(bool(self.app.settings.get('auto_update_enabled', False)))
        self.cb_auto_update.toggled.connect(lambda v: self.app.update_setting('auto_update_enabled', v))
        auto_grid.addWidget(self.cb_auto_update, 0, 0, 1, 2)

        auto_grid.addWidget(QLabel("Update interval (days):"), 1, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 30)  # 1 day to 30 days
        self.interval_spin.setValue(int(self.app.settings.get('auto_update_interval_days', 1)))
        self.interval_spin.valueChanged.connect(lambda v: self.app.update_setting('auto_update_interval_days', v))
        auto_grid.addWidget(self.interval_spin, 1, 1)

        self.layout.addWidget(update_box)

        # Snapshot Settings
        snapshot_box = QGroupBox("Snapshots")
        snapshot_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QPushButton {
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        snap_grid = QGridLayout(snapshot_box)
        snap_grid.setContentsMargins(16, 20, 16, 16)
        snap_grid.setSpacing(12)

        self.cb_snapshot = QCheckBox("Create snapshot before updates")
        self.cb_snapshot.setChecked(bool(self.app.settings.get('snapshot_before_update', False)))
        self.cb_snapshot.toggled.connect(lambda v: self.app.update_setting('snapshot_before_update', v))
        snap_grid.addWidget(self.cb_snapshot, 0, 0, 1, 2)

        snap_btns = QHBoxLayout()
        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.clicked.connect(self.app.create_snapshot)
        snap_btns.addWidget(create_snap_btn)

        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.clicked.connect(self.app.revert_to_snapshot)
        snap_btns.addWidget(revert_snap_btn)

        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.clicked.connect(self.app.delete_snapshots)
        snap_btns.addWidget(delete_snap_btn)

        snap_btns.addStretch()
        snap_grid.addLayout(snap_btns, 1, 0, 1, 2)

        self.layout.addWidget(snapshot_box)

        self.layout.addStretch()
