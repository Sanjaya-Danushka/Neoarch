"""PackageDetailCard — side-panel detail card with rich package info."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QWidget, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush

from neoarch.frontend.tokens import Colors, SourceColors


def _shadow(widget: QWidget, blur=24, offset=(4, 6), alpha=150):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(*offset)
    widget.setGraphicsEffect(s)


class _Avatar(QLabel):
    def __init__(self, letter: str, color: str):
        super().__init__()
        self._letter = letter[0].upper() if letter else "?"
        self._color = color
        self.setFixedSize(42, 42)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QColor(Colors.TEXT))
        f = QFont()
        f.setPointSize(17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._letter)
        p.end()


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_3}; font-size: 9px; font-weight: 700; "
        f"letter-spacing: 0.8px; background: transparent; padding: 0;"
    )
    return lbl


def _detail_row(label: str, value: str) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    l = QHBoxLayout(row)
    l.setContentsMargins(0, 2, 0, 2)
    l.setSpacing(8)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: 12px; background: transparent;")
    lbl.setFixedWidth(56)
    l.addWidget(lbl)
    val = QLabel(value)
    val.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: 12px; background: transparent;")
    val.setWordWrap(True)
    l.addWidget(val, 1)
    return row


def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"background: {Colors.BORDER}; max-height: 1px; border: none;")
    return sep


def _close_btn_stylesheet() -> str:
    return """
        QPushButton {
            background-color: #FF5F57;
            color: transparent;
            border: none;
            border-radius: 9px;
            font-size: 11px;
            font-weight: 700;
        }
        QPushButton:hover {
            background-color: #FF5F57;
            color: rgba(80, 20, 20, 0.7);
        }
        QPushButton:pressed {
            background-color: #E0554E;
        }
    """


def _nav_btn_stylesheet(color: str = Colors.TEXT_2) -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {color};
            padding: 0 20px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {Colors.TEXT};
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.08);
        }}
    """


SOURCE_COLORS = SourceColors


def _fmt_size(b):
    try:
        mb = float(b) / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GiB"
        return f"{mb:.1f} MiB"
    except Exception:
        return "—"


