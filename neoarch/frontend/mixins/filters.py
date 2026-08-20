"""Filters and sources mixin for the main window."""

import os

from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QWidget, QCheckBox,
                             QScrollArea, QLabel, QSizePolicy, QPushButton, QMenu)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QFont

from neoarch.resources.paths import PROJECT_ROOT
from neoarch.frontend.components.source_card import SourceCard, _ActionRow


class _PanelCard(QWidget):
    """Dark painted card matching SourceCard visual style for sidebar sections."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(9, 9, 10))
        painter.drawRect(r)
        glow = QRadialGradient(r.width() / 2.0, 0, r.width() * 0.9)
        glow.setColorAt(0.0, QColor(124, 58, 237, 16))
        glow.setColorAt(0.5, QColor(88, 40, 160, 8))
        glow.setColorAt(1.0, QColor(88, 40, 160, 0))
        painter.setBrush(glow)
        painter.drawRect(r)
        painter.setPen(QPen(QColor(255, 255, 255, 6), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(168, 85, 247, 8))
        painter.drawRect(QRectF(0, 0, r.width(), 1))
        painter.end()


class _BundleActionRow(_ActionRow):
    """ActionRow variant with white icon for bundles sidebar."""

    def __init__(self, title, icon_text="", parent=None):
        super().__init__(title, icon_text, parent)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
        from PyQt6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
            painter.setBrush(QColor(Colors.CARD_HOVER))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)

        icon_size = 16
        icon_x = 16
        icon_y = (h - icon_size) // 2
        font = painter.font()
        font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            QRectF(icon_x, icon_y, icon_size, icon_size),
            Qt.AlignmentFlag.AlignCenter,
            self.icon_text,
        )

        text_x = 40
        text_w = w - 40 - 24

        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT))
        painter.drawText(
            QRectF(text_x, 0, text_w, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        font.setPixelSize(15)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawText(
            QRectF(w - 21, 0, 13, h),
            Qt.AlignmentFlag.AlignCenter,
            "\u203A",
        )

        painter.end()
from neoarch.frontend.tokens import Colors, SourceColors

from neoarch.backend.services import filter as filters_service
from neoarch.frontend.components.updates_table import classify_update, _parse_size, _parse_version

_BASE_DIR = str(PROJECT_ROOT)


class _BundleIcon(QWidget):
    """Painted bundle/folder icon — 20x20, purple accent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._active = False

    def set_active(self, active):
        self._active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor("#C084FC") if self._active else QColor("#A855F7")
        bg = QColor(c.red(), c.green(), c.blue(), 30 if self._active else 18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0, 0, 20, 20), 6, 6)
        p.setPen(QPen(c, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 1, 18, 18), 5, 5)
        tab_w, tab_h = 7, 3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c.red(), c.green(), c.blue(), 40 if self._active else 22))
        p.drawRoundedRect(QRectF(3, 1, tab_w, tab_h), 2, 2)
        p.end()


