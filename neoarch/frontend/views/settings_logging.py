import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QComboBox, QSpinBox, QPushButton,
                             QFileDialog, QCheckBox, QLineEdit)

from neoarch.frontend.tokens import QSS, Colors, Fonts


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
        card.setStyleSheet(QSS.CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel(title_text)
        title.setStyleSheet(f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI}; color: {Colors.TEXT}; border: none;")
        card_layout.addWidget(title)

        return card, card_layout

    def setup_ui(self):
        title = QLabel("Logging")
        title.setStyleSheet(f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD}; color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Configure logging behaviour and log file settings")
        subtitle.setStyleSheet(f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2}; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── General Card ──
        general_card, general_layout = self._make_card("General")

        level_row = QHBoxLayout()
        level_row.setSpacing(12)
        level_label = QLabel("Log level:")
        level_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        level_row.addWidget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.setStyleSheet(QSS.COMBO)
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
        level_hint.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; border: none;")
        level_row.addWidget(level_hint)
        level_row.addStretch()

        general_layout.addLayout(level_row)

        self.cb_console = QCheckBox("Echo log to terminal / console")
        self.cb_console.setStyleSheet(QSS.CHECKBOX)
        self.cb_console.setChecked(bool(self.app.settings.get('log_to_console', False)))
        self.cb_console.toggled.connect(lambda v: self.app.update_setting('log_to_console', v))
        general_layout.addWidget(self.cb_console)

        self.layout.addWidget(general_card)

        # ── Log File Card ──
        file_card, file_layout = self._make_card("Log File")

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_label = QLabel("Log file path:")
        path_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        path_row.addWidget(path_label)

        default_log = os.path.join(os.path.expanduser('~'), '.config', 'neoarch', 'neoarch.log')
        self.path_edit = QLineEdit(self.app.settings.get('log_file_path', default_log))
        self.path_edit.setStyleSheet(QSS.LINEEDIT)
        self.path_edit.textChanged.connect(lambda v: self.app.update_setting('log_file_path', v))
        path_row.addWidget(self.path_edit, 1)

        browse_btn = QPushButton("Browse\u2026")
        browse_btn.setStyleSheet(QSS.BTN_OUTLINE)
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
        max_size_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        max_size_row.addWidget(max_size_label)

        self.max_size_spin = QSpinBox()
        self.max_size_spin.setStyleSheet(QSS.SPINBOX)
        self.max_size_spin.setRange(1, 100)
        self.max_size_spin.setValue(int(self.app.settings.get('log_max_size_mb', 5)))
        self.max_size_spin.valueChanged.connect(lambda v: self.app.update_setting('log_max_size_mb', v))
        max_size_row.addWidget(self.max_size_spin)

        max_size_unit = QLabel("MB")
        max_size_unit.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        max_size_row.addWidget(max_size_unit)
        max_size_row.addStretch()

        file_layout.addLayout(max_size_row)

        self.layout.addWidget(file_card)

    def _on_level_changed(self, index):
        level = self.level_combo.currentData()
        self.app.update_setting('log_level', level)
