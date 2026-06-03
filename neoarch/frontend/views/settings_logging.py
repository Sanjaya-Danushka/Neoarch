import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QComboBox, QSpinBox, QPushButton,
                             QFileDialog, QCheckBox, QLineEdit)

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

_SPINBOX = """
    QSpinBox {
        background-color: rgba(18, 19, 22, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 8px 12px;
        color: #EDEDEF;
        font-size: 13px;
        min-width: 80px;
    }
    QSpinBox:focus {
        border-color: #00BFAE;
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


class LoggingSettingsWidget(QWidget):
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
        title = QLabel("Logging")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Configure logging behaviour and log file settings")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── General Card ──
        general_card, general_layout = self._make_card("General")

        level_row = QHBoxLayout()
        level_row.setSpacing(12)
        level_label = QLabel("Log level:")
        level_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        level_row.addWidget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.setStyleSheet(_COMBO)
        self.level_combo.addItem("DEBUG", "DEBUG")
        self.level_combo.addItem("INFO", "INFO")
        self.level_combo.addItem("WARNING", "WARNING")
        self.level_combo.addItem("ERROR", "ERROR")

        current_level = self.app.settings.get('log_level', 'INFO')
        idx = self.level_combo.findData(current_level)
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)

        self.level_combo.currentIndexChanged.connect(self._on_level_changed)
        level_row.addWidget(self.level_combo)

        level_hint = QLabel("DEBUG shows all details, ERROR shows only failures")
        level_hint.setStyleSheet("color: #5C5E66; font-size: 11px; border: none;")
        level_row.addWidget(level_hint)
        level_row.addStretch()

        general_layout.addLayout(level_row)

        self.cb_console = QCheckBox("Echo log to terminal / console")
        self.cb_console.setStyleSheet(_CHECKBOX)
        self.cb_console.setChecked(bool(self.app.settings.get('log_to_console', False)))
        self.cb_console.toggled.connect(lambda v: self.app.update_setting('log_to_console', v))
        general_layout.addWidget(self.cb_console)

        self.layout.addWidget(general_card)

        # ── Log File Card ──
        file_card, file_layout = self._make_card("Log File")

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_label = QLabel("Log file path:")
        path_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        path_row.addWidget(path_label)

        default_log = os.path.join(os.path.expanduser('~'), '.config', 'neoarch', 'neoarch.log')
        self.path_edit = QLineEdit(self.app.settings.get('log_file_path', default_log))
        self.path_edit.setStyleSheet(_LINEEDIT)
        self.path_edit.textChanged.connect(lambda v: self.app.update_setting('log_file_path', v))
        path_row.addWidget(self.path_edit, 1)

        browse_btn = QPushButton("Browse\u2026")
        browse_btn.setStyleSheet(_BTN_OUTLINE)
        browse_btn.setFixedHeight(40)

        def on_browse():
            path, _ = QFileDialog.getSaveFileName(self, "Select Log File",
                                                   self.path_edit.text(),
                                                   "Log Files (*.log *.txt);;All Files (*)")
            if path:
                self.path_edit.setText(path)
                self.app.update_setting('log_file_path', path)

        browse_btn.clicked.connect(on_browse)
        path_row.addWidget(browse_btn)

        file_layout.addLayout(path_row)

        max_size_row = QHBoxLayout()
        max_size_row.setSpacing(12)
        max_size_label = QLabel("Max log file size:")
        max_size_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        max_size_row.addWidget(max_size_label)

        self.max_size_spin = QSpinBox()
        self.max_size_spin.setStyleSheet(_SPINBOX)
        self.max_size_spin.setRange(1, 100)
        self.max_size_spin.setValue(int(self.app.settings.get('log_max_size_mb', 5)))
        self.max_size_spin.valueChanged.connect(lambda v: self.app.update_setting('log_max_size_mb', v))
        max_size_row.addWidget(self.max_size_spin)

        max_size_unit = QLabel("MB")
        max_size_unit.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        max_size_row.addWidget(max_size_unit)
        max_size_row.addStretch()

        file_layout.addLayout(max_size_row)

        self.layout.addWidget(file_card)

    def _on_level_changed(self, index):
        level = self.level_combo.currentData()
        self.app.update_setting('log_level', level)
