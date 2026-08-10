"""SourceCard Component — premium macOS-style floating panel for package source management."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QPalette
from neoarch.frontend.components.source_item import SourceItem
from neoarch.frontend.components.flow_layout import FlowLayout

# ── macOS design tokens ─────────────────────────────────────────────
_WINDOW = "#0E1116"
_CARD = (12, 12, 14)  # app "black glass" color rgba(12,12,14,0.75)
_RAISED = "#202733"
_HOVER = "#252D3B"
_BLUE = "#3B82F6"
_TEXT = "#F5F6FA"
_SECONDARY = "#A7B1C2"
_BORDER = "rgba(255, 255, 255, 0.05)"


class _RadioRow(QWidget):
    """macOS preference-style radio selection row with smooth animation.

    Thin 2px circle, soft gray border, filled blue center when selected.
    """

    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self._checked = False
        self._hover = False
        self._progress = 0.0
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self._animation = QPropertyAnimation(self, b"progress", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = value
        self.update()

    progress = pyqtProperty(float, get_progress, set_progress)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            self.update()
            return
        self._checked = checked
        self._animation.stop()
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self._hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_HOVER))
            painter.drawRoundedRect(QRectF(self.rect()), 8, 8)

        cs = 12
        cx = 10
        cy = (h - cs) // 2

        if self._progress > 0.01:
            painter.setPen(QPen(QColor(_BLUE), 2))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 55), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx + 1, cy + 1, cs - 2, cs - 2))

        dot = 3.5 * self._progress
        if dot > 0.2:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_BLUE))
            center = cs / 2.0
            painter.drawEllipse(QRectF(cx + center - dot, cy + center - dot, dot * 2, dot * 2))

        font = painter.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium if not self._checked else QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(_TEXT) if self._checked else QColor(_SECONDARY))
        painter.drawText(
            QRectF(cx + cs + 10, 0, w - cx - cs - 10, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text,
        )

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)


class _ActionRow(QWidget):
    """macOS preference-style action row: icon, title, chevron."""

    clicked = pyqtSignal()

    def __init__(self, title, icon_text="", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon_text = icon_text
        self._hover = False
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
            painter.setBrush(QColor(_RAISED))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)

        icon_size = 16
        icon_x = 16
        icon_y = (h - icon_size) // 2
        font = painter.font()
        font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(QColor(_SECONDARY))
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
        painter.setPen(QColor(_TEXT))
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)


class _StatusChip(QPushButton):
    """Refined update-type toggle pill: colored status dot + label.

    Active chips sit on a soft neutral surface with a bright label and a
    full-color dot; inactive chips are quiet (dim dot, muted text).
    """

    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self._color = QColor(color)
        self._hover = False
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(22)
        self.setObjectName("statusChip")
        self.setStyleSheet("background: transparent; border: none; padding: 0;")

    def update_style(self):
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def nextCheckState(self):
        pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        checked = self.isChecked()
        if checked:
            bg = QColor(255, 255, 255, 18) if self._hover else QColor(255, 255, 255, 12)
            border = QColor(255, 255, 255, 26) if self._hover else QColor(255, 255, 255, 16)
        else:
            bg = QColor(255, 255, 255, 8) if self._hover else QColor(0, 0, 0, 0)
            border = QColor(255, 255, 255, 14) if self._hover else QColor(0, 0, 0, 0)

        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 9, 9)

        d = 6
        dot_x = 10
        dot_y = (h - d) / 2
        dot_color = QColor(self._color)
        if not checked:
            dot_color.setAlpha(90)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_color)
        painter.drawEllipse(QRectF(dot_x, dot_y, d, d))

        font = painter.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(237, 237, 239) if checked else QColor(107, 114, 128))
        painter.drawText(
            QRectF(dot_x + d + 7, 0, w - dot_x - d - 15, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )
        painter.end()

    def sizeHint(self):
        font = QFont(self.font())
        font.setPixelSize(11)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.text())
        return QSize(text_w + 10 + 6 + 7 + 16, 22)


class SourceCard(QWidget):
    """Premium floating card panel for source selection with macOS controls."""

    source_changed = pyqtSignal(dict)
    search_mode_changed = pyqtSignal(str)
    status_filter_changed = pyqtSignal(list)
    sort_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sources = {}
        self.search_mode = 'both'
        self.segment_buttons = []
        self._radio_rows = []
        self.sort_field = 'name'
        self.sort_asc = True
        self._active_statuses = {"Security", "Feature", "Bug Fix", "Maintenance"}
        self._status_chips = []
        self._action_buttons = {}
        self._action_rows = {}
        self.init_ui()

    def init_ui(self):
        self.setObjectName("SourceCard")
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(*_CARD))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_header(layout)
        self._build_sources_container(layout)
        self._build_search_mode(layout)
        self._build_status_filter(layout)
        self._build_sort(layout)
        self._build_actions(layout)
        self._build_summary(layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(*_CARD))
        painter.end()
        super().paintEvent(event)

    def _build_header(self, layout):
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 4)

        title = QLabel("Sources")
        title.setObjectName("sourceCardTitle")
        title.setStyleSheet("""
            QLabel#sourceCardTitle {
                color: #F5F6FA;
                font-size: 15px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.select_all_btn = QPushButton()
        self.select_all_btn.setObjectName("toggleAllBtn")
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.setFixedHeight(24)
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        self.select_all_btn.setStyleSheet(self._toggle_all_style(True))
        header_layout.addWidget(self.select_all_btn)

        layout.addWidget(header)

    def _toggle_all_style(self, all_on):
        text = "Pause All" if all_on else "Enable All"
        self.select_all_btn.setText(text)
        if all_on:
            return """
                QPushButton#toggleAllBtn {
                    background-color: rgba(59, 130, 246, 0.12);
                    color: #3B82F6;
                    border: 1px solid rgba(59, 130, 246, 0.25);
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton#toggleAllBtn:hover {
                    background-color: rgba(59, 130, 246, 0.20);
                }
            """
        else:
            return """
                QPushButton#toggleAllBtn {
                    background-color: rgba(255, 255, 255, 0.04);
                    color: #6B7280;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton#toggleAllBtn:hover {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #A7B1C2;
                }
            """

    def _section_header(self, text):
        label = QLabel(text.upper())
        label.setObjectName("sectionHeaderLabel")
        label.setCursor(Qt.CursorShape.ArrowCursor)
        label.setStyleSheet("""
            QLabel#sectionHeaderLabel {
                color: #38BDF8;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1.0px;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        return label

    def _build_sources_container(self, layout):
        self.sources_container = QWidget()
        self.sources_container.setObjectName("sourcesContainer")
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_layout.setContentsMargins(12, 2, 12, 5)
        self.sources_layout.setSpacing(4)
        layout.addWidget(self.sources_container)

    def _build_search_mode(self, layout):
        self.search_mode_widget = QWidget()
        self.search_mode_widget.setObjectName("searchModeWidget")
        search_layout = QVBoxLayout(self.search_mode_widget)
        search_layout.setContentsMargins(16, 6, 16, 5)
        search_layout.setSpacing(1)

        search_layout.addWidget(self._section_header("Search Mode"))

        self._radio_rows = []
        for radio_id, radio_text in [("name", "By Name"), ("id", "By Package ID"), ("both", "Both")]:
            row = _RadioRow(radio_text)
            row.setChecked(radio_id == "both")
            row.clicked.connect(lambda rid=radio_id: self._on_radio_clicked(rid))
            search_layout.addWidget(row)
            self._radio_rows.append((radio_id, row))

        self.search_mode_widget.setStyleSheet("""
            QWidget#searchModeWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.03);
            }
        """)
        layout.addWidget(self.search_mode_widget)

    def _build_summary(self, layout):
        self.summary_widget = QWidget()
        self.summary_widget.setObjectName("summaryWidget")
        s_layout = QHBoxLayout(self.summary_widget)
        s_layout.setContentsMargins(16, 6, 16, 7)
        s_layout.setSpacing(6)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setStyleSheet("""
            QLabel#summaryLabel {
                color: #A7B1C2;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 0;
            }
        """)
        s_layout.addWidget(self.summary_label)
        s_layout.addStretch()
        self.summary_widget.setStyleSheet("""
            QWidget#summaryWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.03);
            }
        """)
        self.summary_widget.setVisible(False)
        layout.addWidget(self.summary_widget)

    def _build_status_filter(self, layout):
        self.status_widget = QWidget()
        self.status_widget.setObjectName("statusWidget")
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setContentsMargins(16, 6, 16, 5)
        status_layout.setSpacing(4)

        status_layout.addWidget(self._section_header("Update Type"))

        chip_container = QWidget()
        chip_container.setObjectName("chipContainer")
        chip_layout = FlowLayout(chip_container, h_spacing=6, v_spacing=6)
        chip_layout.setContentsMargins(0, 0, 0, 0)

        self._status_chips = []
        statuses = [
            ("Security", "#EF4444"),
            ("Feature", "#3B82F6"),
            ("Bug Fix", "#22C55E"),
            ("Maintenance", "#6B7280"),
        ]
        for status_text, status_color in statuses:
            chip = _StatusChip(status_text, status_color)
            chip.clicked.connect(lambda checked=False, s=status_text: self._on_status_chip_clicked(s))
            chip_layout.addWidget(chip)
            self._status_chips.append(chip)

        status_layout.addWidget(chip_container)
        self.status_widget.setStyleSheet(self._section_stylesheet())
        self.status_widget.setVisible(False)
        layout.addWidget(self.status_widget)

    def _build_sort(self, layout):
        self.sort_widget = QWidget()
        self.sort_widget.setObjectName("sortWidget")
        sort_layout = QVBoxLayout(self.sort_widget)
        sort_layout.setContentsMargins(16, 6, 16, 5)
        sort_layout.setSpacing(4)

        sort_layout.addWidget(self._section_header("Sort By"))

        self.sort_btn = QPushButton()
        self.sort_btn.setObjectName("sortBtn")
        self.sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_btn.setFixedHeight(26)
        self.sort_btn.setStyleSheet(self._sort_btn_style())
        sort_layout.addWidget(self.sort_btn)

        self.sort_menu = QMenu(self)
        self.sort_menu.setObjectName("sourceSortMenu")
        self.sort_menu.setStyleSheet("""
            QMenu#sourceSortMenu {
                background-color: #171C25;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 4px;
            }
            QMenu#sourceSortMenu::item {
                padding: 8px 14px;
                border-radius: 6px;
                margin: 1px 0;
                color: #F5F6FA;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
            QMenu#sourceSortMenu::item:selected {
                background-color: rgba(59, 130, 246, 0.16);
                color: #FFFFFF;
            }
            QMenu#sourceSortMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.06);
                margin: 4px 8px;
            }
        """)
        self._sort_actions = {}
        sort_fields = [("name", "Name"), ("size", "Size"), ("version", "Version"), ("status", "Type")]
        for sort_id, sort_text in sort_fields:
            act = self.sort_menu.addAction(sort_text)
            act.setCheckable(True)
            act.setChecked(sort_id == self.sort_field)
            act.triggered.connect(lambda checked=False, s=sort_id: self._on_sort_menu(s))
            self._sort_actions[sort_id] = act
        self.sort_menu.addSeparator()
        self.sort_asc_act = self.sort_menu.addAction("Ascending")
        self.sort_asc_act.setCheckable(True)
        self.sort_asc_act.setChecked(self.sort_asc)
        self.sort_asc_act.triggered.connect(self._on_sort_dir_menu)
        self.sort_desc_act = self.sort_menu.addAction("Descending")
        self.sort_desc_act.setCheckable(True)
        self.sort_desc_act.setChecked(not self.sort_asc)
        self.sort_desc_act.triggered.connect(self._on_sort_dir_menu)

        self._update_sort_btn_text()
        self.sort_widget.setStyleSheet(self._section_stylesheet())
        self.sort_widget.setVisible(False)
        layout.addWidget(self.sort_widget)

    def _sort_btn_style(self):
        return """
            QPushButton#sortBtn {
                color: #A7B1C2;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 12px;
                text-align: left;
            }
            QPushButton#sortBtn:hover {
                background: rgba(255, 255, 255, 0.07);
                border-color: rgba(59, 130, 246, 0.30);
                color: #F5F6FA;
            }
        """

    def _sort_label(self, field):
        return {"name": "Name", "size": "Size", "version": "Version", "status": "Type"}.get(field, "Name")

    def _update_sort_btn_text(self):
        arrow = "\u2191" if self.sort_asc else "\u2193"
        self.sort_btn.setText(f"Sort: {self._sort_label(self.sort_field)} {arrow}")

    def _on_sort_menu(self, sort_id):
        self.sort_field = sort_id
        for sid, act in self._sort_actions.items():
            act.blockSignals(True)
            act.setChecked(sid == sort_id)
            act.blockSignals(False)
        self._update_sort_btn_text()
        self.sort_changed.emit(sort_id)

    def _on_sort_dir_menu(self):
        self.sort_asc = self.sort_asc_act.isChecked()
        self.sort_asc_act.blockSignals(True)
        self.sort_asc_act.setChecked(self.sort_asc)
        self.sort_asc_act.blockSignals(False)
        self.sort_desc_act.blockSignals(True)
        self.sort_desc_act.setChecked(not self.sort_asc)
        self.sort_desc_act.blockSignals(False)
        self._update_sort_btn_text()
        self.sort_changed.emit(self.sort_field)

    def _build_actions(self, layout):
        self.actions_widget = QWidget()
        self.actions_widget.setObjectName("actionsWidget")
        actions_layout = QVBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(16, 6, 16, 7)
        actions_layout.setSpacing(1)

        actions_layout.addWidget(self._section_header("Actions"))

        self._action_buttons = {}
        self._action_rows = {}

        self.action_update_all_btn = QPushButton("Update All")
        self.action_update_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_update_all_btn.setFixedHeight(28)
        self.action_update_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        self._action_buttons["update_all"] = self.action_update_all_btn

        self.action_ignore_btn = QPushButton("Ignore Selected")
        self.action_ignore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_ignore_btn.setFixedHeight(24)
        self.action_ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #A7B1C2;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.07);
                color: #F5F6FA;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.03);
            }
        """)
        self._action_buttons["ignore"] = self.action_ignore_btn

        self.action_manage_btn = QPushButton("Manage Ignored")
        self.action_manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_manage_btn.setFixedHeight(24)
        self.action_manage_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #A7B1C2;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.07);
                color: #F5F6FA;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.03);
            }
        """)
        self._action_buttons["manage"] = self.action_manage_btn

        row_defs = [
            ("update_all", _ActionRow("Update All", "\u21BB"), self.action_update_all_btn),
            ("ignore", _ActionRow("Ignore Selected", "\u2715"), self.action_ignore_btn),
            ("manage", _ActionRow("Manage Ignored", "\u2699"), self.action_manage_btn),
        ]
        for key, row, btn in row_defs:
            row.clicked.connect(btn.click)
            actions_layout.addWidget(row)
            self._action_rows[key] = row
            btn.setVisible(False)

        self.actions_widget.setStyleSheet(self._section_stylesheet())
        self.actions_widget.setVisible(False)
        layout.addWidget(self.actions_widget)

    def _section_stylesheet(self):
        return """
            QWidget#statusWidget, QWidget#sortWidget, QWidget#actionsWidget, QWidget#summaryWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.03);
            }
        """

    def _on_status_chip_clicked(self, status_text):
        chip = None
        for c in self._status_chips:
            if c.text() == status_text:
                chip = c
                break
        if chip is None:
            return
        chip.blockSignals(True)
        chip.setChecked(not chip.isChecked())
        chip.update_style()
        chip.blockSignals(False)
        self._active_statuses = {c.text() for c in self._status_chips if c.isChecked()}
        self.status_filter_changed.emit(sorted(self._active_statuses))

    def set_action_callbacks(self, update_all=None, ignore_selected=None, manage_ignored=None):
        if update_all is not None:
            try:
                self.action_update_all_btn.clicked.disconnect()
            except Exception:
                pass
            self.action_update_all_btn.clicked.connect(update_all)
        if ignore_selected is not None:
            try:
                self.action_ignore_btn.clicked.disconnect()
            except Exception:
                pass
            self.action_ignore_btn.clicked.connect(ignore_selected)
        if manage_ignored is not None:
            try:
                self.action_manage_btn.clicked.disconnect()
            except Exception:
                pass
            self.action_manage_btn.clicked.connect(manage_ignored)

    def set_summary(self, count, size_text):
        if count is None:
            self.summary_widget.setVisible(False)
            return
        self.summary_widget.setVisible(True)
        self.summary_label.setText(f"{count} updates available \u00B7 {size_text}")

    def set_sort(self, field, ascending=True):
        self.sort_field = field
        self.sort_asc = ascending
        for sid, act in self._sort_actions.items():
            act.blockSignals(True)
            act.setChecked(sid == field)
            act.blockSignals(False)
        self.sort_asc_act.blockSignals(True)
        self.sort_asc_act.setChecked(ascending)
        self.sort_asc_act.blockSignals(False)
        self.sort_desc_act.blockSignals(True)
        self.sort_desc_act.setChecked(not ascending)
        self.sort_desc_act.blockSignals(False)
        self._update_sort_btn_text()

    def get_sort(self):
        return self.sort_field

    def get_sort_asc(self):
        return self.sort_asc

    def get_active_statuses(self):
        return set(self._active_statuses)

    def configure_sections(self, show_status=False, show_sort=False, show_actions=False,
                           show_summary=False, show_search=True, show_counts=False):
        self.status_widget.setVisible(show_status)
        self.sort_widget.setVisible(show_sort)
        self.actions_widget.setVisible(show_actions)
        self.summary_widget.setVisible(show_summary)
        self.search_mode_widget.setVisible(show_search)
        if not show_counts:
            for item in self.sources.values():
                item.count_label.setVisible(False)

    def _on_radio_clicked(self, radio_id):
        for rid, row in self._radio_rows:
            row.setChecked(rid == radio_id)
        self.search_mode = radio_id
        self.search_mode_changed.emit(radio_id)

    def _on_segment_clicked(self, seg_id):
        self._on_radio_clicked(seg_id)

    def add_source(self, source_name, icon_path, count=None, size=None):
        source_item = SourceItem(source_name, icon_path, self, count=count, size=size)
        source_item.toggle.toggled.connect(lambda checked=False, s=source_name: self.on_source_changed())
        self.sources[source_name] = source_item
        self.sources_layout.addWidget(source_item)
        self.update_toggle_all_button()
        self.on_source_changed()

    def get_sources(self):
        return {name: item for name, item in self.sources.items()}

    def on_source_changed(self):
        states = {name: item.is_checked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_toggle_all_button()

    def update_toggle_all_button(self):
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)
        all_on = checked_count > 0
        self.select_all_btn.setStyleSheet(self._toggle_all_style(all_on))

    def toggle_select_all(self):
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)
        for item in self.sources.values():
            item.toggle.blockSignals(True)
        if checked_count == total_count:
            for item in self.sources.values():
                item.set_checked(False)
        else:
            for item in self.sources.values():
                item.set_checked(True)
        for item in self.sources.values():
            item.toggle.blockSignals(False)
        states = {name: item.is_checked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_toggle_all_button()

    def get_selected_sources(self):
        return {name: item.is_checked() for name, item in self.sources.items()}

    def get_search_mode(self):
        return self.search_mode

    def set_search_mode(self, mode):
        self.search_mode = mode
        for rid, row in self._radio_rows:
            row.setChecked(rid == mode)
