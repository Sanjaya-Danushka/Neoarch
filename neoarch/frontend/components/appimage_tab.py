"""
AppImage manager tab: list managed AppImages, add from file/URL, check
updates, install updates, and remove entries.
"""

import os
from threading import Thread

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QInputDialog,
    QMessageBox,
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


class AppImageTab(QWidget):
    """Standalone tab managing the NeoArch AppImage store."""

    data_changed = pyqtSignal()

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._busy = False
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("appimageHeader")
        header.setStyleSheet("""
            QFrame#appimageHeader {
                background-color: rgba(14, 14, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        header.setFixedHeight(44)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 8, 4)
        header_layout.setSpacing(6)

        title = QLabel("AppImages")
        title.setStyleSheet("color: #EDEDEF; font-size: 13px; font-weight: 600; border: none;")
        header_layout.addWidget(title)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #8B8D97; font-size: 11px; border: none;")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        self.add_file_btn = self._header_btn("+ Add from File", self.add_from_file)
        header_layout.addWidget(self.add_file_btn)

        self.add_url_btn = self._header_btn("+ Add from URL", self.add_from_url)
        header_layout.addWidget(self.add_url_btn)

        self.check_btn = self._header_btn("Check Updates", self.check_updates)
        header_layout.addWidget(self.check_btn)

        self.update_btn = self._header_btn("Update Selected", self.update_selected)
        header_layout.addWidget(self.update_btn)

        self.remove_btn = self._header_btn("Remove Selected", self.remove_selected)
        header_layout.addWidget(self.remove_btn)

        refresh_btn = self._header_btn("Refresh", self.refresh)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Version", "Source", "Update Available", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(_TABLE)
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

    def _say(self, title, msg):
        try:
            self.main_app.show_message.emit(title, msg)
        except Exception:
            QMessageBox.information(self, title, msg)

    def refresh(self):
        from neoarch.backend.services.appimage import list_appimages
        try:
            entries = list_appimages()
        except Exception as e:
            entries = []
            self._log(f"AppImage list error: {e}")
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("name", entry.get("id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("version") or ""))
            src = entry.get("source_type", "")
            if src == "url" or src == "repo":
                src = f"{src}: {entry.get('source') or ''}"
            elif src == "file":
                src = os.path.basename(entry.get("source") or "")
            self.table.setItem(row, 2, QTableWidgetItem(src))
            if entry.get("latest_version"):
                self.table.setItem(row, 3, QTableWidgetItem(f"{entry['latest_version']} available"))
            else:
                self.table.setItem(row, 3, QTableWidgetItem(""))
            self.table.setItem(row, 4, QTableWidgetItem(
                "Update ready" if entry.get("latest_version") else "Up to date"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, entry.get("id", ""))
        self.status_label.setText(f"{self.table.rowCount()} managed")
        self._set_busy(False)

    def _selected_ids(self):
        ids = []
        for item in self.table.selectedItems():
            if item.column() == 0:
                aid = item.data(Qt.ItemDataRole.UserRole)
                if aid:
                    ids.append(aid)
        return ids

    def _set_busy(self, busy):
        self._busy = busy
        for btn in (self.add_file_btn, self.add_url_btn, self.check_btn,
                    self.update_btn, self.remove_btn):
            btn.setEnabled(not busy)

    def _run(self, title, fn):
        if self._busy:
            return
        self._set_busy(True)
        self.status_label.setText(f"{title}...")

        def task():
            try:
                ok, msg = fn()
            except Exception as e:
                ok, msg = False, f"{e}"
            self.main_app.show_message.emit(title, msg)
            self.refresh()
            self.data_changed.emit()
        Thread(target=task, daemon=True).start()

    def add_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select AppImage", os.path.expanduser("~"),
            "AppImage files (*.AppImage *.appimage);;All files (*)")
        if not path:
            return
        self._run("Add AppImage", lambda: (True, "Added from file.") if _file_add(path) else (False, "Failed."))

    def add_from_url(self):
        name, ok = QInputDialog.getText(self, "Add from URL", "AppImage name (e.g. Obsidian):")
        if not ok or not name.strip():
            return
        url, ok = QInputDialog.getText(self, "Add from URL", "Direct download URL (.AppImage):")
        if not ok or not url.strip():
            return
        self._run("Add AppImage", lambda: _url_add(name.strip(), url.strip()))

    def check_updates(self):
        self._run("Check Updates", _check_all)

    def update_selected(self):
        ids = self._selected_ids()
        if not ids:
            self._say("Update AppImage", "Select one or more AppImages to update.")
            return
        reply = QMessageBox.question(
            self, "Update AppImages",
            f"Update {len(ids)} AppImage(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run("Update AppImages", lambda: _update_ids(ids))

    def remove_selected(self):
        ids = self._selected_ids()
        if not ids:
            self._say("Remove AppImage", "Select one or more AppImages to remove.")
            return
        reply = QMessageBox.question(
            self, "Remove AppImages",
            f"Remove {len(ids)} AppImage(s) and their desktop entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run("Remove AppImages", lambda: _remove_ids(ids))


def _file_add(path):
    from neoarch.backend.services import appimage
    appimage.add_from_file(path)
    return True, f"Added {os.path.basename(path)}."


def _url_add(name, url):
    from neoarch.backend.services import appimage
    entry = appimage.add_from_url(name, url)
    return True, f"Added {entry.get('name', name)}."


def _check_all():
    from neoarch.backend.services import appimage
    results = appimage.check_all_updates()
    if not results:
        return True, "All AppImages up to date."
    return True, f"{len(results)} update(s) available:\n" + "\n".join(
        f"• {r.get('name', r.get('id', ''))}: {r.get('latest_version', '')}" for r in results)


def _update_ids(ids):
    from neoarch.backend.services import appimage
    done = []
    for aid in ids:
        if appimage.install_update(aid):
            done.append(aid)
    return True, f"Updated {len(done)}/{len(ids)} AppImage(s)."


def _remove_ids(ids):
    from neoarch.backend.services import appimage
    for aid in ids:
        appimage.remove_appimage(aid)
    return True, f"Removed {len(ids)} AppImage(s)."
