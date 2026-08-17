from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QComboBox, QSpinBox, QLineEdit,
                             QCheckBox, QPushButton)

from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii


class ProxySettingsWidget(QWidget):
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
        title = QLabel("Proxy & Network")
        title.setStyleSheet(f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD}; color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Configure network proxy settings and connection options")
        subtitle.setStyleSheet(f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2}; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Proxy Card ──
        proxy_card, proxy_layout = self._make_card("Proxy")

        type_row = QHBoxLayout()
        type_row.setSpacing(12)
        type_label = QLabel("Proxy type:")
        type_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        type_row.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet(QSS.COMBO)
        self.type_combo.addItem("None (direct connection)", "none")
        self.type_combo.addItem("HTTP", "http")
        self.type_combo.addItem("HTTPS", "https")
        self.type_combo.addItem("SOCKS5", "socks5")

        current_type = self.app.settings.get('proxy_type', 'none')
        idx = self.type_combo.findData(current_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self.type_combo)
        type_row.addStretch()
        proxy_layout.addLayout(type_row)

        host_row = QHBoxLayout()
        host_row.setSpacing(12)
        host_label = QLabel("Host:")
        host_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        host_row.addWidget(host_label)

        self.host_edit = QLineEdit(self.app.settings.get('proxy_host', ''))
        self.host_edit.setStyleSheet(QSS.LINEEDIT)
        self.host_edit.setPlaceholderText("e.g. 127.0.0.1 or proxy.example.com")
        self.host_edit.textChanged.connect(lambda v: self.app.update_setting('proxy_host', v))
        host_row.addWidget(self.host_edit, 1)
        proxy_layout.addLayout(host_row)

        port_row = QHBoxLayout()
        port_row.setSpacing(12)
        port_label = QLabel("Port:")
        port_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        port_row.addWidget(port_label)

        self.port_spin = QSpinBox()
        self.port_spin.setStyleSheet(QSS.SPINBOX)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(self.app.settings.get('proxy_port', 8080)))
        self.port_spin.valueChanged.connect(lambda v: self.app.update_setting('proxy_port', v))
        port_row.addWidget(self.port_spin)
        port_row.addStretch()
        proxy_layout.addLayout(port_row)

        self._toggle_proxy_fields(current_type != 'none')

        self.layout.addWidget(proxy_card)

        # ── Timeouts Card ──
        timeout_card, timeout_layout = self._make_card("Timeouts")

        req_row = QHBoxLayout()
        req_row.setSpacing(12)
        req_label = QLabel("Request timeout:")
        req_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        req_row.addWidget(req_label)

        self.req_timeout_spin = QSpinBox()
        self.req_timeout_spin.setStyleSheet(QSS.SPINBOX)
        self.req_timeout_spin.setRange(5, 300)
        self.req_timeout_spin.setSingleStep(5)
        self.req_timeout_spin.setValue(int(self.app.settings.get('request_timeout', 30)))
        self.req_timeout_spin.valueChanged.connect(lambda v: self.app.update_setting('request_timeout', v))
        req_row.addWidget(self.req_timeout_spin)

        req_unit = QLabel("seconds")
        req_unit.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        req_row.addWidget(req_unit)
        req_row.addStretch()
        timeout_layout.addLayout(req_row)

        self.layout.addWidget(timeout_card)

        # ── Misc Card ──
        misc_card, misc_layout = self._make_card("Advanced")

        self.cb_verify_ssl = QCheckBox("Verify SSL certificates")
        self.cb_verify_ssl.setStyleSheet(QSS.CHECKBOX)
        self.cb_verify_ssl.setChecked(bool(self.app.settings.get('verify_ssl', True)))
        self.cb_verify_ssl.toggled.connect(lambda v: self.app.update_setting('verify_ssl', v))
        misc_layout.addWidget(self.cb_verify_ssl)

        self.cb_parallel = QCheckBox("Allow parallel network requests")
        self.cb_parallel.setStyleSheet(QSS.CHECKBOX)
        self.cb_parallel.setChecked(bool(self.app.settings.get('parallel_network', True)))
        self.cb_parallel.toggled.connect(lambda v: self.app.update_setting('parallel_network', v))
        misc_layout.addWidget(self.cb_parallel)

        dl_row = QHBoxLayout()
        dl_row.setSpacing(12)
        dl_label = QLabel("pacman ParallelDownloads:")
        dl_label.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; border: none;")
        dl_row.addWidget(dl_label)

        self.dl_spin = QSpinBox()
        self.dl_spin.setStyleSheet(QSS.SPINBOX)
        self.dl_spin.setRange(1, 32)
        try:
            from neoarch.backend.services.pacman_conf import get_parallel_downloads
            current = get_parallel_downloads()
        except Exception:
            current = None
        self.dl_spin.setValue(current if current else 5)
        dl_row.addWidget(self.dl_spin)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(QSS.BTN_OUTLINE)
        apply_btn.clicked.connect(self._apply_parallel_downloads)
        dl_row.addWidget(apply_btn)

        dl_note = QLabel("Requires root; writes /etc/pacman.conf")
        dl_note.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; border: none;")
        dl_row.addWidget(dl_note)
        dl_row.addStretch()
        misc_layout.addLayout(dl_row)

        self.layout.addWidget(misc_card)

    def _apply_parallel_downloads(self):
        from neoarch.backend.services.pacman_conf import set_parallel_downloads
        count = self.dl_spin.value()
        try:
            ok_result = set_parallel_downloads(count)
        except Exception:
            ok_result = False
        if ok_result:
            self.app.show_message.emit("ParallelDownloads", f"Set pacman ParallelDownloads={count}")
        else:
            self.app.show_message.emit("ParallelDownloads", "Failed to apply (need root?).")

    def _on_type_changed(self, index):
        ptype = self.type_combo.currentData()
        self.app.update_setting('proxy_type', ptype)
        self._toggle_proxy_fields(ptype != 'none')

    def _toggle_proxy_fields(self, enabled):
        self.host_edit.setEnabled(enabled)
        self.port_spin.setEnabled(enabled)