class _BundleDeleteBtn(QPushButton):
    """Small × button visible on hover for deleting a bundle."""

    clicked_bundle = pyqtSignal(str)

    def __init__(self, key, parent=None):
        super().__init__("\u00d7", parent)
        self.key = key
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_3};
                border: none;
                border-radius: 9px;
                font-size: 13px;
                font-weight: 600;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(255, 107, 107, 0.15);
                color: #FF6B6B;
            }}
        """)
        self.clicked.connect(lambda: self.clicked_bundle.emit(key))


class _BundleListRow(QWidget):
    """macOS-style bundle row: icon + name + count badge + delete btn.

    Layout: [icon]  Bundle Name  [count badge] [× delete]
    """

    clicked = pyqtSignal(str)
    rename_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, key, name, count=0, parent=None):
        super().__init__(parent)
        self.key = key
        self._name = name
        self._count = count
        self._selected = False
        self._hover = False
        self.setFixedHeight(38)
        self.setMinimumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 6, 3)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._icon = _BundleIcon()
        layout.addWidget(self._icon)

        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self._name_label, 1)

        self._count_badge = QLabel()
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setMinimumWidth(22)
        self._count_badge.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_2};
                font-size: 10px;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 9px;
                padding: 1px 6px;
            }}
        """)
        self._update_count()
        layout.addWidget(self._count_badge)

        self._del_btn = _BundleDeleteBtn(self.key)
        self._del_btn.clicked_bundle.connect(self.delete_requested.emit)
        self._del_btn.setVisible(False)
        layout.addWidget(self._del_btn)

        self._apply_style()

    def _update_count(self):
        c = self._count
        self._count_badge.setText(str(c) if c > 0 else "")
        self._count_badge.setVisible(c > 0)

    def set_selected(self, selected):
        self._selected = selected
        self._icon.set_active(selected)
        self._apply_style()

    def set_info(self, name, count):
        self._name = name
        self._count = count
        self._name_label.setText(name)
        self._update_count()
        self._apply_style()

    def _apply_style(self):
        if self._selected:
            bg = "rgba(168, 85, 247, 0.12)"
            border = "rgba(168, 85, 247, 0.30)"
            text_color = "#FFFFFF"
            badge_bg = "rgba(168, 85, 247, 0.18)"
            badge_border = "rgba(168, 85, 247, 0.35)"
            badge_color = "#C084FC"
        elif self._hover:
            bg = "rgba(255, 255, 255, 0.04)"
            border = "rgba(255, 255, 255, 0.06)"
            text_color = Colors.TEXT
            badge_bg = "rgba(255, 255, 255, 0.08)"
            badge_border = "rgba(255, 255, 255, 0.10)"
            badge_color = Colors.TEXT_2
        else:
            bg = "transparent"
            border = "transparent"
            text_color = Colors.TEXT_2
            badge_bg = "rgba(255, 255, 255, 0.04)"
            badge_border = "rgba(255, 255, 255, 0.06)"
            badge_color = Colors.TEXT_3

        self.setStyleSheet(f"""
            _BundleListRow {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 12px;
                font-weight: {"600" if self._selected else "500"};
                background: transparent;
                border: none;
            }}
        """)
        self._count_badge.setStyleSheet(f"""
            QLabel {{
                color: {badge_color};
                font-size: 10px;
                font-weight: 600;
                background: {badge_bg};
                border: 1px solid {badge_border};
                border-radius: 9px;
                padding: 1px 6px;
            }}
        """)

    def enterEvent(self, e):
        self._hover = True
        self._del_btn.setVisible(True)
        self._apply_style()

    def leaveEvent(self, e):
        self._hover = False
        self._del_btn.setVisible(False)
        self._apply_style()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)

    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #1A1A1E;
                color: {Colors.TEXT};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 4px 0;
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: rgba(255,255,255,0.08);
            }}
        """)
        menu.addAction("Rename", lambda: self.rename_requested.emit(self.key))
        menu.addAction("Delete", lambda: self.delete_requested.emit(self.key))
        menu.exec(self.mapToGlobal(pos))


class _BundlesSourcePanel(QWidget):
    """Custom panel for bundles sidebar — matches SourceCard visual style."""

    source_toggled = pyqtSignal()
    bundle_selected = pyqtSignal(str)
    bundle_created = pyqtSignal()
    bundle_renamed = pyqtSignal(str, str)
    bundle_deleted = pyqtSignal(str)
    export_clicked = pyqtSignal()
    import_clicked = pyqtSignal()
    share_clicked = pyqtSignal()
    import_code_clicked = pyqtSignal(str)
    manage_cloud_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sources = {}
        self._bundle_rows = {}
        self._active_key = ""
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Sources")
        header.setStyleSheet(f"""
            color: {Colors.TEXT}; font-size: 15px; font-weight: 700;
            background: transparent; border: none; padding: 12px 20px 4px 20px;
        """)
        layout.addWidget(header)

        src_widget = QWidget()
        src_layout = QVBoxLayout(src_widget)
        src_layout.setContentsMargins(12, 4, 12, 4)
        src_layout.setSpacing(2)
        self._src_layout = src_layout
        layout.addWidget(src_widget)

        self._src_container = src_widget

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep1)

        self._build_bundles_table(layout)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep2)

        self._build_share_code_section(layout)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep3)

        self._build_import_code_section(layout)

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.HLine)
        sep4.setStyleSheet("color: rgba(255,255,255,0.04);")
        layout.addWidget(sep4)

        self._build_actions_section(layout)

        self._build_count_bar(layout)

    def _build_bundles_table(self, layout):
        hdr_row = QWidget()
        hdr_lay = QHBoxLayout(hdr_row)
        hdr_lay.setContentsMargins(20, 8, 12, 4)
        hdr_lay.setSpacing(0)
        lbl = QLabel("BUNDLES")
        lbl.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 11px; font-weight: 600;
            letter-spacing: 1.0px; background: transparent; border: none;
        """)
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        add_btn = QPushButton("+")
        add_btn.setFixedSize(22, 22)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(168, 85, 247, 0.15);
                color: {Colors.ACCENT};
                border: 1px solid rgba(168, 85, 247, 0.3);
                border-radius: 5px;
                font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(168, 85, 247, 0.3);
                border-color: rgba(168, 85, 247, 0.5);
            }}
        """)
        add_btn.clicked.connect(self._on_create_bundle)
        hdr_lay.addWidget(add_btn)
        layout.addWidget(hdr_row)

        table_header = QWidget()
        table_header.setFixedHeight(24)
        th_lay = QHBoxLayout(table_header)
        th_lay.setContentsMargins(20, 0, 12, 0)
        th_lay.setSpacing(0)
        for text, stretch in [("Name", 1), ("", 0), ("", 0)]:
            col = QLabel(text)
            col.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: 9px; font-weight: 600; letter-spacing: 0.5px; background: transparent; border: none;")
            th_lay.addWidget(col, stretch)
        layout.addWidget(table_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 5px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.10); min-height: 20px; border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.18); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._bundles_list_layout = QVBoxLayout(container)
        self._bundles_list_layout.setContentsMargins(8, 4, 8, 4)
        self._bundles_list_layout.setSpacing(1)
        self._bundles_list_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _build_share_code_section(self, layout):
        header = QLabel("SHARE CODE")
        header.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 11px; font-weight: 600;
            letter-spacing: 1.0px; background: transparent; border: none;
            padding: 8px 20px 4px 20px;
        """)
        layout.addWidget(header)

        card = _PanelCard()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 6, 16, 6)
        cv.setSpacing(4)

        code_row = QHBoxLayout()
        code_row.setSpacing(6)

        self._share_code_label = QLabel("")
        self._share_code_label.setStyleSheet(f"""
            color: {Colors.TEXT_3}; font-size: 11px;
            font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
            font-weight: 500; background: transparent; border: none;
        """)
        code_row.addWidget(self._share_code_label, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(42, 22)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #0C0C0E;
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 6px;
                padding: 0 8px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #E8EAF0; }}
            QPushButton:pressed {{ background: #D3D6DE; }}
        """)
        copy_btn.clicked.connect(self._on_copy_share_code)
        code_row.addWidget(copy_btn)

        cv.addLayout(code_row)

        gen_btn = QPushButton("Generate")
        gen_btn.setFixedHeight(24)
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.04);
                color: {Colors.TEXT_2};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.07);
                color: #EDEDEF;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.03);
            }}
        """)
        gen_btn.clicked.connect(self.share_clicked.emit)
        cv.addWidget(gen_btn)

        layout.addWidget(card)

    def _on_copy_share_code(self):
        code = self._share_code_label.text()
        if code:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(code)
            old = self._share_code_label.text()
            self._share_code_label.setText("Copied!")
            self._share_code_label.setStyleSheet(f"""
                color: {Colors.ACCENT}; font-size: 11px;
                font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
                font-weight: 600; background: transparent; border: none;
            """)
            from PyQt6.QtCore import QTimer
            def _restore():
                self._share_code_label.setText(old)
                self._share_code_label.setStyleSheet(f"""
                    color: {Colors.TEXT_3}; font-size: 11px;
                    font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
                    font-weight: 500; background: transparent; border: none;
                """)
            QTimer.singleShot(1500, _restore)

    def set_share_code(self, code):
        if hasattr(self, '_share_code_label'):
            self._share_code_label.setText(code if code else "")

    def _build_import_code_section(self, layout):
        header = QLabel("IMPORT CODE")
        header.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 11px; font-weight: 600;
            letter-spacing: 1.0px; background: transparent; border: none;
            padding: 8px 20px 4px 20px;
        """)
        layout.addWidget(header)

        card = _PanelCard()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 6, 16, 6)
        cv.setSpacing(4)

        from PyQt6.QtWidgets import QTextEdit
        self._import_code_input = QTextEdit()
        self._import_code_input.setPlaceholderText("Paste share code...")
        self._import_code_input.setFixedHeight(32)
        self._import_code_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0E0E10;
                color: #8B8D97;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
                padding: 6px 8px;
                selection-background-color: rgba(168, 85, 247, 0.3);
            }}
            QTextEdit:focus {{
                border: 1px solid rgba(168, 85, 247, 0.35);
            }}
        """)
        cv.addWidget(self._import_code_input)

        import_btn = QPushButton("Import")
        import_btn.setFixedHeight(24)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #0C0C0E;
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 6px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #E8EAF0; }}
            QPushButton:pressed {{ background: #D3D6DE; }}
        """)
        import_btn.clicked.connect(self._on_import_code_submit)
        cv.addWidget(import_btn)

        layout.addWidget(card)

    def _on_import_code_submit(self):
        code = self._import_code_input.toPlainText().strip()
        if code:
            self.import_code_clicked.emit(code)
            self._import_code_input.clear()

    def refresh_bundles(self, bundles, active_key=""):
        self._active_key = active_key
        lay = self._bundles_list_layout
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._bundle_rows.clear()

        for b in bundles:
            row = _BundleListRow(b["key"], b["name"], b["count"])
            row.set_selected(b["key"] == active_key)
            row.clicked.connect(self._on_bundle_clicked)
            row.rename_requested.connect(self._on_bundle_rename)
            row.delete_requested.connect(self._on_bundle_delete)
            self._bundle_rows[b["key"]] = row
            lay.addWidget(row)

        lay.addStretch()
        self._refresh_count_bar(bundles)

    def _refresh_count_bar(self, bundles):
        total = sum(b.get("count", 0) for b in bundles)
        self.update_count_bar(total, len(bundles))

    def _on_create_bundle(self):
        from neoarch.frontend.components.dark_dialogs import dark_input
        name, ok = dark_input(self, "New Bundle", "Bundle name:", "My Bundle")
        if ok and name.strip():
            from neoarch.backend.services.bundle_storage import create_bundle
            key = create_bundle(name.strip())
            self.bundle_created.emit()
            self.bundle_selected.emit(key)

    def _on_bundle_clicked(self, key):
        if key != self._active_key:
            self.bundle_selected.emit(key)

    def _on_bundle_rename(self, key):
        old_name = ""
        if key in self._bundle_rows:
            old_name = self._bundle_rows[key]._name
        from neoarch.frontend.components.dark_dialogs import dark_input
        name, ok = dark_input(self, "Rename Bundle", "New name:", old_name)
        if ok and name.strip():
            from neoarch.backend.services.bundle_storage import rename_bundle
            rename_bundle(key, name.strip())
            self.bundle_renamed.emit(key, name.strip())

    def _on_bundle_delete(self, key):
        from neoarch.frontend.components.dark_dialogs import dark_confirm
        if dark_confirm(self, "Delete Bundle", "Delete this bundle? This cannot be undone.", danger=True):
            from neoarch.backend.services.bundle_storage import delete_bundle
            delete_bundle(key)
            self.bundle_deleted.emit(key)

    def _build_actions_section(self, layout):
        header = QLabel("ACTIONS")
        header.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 11px; font-weight: 600;
            letter-spacing: 1.0px; background: transparent; border: none;
            padding: 8px 20px 4px 20px;
        """)
        layout.addWidget(header)

        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(12, 0, 12, 0)
        actions_layout.setSpacing(0)

        defs = [
            ("Export", "\U0001f4e4", self.export_clicked),
            ("Import", "\U0001f4e5", self.import_clicked),
            ("Manage Cloud", "\u2699", self.manage_cloud_clicked),
        ]
        for title, icon, signal in defs:
            row = _BundleActionRow(title, icon)
            row.clicked.connect(signal.emit)
            actions_layout.addWidget(row)

        layout.addWidget(actions_widget)

    def _build_count_bar(self, layout):
        bar = QWidget()
        bar.setObjectName("countBar")
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"""
            QWidget#countBar {{
                background: rgba(255, 255, 255, 0.02);
                border-top: 1px solid rgba(255, 255, 255, 0.04);
            }}
        """)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(20, 0, 20, 0)

        self._count_bar_label = QLabel("0 items · 0 bundles")
        self._count_bar_label.setStyleSheet(f"""
            color: {Colors.TEXT_3}; font-size: 10px; font-weight: 500;
            background: transparent; border: none;
        """)
        bl.addWidget(self._count_bar_label)

        layout.addWidget(bar)

    def update_count_bar(self, total_items, total_bundles):
        if hasattr(self, '_count_bar_label'):
            self._count_bar_label.setText(f"{total_items} items \u00b7 {total_bundles} bundles")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(9, 9, 10))
        painter.drawRect(r)
        glow = QRadialGradient(r.width() / 2.0, 0, r.width() * 0.9)
        glow.setColorAt(0.0, QColor(124, 58, 237, 16))
        glow.setColorAt(0.5, QColor(88, 40, 160, 8))
        glow.setColorAt(1.0, QColor(88, 40, 160, 0))
        painter.setBrush(glow)
        painter.drawRect(r)
        painter.setPen(QPen(QColor(255, 255, 255, 6), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(168, 85, 247, 8))
        painter.drawRect(QRectF(0, 0, r.width(), 1))
        painter.end()
        super().paintEvent(event)

    def add_source(self, name, icon_path, count=0):
        from neoarch.frontend.components.source_item import SourceItem
        item = SourceItem(name, icon_path, count=count)
        item.toggle.toggled.connect(lambda: self.source_toggled.emit())
        self._sources[name] = item
        self._src_layout.addWidget(item)

    def get_source_states(self):
        return {name: item.is_checked() for name, item in self._sources.items()}

    def set_source_count(self, name, count):
        item = self._sources.get(name)
        if item:
            item.set_count(count)

    def set_summary(self, total):
        if hasattr(self, '_count_bar_label'):
            from neoarch.backend.services.bundle_storage import list_bundles
            n_bundles = len(list_bundles())
            self._count_bar_label.setText(f"{total} items \u00b7 {n_bundles} bundles")


def _fmt_size(b):
    try:
        mb = float(b) / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GiB"
        return f"{mb:.1f} MiB"
    except Exception:
        return ""


class _FiltersMixin:
    def get_row_checkbox(self, row):
        cell = self.package_table.cellWidget(row, 0)
        if not cell:
            return None
        if isinstance(cell, QCheckBox):
            return cell
        try:
            chks = cell.findChildren(QCheckBox)
            return chks[0] if chks else None
        except Exception:
            return None

    def create_filters_panel(self):
        self.filters_panel = QFrame()
        self.filters_panel.setMinimumWidth(250)
        self.filters_panel.setMaximumWidth(268)
        self.filters_panel.setStyleSheet("""
            QFrame {
                background-color: #0C0C0E;
            }
        """)

        panel_layout = QVBoxLayout(self.filters_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        scroll = QScrollArea(self.filters_panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.10);
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.18);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sources_section = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_section)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setSpacing(0)

        layout.addWidget(self.sources_section, 1)

        self.filters_section = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_section)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(8)

        layout.addWidget(self.filters_section)

        scroll.setWidget(container)
        panel_layout.addWidget(scroll)

        return self.filters_panel

    def update_filters_panel(self, view_id):
        # Clear existing filters section
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Recreate filters based on view
        if view_id == "updates":
            self.update_updates_sources()
        elif view_id == "installed":
            pass
        else:
            filter_options = []

        # Update visibility
        if view_id == "installed":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_installed_sources()
        elif view_id == "updates":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
        elif view_id == "discover":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_discover_sources()
        elif view_id == "bundles":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_bundles_sources()
        elif view_id in ("git", "docker"):
            # No source or status filters for Git/Docker pages
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        elif view_id == "plugins":
            # Show a source panel like the updates/installed page
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            self.update_plugins_sources()
        elif view_id == "settings":
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
        else:
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)

    def on_filter_selection_changed(self, filter_states):
        """Handle changes in filter selection"""
        # Apply filtering based on current view
        if self.current_view == "installed":
            self._installed_filter_states = filter_states.copy()
            self.apply_filters()
        elif self.current_view == "updates":
            self._recompute_updates()
        elif self.current_view == "plugins":
            # Apply plugin status filters (Available/Installed)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.apply_filters(filter_states)

    def update_discover_sources(self):
        """Update the discover sources using the new SourceCard component"""
        # Clear existing sources layout
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Always create a new SourceCard component
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_source_selection_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        self.source_card.sort_changed.connect(self.on_discover_sort_changed)
        self.source_card.installed_filter_changed.connect(self.on_discover_installed_filter_changed)

        # Add the four main sources (exclude Local from Discover)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "sources", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "sources", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "sources", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "sources", "node.svg")),
        ]

        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)

        # Discover-specific sort options. "relevance" keeps the best-match
        # ordering produced by the search; the rest are plain field sorts.
        self.source_card.set_sort_methods([
            ("relevance", True, "Best Match"),
            ("name", True, "Name A-Z"),
            ("name", False, "Name Z-A"),
            ("version", True, "Version (Oldest)"),
            ("version", False, "Version (Latest)"),
            ("source", True, "Source A-Z"),
            ("source", False, "Source Z-A"),
            ("installed", False, "Not Installed First"),
            ("installed", True, "Installed First"),
        ])
        self.source_card.set_sort("relevance", True)

        self.sources_layout.addWidget(self.source_card)
        self.source_card.maintenance_action.connect(self.on_installed_maintenance_action)
        self.source_card.configure_sections(
            show_search=True, show_counts=True, show_sort=True, show_installed_filter=True,
            show_storage=True, show_summary=True)
        self._refresh_discover_storage_async()

    def _refresh_discover_storage_async(self):
        """Fetch disk usage and cache size in the background for Discover."""
        try:
            def _run_storage():
                try:
                    from neoarch.backend.services.hygiene import disk_usage, package_cache_size
                    disk = disk_usage("/")
                    cache = package_cache_size()
                except Exception:
                    disk, cache = {}, 0
                self.ui_call.emit(lambda: self._apply_discover_storage(disk, cache))

            from threading import Thread
            Thread(target=_run_storage, daemon=True).start()
        except Exception:
            pass

    def _apply_discover_storage(self, disk, cache):
        if self.current_view != "discover" or not getattr(self, 'source_card', None):
            return
        try:
            self.source_card.set_storage(disk=disk, cache_size=cache)
        except Exception:
            pass

    def update_updates_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "sources", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "sources", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "sources", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "sources", "node.svg")),
            ("Local", os.path.join(_BASE_DIR, "assets", "icons", "sources", "local.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        self.source_card.source_changed.connect(self.on_updates_source_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        self.source_card.search_mode_changed.connect(self._recompute_updates)
        self.source_card.status_filter_changed.connect(self._recompute_updates)
        self.source_card.sort_changed.connect(self._recompute_updates)
        self.source_card.set_action_callbacks(
            update_all=self.perform_update_all,
            ignore_selected=self.ignore_selected,
            manage_ignored=self.manage_ignored,
        )
        self.source_card.configure_sections(
            show_status=True, show_sort=True, show_actions=True,
            show_summary=True, show_search=True, show_counts=True,
        )
        try:
            self.source_card.on_source_changed()
        except Exception:
            pass
        self._refresh_updates_summary()
        self._recompute_updates()

    def update_installed_sources(self):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_installed_source_changed)
        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "sources", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "sources", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "sources", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "sources", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        self.source_card.health_action.connect(self.on_installed_health_action)
        self.source_card.sort_changed.connect(self.apply_filters)
        self.source_card.maintenance_action.connect(self.on_installed_maintenance_action)
        self.source_card.configure_sections(
            show_search=False, show_health=True, show_counts=True, show_summary=True, show_sort=True,
            show_quick_actions=True,
        )
        self._refresh_installed_sources()
        self._refresh_installed_health_async()

    def on_installed_maintenance_action(self, action):
        if action == "purge_cache":
            if not self.ensure_session_auth():
                self.log("Cache purge cancelled: authentication required.")
                return

            def _run():
                try:
                    from neoarch.backend.services.hygiene import purge_cache
                    ok = purge_cache(retain=2)
                except Exception:
                    ok = False
                self.ui_call.emit(lambda: self._on_cache_cleared(ok))
            try:
                from threading import Thread
                Thread(target=_run, daemon=True).start()
            except Exception:
                pass
        elif action == "update_all":
            try:
                self.perform_update_all()
            except Exception:
                pass
        elif action == "clean_orphans":
            try:
                self.cleanup_orphans()
            except Exception:
                pass

    def _on_cache_cleared(self, ok):
        if ok:
            self._notify("Cache cleared", "Old package versions were removed from the cache.",
                         level="success", event="install")
        else:
            self._notify("Cache clear failed", "Could not trim the package cache.",
                         level="error", event="errors")
        if self.current_view == "installed":
            self._refresh_installed_storage_async()
        elif self.current_view == "discover":
            self._refresh_discover_storage_async()

    def _refresh_installed_storage_async(self):
        """Fetch disk usage and cache size in the background."""
        try:
            def _run():
                try:
                    from neoarch.backend.services.hygiene import disk_usage, package_cache_size
                    disk = disk_usage("/")
                    cache = package_cache_size()
                except Exception:
                    disk, cache = {}, 0
                self.ui_call.emit(lambda: self._apply_installed_storage(disk, cache))
            from threading import Thread
            Thread(target=_run, daemon=True).start()
        except Exception:
            pass

    def _apply_installed_storage(self, disk, cache):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        try:
            self.source_card.set_storage(disk=disk, cache_size=cache)
        except Exception:
            pass

    def on_installed_health_action(self, action):
        if action == "orphans":
            self.cleanup_orphans()
        elif action == "pacnew":
            self.manage_pacnew()
        elif action == "outdated":
            self.switch_view("updates")

    def _refresh_installed_sources(self):
        """Populate the installed source card: counts, distribution, health, summary."""
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'installed_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = 0
            per[s] += 1
        try:
            for name, item in self.source_card.sources.items():
                item.set_count(per.get(name, 0))
        except Exception:
            pass
        try:
            self.source_card.set_distribution(per)
        except Exception:
            pass
        outdated = sum(1 for p in base if p.get('has_update'))
        sizes = getattr(self, '_installed_sizes', None) or {}
        total_b = sum(sizes.values())
        size_text = f"{_fmt_size(total_b)}" if total_b > 0 else ""
        try:
            self.source_card.set_health(
                orphans=len(getattr(self, '_orphans_list', None) or []),
                pacnew=len(getattr(self, '_pacnew_list', None) or []),
                outdated=outdated,
            )
        except Exception:
            pass
        try:
            self.source_card.set_summary(len(base), size_text, noun="packages installed", size_label="on disk")
        except Exception:
            pass

    def _refresh_installed_health_async(self):
        """Fetch orphan/pacnew counts first (fast), then sizes (slow) in background."""
        try:
            def _run_counts():
                try:
                    from neoarch.backend.services.hygiene import list_orphans, list_pacnew, list_explicit_packages
                    orphans = list_orphans()
                    pacnew = list_pacnew()
                    explicit = list_explicit_packages()
                except Exception:
                    orphans, pacnew, explicit = [], [], set()
                self.ui_call.emit(lambda: self._apply_installed_counts(orphans, pacnew, explicit))

            def _run_sizes():
                try:
                    from neoarch.backend.services.hygiene import list_installed_sizes
                    sizes = list_installed_sizes()
                except Exception:
                    sizes = {}
                self.ui_call.emit(lambda: self._apply_installed_sizes(sizes))

            from threading import Thread
            Thread(target=_run_counts, daemon=True).start()
            Thread(target=_run_sizes, daemon=True).start()
        except Exception:
            pass

    def _apply_installed_counts(self, orphans, pacnew, explicit=None):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        self._orphans_list = orphans or []
        self._pacnew_list = pacnew or []
        if explicit is not None:
            self._explicit_packages = explicit
        self._refresh_installed_sources()

    def _apply_installed_sizes(self, sizes=None):
        if self.current_view != "installed" or not getattr(self, 'source_card', None):
            return
        self._installed_sizes = sizes or {}
        self._refresh_installed_sources()

    def update_plugins_sources(self):
        """Update plugins sources using the SourceCard component (like updates/installed)."""
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_plugins_source_changed)
        self.source_card.sort_changed.connect(self.on_plugins_sort_changed)

        # Per-source counts from the curated catalog
        counts = {"pacman": 0, "AUR": 0, "Flatpak": 0, "npm": 0}
        plugins = []
        try:
            from neoarch.resources.plugin_data import get_all_plugins_data
            from neoarch.frontend.components.plugins_view import PluginsView, _canonical_source
            plugins = get_all_plugins_data()
            for p in plugins:
                src = _canonical_source(PluginsView._get_package_source(p))
                counts[src] = counts.get(src, 0) + 1
        except Exception:
            pass

        sources = [
            ("pacman", os.path.join(_BASE_DIR, "assets", "icons", "sources", "pacman.svg")),
            ("AUR", os.path.join(_BASE_DIR, "assets", "icons", "sources", "aur.svg")),
            ("Flatpak", os.path.join(_BASE_DIR, "assets", "icons", "sources", "flatpack.svg")),
            ("npm", os.path.join(_BASE_DIR, "assets", "icons", "sources", "node.svg")),
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path, count=counts.get(source_name, 0))

        self.source_card.set_sort_methods([
            ("name_asc", True, "Name A-Z"),
            ("name_desc", True, "Name Z-A"),
            ("category", True, "Category"),
            ("source", True, "Source"),
            ("installed", True, "Installed First"),
        ])
        self.source_card.set_sort("name_asc", True)

        self.sources_layout.addWidget(self.source_card)
        self.source_card.category_changed.connect(self._on_plugins_category_changed)
        self.source_card.status_mode_changed.connect(self._on_plugins_status_mode_changed)
        cats = sorted({(p.get('category') or '') for p in plugins if p.get('category')})
        cat_counts = {}
        for p in plugins:
            cat = p.get('category') or ''
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        self.source_card.set_categories(cats, cat_counts)
        self._plugins_status_mode = "all"
        self._plugins_category = ""
        self.source_card.configure_sections(
            show_search=False, show_counts=True, show_sort=True, show_summary=True,
            show_categories=True, show_status_mode=True, show_stats=False)
        self._refresh_plugins_summary()

    def _on_plugins_category_changed(self, category):
        self._plugins_category = category or ""
        self._apply_plugins_filters()

    def _on_plugins_status_mode_changed(self, mode):
        self._plugins_status_mode = mode or "all"
        try:
            if not (hasattr(self, 'plugins_view') and self.plugins_view):
                return
            states = {
                "all": {"Available": True, "Installed": True},
                "available": {"Available": True, "Installed": False},
                "installed": {"Available": False, "Installed": True},
            }.get(self._plugins_status_mode, {"Available": True, "Installed": True})
            self.plugins_view.apply_filters(states)
            self._refresh_plugins_summary()
        except Exception:
            pass

    def _apply_plugins_filters(self):
        try:
            if not (hasattr(self, 'plugins_view') and self.plugins_view):
                return
            query = getattr(self, '_plugins_search_query', "")
            cats = [getattr(self, '_plugins_category', "")] if getattr(self, '_plugins_category', "") else []
            self.plugins_view.set_filter(query, False, cats)
            self._refresh_plugins_summary()
        except Exception:
            pass

    def _refresh_plugins_summary(self):
        """Update the bottom extension count and status counts on the plugins source card."""
        try:
            if not (hasattr(self, 'source_card') and self.source_card):
                return
            from neoarch.resources.plugin_data import get_all_plugins_data
            plugins = get_all_plugins_data()
            total = len(plugins)
            installed = 0
            if hasattr(self, 'plugins_view') and self.plugins_view:
                try:
                    cache = getattr(self.plugins_view, '_installed_cache', {})
                    installed = sum(1 for val in cache.values() if val)
                except Exception:
                    installed = 0
            count = total
            if hasattr(self, 'plugins_view') and self.plugins_view:
                try:
                    count = len(self.plugins_view._get_filtered_plugins()) or total
                except Exception:
                    count = total
            self.source_card.set_summary(count, noun="extensions")
            self.source_card.set_status_counts({
                "all": total,
                "available": max(0, total - installed),
                "installed": installed,
            })
        except Exception:
            pass

    def on_installed_source_changed(self, source_states):
        self.apply_filters()

    def on_plugins_source_changed(self, source_states):
        if hasattr(self, 'plugins_view') and self.plugins_view:
            self.plugins_view.apply_source_filters(source_states)
            self._refresh_plugins_summary()

    def on_updates_source_changed(self, source_states):
        self._recompute_updates()

    def _pkg_status(self, pkg):
        try:
            return pkg.get("status") or classify_update(pkg.get("version"), pkg.get("new_version"))
        except Exception:
            return "Maintenance"

    def _matches_query(self, pkg, query, mode):
        name = (pkg.get('name') or '').lower()
        pid = (pkg.get('id') or pkg.get('name') or '').lower()
        if mode == 'name':
            return query in name
        if mode == 'id':
            return query in pid
        return query in name or query in pid

    def _sort_updates(self, dataset, field, asc):
        try:
            if field == 'size':
                def key(p): return _parse_size(p.get('download_size') or '')
            elif field == 'version':
                def key(p): return (_parse_version(p.get('version')), _parse_version(p.get('new_version')))
            elif field == 'status':
                def key(p): return classify_update(p.get('version'), p.get('new_version'))
            elif field == 'date':
                def key(p): return p.get('installed_date') or 0
            elif field == 'source':
                def key(p): return (p.get('source') or '').lower()
            else:
                def key(p): return (p.get('name') or '').lower()
            return sorted(dataset, key=key, reverse=not asc)
        except Exception:
            return dataset

    def _refresh_updates_summary(self):
        """Refresh per-source counts and the total size summary from updates_all."""
        if self.current_view != "updates" or not getattr(self, 'source_card', None):
            return
        base = getattr(self, 'updates_all', None) or []
        per = {}
        for pkg in base:
            s = pkg.get('source')
            if s not in per:
                per[s] = [0, 0.0]
            per[s][0] += 1
            per[s][1] += _parse_size(pkg.get('download_size') or '')
        try:
            for name, item in self.source_card.sources.items():
                n, b = per.get(name, (0, 0.0))
                item.set_count(n, _fmt_size(b))
        except Exception:
            pass
        total_b = sum(per[s][1] for s in per)
        known = sum(1 for p in base if _parse_size(p.get('download_size') or '') > 0)
        size_text = ""
        if total_b > 0:
            prefix = "~" if known < len(base) else ""
            size_text = f"{prefix}{_fmt_size(total_b)}"
        try:
            self.source_card.set_summary(len(base), size_text, noun="updates available", size_label="to download")
        except Exception:
            pass

    def _recompute_updates(self):
        """Compose source, status, search, and sort filters for the updates view."""
        if self.current_view != "updates":
            return
        self._refresh_updates_summary()
        dataset = list(getattr(self, 'updates_all', None) or [])
        states = {}
        try:
            states = self.source_card.get_selected_sources()
        except Exception:
            states = {}
        if states:
            dataset = [p for p in dataset if states.get(p.get('source'), True)]
        try:
            active = self.source_card.get_active_statuses()
            dataset = [p for p in dataset if self._pkg_status(p) in active]
        except Exception:
            pass
        query = ""
        try:
            query = (self.search_input.text() or '').strip().lower()
        except Exception:
            pass
        if query:
            mode = 'both'
            try:
                mode = self.source_card.get_search_mode()
            except Exception:
                pass
            dataset = [p for p in dataset if self._matches_query(p, query, mode)]
        field, asc = 'name', True
        try:
            field = self.source_card.get_sort()
            asc = self.source_card.get_sort_asc()
        except Exception:
            pass
        dataset = self._sort_updates(dataset, field, asc)
        self.all_packages = dataset
        self.current_page = 0
        try:
            self.load_more_btn.setVisible(False)
        except Exception:
            pass
        try:
            col_map = {"name": 1, "size": 3, "version": 2, "status": 5, "source": 4}
            self.updates_table.sort_by_column(col_map.get(field, 1), asc)
        except Exception:
            pass
        if query:
            total = len(getattr(self, 'updates_all', None) or [])
            self.header_info.setText(
                f"{total} packages were found, {len(dataset)} of which match the specified filters")
        else:
            self.update_updates_header_counts()
        try:
            self._sync_updates_table(dataset)
        except Exception:
            pass

    def on_source_selection_changed(self, source_states):
        """Handle changes in source selection"""
        if self.current_view == "discover" and hasattr(self, 'search_results') and self.search_results:
            self.display_discover_results(selected_sources=source_states)

    def apply_filters(self):
        return filters_service.apply_filters(self)

    def apply_update_filters(self):
        return filters_service.apply_update_filters(self)

    # ── Bundles source panel ──────────────────────────────────────────────

    def update_bundles_sources(self):
        """Build the bundles sidebar — custom panel matching SourceCard style."""
        from neoarch.backend.services.bundle_storage import list_bundles, create_bundle

        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        panel = _BundlesSourcePanel(self)
        self._bundle_panel = panel
        panel.source_toggled.connect(self._on_bundle_source_toggle)
        panel.export_clicked.connect(self.export_bundle)
        panel.import_clicked.connect(self.import_bundle)
        panel.share_clicked.connect(self._share_bundle)
        panel.import_code_clicked.connect(self._import_by_code)
        panel.manage_cloud_clicked.connect(self._cloud_manage_bundles)
        panel.bundle_selected.connect(self._on_bundle_row_selected)
        panel.bundle_created.connect(self._on_bundle_row_created)
        panel.bundle_renamed.connect(self._on_bundle_row_renamed)
        panel.bundle_deleted.connect(self._on_bundle_row_deleted)

        src_icon = os.path.join(_BASE_DIR, "assets", "icons", "sources")
        for name, icon_file in [
            ("pacman", "pacman.svg"), ("AUR", "aur.svg"),
            ("Flatpak", "flatpack.svg"), ("npm", "node.svg"),
        ]:
            panel.add_source(name, os.path.join(src_icon, icon_file), count=0)

        bundles = list_bundles()
        active = getattr(self, '_active_bundle_key', '')
        if not bundles:
            key = create_bundle("My Bundle")
            self._active_bundle_key = key
            bundles = list_bundles()
            active = key
        elif not active:
            active = bundles[0]["key"]
            self._active_bundle_key = active

        panel.refresh_bundles(bundles, active)
        from neoarch.backend.services.bundle_storage import load_bundle
        self.bundle_items = load_bundle(active) if active else []
        self.sources_layout.addWidget(panel)

    def _on_bundle_row_selected(self, key):
        from neoarch.backend.services.bundle_storage import load_bundle
        self._active_bundle_key = key
        self.bundle_items = load_bundle(key)
        self.refresh_bundles_table()

    def _on_bundle_row_created(self):
        from neoarch.backend.services.bundle_storage import list_bundles, load_bundle
        bundles = list_bundles()
        active = self._active_bundle_key
        if bundles:
            active = bundles[0]["key"]
            self._active_bundle_key = active
            self.bundle_items = load_bundle(active)
        panel = getattr(self, '_bundle_panel', None)
        if panel:
            panel.refresh_bundles(bundles, active)
        self.refresh_bundles_table()

    def _on_bundle_row_renamed(self, key, new_name):
        from neoarch.backend.services.bundle_storage import list_bundles
        panel = getattr(self, '_bundle_panel', None)
        if panel:
            panel.refresh_bundles(list_bundles(), self._active_bundle_key)

    def _on_bundle_row_deleted(self, key):
        from neoarch.backend.services.bundle_storage import list_bundles, load_bundle
        bundles = list_bundles()
        active = self._active_bundle_key
        if active == key:
            active = bundles[0]["key"] if bundles else ""
            self._active_bundle_key = active
            self.bundle_items = load_bundle(active) if active else []
        panel = getattr(self, '_bundle_panel', None)
        if panel:
            panel.refresh_bundles(bundles, active)
        self.refresh_bundles_table()

    def _share_bundle(self):
        """Generate a share code for the active bundle."""
        cm = getattr(self, '_cloud_auth', None)
        if not cm or not cm.is_logged_in:
            self.log("Sign in to share bundles")
            return
        if not self.bundle_items:
            self.log("Bundle is empty — add packages before sharing")
            return
        from neoarch.backend.services.bundle_storage import list_bundles
        bundle_name = "My Bundle"
        for b in list_bundles():
            if b["key"] == self._active_bundle_key:
                bundle_name = b["name"]
                break
        code = cm.generate_share_code(bundle_name, self.bundle_items)
        if code:
            if hasattr(self, '_bundle_panel') and self._bundle_panel:
                self._bundle_panel.set_share_code(code)
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(code)
            self.log(f"Share code: {code}")
        else:
            self.log("Failed to generate share code")

    def _import_by_code(self, code=None):
        """Import a bundle by share code."""
        cm = getattr(self, '_cloud_auth', None)
        if not cm or not cm.is_logged_in:
            self.log("Sign in to import shared bundles")
            return
        if not code:
            from neoarch.frontend.components.dark_dialogs import dark_input
            code, ok = dark_input(self, "Import Shared Bundle", "Enter share code:")
            if not ok or not code.strip():
                return
            code = code.strip()
        else:
            code = code.strip()
        data = cm.get_shared_bundle(code)
        if not data:
            self.log("Share code not found or expired")
            return
        items = data.get("items", [])
        bundle_name = data.get("name", "Shared Bundle")
        existing = {(i.get('source'), i.get('id') or i.get('name')) for i in self.bundle_items}
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            key = (it.get('source'), it.get('id') or it.get('name'))
            if key not in existing:
                self.bundle_items.append(it)
                existing.add(key)
                added += 1
        self.log(f"Imported {added} items from shared bundle '{bundle_name}'")
        key = getattr(self, '_active_bundle_key', '')
        if key:
            from neoarch.backend.services.bundle_storage import save_bundle
            save_bundle(key, self.bundle_items)
        self.refresh_bundles_table()

    def _on_bundle_source_toggle(self):
        if self.current_view != "bundles":
            return
        states = self._bundle_panel.get_source_states()
        items = getattr(self, 'bundle_items', [])
        if not items:
            return
        filtered = [it for it in items if states.get(it.get('source', ''), True)]
        try:
            self.updates_table.set_bundles_mode(True)
            self.updates_table.set_packages(filtered)
        except Exception:
            pass

    def update_bundle_source_counts(self):
        items = getattr(self, 'bundle_items', [])
        counts = {"pacman": 0, "AUR": 0, "Flatpak": 0, "npm": 0}
        for it in items:
            src = it.get('source', '')
            if src in counts:
                counts[src] += 1
        panel = getattr(self, '_bundle_panel', None)
        if panel:
            for name, cnt in counts.items():
                panel.set_source_count(name, cnt)
            panel.set_summary(len(items))
            try:
                from neoarch.backend.services.bundle_storage import list_bundles
                panel.refresh_bundles(list_bundles(), getattr(self, '_active_bundle_key', ''))
            except Exception:
                pass
