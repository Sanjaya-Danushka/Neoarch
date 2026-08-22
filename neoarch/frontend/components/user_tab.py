"""
User profile page for NeoArch — full-page view matching the Git Projects
visual identity.  Shows account info, cloud sync status, and actions.
"""

import os
import getpass

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QMessageBox,
)

from neoarch.frontend.tokens import Colors, Radii

__all__ = ["UserTab"]

_BG = Colors.BG_SECONDARY
_SURFACE = Colors.SURFACE
_SURFACE_2 = Colors.SURFACE_2
_TEXT = Colors.TEXT
_TEXT2 = Colors.TEXT_2
_TEXT3 = Colors.TEXT_3
_ACCENT = Colors.ACCENT
_BORDER = Colors.BORDER
_BORDER_HOVER = Colors.BORDER_HOVER
_GREEN = Colors.GREEN
_ORANGE = Colors.ORANGE
_RED = Colors.RED

_R_SM = int(Radii.SM)
_R_MD = int(Radii.MD)
_R_LG = int(Radii.LG)


def _svg_icon(rel_path, size, color="#FFFFFF"):
    from neoarch.resources.paths import PROJECT_ROOT
    path = os.path.join(str(PROJECT_ROOT), "assets", "icons", rel_path)
    try:
        r = QSvgRenderer(path)
        if r.isValid():
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r.render(p, QRectF(0, 0, size, size))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(QRectF(0, 0, size, size), QColor(color))
            p.end()
            return QIcon(pm)
    except Exception:
        pass
    return QIcon()


# ── Info Card ──────────────────────────────────────────────────────

