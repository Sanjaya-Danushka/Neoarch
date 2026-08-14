from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QCheckBox, QSpinBox, QPushButton, QTimeEdit)
from PyQt6.QtCore import QTime

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

_BTN_OUTLINE = """
    QPushButton {
        background-color: transparent;
        color: #00BFAE;
        border: 1px solid rgba(0, 191, 174, 0.35);
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: rgba(0, 191, 174, 0.12);
        border-color: #00BFAE;
    }
"""


class AutoUpdateSettingsWidget(QWidget):
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
        title = QLabel("Auto Update")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #EDEDEF; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel("Manage automatic updates and system snapshots")
        subtitle.setStyleSheet("font-size: 13px; color: #8B8D97; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Auto Update Card ──
        update_card, update_layout = self._make_card("Auto Update")

        self.cb_auto_update = QCheckBox("Enable automatic updates")
        self.cb_auto_update.setStyleSheet(_CHECKBOX)
        self.cb_auto_update.setChecked(bool(self.app.settings.get('auto_update_enabled', False)))
        self.cb_auto_update.toggled.connect(lambda v: self.app.update_setting('auto_update_enabled', v))
        update_layout.addWidget(self.cb_auto_update)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(12)
        interval_label = QLabel("Update interval (days):")
        interval_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        interval_row.addWidget(interval_label)

        self.interval_spin = QSpinBox()
        self.interval_spin.setStyleSheet(_SPINBOX)
        self.interval_spin.setRange(1, 30)
        self.interval_spin.setValue(int(self.app.settings.get('auto_update_interval_days', 1)))
        self.interval_spin.valueChanged.connect(lambda v: self.app.update_setting('auto_update_interval_days', v))
        interval_row.addWidget(self.interval_spin)
        interval_row.addStretch()

        update_layout.addLayout(interval_row)
        self.layout.addWidget(update_card)

        # ── Scheduled Checks Card ──
        sched_card, sched_layout = self._make_card("Scheduled Checks")
        hint = QLabel("Run the update check automatically on a weekly schedule "
                      "(evaluated by the CLI/service layer; applies when the app is running).")
        hint.setStyleSheet("color: #8B8D97; font-size: 12px; border: none;")
        hint.setWordWrap(True)
        sched_layout.addWidget(hint)

        self.cb_schedule = QCheckBox("Enable scheduled update checks")
        self.cb_schedule.setStyleSheet(_CHECKBOX)
        self.cb_schedule.setChecked(bool(self.app.settings.get('schedule_enabled', False)))
        self.cb_schedule.toggled.connect(self.on_schedule_enabled)
        sched_layout.addWidget(self.cb_schedule)

        days_row = QHBoxLayout()
        days_row.setSpacing(8)
        days_label = QLabel("Days:")
        days_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        days_row.addWidget(days_label)

        self.day_cbs = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        current_days = set(int(d) for d in self.app.settings.get('schedule_days', [0, 1, 2, 3, 4, 5, 6]))
        for idx, name in enumerate(day_names):
            cb = QCheckBox(name)
            cb.setStyleSheet(_CHECKBOX)
            cb.setChecked(idx in current_days)
            cb.toggled.connect(self.on_schedule_changed)
            self.day_cbs.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch()
        sched_layout.addLayout(days_row)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        time_label = QLabel("Time:")
        time_label.setStyleSheet("color: #8B8D97; font-size: 13px; border: none;")
        time_row.addWidget(time_label)

        self.time_edit = QTimeEdit()
        self.time_edit.setStyleSheet("""
            QTimeEdit {
                background-color: rgba(18, 19, 22, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                color: #EDEDEF;
                font-size: 13px;
            }
            QTimeEdit:focus { border-color: #00BFAE; }
        """)
        self.time_edit.setDisplayFormat("HH:mm")
        try:
            hh, mm = str(self.app.settings.get('schedule_time', '03:00')).split(':')
            self.time_edit.setTime(QTime(int(hh), int(mm)))
        except Exception:
            self.time_edit.setTime(QTime(3, 0))
        self.time_edit.timeChanged.connect(self.on_schedule_changed)
        time_row.addWidget(self.time_edit)

        self.next_label = QLabel()
        self.next_label.setStyleSheet("color: #8B8D97; font-size: 12px; border: none;")
        time_row.addWidget(self.next_label)
        time_row.addStretch()
        sched_layout.addLayout(time_row)

        self.layout.addWidget(sched_card)
        self._update_next_label()

        # ── Backup Card (built-in) ──
        backup_card, backup_layout = self._make_card("Backup")

        self.cb_snapshot = QCheckBox("Create backup before updates")
        self.cb_snapshot.setStyleSheet(_CHECKBOX)
        self.cb_snapshot.setChecked(bool(self.app.settings.get('snapshot_before_update', False)))
        self.cb_snapshot.toggled.connect(lambda v: self.app.update_setting('snapshot_before_update', v))
        backup_layout.addWidget(self.cb_snapshot)

        fs_info = QLabel()
        fs_info.setStyleSheet("color: #8B8D97; font-size: 12px; border: none;")
        from neoarch.backend.services.backup import get_filesystem_type, _is_btrfs_root_snapshottable
        fs = get_filesystem_type()
        if fs == "btrfs" and _is_btrfs_root_snapshottable():
            fs_info.setText("Filesystem: BTRFS - native snapshots available")
        else:
            fs_info.setText(f"Filesystem: {fs} - package list + config backup only")
        backup_layout.addWidget(fs_info)

        backup_btn_row = QHBoxLayout()
        backup_btn_row.setSpacing(10)

        create_backup_btn = QPushButton("Create Backup")
        create_backup_btn.setStyleSheet(_BTN_OUTLINE)
        create_backup_btn.clicked.connect(self.app.create_backup)
        backup_btn_row.addWidget(create_backup_btn)

        list_backup_btn = QPushButton("List Backups")
        list_backup_btn.setStyleSheet(_BTN_OUTLINE)
        list_backup_btn.clicked.connect(self.app.list_backups)
        backup_btn_row.addWidget(list_backup_btn)

        restore_backup_btn = QPushButton("Restore Backup")
        restore_backup_btn.setStyleSheet(_BTN_OUTLINE)
        restore_backup_btn.clicked.connect(self.app.restore_backup)
        backup_btn_row.addWidget(restore_backup_btn)

        prune_backup_btn = QPushButton("Prune Old")
        prune_backup_btn.setStyleSheet(_BTN_OUTLINE)
        prune_backup_btn.clicked.connect(self.app.prune_backups)
        backup_btn_row.addWidget(prune_backup_btn)

        backup_btn_row.addStretch()
        backup_layout.addLayout(backup_btn_row)
        self.layout.addWidget(backup_card)

        # ── Snapshots Card (Timeshift, advanced/optional) ──
        snap_card, snap_layout = self._make_card("Timeshift (advanced)")

        snap_hint = QLabel("Requires the external 'timeshift' tool. Optional - the built-in backup above is recommended.")
        snap_hint.setStyleSheet("color: #8B8D97; font-size: 12px; border: none;")
        snap_hint.setWordWrap(True)
        snap_layout.addWidget(snap_hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.setStyleSheet(_BTN_OUTLINE)
        create_snap_btn.clicked.connect(self.app.create_snapshot)
        btn_row.addWidget(create_snap_btn)

        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.setStyleSheet(_BTN_OUTLINE)
        revert_snap_btn.clicked.connect(self.app.revert_to_snapshot)
        btn_row.addWidget(revert_snap_btn)

        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.setStyleSheet(_BTN_OUTLINE)
        delete_snap_btn.clicked.connect(self.app.delete_snapshots)
        btn_row.addWidget(delete_snap_btn)

        btn_row.addStretch()
        snap_layout.addLayout(btn_row)

        self.layout.addWidget(snap_card)

    def _collect_days(self):
        return [idx for idx, cb in enumerate(self.day_cbs) if cb.isChecked()]

    def _time_str(self):
        t = self.time_edit.time()
        return f"{t.hour():02d}:{t.minute():02d}"

    def _update_next_label(self):
        from neoarch.backend.services.scheduler import next_run
        if not self.cb_schedule.isChecked():
            self.next_label.setText("Schedule disabled")
            return
        days = self._collect_days()
        nxt = next_run(days, self._time_str()) if days else None
        self.next_label.setText(f"Next: {nxt.strftime('%a %Y-%m-%d %H:%M')}" if nxt
                                else "No run scheduled (pick at least one day)")

    def on_schedule_enabled(self, value):
        self.app.update_setting('schedule_enabled', value)
        self._update_next_label()

    def on_schedule_changed(self, *_):
        days = self._collect_days()
        if days:
            self.app.update_setting('schedule_days', days)
        self.app.update_setting('schedule_time', self._time_str())
        self._update_next_label()
