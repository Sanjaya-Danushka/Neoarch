import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QCheckBox, QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QFrame)
from PyQt6.QtCore import Qt

from neoarch.backend import sys_utils

_CARD = """
    QFrame#settingsCard {
        background-color: rgba(28, 30, 36, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
    }
"""

_CHECKBOX = """
    QCheckBox {
        color: #EDEDEF;
        font-size: 13px;
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1.5px solid #5C5E66;
        background-color: rgba(18, 19, 22, 0.8);
    }
    QCheckBox::indicator:hover {
        border-color: #00BFAE;
    }
    QCheckBox::indicator:checked {
        background-color: #00BFAE;
        border: 1.5px solid #00BFAE;
    }
"""

_COMBO = """
    QComboBox {
        background-color: rgba(18, 19, 22, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 10px 14px;
        color: #EDEDEF;
        min-width: 180px;
        font-size: 13px;
    }
    QComboBox:hover {
        border-color: #00BFAE;
    }
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox::down-arrow {
        image: none;
        border: none;
    }
"""

_LINEEDIT = """
    QLineEdit {
        background-color: rgba(18, 19, 22, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 10px 14px;
        color: #EDEDEF;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: #00BFAE;
    }
"""

_BTN_OUTLINE = """
    QPushButton {
        background-color: transparent;
        color: #00BFAE;
        border: 1px solid rgba(0, 191, 174, 0.35);
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: rgba(0, 191, 174, 0.12);
        border-color: #00BFAE;
    }
"""

_BTN_GHOST = """
    QPushButton {
        background-color: transparent;
        color: #8B8D97;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.2);
    }
"""


class GeneralSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)

        self.setup_ui()

    def _make_card(self, title_text):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(_CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #EDEDEF; border: none;")
        card_layout.addWidget(title)

        return card, card_layout

    def setup_ui(self):
        title = QLabel("General")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Configure basic application settings and preferences")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Basic Settings Card ──
        basic_card, basic_layout = self._make_card("Basic Settings")

        self.cb_auto_check = QCheckBox("Auto check updates on launch")
        self.cb_auto_check.setStyleSheet(_CHECKBOX)
        self.cb_auto_check.setChecked(bool(self.app.settings.get('auto_check_updates', True)))
        self.cb_auto_check.toggled.connect(lambda v: self.app.update_setting('auto_check_updates', v))
        basic_layout.addWidget(self.cb_auto_check)

        self.cb_local = QCheckBox("Include Local source (custom scripts)")
        self.cb_local.setStyleSheet(_CHECKBOX)
        self.cb_local.setChecked(bool(self.app.settings.get('include_local_source', True)))
        self.cb_local.toggled.connect(lambda v: self.app.update_setting('include_local_source', v))
        basic_layout.addWidget(self.cb_local)

        self.cb_npm = QCheckBox("Use npm user mode for global installs")
        self.cb_npm.setStyleSheet(_CHECKBOX)
        self.cb_npm.setChecked(bool(self.app.settings.get('npm_user_mode', True)))
        self.cb_npm.toggled.connect(lambda v: self.app.update_setting('npm_user_mode', v))
        basic_layout.addWidget(self.cb_npm)

        aur_row = QHBoxLayout()
        aur_row.setSpacing(12)
        aur_label = QLabel("AUR Helper:")
        aur_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        aur_row.addWidget(aur_label)

        self.aur_helper_combo = QComboBox()
        self.aur_helper_combo.setStyleSheet(_COMBO)

        available_helpers = sys_utils.get_available_aur_helpers()
        self.aur_helper_combo.addItem("Auto (detect available)", "auto")
        for helper in ['yay', 'paru', 'trizen', 'pikaur']:
            label = helper if helper in available_helpers else f"{helper} (not installed)"
            self.aur_helper_combo.addItem(label, helper)

        current_helper = self.app.settings.get('aur_helper', 'auto')
        index = self.aur_helper_combo.findData(current_helper)
        if index >= 0:
            self.aur_helper_combo.setCurrentIndex(index)

        self.aur_helper_combo.currentIndexChanged.connect(self.on_aur_helper_changed)
        aur_row.addWidget(self.aur_helper_combo)

        detected_helper = sys_utils.get_aur_helper()
        if detected_helper:
            status_text = f"Currently using: {detected_helper}"
            status_color = "#8B8D97"
        else:
            status_text = "No AUR helper detected"
            status_color = "#FF6B6B"
        helper_status = QLabel(status_text)
        helper_status.setStyleSheet(f"color: {status_color}; font-size: 11px; border: none;")
        aur_row.addWidget(helper_status)
        aur_row.addStretch()

        basic_layout.addLayout(aur_row)
        self.layout.addWidget(basic_card)

        # ── Bundle Autosave Card ──
        bundle_card, bundle_layout = self._make_card("Bundle Autosave")

        self.cb_bsave = QCheckBox("Autosave bundle to file")
        self.cb_bsave.setStyleSheet(_CHECKBOX)
        self.cb_bsave.setChecked(bool(self.app.settings.get('bundle_autosave', True)))
        self.cb_bsave.toggled.connect(lambda v: self.app.update_setting('bundle_autosave', v))
        bundle_layout.addWidget(self.cb_bsave)

        from_path = self.app.settings.get('bundle_autosave_path') or os.path.join(
            os.path.expanduser('~'), '.config', 'neoarch', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_label = QLabel("Autosave path:")
        path_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        path_row.addWidget(path_label)

        self.path_edit = QLineEdit(from_path)
        self.path_edit.setStyleSheet(_LINEEDIT)
        path_row.addWidget(self.path_edit, 1)

        browse_btn = QPushButton("Browse\u2026")
        browse_btn.setStyleSheet(_BTN_OUTLINE)
        browse_btn.setFixedHeight(40)

        def on_browse():
            path, _ = QFileDialog.getSaveFileName(self, "Select Bundle Autosave Path",
                                                   from_path, "Bundle JSON (*.json)")
            if path:
                self.path_edit.setText(path)
                self.app.update_setting('bundle_autosave_path', path)

        browse_btn.clicked.connect(on_browse)
        path_row.addWidget(browse_btn)

        bundle_layout.addLayout(path_row)
        self.layout.addWidget(bundle_card)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.06); background-color: rgba(255,255,255,0.06); max-height: 1px;")
        self.layout.addWidget(sep)

        # ── Export / Import ──
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        export_btn = QPushButton("Export Settings")
        export_btn.setStyleSheet(_BTN_OUTLINE)
        export_btn.setFixedHeight(42)
        export_btn.setMinimumWidth(160)
        export_btn.clicked.connect(lambda: self.app.export_settings())
        btn_box.addWidget(export_btn)

        import_btn = QPushButton("Import Settings")
        import_btn.setStyleSheet(_BTN_GHOST)
        import_btn.setFixedHeight(42)
        import_btn.setMinimumWidth(160)
        import_btn.clicked.connect(lambda: self.app.import_settings())
        btn_box.addWidget(import_btn)

        btn_box.addStretch()
        self.layout.addLayout(btn_box)

    def on_aur_helper_changed(self, index):
        helper = self.aur_helper_combo.currentData()
        self.app.update_setting('aur_helper', helper)
