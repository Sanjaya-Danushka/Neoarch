"""Proxy & Network settings page — descriptive, education-first.

Explains what each connection option controls and *why* you would change
it, built with the same card language as the Security, Notifications and
Logging pages.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QWidget)

from neoarch.frontend.tokens import Colors, Fonts, QSS
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.views._settings_kit import make_card, row, sep, Stepper

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_GLOBE = (
    '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/>'
    '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10'
    ' 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'
)
_ICON_TIMER = (
    '<line x1="10" x2="14" y1="2" y2="2"/>'
    '<line x1="12" x2="15" y1="14" y2="11"/>'
    '<circle cx="12" cy="14" r="8"/>'
)
_ICON_WRENCH = (
    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77'
    'a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91'
    'a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
)


def _type_combo(app):
    combo = QComboBox()
    combo.setStyleSheet(QSS.COMBO)
    combo.addItem(_("None (direct connection)"), "none")
    combo.addItem("HTTP", "http")
    combo.addItem("HTTPS", "https")
    combo.addItem("SOCKS5", "socks5")
    idx = combo.findData(app.settings.get("proxy_type", "none"))
    if idx >= 0:
        combo.setCurrentIndex(idx)
    return combo


def _host_port_control(app):
    widget = QWidget()
    widget.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(widget)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)

    host = QLineEdit(app.settings.get("proxy_host", ""))
    host.setStyleSheet(QSS.LINEEDIT)
    host.setPlaceholderText(_("e.g. 127.0.0.1 or proxy.example.com"))
    host.textChanged.connect(lambda v: app.update_setting("proxy_host", v))
    lay.addWidget(host, 1)

    port = Stepper(1, 65535)
    port.setValue(int(app.settings.get("proxy_port", 8080)))
    port.valueChanged.connect(lambda v: app.update_setting("proxy_port", v))
    lay.addWidget(port)
    return widget, host, port


class ProxySettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.setup_ui()

    def setup_ui(self):
        title = QLabel(_("Proxy & Network"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(
            _("How NeoArch reaches the internet — proxies, timeouts and "
              "pacman's download behaviour"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        self.layout.addWidget(subtitle)

        # ── Connection ──
        self._type_combo = _type_combo(self.app)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._host_port, self._host, self._port = _host_port_control(self.app)

        connection_card, connection = make_card(_("Connection"), _ICON_GLOBE)
        connection.addWidget(row(
            _("Proxy type"),
            _("Nothing is routed through a proxy by default. Pick HTTP, "
              "HTTPS or SOCKS5 to send package, AUR and Flatpak requests "
              "through one."),
            control=self._type_combo))
        connection.addWidget(sep())
        connection.addWidget(row(
            _("Host & port"),
            _("The proxy's address and the TCP port it listens on. Only "
              "applied when a proxy type other than \"none\" is chosen."),
            control=self._host_port))
        self.layout.addWidget(connection_card)

        self._host_port.setEnabled(
            self._type_combo.currentData() != "none")

        # ── Timeouts ──
        self._timeout = Stepper(5, 300, step=5, suffix=" s")
        self._timeout.setValue(int(self.app.settings.get("request_timeout", 30)))
        self._timeout.valueChanged.connect(
            lambda v: self.app.update_setting("request_timeout", v))

        timeout_card, timeout = make_card(_("Timeouts"), _ICON_TIMER)
        timeout.addWidget(row(
            _("Request timeout"),
            _("How long NeoArch waits for a network reply before giving "
              "up. Raise it on slow links, lower it to fail fast."),
            control=self._timeout))
        self.layout.addWidget(timeout_card)

        # ── Advanced ──
        ssl_toggle = ToggleSwitch()
        ssl_toggle.setChecked(bool(self.app.settings.get("verify_ssl", True)))
        ssl_toggle.toggled.connect(
            lambda v: self.app.update_setting("verify_ssl", v))

        parallel_toggle = ToggleSwitch()
        parallel_toggle.setChecked(
            bool(self.app.settings.get("parallel_network", True)))
        parallel_toggle.toggled.connect(
            lambda v: self.app.update_setting("parallel_network", v))

        self._dl_stepper = Stepper(1, 32)
        try:
            from neoarch.backend.services.pacman_conf import get_parallel_downloads
            current = get_parallel_downloads()
        except Exception:
            current = None
        self._dl_stepper.setValue(current if current else 5)

        apply_btn = QPushButton(_("Apply"))
        apply_btn.setStyleSheet(QSS.BTN_OUTLINE)
        apply_btn.setFixedHeight(34)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_parallel_downloads)

        dl_control = QWidget()
        dl_control.setStyleSheet("background: transparent;")
        dl_lay = QHBoxLayout(dl_control)
        dl_lay.setContentsMargins(0, 0, 0, 0)
        dl_lay.setSpacing(8)
        dl_lay.addWidget(self._dl_stepper)
        dl_lay.addWidget(apply_btn)

        advanced_card, advanced = make_card(_("Advanced"), _ICON_WRENCH)
        advanced.addWidget(row(
            _("Verify SSL certificates"),
            _("Checks certificates on every HTTPS request. Disable only "
              "if a proxy inspects your traffic — it does weaken "
              "security."),
            control=ssl_toggle))
        advanced.addWidget(sep())
        advanced.addWidget(row(
            _("Parallel network requests"),
            _("Fetch from several sources at the same time. Faster "
              "lookups, at the cost of more simultaneous connections."),
            control=parallel_toggle))
        advanced.addWidget(sep())
        advanced.addWidget(row(
            _("Pacman ParallelDownloads"),
            _("How many packages pacman may download at once while "
              "updating. Applies to /etc/pacman.conf and needs root."),
            control=dl_control))
        self.layout.addWidget(advanced_card)

    def _apply_parallel_downloads(self):
        from neoarch.backend.services.pacman_conf import set_parallel_downloads
        count = self._dl_stepper.value()
        try:
            ok_result = set_parallel_downloads(count)
        except Exception:
            ok_result = False
        if ok_result:
            self.app.show_message.emit(
                "ParallelDownloads",
                _("Set pacman ParallelDownloads={count}").format(count=count))
        else:
            self.app.show_message.emit(
                "ParallelDownloads", _("Failed to apply (need root?)."))

    def _on_type_changed(self, _index):
        ptype = self._type_combo.currentData()
        self.app.update_setting("proxy_type", ptype)
        self._host_port.setEnabled(ptype != "none")