class _InfoCard(QFrame):
    def __init__(self, title, value, subtitle="", color=_TEXT, parent=None):
        super().__init__(parent)
        self.setObjectName("userInfoCard")
        self.setStyleSheet(f"""
            QFrame#userInfoCard {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_R_LG}px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(
            f"color: {_TEXT2}; font-size: 11px; font-weight: 500;"
            "background: transparent; border: none;")
        layout.addWidget(t)

        v = QLabel(str(value))
        v.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: 700;"
            "background: transparent; border: none;")
        v.setWordWrap(True)
        layout.addWidget(v)

        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px;"
                "background: transparent; border: none;")
            s.setWordWrap(True)
            layout.addWidget(s)


# ── Main UserTab ───────────────────────────────────────────────────

class UserTab(QWidget):
    """Full-page User/Profile view."""

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        self._build_header(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 3px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(12)

        self._build_profile_card(cl)
        self._build_sync_section(cl)
        self._build_system_info(cl)

        cl.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _build_header(self, parent):
        row = QHBoxLayout()
        row.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(2)

        title = QLabel("Profile")
        title.setStyleSheet(
            f"color: {_TEXT}; font-size: 20px; font-weight: 700;"
            "background: transparent; border: none;")
        left.addWidget(title)

        subtitle = QLabel("Manage your account and cloud sync")
        subtitle.setStyleSheet(
            f"color: {_TEXT2}; font-size: 12px;"
            "background: transparent; border: none;")
        left.addWidget(subtitle)

        row.addLayout(left, 1)

        parent.addLayout(row)

    def _build_profile_card(self, parent):
        cm = getattr(self.main_app, '_cloud_auth', None)
        user = cm.user if cm and cm.is_logged_in else None

        card = QFrame()
        card.setObjectName("profileCard")
        card.setStyleSheet(f"""
            QFrame#profileCard {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: {_R_LG}px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Avatar
        avatar_frame = QFrame()
        avatar_frame.setFixedSize(72, 72)
        avatar_frame.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE_2};
                border: 2px solid {_BORDER};
                border-radius: 36px;
            }}
        """)
        avatar_layout = QVBoxLayout(avatar_frame)
        avatar_layout.setContentsMargins(0, 0, 0, 0)

        avatar_icon = QLabel()
        avatar_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if user and user.avatar_url:
            try:
                import urllib.request
                from PyQt6.QtCore import QBuffer, QByteArray
                data = urllib.request.urlopen(user.avatar_url, timeout=5).read()
                pm = QPixmap()
                pm.loadFromData(data)
                if not pm.isNull():
                    avatar_icon.setPixmap(pm.scaled(
                        64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation))
                else:
                    avatar_icon.setText("👤")
                    avatar_icon.setStyleSheet("font-size: 28px; background: transparent; border: none;")
            except Exception:
                avatar_icon.setText("👤")
                avatar_icon.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        else:
            avatar_icon.setText("👤")
            avatar_icon.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        avatar_layout.addWidget(avatar_icon)
        layout.addWidget(avatar_frame, 0, Qt.AlignmentFlag.AlignTop)

        # Info
        info = QVBoxLayout()
        info.setSpacing(4)

        name = user.name if user else getpass.getuser()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 18px; font-weight: 700;"
            "background: transparent; border: none;")
        info.addWidget(name_lbl)

        if user and user.email:
            email_lbl = QLabel(user.email)
            email_lbl.setStyleSheet(
                f"color: {_TEXT2}; font-size: 12px;"
                "background: transparent; border: none;")
            info.addWidget(email_lbl)

        status_text = "Signed in" if user else "Not signed in"
        status_color = _GREEN if user else _TEXT3
        status_lbl = QLabel(f"● {status_text}")
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 12px; font-weight: 500;"
            "background: transparent; border: none;")
        info.addWidget(status_lbl)

        info.addStretch(1)
        layout.addLayout(info, 1)

        # Action button
        if user:
            action_btn = QPushButton("Sign Out")
            action_btn.setFixedHeight(34)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,80,80,0.12);
                    color: {_RED};
                    border: 1px solid rgba(255,80,80,0.3);
                    border-radius: {_R_SM}px;
                    padding: 0 18px;
                    font-size: 12px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba(255,80,80,0.2);
                }}
            """)
            action_btn.clicked.connect(self._on_sign_out)
            layout.addWidget(action_btn, 0, Qt.AlignmentFlag.AlignTop)
        else:
            action_btn = QPushButton(" Sign In")
            action_btn.setIcon(_svg_icon("ui/cloud.svg", 14, "#0C0C0E"))
            action_btn.setIconSize(QRectF(0, 0, 14, 14).toRect().size())
            action_btn.setFixedHeight(34)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF; color: #0C0C0E;
                    border: 1px solid rgba(255,255,255,0.9);
                    border-radius: 10px; padding: 0 18px;
                    font-size: 12px; font-weight: 600;
                }}
                QPushButton:hover {{ background-color: #E8EAF0; }}
            """)
            action_btn.clicked.connect(self._on_sign_in)
            layout.addWidget(action_btn, 0, Qt.AlignmentFlag.AlignTop)

        parent.addWidget(card)

    def _build_sync_section(self, parent):
        section = QLabel("Cloud Sync")
        section.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 600;"
            "background: transparent; border: none;")
        parent.addWidget(section)

        cm = getattr(self.main_app, '_cloud_auth', None)
        user = cm.user if cm and cm.is_logged_in else None

        if not user:
            empty = QFrame()
            empty.setStyleSheet(f"""
                QFrame {{
                    background: {_SURFACE};
                    border: 1px solid {_BORDER};
                    border-radius: {_R_MD}px;
                }}
            """)
            el = QVBoxLayout(empty)
            el.setContentsMargins(16, 20, 16, 20)
            el.setSpacing(4)
            el.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            t = QLabel("Sign in to sync your data")
            t.setStyleSheet(
                f"color: {_TEXT2}; font-size: 13px; font-weight: 500;"
                "background: transparent; border: none;")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.addWidget(t)

            d = QLabel("Sync favourites and bundles across your devices")
            d.setStyleSheet(
                f"color: {_TEXT3}; font-size: 11px;"
                "background: transparent; border: none;")
            d.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.addWidget(d)

            parent.addWidget(empty)
            return

        grid = QGridLayout()
        grid.setSpacing(10)

        cards = [
            ("Favourites", "Sync", "Save and load favourite packages", _ACCENT),
            ("Bundles", "Sync", "Backup and restore bundle collections", _ACCENT),
        ]

        for i, (title, action, desc, color) in enumerate(cards):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {_SURFACE};
                    border: 1px solid {_BORDER};
                    border-radius: {_R_LG}px;
                }}
                QFrame:hover {{
                    border-color: {_BORDER_HOVER};
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(6)

            t = QLabel(title)
            t.setStyleSheet(
                f"color: {_TEXT}; font-size: 13px; font-weight: 600;"
                "background: transparent; border: none;")
            cl.addWidget(t)

            d = QLabel(desc)
            d.setStyleSheet(
                f"color: {_TEXT3}; font-size: 11px;"
                "background: transparent; border: none;")
            cl.addWidget(d)

            btn = QPushButton(action)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.04);
                    color: {color};
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 11px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.08);
                    border-color: rgba(255,255,255,0.14);
                }}
            """)
            if title == "Favourites":
                btn.clicked.connect(self._on_sync_favourites)
            else:
                btn.clicked.connect(self._on_sync_bundles)
            cl.addWidget(btn)

            grid.addWidget(card, i // 2, i % 2)

        parent.addLayout(grid)

    def _build_system_info(self, parent):
        section = QLabel("System")
        section.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 600;"
            "background: transparent; border: none;")
        parent.addWidget(section)

        grid = QGridLayout()
        grid.setSpacing(10)

        import platform as _platform
        cards = [
            ("OS", f"{_platform.system()} {_platform.release()}", _platform.machine(), _TEXT),
            ("Python", _platform.python_version(), "Runtime", _TEXT),
            ("User", getpass.getuser(), "System user", _TEXT),
        ]

        for i, (title, value, sub, color) in enumerate(cards):
            card = _InfoCard(title, value, sub, color)
            grid.addWidget(card, i // 2, i % 2)

        parent.addLayout(grid)

    # ── Actions ─────────────────────────────────────────────────────

    def _on_sign_in(self):
        cm = getattr(self.main_app, '_cloud_auth', None)
        if cm:
            cm.start_login()

    def _on_sign_out(self):
        reply = QMessageBox.question(
            self, "Sign Out",
            "Are you sure you want to sign out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        cm = getattr(self.main_app, '_cloud_auth', None)
        if cm:
            cm.logout()

    def _on_sync_favourites(self):
        cm = getattr(self.main_app, '_cloud_auth', None)
        if cm and cm.is_logged_in:
            try:
                self.main_app._cloud_sync_favourites()
            except Exception:
                pass

    def _on_sync_bundles(self):
        cm = getattr(self.main_app, '_cloud_auth', None)
        if cm and cm.is_logged_in:
            try:
                self.main_app._cloud_manage_bundles()
            except Exception:
                pass