class PackageDetailCard(QFrame):
    install_requested = pyqtSignal()
    update_requested = pyqtSignal()
    uninstall_requested = pyqtSignal()
    updates_check_completed = pyqtSignal(str, str, bool, bool)  # name, new_version, has_updates, check_ok

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pkg_data = None
        self.setObjectName("packageDetailCard")
        self.setFixedWidth(320)
        self.setVisible(False)
        self._build()

    def close_card(self):
        self.clear()

    def _build(self):
        self.setStyleSheet(f"""
            QFrame#packageDetailCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(28, 30, 36, 0.55),
                    stop:1 rgba(20, 22, 26, 0.40));
                border: 1px solid {Colors.BORDER_INPUT};
                border-top: 1px solid {Colors.BORDER_HOVER};
                border-radius: 16px;
            }}
        """)
        _shadow(self, blur=40, offset=(8, 12), alpha=180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)

        content = QVBoxLayout(inner)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)

        self.avatar = _Avatar("?", Colors.ACCENT)
        hl.addWidget(self.avatar)

        nc = QVBoxLayout()
        nc.setSpacing(1)
        self.name_label = QLabel()
        f = QFont()
        f.setBold(True)
        f.setPointSize(14)
        self.name_label.setFont(f)
        self.name_label.setStyleSheet(f"color: {Colors.TEXT}; background: transparent;")
        self.name_label.setWordWrap(True)
        nc.addWidget(self.name_label)
        self.version_label = QLabel()
        self.version_label.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: 11px; background: transparent;"
        )
        nc.addWidget(self.version_label)
        hl.addLayout(nc, 1)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(_close_btn_stylesheet())
        self.close_btn.clicked.connect(self.close_card)
        self.close_btn.setVisible(True)
        hl.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)

        content.addWidget(header)

        # ── Status badge ──
        self.status_badge = QLabel()
        self.status_badge.setVisible(False)
        content.addSpacing(10)
        content.addWidget(self.status_badge)

        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)

        # ── Details ──
        content.addWidget(_section_title("Details"))
        content.addSpacing(6)

        self.version_row = QLabel()
        self.version_row.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: 12px; background: transparent;"
        )
        content.addWidget(self.version_row)

        self.source_row = _detail_row("Source", "")
        content.addWidget(self.source_row)
        self.id_row = _detail_row("ID", "")
        content.addWidget(self.id_row)

        self.reason_row = _detail_row("Reason", "")
        self.reason_row.setVisible(False)
        content.addWidget(self.reason_row)

        self.size_row = _detail_row("Size", "")
        self.size_row.setVisible(False)
        content.addWidget(self.size_row)

        # ── Reverse dependencies ──
        self.revdeps_widget = QWidget()
        self.revdeps_widget.setStyleSheet("background: transparent;")
        self.revdeps_layout = QVBoxLayout(self.revdeps_widget)
        self.revdeps_layout.setContentsMargins(0, 0, 0, 0)
        self.revdeps_layout.setSpacing(0)

        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)
        content.addWidget(_section_title("Required By"))
        content.addSpacing(6)
        self.revdeps_label = QLabel()
        self.revdeps_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: 12px; background: transparent;"
        )
        self.revdeps_label.setWordWrap(True)
        self.revdeps_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.revdeps_layout.addWidget(self.revdeps_label)
        content.addWidget(self.revdeps_widget)

        # ── Description ──
        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)
        content.addWidget(_section_title("Description"))
        content.addSpacing(6)

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: 12px; background: transparent;"
        )
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.addWidget(self.desc_label)

        content.addStretch(1)

        # ── Actions ──
        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)

        self.action_container = QWidget()
        self.action_container.setStyleSheet("background: transparent;")
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(6)

        self.install_btn = QPushButton("Install Package")
        self.install_btn.setMinimumHeight(40)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.ACCENT)
        )
        self.install_btn.clicked.connect(self.install_requested.emit)
        self.action_layout.addWidget(self.install_btn)

        self.update_btn = QPushButton("Update Package")
        self.update_btn.setMinimumHeight(40)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(
            _nav_btn_stylesheet("#FF8A65")
        )
        self.update_btn.clicked.connect(self.update_requested.emit)
        self.action_layout.addWidget(self.update_btn)

        self.uninstall_btn = QPushButton("Uninstall Package")
        self.uninstall_btn.setMinimumHeight(40)
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.RED)
        )
        self.uninstall_btn.clicked.connect(self.uninstall_requested.emit)
        self.action_layout.addWidget(self.uninstall_btn)

        self.check_updates_btn = QPushButton("Check for Updates")
        self.check_updates_btn.setMinimumHeight(40)
        self.check_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_updates_btn.setStyleSheet(
            _nav_btn_stylesheet("#FF8A65")
        )
        self.action_layout.addWidget(self.check_updates_btn)

        self.up_to_date_label = QLabel("✓  Up to date")
        self.up_to_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.up_to_date_label.setStyleSheet(
            "color: #10B981; font-size: 12px; font-weight: 600; "
            "background: rgba(16,185,129,0.08); border-radius: 8px; padding: 8px;"
        )
        self.action_layout.addWidget(self.up_to_date_label)

        content.addWidget(self.action_container)
        layout.addWidget(scroll)

    def _source_color(self, source: str) -> str:
        return SOURCE_COLORS.get(source.lower(), Colors.ACCENT)

    def show_package(self, pkg_data: dict):
        self._pkg_data = pkg_data
        name = pkg_data.get("name", "")
        version = pkg_data.get("version", "")
        new_version = pkg_data.get("new_version", "")
        source = pkg_data.get("source", "")
        installed = pkg_data.get("installed", False)
        has_update = pkg_data.get("has_update", False)
        description = pkg_data.get("description", "")
        pkg_id = pkg_data.get("id", name)
        view = pkg_data.get("_view", "")

        sc = self._source_color(source)

        self.avatar._letter = name[0].upper() if name else "?"
        self.avatar._color = sc
        self.avatar.update()
        self.name_label.setText(name)

        vt = f"v{version}"
        if new_version and new_version != version:
            vt += f"  →  {new_version}"
        self.version_label.setText(vt)

        # status badge
        if installed:
            if has_update:
                self.status_badge.setText("◉  Update Available")
                self.status_badge.setStyleSheet(
                    "background: rgba(255,138,101,0.12); color: #FF8A65;"
                    " font-size: 11px; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
            else:
                self.status_badge.setText("◉  Installed")
                self.status_badge.setStyleSheet(
                    "background: rgba(16,185,129,0.12); color: #10B981;"
                    " font-size: 11px; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
        else:
            self.status_badge.setText("○  Not Installed")
            self.status_badge.setStyleSheet(
                f"background: rgba(92,94,102,0.12); color: {Colors.TEXT_3};"
                f" font-size: 11px; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
            )
        self.status_badge.setVisible(True)

        vd = f"v{version}"
        if new_version and new_version != version:
            vd = f"v{version}  →  v{new_version}"
        self.version_row.setText(vd)

        self._set_row_text(self.source_row, source.capitalize() if source else "—")
        self._set_row_text(self.id_row, pkg_id)

        if description:
            self.desc_label.setText(description)
        else:
            self.desc_label.setText("No description available.")

        # Installed-only extras: install reason, size, reverse dependencies
        install_reason = pkg_data.get("install_reason", "")
        installed_size = pkg_data.get("installed_size")
        required_by = pkg_data.get("required_by") or []
        is_pacman_managed = source in ("pacman", "AUR", "")
        show_installed_extra = installed and is_pacman_managed

        self.reason_row.setVisible(show_installed_extra)
        self.size_row.setVisible(show_installed_extra)
        self.revdeps_widget.setVisible(show_installed_extra)

        if show_installed_extra:
            self._set_row_text(self.reason_row, install_reason or "Explicitly installed")
            if installed_size:
                self._set_row_text(self.size_row, _fmt_size(installed_size))
            else:
                self._set_row_text(self.size_row, "—")
            if required_by:
                self.revdeps_label.setText(", ".join(required_by))
            else:
                self.revdeps_label.setText("Nothing depends on this package (it is not needed by anything installed).")

        if view == "updates":
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(True)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(False)
            self.up_to_date_label.setVisible(False)
        elif view == "discover" and installed:
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(True)
            self.check_updates_btn.setText("Check for Updates")
            self.check_updates_btn.setEnabled(True)
            self.up_to_date_label.setVisible(False)
        elif installed:
            if has_update:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(True)
                self.uninstall_btn.setVisible(True)
                self.check_updates_btn.setVisible(False)
                self.up_to_date_label.setVisible(False)
            else:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(False)
                self.uninstall_btn.setVisible(True)
                self.check_updates_btn.setVisible(False)
                self.up_to_date_label.setVisible(False)
        else:
            self.install_btn.setVisible(True)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(False)
            self.up_to_date_label.setVisible(False)

        self.setVisible(True)

    @staticmethod
    def _set_row_text(row: QWidget, value: str):
        for i in range(row.layout().count()):
            w = row.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and i == 1:
                w.setText(value)
                break

    def set_extra_info(self, info: dict):
        """Populate async-loaded installed-only extras (reason, size, reverse deps)."""
        if not self._pkg_data:
            return
        source = (self._pkg_data.get("source") or "").lower()
        if source not in ("pacman", "aur"):
            return
        install_reason = info.get("install_reason") or ""
        installed_size = info.get("installed_size")
        required_by = info.get("required_by") or []

        self.reason_row.setVisible(True)
        self._set_row_text(self.reason_row, install_reason or "Explicitly installed")

        if installed_size:
            self.size_row.setVisible(True)
            self._set_row_text(self.size_row, _fmt_size(installed_size))

        if required_by:
            self.revdeps_widget.setVisible(True)
            self.revdeps_label.setText(", ".join(required_by))

    def clear(self):
        self._pkg_data = None
        self.name_label.clear()
        self.version_label.clear()
        self.version_row.clear()
        self.desc_label.clear()
        self.status_badge.setVisible(False)
        self.setVisible(False)
