"""Full-page Git repository manager tab for NeoArch.

Lists cloned Git repositories in a table with per-row actions, plus
header actions for installing from a Git URL, updating, cleaning, and
opening the repositories folder.
"""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu,
)

_HEADER_BTN = """
    QPushButton {
        background-color: transparent;
        color: #8B8D97;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 7px;
        padding: 0 14px;
        font-weight: 500;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 0.04);
        color: #EDEDEF;
        border-color: rgba(255, 255, 255, 0.12);
    }
"""

_TABLE = """
    QTableWidget {
        background-color: rgba(18, 19, 22, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        gridline-color: rgba(255, 255, 255, 0.04);
        color: #EDEDEF;
        font-size: 12px;
    }
    QHeaderView::section {
        background-color: rgba(14, 14, 16, 0.9);
        color: #8B8D97;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        padding: 8px;
        font-size: 11px;
        font-weight: 600;
    }
    QTableWidget::item { padding: 6px 8px; }
    QTableWidget::item:selected { background-color: rgba(0, 191, 174, 0.15); color: #00BFAE; }
"""

_MENU = """
    QMenu { background-color: #2A2D33; color: #F0F0F0; border: 1px solid rgba(0,191,174,0.3); }
    QMenu::item:selected { background-color: rgba(0,191,174,0.2); }
"""


class GitTab(QWidget):
    """Standalone tab managing Git repositories under ~/git-repos."""

    def __init__(self, manager, main_app, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.main_app = main_app
        self._init_ui()
        try:
            self.manager.repos_changed.connect(self.refresh)
        except Exception:
            pass
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("gitTabHeader")
        header.setStyleSheet("""
            QFrame#gitTabHeader {
                background-color: rgba(14, 14, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        header.setFixedHeight(44)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 8, 4)
        header_layout.setSpacing(6)

        title = QLabel("Git Repositories")
        title.setStyleSheet("color: #EDEDEF; font-size: 13px; font-weight: 600; border: none;")
        header_layout.addWidget(title)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #8B8D97; font-size: 11px; border: none;")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        self.install_btn = self._header_btn("+ Install from Git", self.install_from_git)
        header_layout.addWidget(self.install_btn)

        self.open_btn = self._header_btn("Open Folder", self.open_folder)
        header_layout.addWidget(self.open_btn)

        self.update_btn = self._header_btn("Update All", self.update_all)
        header_layout.addWidget(self.update_btn)

        self.clean_btn = self._header_btn("Clean", self.clean)
        header_layout.addWidget(self.clean_btn)

        refresh_btn = self._header_btn("Refresh", self.refresh)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Repository", "Path", "Modified"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(_TABLE)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table, 1)

    def _header_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(_HEADER_BTN)
        btn.clicked.connect(slot)
        return btn

    def _log(self, msg):
        try:
            self.main_app.log(msg)
        except Exception:
            pass

    def _row_repo_path(self, row):
        item = self.table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _row_repo_name(self, row):
        item = self.table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole + 1)
        return None

    def refresh(self):
        if getattr(self, '_refreshing', False):
            return
        self._refreshing = True
        try:
            try:
                repos = self.manager.get_repos()
            except Exception as e:
                repos = []
                self._log(f"Git list error: {e}")
            self.table.setRowCount(0)
            for r in repos:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(r["name"]))
                self.table.setItem(row, 1, QTableWidgetItem(r["path"]))
                self.table.setItem(row, 2, QTableWidgetItem(self._fmt_mtime(r.get("mtime", 0))))
                for col in range(3):
                    item = self.table.item(row, col)
                    item.setData(Qt.ItemDataRole.UserRole, r["path"])
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole + 1, r["name"])
            self.status_label.setText(f"{self.table.rowCount()} repositories")
        finally:
            self._refreshing = False

    def _fmt_mtime(self, mtime):
        try:
            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""

    def _on_double_click(self, item):
        path = self._row_repo_path(item.row())
        if path:
            self.manager.open_repo(path)

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        path = self._row_repo_path(row)
        name = self._row_repo_name(row)
        if not path:
            return
        menu = QMenu(self)
        menu.setStyleSheet(_MENU)
        upd = menu.addAction("Update")
        open_act = menu.addAction("Open Folder")
        remove_act = menu.addAction("Remove")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == upd:
            self.manager.update_repo(path)
        elif action == open_act:
            self.manager.open_repo(path)
        elif action == remove_act:
            self._remove_repo(path, name)

    def _remove_repo(self, path, name):
        reply = QMessageBox.question(
            self, "Remove Repository",
            f"Permanently delete the local clone of '{name}'?\n\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_repo(path)

    def install_from_git(self):
        self.manager.install_from_git()

    def open_folder(self):
        self.manager.open_git_repos_dir()

    def update_all(self):
        self.manager.update_all_git_repos()

    def clean(self):
        self.manager.clean_git_repos()
