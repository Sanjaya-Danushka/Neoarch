"""Full-page Docker container manager tab for NeoArch.

Lists Docker containers in a table with per-row Start/Stop/Logs/Remove
actions, plus header actions for running a container, viewing images,
stopping containers, opening a shell, and cleaning up.
"""

import shutil

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

_ACCENT_BTN = """
    QPushButton {
        background-color: #00BFAE;
        color: #0C0C0E;
        border: none;
        border-radius: 7px;
        padding: 0 14px;
        font-weight: 600;
        font-size: 11px;
    }
    QPushButton:hover { background-color: #00D4C1; }
    QPushButton:pressed { background-color: #009688; }
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

_ROW_BTN = """
    QPushButton {
        background-color: transparent;
        color: #8B8D97;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 5px;
        padding: 2px 10px;
        font-size: 10px;
        font-weight: 500;
    }
    QPushButton:hover { background-color: rgba(255, 255, 255, 0.06); color: #EDEDEF; }
"""

_ROW_STOP = """
    QPushButton {
        background: rgba(224, 108, 117, 0.12);
        color: #E06C75;
        border: 1px solid rgba(224, 108, 117, 0.2);
        border-radius: 5px;
        padding: 2px 10px;
        font-size: 10px;
        font-weight: 600;
    }
    QPushButton:hover { background: rgba(224, 108, 117, 0.22); }
"""

_ROW_START = """
    QPushButton {
        background: rgba(0, 191, 174, 0.1);
        color: #00BFAE;
        border: 1px solid rgba(0, 191, 174, 0.2);
        border-radius: 5px;
        padding: 2px 10px;
        font-size: 10px;
        font-weight: 600;
    }
    QPushButton:hover { background: rgba(0, 191, 174, 0.18); }
"""

_MENU = """
    QMenu { background-color: #2A2D33; color: #F0F0F0; border: 1px solid rgba(0,191,174,0.3); }
    QMenu::item:selected { background-color: rgba(0,191,174,0.2); }
"""


class DockerTab(QWidget):
    """Standalone tab managing Docker containers."""

    def __init__(self, manager, main_app, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.main_app = main_app
        self._init_ui()
        try:
            self.manager.containers_changed.connect(self.refresh)
        except Exception:
            pass
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("dockerTabHeader")
        header.setStyleSheet("""
            QFrame#dockerTabHeader {
                background-color: rgba(14, 14, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        header.setFixedHeight(44)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 8, 4)
        header_layout.setSpacing(6)

        title = QLabel("Docker Containers")
        title.setStyleSheet("color: #EDEDEF; font-size: 13px; font-weight: 600; border: none;")
        header_layout.addWidget(title)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #8B8D97; font-size: 11px; border: none;")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        self.run_btn = self._header_btn("+ Run Container", self.run_container, accent=True)
        header_layout.addWidget(self.run_btn)

        self.images_btn = self._header_btn("Images", self.show_images)
        header_layout.addWidget(self.images_btn)

        self.stop_btn = self._header_btn("Stop All", self.stop_all)
        header_layout.addWidget(self.stop_btn)

        self.shell_btn = self._header_btn("Shell", self.open_shell)
        header_layout.addWidget(self.shell_btn)

        self.clean_btn = self._header_btn("Clean", self.clean)
        header_layout.addWidget(self.clean_btn)

        refresh_btn = self._header_btn("Refresh", self.refresh)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Image", "ID", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(_TABLE)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table, 1)

    def _header_btn(self, text, slot, accent=False):
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(_ACCENT_BTN if accent else _HEADER_BTN)
        btn.clicked.connect(slot)
        return btn

    def _log(self, msg):
        try:
            self.main_app.log(msg)
        except Exception:
            pass

    def _row_cid(self, row):
        item = self.table.item(row, 2)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _row_running(self, row):
        item = self.table.item(row, 3)
        if item:
            return item.text().startswith("Up")
        return False

    def refresh(self):
        if getattr(self, '_refreshing', False):
            return
        self._refreshing = True
        try:
            try:
                containers = self.manager.load_containers(include_all=True)
            except Exception as e:
                containers = []
                self._log(f"Docker list error: {e}")
            running = sum(1 for c in containers if c.get("status", "").startswith("Up"))
            self.table.setRowCount(0)
            for c in containers:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(c.get("name", "")))
                self.table.setItem(row, 1, QTableWidgetItem(c.get("image", "")))
                self.table.setItem(row, 2, QTableWidgetItem(c.get("id", "")))
                self.table.setItem(row, 3, QTableWidgetItem(c.get("status", "")))
                for col in range(4):
                    self.table.item(row, col).setData(Qt.ItemDataRole.UserRole, c.get("id", ""))
                self._add_row_actions(row, c.get("id", ""), c.get("status", ""))
            if not shutil.which("docker"):
                self.status_label.setText("Docker is not installed")
            else:
                self.status_label.setText(f"{self.table.rowCount()} containers ({running} running)")
        finally:
            self._refreshing = False

    def _add_row_actions(self, row, cid, status):
        cell = QWidget()
        lay = QHBoxLayout(cell)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        lay.addStretch()
        running = status.startswith("Up")
        toggle = QPushButton("Stop" if running else "Start")
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setStyleSheet(_ROW_STOP if running else _ROW_START)
        toggle.clicked.connect(
            lambda checked=False, c=cid, r=running: (self.manager.stop_container(c) if r else self.manager.start_container(c)))
        lay.addWidget(toggle)
        logs_btn = QPushButton("Logs")
        logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logs_btn.setStyleSheet(_ROW_BTN)
        logs_btn.clicked.connect(lambda checked=False, c=cid: self.manager.show_container_logs(c))
        lay.addWidget(logs_btn)
        rm_btn = QPushButton("Remove")
        rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rm_btn.setStyleSheet(_ROW_BTN)
        rm_btn.clicked.connect(lambda checked=False, c=cid: self._remove_container(c))
        lay.addWidget(rm_btn)
        self.table.setCellWidget(row, 4, cell)

    def _remove_container(self, cid):
        reply = QMessageBox.question(
            self, "Remove Container",
            f"Force-remove container {cid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_container(cid)

    def _on_double_click(self, item):
        cid = self._row_cid(item.row())
        if cid:
            self.manager.show_container_logs(cid)

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        cid = self._row_cid(row)
        if not cid:
            return
        menu = QMenu(self)
        menu.setStyleSheet(_MENU)
        start_act = menu.addAction("Start")
        stop_act = menu.addAction("Stop")
        restart_act = menu.addAction("Restart")
        logs_act = menu.addAction("View Logs")
        shell_act = menu.addAction("Open Shell")
        remove_act = menu.addAction("Remove")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == start_act:
            self.manager.start_container(cid)
        elif action == stop_act:
            self.manager.stop_container(cid)
        elif action == restart_act:
            self.manager.restart_container(cid)
        elif action == logs_act:
            self.manager.show_container_logs(cid)
        elif action == shell_act:
            self.manager.open_container_shell(cid)
        elif action == remove_act:
            self._remove_container(cid)

    def run_container(self):
        self.manager.show_advanced_run_dialog()

    def show_images(self):
        self.manager.list_docker_images()

    def stop_all(self):
        self.manager.stop_docker_containers(only_running=True)

    def open_shell(self):
        self.manager.show_shell_menu()

    def clean(self):
        self.manager.clean_docker_containers()
