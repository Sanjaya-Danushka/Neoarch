from typing import Any
from threading import Thread

from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton)

from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.toggle_switch import ToggleSwitch

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_REFRESH = (
    '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>'
)
_ICON_CALENDAR = (
    '<rect x="3" y="4" width="18" height="18" rx="2"/>'
    '<line x1="16" y1="2" x2="16" y2="6"/>'
    '<line x1="8" y1="2" x2="8" y2="6"/>'
    '<line x1="3" y1="10" x2="21" y2="10"/>'
)
_ICON_SHIELD = (
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
)
_ICON_CAMERA = (
    '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0'
    ' 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>'
)
_ICON_LAYERS = (
    '<path d="M12 2 2 7l10 5 10-5-10-5z"/>'
    '<path d="M2 17l10 5 10-5"/>'
    '<path d="M2 12l10 5 10-5"/>'
)
_ICON_MINUS = '<line x1="5" y1="12" x2="19" y2="12"/>'
_ICON_PLUS = (
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
)

_STEPPER_QSS = f"""
    QFrame#stepper {{
        background-color: {Colors.INPUT_BG};
        border: 1px solid {Colors.BORDER_INPUT};
        border-radius: 10px;
    }}
    QFrame#stepper QPushButton#stepBtn {{
        background: transparent;
        border: none;
        border-radius: 7px;
        padding: 0;
    }}
    QFrame#stepper QPushButton#stepBtn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}
    QFrame#stepper QPushButton#stepBtn:pressed {{
        background-color: rgba(255, 255, 255, 0.15);
    }}
"""

_DAY_DOT_QSS = f"""
    QPushButton {{
        background-color: transparent;
        color: {Colors.TEXT_2};
        border: 1px solid {Colors.BORDER_INPUT};
        border-radius: 8px;
        font-size: {Fonts.SM};
        font-weight: {Fonts.MEDIUM};
        padding: 0;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.05);
        border-color: {Colors.BORDER_HOVER};
        color: {Colors.TEXT};
    }}
    QPushButton:checked {{
        background-color: {Colors.ACCENT};
        border: 1px solid {Colors.ACCENT};
        color: #06201C;
        font-weight: {Fonts.BOLD};
    }}
    QPushButton:checked:hover {{
        background-color: {Colors.ACCENT_HOVER};
        border-color: {Colors.ACCENT_HOVER};
        color: #06201C;
    }}
    QPushButton:disabled {{
        color: {Colors.TEXT_3};
        border-color: {Colors.BORDER};
        background-color: transparent;
    }}
"""

_DAY_PANEL_QSS = f"""
    QFrame#dayPanel {{
        background-color: {Colors.INPUT_BG};
        border: 1px solid {Colors.BORDER};
        border-radius: 10px;
    }}
"""

# 2-letter day labels — match the app's 28x28 SURFACE_2 badge chips
_DAY_SHORT = [_("Mo"), _("Tu"), _("We"), _("Th"), _("Fr"), _("Sa"), _("Su")]


def _icon(svg_body, size=12, color=None):
    color = color or Colors.TEXT_2
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


