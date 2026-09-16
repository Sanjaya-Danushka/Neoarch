import os
import time
import json
from typing import Any
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QRectF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QFrame)

from neoarch.backend import sys_utils
from neoarch.backend.services.i18n import _, language_label, available_languages, set_language, detect_system_language
from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii
from neoarch.frontend.components.toggle_switch import ToggleSwitch

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_SLIDERS = (
    '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/>'
    '<line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/>'
    '<line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/>'
    '<line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/>'
)
_ICON_PACKAGE = (
    '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8'
    'a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
    '<path d="M3.27 6.96 12 12.01l8.73-5.05"/><path d="M12 22.08V12"/>'
)
_ICON_SAVE = (
    '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
    '<polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>'
)
_ICON_SIGNAL = (
    '<path d="M2 20h.01"/><path d="M7 20v-4"/><path d="M12 20v-8"/>'
    '<path d="M17 20V8"/><path d="M22 4v16"/>'
)
_ICON_DATABASE = (
    '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/>'
    '<path d="M3 12A9 3 0 0 0 21 12"/>'
)


class _AurApiTestThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        t0 = time.time()
        try:
            from neoarch.backend.services.network import urlopen as _urlopen
            with _urlopen(
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

    # ── building blocks (About-page pattern) ────────────────────────

    @staticmethod
    def _icon_pixmap(svg_body, size=14, color="#EDEDEF"):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
            ' fill="none" stroke="{c}" stroke-width="2"'
            ' stroke-linecap="round" stroke-linejoin="round">{b}</svg>'
        ).format(c=color, b=svg_body)
        renderer = QSvgRenderer(svg.encode("utf-8"))
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        if renderer.isValid():
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
        return pm

    @staticmethod
    def _make_card(title_text, svg_body=None):
        """A flat settings card, exactly like the About page."""
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(QSS.CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 12)
        card_layout.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(10)
        if svg_body is not None:
            badge = QLabel()
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background: {Colors.SURFACE_2}; border: none;"
                f" border-radius: {Radii.SM}px;")
            badge.setPixmap(GeneralSettingsWidget._icon_pixmap(svg_body, 15))
            header.addWidget(badge)
        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)

        pad = QWidget()
        pad.setStyleSheet("background: transparent;")
        pad.setFixedHeight(2)
        card_layout.addWidget(pad)
        return card, card_layout

    @staticmethod
    def _row(title_text, subtitle_text=None, subtitle_color=None, control=None):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setSpacing(16)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)

        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        texts.addWidget(title)

        if subtitle_text:
            color = subtitle_color or Colors.TEXT_2
            subtitle = QLabel(subtitle_text)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {color};"
                " border: none; background: transparent;")
            texts.addWidget(subtitle)

        row.addLayout(texts, 1)
        if control is not None:
            row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row_widget

    @staticmethod
    def _sep():
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(
            f"background: {Colors.BORDER}; border: none; margin: 4px 0;")
        return line

    @staticmethod
    def _btn(text, on_click=None):
        """Quiet light button — same look as the About page links."""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 8px 18px;
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(0, 191, 174, 0.4);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.14);
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_3};
                border-color: {Colors.BORDER};
                background-color: transparent;
            }}
        """)
        btn.setFixedHeight(36)
        if on_click is not None:
            btn.clicked.connect(lambda checked=False: on_click())
        return btn

    # ── UI ─────────────────────────────────────────────────────────

    def setup_ui(self):
        title = QLabel(_("General"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Configure basic application settings and preferences"))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent;")
        self.layout.addWidget(subtitle)

        # ── Basic Settings ──
        basic_card, basic_layout = self._make_card(_("Basic Settings"), _ICON_SLIDERS)

        self.sw_auto_check = ToggleSwitch(self, _("Auto check updates on launch"))
        self.sw_auto_check.setChecked(bool(self.app.settings.get('auto_check_updates', True)), animate=False)
        self.sw_auto_check.toggled.connect(lambda v: self.app.update_setting('auto_check_updates', v))
        basic_layout.addWidget(self._row(
            _("Auto check updates on launch"),
            _("Checks for available updates each time the app starts."),
            control=self.sw_auto_check))
        basic_layout.addWidget(self._sep())

        self.sw_firmware = ToggleSwitch(self, _("Check for firmware updates"))
        self.sw_firmware.setChecked(bool(self.app.settings.get('include_firmware_updates', True)), animate=False)
        self.sw_firmware.toggled.connect(lambda v: self.app.update_setting('include_firmware_updates', v))
        basic_layout.addWidget(self._row(
            _("Check for firmware updates"),
            _("Detects firmware updates via fwupd on the Updates page. Applying "
              "always requires your explicit confirmation."),
            control=self.sw_firmware))
        basic_layout.addWidget(self._sep())

        self.sw_npm = ToggleSwitch(self, _("Use npm user mode"))
        self.sw_npm.setChecked(bool(self.app.settings.get('npm_user_mode', True)), animate=False)
        self.sw_npm.toggled.connect(lambda v: self.app.update_setting('npm_user_mode', v))
        basic_layout.addWidget(self._row(
            _("Use npm user mode for global installs"),
            _("Installs global npm packages to ~/.npm-global without sudo."),
            control=self.sw_npm))

        self.layout.addWidget(basic_card)

        # ── Package Sources ──
        sources_card, sources_layout = self._make_card(_("Package Sources"), _ICON_PACKAGE)

        aur_status = sys_utils.get_aur_helper()
        if aur_status:
            aur_note = f"{_('Currently using')}: {aur_status}"
            aur_color = Colors.TEXT_2
        else:
            aur_note = _("No AUR helper detected")
            aur_color = Colors.RED

        self.aur_helper_combo = QComboBox()
        self.aur_helper_combo.setStyleSheet(QSS.COMBO)
        self.aur_helper_combo.setMinimumWidth(210)

        available_helpers = sys_utils.get_available_aur_helpers()
        self.aur_helper_combo.addItem(_("Auto (detect available)"), "auto")
        for helper in ['yay', 'paru', 'trizen', 'pikaur']:
            label = helper if helper in available_helpers else f"{helper} ({_('not installed')})"
            self.aur_helper_combo.addItem(label, helper)

        current_helper = self.app.settings.get('aur_helper', 'auto')
        index = self.aur_helper_combo.findData(current_helper)
        if index >= 0:
            self.aur_helper_combo.setCurrentIndex(index)

        self.aur_helper_combo.currentIndexChanged.connect(self.on_aur_helper_changed)
        sources_layout.addWidget(self._row(
            _("AUR Helper"),
            aur_note,
            subtitle_color=aur_color,
            control=self.aur_helper_combo))
        sources_layout.addWidget(self._sep())

        self.culture_combo = QComboBox()
        self.culture_combo.setStyleSheet(QSS.COMBO)
        self.culture_combo.setMinimumWidth(210)
        try:
            langs = available_languages()
        except Exception:
            langs = []
        for lang in ["en"] + langs:
            self.culture_combo.addItem(language_label(lang), lang)

        current_culture = self.app.settings.get('culture') or detect_system_language() or 'en'
        self.culture_combo.blockSignals(True)
        index = self.culture_combo.findData(current_culture)
        if index >= 0:
            self.culture_combo.setCurrentIndex(index)
        self.culture_combo.blockSignals(False)
        self.culture_combo.currentIndexChanged.connect(self.on_culture_changed)
        sources_layout.addWidget(self._row(
            _("Language"),
            _("Applies to all pages immediately."),
            control=self.culture_combo))

        self.layout.addWidget(sources_card)

        # ── Bundle Autosave ──
        bundle_card, bundle_layout = self._make_card(_("Bundle Autosave"), _ICON_SAVE)

        self.sw_bsave = ToggleSwitch(self, _("Autosave bundle to file"))
        self.sw_bsave.setChecked(bool(self.app.settings.get('bundle_autosave', True)), animate=False)
        self.sw_bsave.toggled.connect(lambda v: self.app.update_setting('bundle_autosave', v))
        bundle_layout.addWidget(self._row(
            _("Autosave bundle to file"),
            _("Save the selected bundle automatically."),
            control=self.sw_bsave))
        bundle_layout.addWidget(self._sep())

        from_path = self.app.settings.get('bundle_autosave_path') or os.path.join(
            os.path.expanduser('~'), '.config', 'neoarch', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass

        self.path_edit = QLineEdit(from_path)
        self.path_edit.setStyleSheet(QSS.LINEEDIT)
        self.path_edit.setMinimumWidth(260)

        browse_btn = QPushButton(_("Browse…"))
        browse_btn.setStyleSheet(QSS.BTN_OUTLINE)
        browse_btn.setFixedHeight(36)

        def on_browse():
            path, _filter = QFileDialog.getSaveFileName(self, _("Select Bundle Autosave Path"),
                                                   from_path, "Bundle JSON (*.json)")
            if path:
                self.path_edit.setText(path)
                self.app.update_setting('bundle_autosave_path', path)

        browse_btn.clicked.connect(on_browse)

        path_control = QWidget()
        path_control.setStyleSheet("background: transparent;")
        path_control_layout = QHBoxLayout(path_control)
        path_control_layout.setContentsMargins(0, 0, 0, 0)
        path_control_layout.setSpacing(8)
        path_control_layout.addWidget(self.path_edit)
        path_control_layout.addWidget(browse_btn)

        bundle_layout.addWidget(self._row(
            _("Autosave path"),
            control=path_control))

        self.layout.addWidget(bundle_card)

        # ── Diagnostics ──
        diag_card, diag_layout = self._make_card(_("Diagnostics"), _ICON_SIGNAL)

        self.aur_test_btn = self._btn(_("Test AUR API"), self.test_aur_api)
        self.aur_test_btn.setMinimumWidth(132)
        diag_layout.addWidget(self._row(
            _("AUR RPC endpoint"),
            _("Verifies reachability of the AUR RPC endpoint used to resolve"
              " packages from the AUR source."),
            control=self.aur_test_btn))

        self.aur_result = QLabel(_("Idle"))
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        diag_layout.addWidget(self.aur_result)

        self.layout.addWidget(diag_card)

        # ── Data ──
        data_card, data_layout = self._make_card(_("Data"), _ICON_DATABASE)

        export_btn = self._btn(_("Export Settings"), lambda: self.app.export_settings())
        export_btn.setMinimumWidth(132)
        data_layout.addWidget(self._row(
            _("Export settings to file"),
            control=export_btn))
        data_layout.addWidget(self._sep())

        import_btn = self._btn(_("Import Settings"), lambda: self.app.import_settings())
        import_btn.setMinimumWidth(132)
        data_layout.addWidget(self._row(
            _("Import settings from file"),
            control=import_btn))

        self.layout.addWidget(data_card)

        self.layout.addStretch()

    def on_aur_helper_changed(self, index):
        helper = self.aur_helper_combo.currentData()
        self.app.update_setting('aur_helper', helper)

    def on_culture_changed(self, index):
        culture = self.culture_combo.currentData()
        self.app.update_setting('culture', culture)
        try:
            set_language(culture or 'en')
        except Exception:
            pass
        QTimer.singleShot(0, lambda: self.app.rebuild_ui())

    def test_aur_api(self):
        if self._aur_thread is not None and self._aur_thread.isRunning():
            return
        self.aur_test_btn.setEnabled(False)
        self.aur_result.setText(_("Testing…"))
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        self._aur_thread = _AurApiTestThread(self)
        self._aur_thread.finished.connect(self._on_aur_test_done)
        self._aur_thread.start()

    def _on_aur_test_done(self, result):
        self.aur_test_btn.setEnabled(True)
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        if result.get("ok"):
            text = _("OK")
            data = result.get("data") or {}
            if isinstance(data, dict) and data.get("resultcount", 0) > 0:
                text = _("OK (bash resolved)")
            self.aur_result.setText(f"{text} \u00b7 {result['ms']:.0f} ms")
            self.aur_result.setStyleSheet(
                f"color: {Colors.GREEN}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI};"
                " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        else:
            self.aur_result.setText(
                f"{_('Unreachable')} \u00b7 {result['ms']:.0f} ms"
                f" \u00b7 {result.get('err', '')[:80]}")
            self.aur_result.setStyleSheet(
                f"color: {Colors.RED}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI};"
                " border: none; background: transparent; padding: 8px 4px 4px 4px;")