"""Update-review dialog: what will change before 'Update All' runs.

Built to match the app's standard prompt design (same shape as the
"Manage Ignored" dialog): a native window with a header count, a clean
table of pending changes, and a clear confirm button. Nothing starts
unless Update All / Enter is used; Esc or close cancels.

A read-only "Release notes" column links to the upstream release-notes
page for packages known to the offline changelog map (nothing is fetched
from the network here; unknown packages simply show no link).
"""

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QStyledItemDelegate, QStyle,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.backend.services.i18n import _
from neoarch.resources.changelog_map import get_changelog_url

_TABLE_NO_FOCUS = """
    QTableView { outline: none; }
    QTableWidget { outline: none; }
    QTableView::item:selected { background: transparent; }
    QTableWidget::item:selected { background: transparent; }
    QTableView::item:selected:active { background: transparent; border: none; }
    QTableWidget::item:selected:active { background: transparent; border: none; }
    QTableView::item:selected:!active { background: transparent; border: none; }
    QTableWidget::item:selected:!active { background: transparent; border: none; }
    QTableView::item:focus { outline: none; }
    QTableWidget::item:focus { outline: none; }
    QTableView::item:hover { background: transparent; }
    QTableWidget::item:hover { background: transparent; }
    QTableView::item { padding: 0px; margin: 0px; border: none; }
    QTableWidget::item { padding: 0px; margin: 0px; border: none; }
"""


class _NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)


class UpdateReviewDialog(QDialog):
    def __init__(self, packages, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Update Review"))
        self.resize(640, 420)
        self.setMinimumWidth(560)
        self.setStyleSheet(
            f"QDialog {{ background-color: rgba(22, 23, 26, 235); }}")
        self._build(packages or [])

    def _build(self, packages):
        v = QVBoxLayout(self)
        v.setSpacing(10)

        self.header_label = QLabel(
            _("Packages to update: {n}").format(n=len(packages)))
        v.addWidget(self.header_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [_("Package"), _("Source"), _("Version"), _("New Version"),
             _("Release notes")])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        try:
            self.table.verticalHeader().setDefaultSectionSize(36)
            self.table.horizontalHeader().setMinimumSectionSize(36)
        except Exception:
            pass
        try:
            self.table.verticalHeader().setHighlightSections(False)
            self.table.horizontalHeader().setHighlightSections(False)
        except Exception:
            pass
        try:
            self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setStyleSheet(_TABLE_NO_FOCUS)
        except Exception:
            pass
        try:
            self.table.setShowGrid(False)
        except Exception:
            pass
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        try:
            self.table.setItemDelegate(_NoFocusDelegate(self.table))
        except Exception:
            pass
        v.addWidget(self.table)

        self.table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name = pkg.get("name") or pkg.get("id") or "?"
            source = (pkg.get("source") or "pacman").capitalize()
            old = pkg.get("version") or ""
            new = pkg.get("new_version") or ""
            for col, text in enumerate([name, source, old, new]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, col, item)

            notes_url = get_changelog_url(name, source=pkg.get("source") or "")
            notes_item = QTableWidgetItem(
                _("View changes ↗") if notes_url else "")
            notes_item.setFlags(notes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if notes_url:
                notes_item.setForeground(QColor(Colors.ACCENT))
                notes_item.setToolTip(notes_url)
                notes_item.setData(Qt.ItemDataRole.UserRole, notes_url)
            self.table.setItem(i, 4, notes_item)

        self.table.itemClicked.connect(self._on_item_clicked)

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        self.cancel_btn = QPushButton(_("Cancel"))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.CARD};"
            f" color: {Colors.TEXT}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: {Fonts.BASE}; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {Colors.CARD_HOVER};"
            f" border-color: {Colors.BORDER_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.SURFACE_3}; }}")
        self.cancel_btn.clicked.connect(self.reject)
        h.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton(_("Update All"))
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setMinimumHeight(36)
        self.confirm_btn.setDefault(True)
        try:
            self.confirm_btn.setMinimumWidth(140)
        except Exception:
            pass
        self.confirm_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.WHITE};"
            f" color: {Colors.TEXT_ON_ACCENT};"
            f" border: 1px solid rgba(255, 255, 255, 0.9);"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: {Fonts.BASE}; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.WHITE_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.WHITE_PRESSED}; }}")
        self.confirm_btn.clicked.connect(self.accept)
        h.addWidget(self.confirm_btn)

        v.addWidget(row)

    def _on_item_clicked(self, item):
        """Open the release-notes link when a notes cell is clicked."""
        if item.column() != 4:
            return
        url = item.data(Qt.ItemDataRole.UserRole)
        if not url:
            return
        try:
            webbrowser.open(url)
        except Exception:
            pass