import os
import time
import json
import urllib.request
from typing import Any
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QFrame)

from neoarch.backend import sys_utils
from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii


class _AurApiTestThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        t0 = time.time()
        try:
            with urllib.request.urlopen(
                "https://aur.archlinux.org/rpc/?v=5&type=info&arg[]=bash",
                timeout=15,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ms = (time.time() - t0) * 1000
            self.finished.emit({"ok": True, "ms": ms, "data": data, "err": ""})
        except Exception as err:
            ms = (time.time() - t0) * 1000
            self.finished.emit({"ok": False, "ms": ms, "data": None, "err": str(err)})


class GeneralSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self._aur_thread = None

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
        title = QLabel("General")
        title.setStyleSheet(f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD}; color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Configure basic application settings and preferences")
        subtitle.setStyleSheet(f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2}; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Basic Settings Card ──
        basic_card, basic_layout = self._make_card("Basic Settings")

        self.cb_auto_check = QCheckBox("Auto check updates on launch")
        self.cb_auto_check.setStyleSheet(QSS.CHECKBOX)
        self.cb_auto_check.setChecked(bool(self.app.settings.get('auto_check_updates', True)))
        self.cb_auto_check.toggled.connect(lambda v: self.app.update_setting('auto_check_updates', v))
        basic_layout.addWidget(self.cb_auto_check)

        self.cb_local = QCheckBox("Include Local source (custom scripts)")
        self.cb_local.setStyleSheet(QSS.CHECKBOX)
        self.cb_local.setChecked(bool(self.app.settings.get('include_local_source', True)))
        self.cb_local.toggled.connect(lambda v: self.app.update_setting('include_local_source', v))
        basic_layout.addWidget(self.cb_local)

        self.cb_npm = QCheckBox("Use npm user mode for global installs")
        self.cb_npm.setStyleSheet(QSS.CHECKBOX)
        self.cb_npm.setChecked(bool(self.app.settings.get('npm_user_mode', True)))
        self.cb_npm.toggled.connect(lambda v: self.app.update_setting('npm_user_mode', v))
        basic_layout.addWidget(self.cb_npm)

        aur_row = QHBoxLayout()
        aur_row.setSpacing(12)
        aur_label = QLabel("AUR Helper:")
        aur_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        aur_row.addWidget(aur_label)

        self.aur_helper_combo = QComboBox()
        self.aur_helper_combo.setStyleSheet(QSS.COMBO)

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
            status_color = Colors.TEXT_2
        else:
            status_text = "No AUR helper detected"
            status_color = Colors.RED
        helper_status = QLabel(status_text)
        helper_status.setStyleSheet(f"color: {status_color}; font-size: {Fonts.SM}; border: none;")
        aur_row.addWidget(helper_status)
        aur_row.addStretch()

        basic_layout.addLayout(aur_row)

        culture_row = QHBoxLayout()
        culture_row.setSpacing(12)
        culture_label = QLabel("Language / Culture:")
        culture_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        culture_row.addWidget(culture_label)

        self.culture_combo = QComboBox()
        self.culture_combo.setStyleSheet(QSS.COMBO)
        try:
            from neoarch.backend.services.i18n import available_languages
            langs = available_languages()
        except Exception:
            langs = []
        for lang in ["en"] + langs:
            label = {"en": "English", "si": "සිංහල (Sinhala)", "es": "Español (Spanish)"}.get(lang, lang)
            self.culture_combo.addItem(label, lang)

        current_culture = self.app.settings.get('culture', 'en')
        index = self.culture_combo.findData(current_culture)
        if index >= 0:
            self.culture_combo.setCurrentIndex(index)
        self.culture_combo.currentIndexChanged.connect(self.on_culture_changed)
        culture_row.addWidget(self.culture_combo)

        culture_note = QLabel("Affects the CLI translation catalog; the GUI ships in English.")
        culture_note.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; border: none;")
        culture_row.addWidget(culture_note)
        culture_row.addStretch()

        basic_layout.addLayout(culture_row)
        self.layout.addWidget(basic_card)

        # ── Bundle Autosave Card ──
        bundle_card, bundle_layout = self._make_card("Bundle Autosave")

        self.cb_bsave = QCheckBox("Autosave bundle to file")
        self.cb_bsave.setStyleSheet(QSS.CHECKBOX)
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
        path_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        path_row.addWidget(path_label)

        self.path_edit = QLineEdit(from_path)
        self.path_edit.setStyleSheet(QSS.LINEEDIT)
        path_row.addWidget(self.path_edit, 1)

        browse_btn = QPushButton("Browse\u2026")
        browse_btn.setStyleSheet(QSS.BTN_OUTLINE)
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
        sep.setStyleSheet(f"color: {Colors.BORDER}; background-color: {Colors.BORDER}; max-height: 1px;")
        self.layout.addWidget(sep)

        # ── AUR RPC Connectivity Card ──
        aur_card, aur_layout = self._make_card("AUR RPC Connectivity")

        aur_row = QHBoxLayout()
        aur_row.setSpacing(12)
        self.aur_test_btn = QPushButton("Test AUR API")
        self.aur_test_btn.setStyleSheet(QSS.BTN_OUTLINE)
        self.aur_test_btn.setFixedHeight(38)
        self.aur_test_btn.setMaximumWidth(140)
        self.aur_test_btn.clicked.connect(self.test_aur_api)
        aur_row.addWidget(self.aur_test_btn)

        self.aur_result = QLabel("Idle")
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; border: none;")
        aur_row.addWidget(self.aur_result)
        aur_row.addStretch()
        aur_layout.addLayout(aur_row)

        aur_note = QLabel(
            "Verifies reachability of the AUR RPC endpoint used to resolve"
            " packages from the AUR source.")
        aur_note.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; border: none;")
        aur_layout.addWidget(aur_note)

        self.layout.addWidget(aur_card)

        # ── Separator ──
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {Colors.BORDER}; background-color: {Colors.BORDER}; max-height: 1px;")
        self.layout.addWidget(sep2)

        # ── Export / Import ──
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        export_btn = QPushButton("Export Settings")
        export_btn.setStyleSheet(QSS.BTN_OUTLINE)
        export_btn.setFixedHeight(42)
        export_btn.setMinimumWidth(160)
        export_btn.clicked.connect(lambda: self.app.export_settings())
        btn_box.addWidget(export_btn)

        import_btn = QPushButton("Import Settings")
        import_btn.setStyleSheet(QSS.BTN_GHOST)
        import_btn.setFixedHeight(42)
        import_btn.setMinimumWidth(160)
        import_btn.clicked.connect(lambda: self.app.import_settings())
        btn_box.addWidget(import_btn)

        btn_box.addStretch()
        self.layout.addLayout(btn_box)

    def on_aur_helper_changed(self, index):
        helper = self.aur_helper_combo.currentData()
        self.app.update_setting('aur_helper', helper)

    def on_culture_changed(self, index):
        culture = self.culture_combo.currentData()
        self.app.update_setting('culture', culture)

    def test_aur_api(self):
        if self._aur_thread is not None and self._aur_thread.isRunning():
            return
        self.aur_test_btn.setEnabled(False)
        self.aur_result.setText("Testing\u2026")
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; border: none;")
        self._aur_thread = _AurApiTestThread(self)
        self._aur_thread.finished.connect(self._on_aur_test_done)
        self._aur_thread.start()

    def _on_aur_test_done(self, result):
        self.aur_test_btn.setEnabled(True)
        if result.get("ok"):
            text = "OK"
            data = result.get("data") or {}
            if isinstance(data, dict) and data.get("resultcount", 0) > 0:
                text = "OK (bash resolved)"
            self.aur_result.setText(f"{text} \u00b7 {result['ms']:.0f} ms")
            self.aur_result.setStyleSheet(
                f"color: {Colors.GREEN}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI}; border: none;")
        else:
            self.aur_result.setText(
                f"Unreachable \u00b7 {result['ms']:.0f} ms"
                f" \u00b7 {result.get('err', '')[:80]}")
            self.aur_result.setStyleSheet(
                f"color: {Colors.RED}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI}; border: none;")
