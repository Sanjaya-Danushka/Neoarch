from typing import Any
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QSpinBox)

from neoarch.backend.services.hygiene import news_unseen_count
from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii
from neoarch.backend.services.i18n import _


class MaintenanceSettingsWidget(QWidget):
    # Emitted from the news-count worker thread; updates the button label.
    _news_count_ready = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self._news_count_ready.connect(self._set_news_badge)
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

    def _row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        return row

    def scan_corrupted(self):
        from neoarch.backend.services.hygiene import list_corrupted_packages
        from threading import Thread

        def task():
            try:
                corrupted = list_corrupted_packages()
            except Exception as e:
                corrupted = None
                err = str(e)
            if corrupted is None:
                self.app.show_message.emit("Cache Scan", _("Scan failed: {err}").format(err=err))
                return
            if not corrupted:
                self.app.show_message.emit("Cache Scan", _("No corrupted package archives found."))
            else:
                self.app.show_message.emit(
                    "Cache Scan",
                    _("Found {n} corrupted archive(s):\n{list}").format(
                        n=len(corrupted), list=', '.join(corrupted[:10]))
                    + ("\n..." if len(corrupted) > 10 else ""))
        Thread(target=task, daemon=True).start()

    def purge_cache(self):
        from neoarch.backend.services.hygiene import purge_cache
        from threading import Thread

        def task():
            ok = purge_cache(retain=self.cache_keep.value())
            if ok:
                self.app.show_message.emit("Cache Purge", _("Old cached versions removed."))
            else:
                self.app.show_message.emit("Cache Purge", _("Nothing to purge (or failed)."))
        Thread(target=task, daemon=True).start()

    def setup_ui(self):
        title = QLabel(_("Maintenance"))
        title.setStyleSheet(f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD}; color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Keep your system tidy: orphans, leftover configs, and news"))
        subtitle.setStyleSheet(f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2}; margin-top: -16px;")
        self.layout.addWidget(subtitle)

        # ── Orphans ──
        card, card_layout = self._make_card(_("Orphaned Packages"))
        hint = QLabel(_("Packages installed as dependencies that nothing needs anymore."))
        hint.setStyleSheet(QSS.HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton(_("Remove Orphans"))
        btn.setStyleSheet(QSS.BTN_OUTLINE)
        btn.clicked.connect(self.app.cleanup_orphans)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)

        # ── .pacnew files ──
        card, card_layout = self._make_card(_("Config Files (.pacnew)"))
        hint = QLabel(_("When packages ship new configs, the old one is kept as .pacnew."))
        hint.setStyleSheet(QSS.HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton(_("Manage .pacnew"))
        btn.setStyleSheet(QSS.BTN_OUTLINE)
        btn.clicked.connect(self.app.manage_pacnew)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)

        # ── Download Cache ──
        card, card_layout = self._make_card(_("Download Cache"))

        corrupt_hint = QLabel(_("Scan cached package archives for corruption before they cause failures."))
        corrupt_hint.setStyleSheet(QSS.HINT)
        corrupt_hint.setWordWrap(True)
        card_layout.addWidget(corrupt_hint)

        row = self._row()
        btn = QPushButton(_("Scan for Corrupted Archives"))
        btn.setStyleSheet(QSS.BTN_OUTLINE)
        btn.clicked.connect(self.scan_corrupted)
        row.addWidget(btn)
        row.addStretch()
        card_layout.addLayout(row)

        cache_row = QHBoxLayout()
        cache_row.setSpacing(10)
        cache_label = QLabel(_("Keep last:"))
        cache_label.setStyleSheet(QSS.HINT)
        cache_row.addWidget(cache_label)

        self.cache_keep = QSpinBox()
        self.cache_keep.setStyleSheet(QSS.SPINBOX)
        self.cache_keep.setRange(1, 10)
        self.cache_keep.setValue(3)
        cache_row.addWidget(self.cache_keep)

        cache_unit = QLabel(_("versions per package"))
        cache_unit.setStyleSheet(QSS.HINT)
        cache_row.addWidget(cache_unit)

        purge_btn = QPushButton(_("Purge Old Cache"))
        purge_btn.setStyleSheet(QSS.BTN_OUTLINE)
        purge_btn.clicked.connect(self.purge_cache)
        cache_row.addWidget(purge_btn)
        cache_row.addStretch()
        card_layout.addLayout(cache_row)
        self.layout.addWidget(card)

        # ── Arch News ──
        card, card_layout = self._make_card(_("Arch Linux News"))
        hint = QLabel(_("Stay informed about important announcements before updating."))
        hint.setStyleSheet(QSS.HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        row = self._row()
        btn = QPushButton(_("Show News"))
        btn.setStyleSheet(QSS.BTN_OUTLINE)
        btn.clicked.connect(self.app.show_arch_news)
        row.addWidget(btn)
        self._news_btn = btn
        self._load_news_count_async()
        row.addStretch()
        card_layout.addLayout(row)
        self.layout.addWidget(card)

    def _load_news_count_async(self):
        """Resolve the unread-news badge off the UI thread.

        news_unseen_count() performs a synchronous RSS fetch; running it
        inline used to freeze the first Settings open for seconds.
        """
        from threading import Thread

        def task():
            try:
                n = news_unseen_count()
            except Exception:
                return
            if n:
                try:
                    self._news_count_ready.emit(int(n))
                except RuntimeError:
                    pass  # widget destroyed during a rebuild

        Thread(target=task, daemon=True).start()

    def _set_news_badge(self, n: int):
        try:
            self._news_btn.setText(_("Show News ({n} new)").format(n=n))
        except RuntimeError:
            pass  # widget already destroyed
