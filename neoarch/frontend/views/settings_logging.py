"""Logging settings page — descriptive, education-first.

Explains what each log option controls and *why* you would change it,
built with the same card language as the Security, Notifications and
Appearance pages.
"""

import os

from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QWidget, QFileDialog)

from neoarch.frontend.tokens import Colors, Fonts, QSS
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.views._settings_kit import (
    make_card, row, sep, advice, Stepper)

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_TERMINAL = (
    '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
)
_ICON_FILE = (
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/>'
    '<line x1="8" y1="13" x2="16" y2="13"/>'
    '<line x1="8" y1="17" x2="13" y2="17"/>'
)
_ICON_BOOK = (
    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
    '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
)


def _level_combo(app):
    combo = QComboBox()
    combo.setStyleSheet(QSS.COMBO)
    combo.addItem(_("DEBUG"), "DEBUG")
    combo.addItem(_("INFO"), "INFO")
    combo.addItem(_("WARNING"), "WARNING")
    combo.addItem(_("ERROR"), "ERROR")
    idx = combo.findData(app.settings.get("log_level", "INFO"))
    if idx >= 0:
        combo.setCurrentIndex(idx)
    combo.currentIndexChanged.connect(
        lambda _i: app.update_setting("log_level", combo.currentData()))
    return combo


def _console_toggle(app):
    toggle = ToggleSwitch()
    toggle.setChecked(bool(app.settings.get("log_to_console", False)))
    toggle.toggled.connect(lambda v: app.update_setting("log_to_console", v))
    return toggle


def _path_control(app):
    widget = QWidget()
    widget.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(widget)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)

    default_log = os.path.join(
        os.path.expanduser("~"), ".config", "neoarch", "neoarch.log")
    edit = QLineEdit(app.settings.get("log_file_path", default_log))
    edit.setStyleSheet(QSS.LINEEDIT)
    edit.textChanged.connect(
        lambda v: app.update_setting("log_file_path", v))
    lay.addWidget(edit, 1)

    browse = QPushButton(_("Browse…"))
    browse.setStyleSheet(QSS.BTN_OUTLINE)
    browse.setFixedHeight(38)

    def on_browse():
        path, _filt = QFileDialog.getSaveFileName(
            widget, _("Select Log File"), edit.text(),
            _("Log Files (*.log *.txt);;All Files (*)"))
        if path:
            edit.setText(path)
            app.update_setting("log_file_path", path)

    browse.clicked.connect(on_browse)
    lay.addWidget(browse)
    return widget


def _max_size(app):
    stepper = Stepper(1, 100, step=1, suffix=" MB")
    stepper.setValue(int(app.settings.get("log_max_size_mb", 5)))
    stepper.valueChanged.connect(
        lambda v: app.update_setting("log_max_size_mb", v))
    return stepper


def _general_card(app):
    card, lay = make_card(_("General"), _ICON_TERMINAL)

    level_row = row(
        _("Log level"),
        _("How much detail NeoArch writes. DEBUG records everything "
          "including network calls and is ideal for bug reports; ERROR "
          "writes only failures."),
        control=_level_combo(app))
    lay.addWidget(level_row)
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Echo to console"),
        _("Mirror messages to the terminal NeoArch was started from. "
          "Mostly useful when you run the app from a shell — the log "
          "file already records everything."),
        control=_console_toggle(app)))

    return card


def _file_card(app):
    card, lay = make_card(_("Log File"), _ICON_FILE)

    lay.addWidget(row(
        _("Log file path"),
        _("Where the rolling log lives. Defaults to "
          "~/.config/neoarch/neoarch.log on your home directory.")))
    lay.addWidget(_path_control(app))
    lay.addWidget(sep())
    lay.addWidget(row(
        _("Maximum size"),
        _("Once the log grows past this size, NeoArch rolls it over so "
          "it never fills your drive."),
        control=_max_size(app)))

    return card


def _habits_card():
    card, lay = make_card(
        _("Good Habits"), _ICON_BOOK)

    lay.addWidget(advice(
        "do",
        _("Attach a DEBUG log when reporting bugs"),
        _("Set the level above to DEBUG, reproduce the problem, then "
          "attach the log file — it turns a vague report into a quick "
          "fix. Remember to switch back to INFO afterwards.")))
    lay.addWidget(sep())
    lay.addWidget(advice(
        "dont",
        _("Leave console echo on during daily use"),
        _("Messages are already written to the log file. Console echo "
          "is a terminal-first tool and adds busy output to the window "
          "you launched NeoArch from.")))

    return card


class LoggingSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.setup_ui()

    def setup_ui(self):
        title = QLabel(_("Logging"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(
            _("Control how much NeoArch records, where it writes it, and "
              "when it rolls the log over"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        self.layout.addWidget(subtitle)

        self.layout.addWidget(_general_card(self.app))
        self.layout.addWidget(_file_card(self.app))
        self.layout.addWidget(_habits_card())