class _Stepper(QFrame):
    """− value + compact stepper — a beautiful replacement for QSpinBox."""

    valueChanged = pyqtSignal(int)

    def __init__(self, minimum, maximum, step=1, suffix="",
                 on_text=None, pad=0, parent=None):
        super().__init__(parent)
        self._min, self._max, self._step = minimum, maximum, step
        self._suffix = suffix
        self._on_text = on_text
        self._pad = pad
        self._value = minimum

        self.setObjectName("stepper")
        self.setStyleSheet(_STEPPER_QSS)
        self.setFixedHeight(34)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(2)

        self._minus = QPushButton()
        self._minus.setObjectName("stepBtn")
        self._minus.setFixedSize(28, 26)
        self._minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus.setStyleSheet("border: none; background: transparent;")
        self._minus.clicked.connect(self._decrement)
        lay.addWidget(self._minus)

        self._value_label = QLabel()
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setMinimumWidth(56)
        self._value_label.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.SEMI}; border: none; background: transparent;")
        lay.addWidget(self._value_label, 1)

        self._plus = QPushButton()
        self._plus.setObjectName("stepBtn")
        self._plus.setFixedSize(28, 26)
        self._plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus.setStyleSheet("border: none; background: transparent;")
        self._plus.clicked.connect(self._increment)
        lay.addWidget(self._plus)

        self.setValue(minimum)

    def value(self):
        return self._value

    def setValue(self, value):
        value = max(self._min, min(self._max, int(value)))
        self._value = value

        if self._on_text is not None and value == 0:
            text = self._on_text
        else:
            text = f"{value:0{self._pad}d}{self._suffix}"
        self._value_label.setText(text)

        self._minus.setEnabled(value > self._min)
        self._plus.setEnabled(value < self._max)
        self._minus.setIcon(QIcon(_icon(
            _ICON_MINUS,
            color=Colors.TEXT_2 if value > self._min else Colors.TEXT_3)))
        self._plus.setIcon(QIcon(_icon(
            _ICON_PLUS,
            color=Colors.TEXT_2 if value < self._max else Colors.TEXT_3)))
        self.valueChanged.emit(value)

    def _increment(self):
        self.setValue(self._value + self._step)

    def _decrement(self):
        self.setValue(self._value - self._step)


class _Dot(QFrame):
    """Small teal selection dot, same look as the theme selector."""

    def __init__(self, active=False, parent=None):
        super().__init__(parent)
        self._active = active
        self.setFixedSize(16, 16)

    def setActive(self, active):
        self._active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active:
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
            p.setBrush(QColor(Colors.ACCENT))
        else:
            p.setPen(QPen(QColor(Colors.BORDER), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(1.5, 1.5, 13, 13))
        p.end()


class _EngineRow(QFrame):
    """One snapshot engine as a settings row: icon badge + name/status + dot."""

    def __init__(self, engine_id, label, icon_body, selected, status,
                 on_select, parent=None):
        super().__init__(parent)
        self.engine_id = engine_id
        self._on_select = on_select
        self._selected = selected
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        badge = QLabel()
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background: {Colors.SURFACE_2}; border: none;"
            f" border-radius: {Radii.SM}px;")
        badge.setPixmap(_icon(icon_body, 15))
        layout.addWidget(badge)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self._name = QLabel(label)
        self._name.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.ACCENT if selected else Colors.TEXT};"
            " border: none; background: transparent;")
        texts.addWidget(self._name)

        self._status = QLabel()
        self._status.setWordWrap(True)
        texts.addWidget(self._status)
        layout.addLayout(texts, 1)

        self._dot = _Dot(selected)
        layout.addWidget(self._dot)

        self.set_status(*status)
        self._update_style()

    def set_status(self, text, color):
        self._status.setText(text)
        self._status.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {color};"
            " border: none; background: transparent;")

    def setSelected(self, selected):
        self._selected = selected
        self._dot.setActive(selected)
        self._name.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.ACCENT if selected else Colors.TEXT};"
            " border: none; background: transparent;")
        self._update_style()

    def _update_style(self):
        if self._selected:
            bg = "rgba(255, 255, 255, 0.03)"
            border = "#3A3D44"
        elif self._hovered:
            bg = "rgba(255, 255, 255, 0.05)"
            border = "rgba(255, 255, 255, 0.10)"
        else:
            bg = "transparent"
            border = "transparent"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border};"
            " border-radius: 10px; }")

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_select(self.engine_id)


class AutoUpdateSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.day_cbs = []
        self.next_label = None

        self.setup_ui()

    # ── building blocks (About-page pattern) ────────────────────────

    @staticmethod
    def _icon_pixmap(svg_body, size=14, color="#EDEDEF"):
        return _icon(svg_body, size=size, color=color)

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
            badge.setPixmap(AutoUpdateSettingsWidget._icon_pixmap(svg_body, 15))
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

    @staticmethod
    def _actions_row(buttons):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(10)
        for btn in buttons:
            row.addWidget(btn)
        row.addStretch()
        return row_widget

    # ── UI ─────────────────────────────────────────────────────────

    def setup_ui(self):
        title = QLabel(_("Auto Update"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Manage automatic updates and system snapshots"))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent;")
        self.layout.addWidget(subtitle)

        # ── Auto Update ──
        update_card, update_layout = self._make_card(_("Auto Update"), _ICON_REFRESH)

        self.sw_auto_update = ToggleSwitch(self, _("Enable automatic updates"))
        self.sw_auto_update.setChecked(
            bool(self.app.settings.get('auto_update_enabled', False)), animate=False)
        self.sw_auto_update.toggled.connect(
            lambda v: self.app.update_setting('auto_update_enabled', v))
        update_layout.addWidget(self._row(
            _("Enable automatic updates"),
            _("Checks for new packages on the configured schedule."),
            control=self.sw_auto_update))
        update_layout.addWidget(self._sep())

        self.interval_stepper = _Stepper(1, 30, step=1, suffix=_(" days"))
        self.interval_stepper.setValue(
            int(self.app.settings.get('auto_update_interval_days', 1)))
        self.interval_stepper.valueChanged.connect(
            lambda v: self.app.update_setting('auto_update_interval_days', v))
        update_layout.addWidget(self._row(
            _("Update interval (days)"),
            _("How many days between automatic update checks."),
            control=self.interval_stepper))
        update_layout.addWidget(self._sep())

        self.refresh_stepper = _Stepper(0, 360, step=5, suffix=_(" min"),
                                        on_text=_("Off"))
        try:
            self.refresh_stepper.setValue(
                int(self.app.settings.get('auto_refresh_updates_minutes', 0) or 0))
        except (TypeError, ValueError):
            self.refresh_stepper.setValue(0)
        self.refresh_stepper.valueChanged.connect(
            lambda v: self.app.update_setting('auto_refresh_updates_minutes', v))
        update_layout.addWidget(self._row(
            _("Re-check while open (min)"),
            _("Re-checks for updates in the background every X minutes while"
              " the app is running. Set to Off to disable."),
            control=self.refresh_stepper))

        self.layout.addWidget(update_card)

        # ── Scheduled Checks ──
        sched_card, sched_layout = self._make_card(_("Scheduled Checks"), _ICON_CALENDAR)

        self.sw_schedule = ToggleSwitch(self, _("Enable scheduled update checks"))
        self.sw_schedule.setChecked(
            bool(self.app.settings.get('schedule_enabled', False)), animate=False)
        self.sw_schedule.toggled.connect(self.on_schedule_enabled)
        sched_layout.addWidget(self._row(
            _("Enable scheduled update checks"),
            _("Runs the update check automatically on a weekly schedule"
              " (applies while the app is running)."),
            control=self.sw_schedule))
        sched_layout.addWidget(self._sep())

        # Day-of-week badge toggles in a soft panel
        current_days = set(
            int(d) for d in self.app.settings.get('schedule_days', [0, 1, 2, 3, 4, 5, 6]))
        chips = QFrame()
        chips.setObjectName("dayPanel")
        chips.setStyleSheet(_DAY_PANEL_QSS)
        chip_row = QHBoxLayout(chips)
        chip_row.setContentsMargins(4, 4, 4, 4)
        chip_row.setSpacing(8)
        for idx, label in enumerate(_DAY_SHORT):
            cb = QPushButton(label)
            cb.setCheckable(True)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setFixedSize(28, 28)
            cb.setStyleSheet(_DAY_DOT_QSS)
            cb.setChecked(idx in current_days)
            cb.toggled.connect(self.on_schedule_changed)
            self.day_cbs.append(cb)
            chip_row.addWidget(cb)
        sched_layout.addWidget(self._row(
            _("Weekdays"),
            _("Select the days the scheduled check runs on."),
            control=chips))
        sched_layout.addWidget(self._sep())

        # Run at — two compact steppers (HH : MM)
        try:
            hh, mm = (
                int(p) for p in str(self.app.settings.get('schedule_time',
                                                          '03:00')).split(':'))
        except Exception:
            hh, mm = 3, 0

        self.hour_stepper = _Stepper(0, 23, step=1, pad=2)
        self.hour_stepper.setValue(hh)
        self.hour_stepper.valueChanged.connect(self.on_schedule_changed)

        self.min_stepper = _Stepper(0, 59, step=5, pad=2)
        self.min_stepper.setValue(mm)
        self.min_stepper.valueChanged.connect(self.on_schedule_changed)

        time_box = QWidget()
        time_box.setStyleSheet("background: transparent;")
        time_lay = QHBoxLayout(time_box)
        time_lay.setContentsMargins(0, 0, 0, 0)
        time_lay.setSpacing(8)
        time_lay.addWidget(self.hour_stepper)
        colon = QLabel(":")
        colon.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.MEDIUM}; border: none; background: transparent;")
        time_lay.addWidget(colon)
        time_lay.addWidget(self.min_stepper)

        sched_layout.addWidget(self._row(
            _("Run at"),
            _("Time of day the weekly check starts."),
            control=time_box))
        sched_layout.addWidget(self._sep())

        # Next run — dynamic subtitle
        next_row = QWidget()
        next_row.setStyleSheet("background: transparent;")
        next_hl = QHBoxLayout(next_row)
        next_hl.setSpacing(16)
        next_hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        next_texts = QVBoxLayout()
        next_texts.setSpacing(2)
        next_title = QLabel(_("Next run"))
        next_title.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        next_texts.addWidget(next_title)
        self.next_label = QLabel()
        self.next_label.setWordWrap(True)
        self.next_label.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.ACCENT};"
            " border: none; background: transparent;")
        next_texts.addWidget(self.next_label)
        next_hl.addLayout(next_texts, 1)
        sched_layout.addWidget(next_row)

        self.layout.addWidget(sched_card)
        self._update_next_label()

        # ── Backup ──
        backup_card, backup_layout = self._make_card(_("Backup"), _ICON_SHIELD)

        self.sw_snapshot = ToggleSwitch(self, _("Create backup before updates"))
        self.sw_snapshot.setChecked(
            bool(self.app.settings.get('snapshot_before_update', False)), animate=False)
        self.sw_snapshot.toggled.connect(
            lambda v: self.app.update_setting('snapshot_before_update', v))
        backup_layout.addWidget(self._row(
            _("Create backup before updates"),
            _("Backs up your package list and config before installing."),
            control=self.sw_snapshot))
        backup_layout.addWidget(self._sep())

        from neoarch.backend.services.backup import (
            get_filesystem_type, _is_btrfs_root_snapshottable)
        fs = get_filesystem_type()
        if fs == "btrfs" and _is_btrfs_root_snapshottable():
            fs_text = _("Filesystem: BTRFS - native snapshots available")
        else:
            fs_text = _("Filesystem: {fs} - package list + config backup only").format(fs=fs)
        backup_layout.addWidget(self._row(
            _("Backup method"),
            fs_text,
            subtitle_color=Colors.TEXT_2))

        backup_layout.addWidget(self._actions_row([
            self._btn(_("Create Backup"), self.app.create_backup),
            self._btn(_("List Backups"), self.app.list_backups),
            self._btn(_("Restore Backup"), self.app.restore_backup),
            self._btn(_("Prune Old"), self.app.prune_backups),
        ]))

        self.layout.addWidget(backup_card)

        # ── Snapshots (timeshift / snapper) ──
        snap_card, snap_layout = self._make_card(_("Snapshots"), _ICON_CAMERA)

        current_backend = self.app.settings.get(
            'snapshot_backend', 'timeshift')
        if current_backend not in ('timeshift', 'snapper'):
            current_backend = 'timeshift'

        self._engine_rows = {}
        engines = [
            ('timeshift', _("Timeshift"), _ICON_CAMERA),
            ('snapper', _("Snapper"), _ICON_LAYERS),
        ]
        for i, (key, label, icon_body) in enumerate(engines):
            if i > 0:
                snap_layout.addWidget(self._sep())
            row = _EngineRow(
                key, label, icon_body,
                selected=(key == current_backend),
                status=self._engine_status(key),
                on_select=self._select_engine)
            self._engine_rows[key] = row
            snap_layout.addWidget(row)

        snap_layout.addWidget(self._sep())

        self._snap_action_btns = [
            self._btn(_("Create Snapshot"), self.app.create_snapshot),
            self._btn(_("Revert to Snapshot"), self.app.revert_to_snapshot),
            self._btn(_("Delete Snapshots"), self.app.delete_snapshots),
        ]
        snap_layout.addWidget(self._actions_row(self._snap_action_btns))

        self.hook_row = QWidget()
        self.hook_row.setStyleSheet("background: transparent;")
        hook_lay = QHBoxLayout(self.hook_row)
        hook_lay.setContentsMargins(0, 4, 0, 0)
        hook_lay.setSpacing(10)
        self._hook_btns = [
            self._btn(
                _("Install update-time hooks"), self.app.install_snapshot_hooks),
            self._btn(
                _("Remove hooks"), self.app.remove_snapshot_hooks),
        ]
        hook_lay.addWidget(self._hook_btns[0])
        hook_lay.addWidget(self._hook_btns[1])
        hook_lay.addStretch()
        snap_layout.addWidget(self.hook_row)

        self.snap_progress_row = QWidget()
        self.snap_progress_row.setStyleSheet("background: transparent;")
        prog_lay = QHBoxLayout(self.snap_progress_row)
        prog_lay.setContentsMargins(2, 6, 2, 0)
        prog_lay.setSpacing(8)
        self._snap_dot = _Dot()
        prog_lay.addWidget(self._snap_dot)
        self.snap_status = QLabel("")
        self.snap_status.setWordWrap(True)
        self.snap_status.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.TEXT_2};"
            " border: none; background: transparent;")
        prog_lay.addWidget(self.snap_status, 1)
        self.snap_progress_row.setVisible(False)
        snap_layout.addWidget(self.snap_progress_row)

        self._snap_secs = 0
        self._snap_tick = QTimer(self)
        self._snap_tick.setInterval(1000)
        self._snap_tick.timeout.connect(self._on_snap_tick)

        self.last_snap_label = QLabel(_("Last snapshot: —"))
        self.last_snap_label.setWordWrap(True)
        self.last_snap_label.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.TEXT_3};"
            " border: none; background: transparent; padding: 2px 2px 0 2px;")
        snap_layout.addWidget(self.last_snap_label)

        self.layout.addWidget(snap_card)

        snapshot_progress = getattr(self.app, 'snapshot_progress', None)
        if snapshot_progress is not None and hasattr(snapshot_progress, 'connect'):
            snapshot_progress.connect(self._on_snapshot_status)

        self._refresh_engine_rows()
        self._refresh_last_snapshot()

        self.layout.addStretch()

    # ── behavior (unchanged) ───────────────────────────────────────

    def _collect_days(self):
        return [idx for idx, cb in enumerate(self.day_cbs) if cb.isChecked()]

    def _time_str(self):
        return f"{self.hour_stepper.value():02d}:{self.min_stepper.value():02d}"

    def _update_next_label(self):
        from neoarch.backend.services.scheduler import next_run
        if self.next_label is None:
            return
        if not self.sw_schedule.isChecked():
            self.next_label.setText(_("Schedule disabled"))
            self.next_label.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.TEXT_2};"
                " border: none; background: transparent;")
            return
        days = self._collect_days()
        nxt = next_run(days, self._time_str()) if days else None
        self.next_label.setText(
            _("Next: {nxt}").format(nxt=nxt.strftime('%a %Y-%m-%d %H:%M'))
            if nxt else _("No run scheduled (pick at least one day)"))
        self.next_label.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.ACCENT};"
            " border: none; background: transparent;")

    def on_schedule_enabled(self, value):
        self.app.update_setting('schedule_enabled', value)
        self._update_next_label()

    def _engine_status(self, engine):
        """Return (status_text, color) for a snapshot engine."""
        if engine == 'timeshift':
            if self.app.cmd_exists('timeshift'):
                return _("Installed"), Colors.ACCENT
            return _("Requires the 'timeshift' tool"), Colors.TEXT_3
        import shutil
        from neoarch.backend.services.backup import get_filesystem_type
        from neoarch.backend.services.snapper import (
            snapper_supported, snapper_available_configs)
        if snapper_supported():
            return _("Ready — snapshots available"), Colors.ACCENT
        if get_filesystem_type() != 'btrfs':
            return _("Needs a BTRFS filesystem"), Colors.TEXT_3
        if not shutil.which('snapper'):
            return _("Requires the 'snapper' tool"), Colors.TEXT_3
        if not snapper_available_configs():
            return (_("Needs a snapper config"
                      " (sudo snapper create-config /)"), Colors.TEXT_3)
        return _("Snapper setup is incomplete"), Colors.TEXT_3

    def _select_engine(self, engine):
        self.app.update_setting('snapshot_backend', engine)
        self._refresh_engine_rows()

    def _refresh_engine_rows(self):
        current = self.app.settings.get('snapshot_backend', 'timeshift')
        for key, row in self._engine_rows.items():
            row.setSelected(key == current)
            row.set_status(*self._engine_status(key))
        ready = (current == 'snapper' and
                 self._engine_status('snapper')[0]
                 == _("Ready — snapshots available"))
        self.hook_row.setVisible(ready)

    def on_schedule_changed(self, *_):
        days = self._collect_days()
        if days:
            self.app.update_setting('schedule_days', days)
        self.app.update_setting('schedule_time', self._time_str())
        self._update_next_label()

    def _set_snap_actions_enabled(self, enabled):
        for btn in self._snap_action_btns + self._hook_btns:
            try:
                btn.setEnabled(enabled)
            except Exception:
                pass

    def _on_snapshot_status(self, state, detail):
        if state == "busy":
            self._set_snap_actions_enabled(False)
            self._snap_secs = 0
            self._snap_tick.start()
            self._snap_dot.setActive(True)
            self.snap_status.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.TEXT};"
                " border: none; background: transparent;")
            self.snap_status.setText(
                detail + "  " + self._snap_elapsed())
            self.snap_progress_row.setVisible(True)
        elif state == "done":
            self._set_snap_actions_enabled(True)
            self._snap_tick.stop()
            self._snap_secs = 0
            self._snap_dot.setActive(True)
            self.snap_status.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.ACCENT};"
                " border: none; background: transparent;")
            self.snap_status.setText(detail)
            QTimer.singleShot(6000, self.snap_progress_row.hide)
            self._refresh_last_snapshot()
        elif state == "error":
            self._set_snap_actions_enabled(True)
            self._snap_tick.stop()
            self._snap_secs = 0
            self._snap_dot.setActive(False)
            self.snap_status.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.RED};"
                " border: none; background: transparent;")
            self.snap_status.setText(detail)
            QTimer.singleShot(6000, self.snap_progress_row.hide)

    def _on_snap_tick(self):
        self._snap_secs += 1
        self.snap_status.setText(
            (self.snap_status.text().split("  (")[0] if "  (" in
             self.snap_status.text() else self.snap_status.text())
            + "  " + self._snap_elapsed())

    def _snap_elapsed(self):
        return f"({self._snap_secs} s)"

    def _refresh_last_snapshot(self):
        backend = self.app.settings.get('snapshot_backend', 'timeshift')
        Thread(target=self._fetch_last_snapshot,
               args=(backend,), daemon=True).start()

    def _fetch_last_snapshot(self, backend):
        try:
            import shutil
            import subprocess
            from PyQt6.QtCore import QTimer as _QT
            if backend == 'snapper':
                from neoarch.backend.services.snapper import (
                    default_config, _list_snapshots)
                cfg = default_config()
                if not cfg:
                    _QT.singleShot(0, lambda: self.last_snap_label.setText(
                        _("Last snapshot: —")))
                    return
                snaps = _list_snapshots(cfg)
                line = (snaps[0]["date"] + " — " + snaps[0]["description"]
                        if snaps else None)
            else:
                import re
                result = subprocess.run(
                    [shutil.which("timeshift") or "timeshift", "--list"],
                    capture_output=True, text=True, timeout=30, check=False)
                if result.returncode != 0 or not result.stdout.strip():
                    _QT.singleShot(0, lambda: self.last_snap_label.setText(
                        _("Last snapshot: —")))
                    return
                m = re.search(r"^\s+\d+\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})",
                              result.stdout, re.M)
                if not m:
                    _QT.singleShot(0, lambda: self.last_snap_label.setText(
                        _("Last snapshot: —")))
                    return
                line = f"{m.group(1)} {m.group(2)}"
            _QT.singleShot(0,
                           lambda ln=line: self.last_snap_label.setText(
                               _("Last snapshot: {date}").format(date=ln)))
        except Exception:
            pass
