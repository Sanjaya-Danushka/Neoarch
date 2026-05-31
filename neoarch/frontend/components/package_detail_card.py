"""PackageDetailCard — side-panel detail card with rich package info."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QWidget, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush


_C = {
    "border": "rgba(255, 255, 255, 0.06)",
    "accent": "#00BFAE",
    "text": "#EDEDEF",
    "text_sec": "#8B8D97",
    "text_muted": "#5C5E66",
    "success": "#10B981",
    "warning": "#FF8A65",
    "danger": "#FF6B6B",
}


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
        p.setPen(QColor("#EDEDEF"))
        f = QFont()
        f.setPointSize(17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._letter)
        p.end()


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {_C['text_muted']}; font-size: 9px; font-weight: 700; "
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
    lbl.setStyleSheet(f"color: {_C['text_muted']}; font-size: 12px; background: transparent;")
    lbl.setFixedWidth(56)
    l.addWidget(lbl)
    val = QLabel(value)
    val.setStyleSheet(f"color: {_C['text_sec']}; font-size: 12px; background: transparent;")
    val.setWordWrap(True)
    l.addWidget(val, 1)
    return row


def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"background: {_C['border']}; max-height: 1px; border: none;")
    return sep


def _close_btn_stylesheet() -> str:
    return """
        QPushButton {
            background: rgba(255,255,255,0.08);
            color: #8B8D97;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            font-size: 15px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: rgba(255,80,80,0.2);
            color: #FF6B6B;
            border-color: rgba(255,80,80,0.25);
        }
        QPushButton:pressed {
            background: rgba(255,80,80,0.35);
        }
    """


def _action_btn_stylesheet(color: str, hover_border: str) -> str:
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color}18,
                stop:1 {color}0A);
            color: {color};
            border: 1px solid {color}35;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            padding: 0 20px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color}2A,
                stop:1 {color}14);
            border: 1px solid {hover_border};
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color}38,
                stop:1 {color}20);
            border: 1px solid {color}50;
        }}
    """


SOURCE_COLORS = {
    "pacman": "#00BFAE",
    "aur": "#A855F7",
    "flatpak": "#3B82F6",
    "npm": "#F97316",
}


class PackageDetailCard(QFrame):
    install_requested = pyqtSignal()
    update_requested = pyqtSignal()
    uninstall_requested = pyqtSignal()

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
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.10);
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

        self.avatar = _Avatar("?", _C["accent"])
        hl.addWidget(self.avatar)

        nc = QVBoxLayout()
        nc.setSpacing(1)
        self.name_label = QLabel()
        f = QFont()
        f.setBold(True)
        f.setPointSize(14)
        self.name_label.setFont(f)
        self.name_label.setStyleSheet(f"color: {_C['text']}; background: transparent;")
        self.name_label.setWordWrap(True)
        nc.addWidget(self.name_label)
        self.version_label = QLabel()
        self.version_label.setStyleSheet(
            f"color: {_C['text_muted']}; font-size: 11px; background: transparent;"
        )
        nc.addWidget(self.version_label)
        hl.addLayout(nc, 1)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
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
            f"color: {_C['text_sec']}; font-size: 12px; background: transparent;"
        )
        content.addWidget(self.version_row)

        self.source_row = _detail_row("Source", "")
        content.addWidget(self.source_row)
        self.id_row = _detail_row("ID", "")
        content.addWidget(self.id_row)

        # ── Description ──
        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)
        content.addWidget(_section_title("Description"))
        content.addSpacing(6)

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(
            f"color: {_C['text_sec']}; font-size: 12px; background: transparent;"
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
            _action_btn_stylesheet(_C["accent"], "rgba(0,191,174,0.5)")
        )
        self.install_btn.clicked.connect(self.install_requested.emit)
        self.action_layout.addWidget(self.install_btn)

        self.update_btn = QPushButton("Update Package")
        self.update_btn.setMinimumHeight(40)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(
            _action_btn_stylesheet(_C["warning"], "rgba(255,138,101,0.5)")
        )
        self.update_btn.clicked.connect(self.update_requested.emit)
        self.action_layout.addWidget(self.update_btn)

        self.uninstall_btn = QPushButton("Uninstall Package")
        self.uninstall_btn.setMinimumHeight(40)
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_btn.setStyleSheet(
            _action_btn_stylesheet(_C["danger"], "rgba(255,107,107,0.5)")
        )
        self.uninstall_btn.clicked.connect(self.uninstall_requested.emit)
        self.action_layout.addWidget(self.uninstall_btn)

        content.addWidget(self.action_container)
        layout.addWidget(scroll)

    def _source_color(self, source: str) -> str:
        return SOURCE_COLORS.get(source.lower(), _C["accent"])

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
                    f"background: rgba(255,138,101,0.12); color: {_C['warning']};"
                    f" font-size: 11px; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
            else:
                self.status_badge.setText("◉  Installed")
                self.status_badge.setStyleSheet(
                    f"background: rgba(16,185,129,0.12); color: {_C['success']};"
                    f" font-size: 11px; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
        else:
            self.status_badge.setText("○  Not Installed")
            self.status_badge.setStyleSheet(
                f"background: rgba(92,94,102,0.12); color: {_C['text_muted']};"
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

        if view == "updates":
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(True)
            self.uninstall_btn.setVisible(False)
        elif installed:
            if has_update:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(True)
                self.uninstall_btn.setVisible(True)
            else:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(False)
                self.uninstall_btn.setVisible(True)
        else:
            self.install_btn.setVisible(True)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(False)

        self.setVisible(True)

    @staticmethod
    def _set_row_text(row: QWidget, value: str):
        for i in range(row.layout().count()):
            w = row.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and i == 1:
                w.setText(value)
                break

    def clear(self):
        self._pkg_data = None
        self.name_label.clear()
        self.version_label.clear()
        self.version_row.clear()
        self.desc_label.clear()
        self.status_badge.setVisible(False)
        self.setVisible(False)
