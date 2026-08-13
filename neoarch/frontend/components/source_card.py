"""SourceCard Component — premium macOS-style floating panel for package source management."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QLinearGradient, QRadialGradient
from neoarch.frontend.components.source_item import SourceItem
from neoarch.frontend.components.flow_layout import FlowLayout

# ── app theme design tokens ─────────────────────────────────────────
_RAISED = "#22242A"
_HOVER = "#24262C"
_ACCENT = "#3B82F6"
_TEXT = "#EDEDEF"
_SECONDARY = "#8B8D97"
_MUTED = "#5C5E66"
_BORDER = "rgba(255, 255, 255, 0.06)"


def _fmt_bytes(b):
    try:
        b = int(b or 0)
        if b >= 1024 ** 4:
            return f"{b / 1024 ** 4:.2f} TiB"
        if b >= 1024 ** 3:
            return f"{b / 1024 ** 3:.1f} GiB"
        if b >= 1024 ** 2:
            return f"{b / 1024 ** 2:.0f} MiB"
        if b >= 1024:
            return f"{b / 1024:.0f} KiB"
        return f"{b} B"
    except Exception:
        return "0 B"


class _DiskBar(QWidget):
    """Thin usage bar that fills proportionally to the stored fraction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = 0.0

    def set_percent(self, percent):
        self._percent = max(0.0, min(1.0, float(percent)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        fill = max(self._percent, 0.0)
        if fill > 0:
            color = QColor("#22C55E") if fill < 0.7 else (QColor("#F59E0B") if fill < 0.9 else QColor("#EF4444"))
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(0, 0, max(w * fill, h), h), h / 2, h / 2)
        painter.end()
        super().paintEvent(event)


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
            painter.setPen(QPen(QColor(_ACCENT), 2))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 55), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx + 1, cy + 1, cs - 2, cs - 2))

        dot = 3.5 * self._progress
        if dot > 0.2:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_ACCENT))
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


class _HealthRow(QWidget):
    """macOS-style system health row: colored dot, title, count badge, chevron."""

    clicked = pyqtSignal()

    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = QColor(color)
        self._count = 0
        self._hover = False
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_count(self, count):
        self._count = int(count or 0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
            painter.setBrush(QColor(_RAISED))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)

        dot = 8
        dot_x = 16
        dot_y = (h - dot) / 2
        dot_color = QColor(self.color)
        if self._count == 0:
            dot_color = QColor(34, 197, 94)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_color)
        painter.drawEllipse(QRectF(dot_x, dot_y, dot, dot))

        font = painter.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(_TEXT))
        text_x = 32
        text_w = w - text_x - 80
        painter.drawText(
            QRectF(text_x, 0, text_w, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        if self._count > 0:
            badge_color = QColor(self.color)
            badge_color.setAlpha(40)
            border = QColor(self.color)
            border.setAlpha(120)
            text_color = QColor(self.color).lighter(120)
            text = str(self._count)
        else:
            badge_color = QColor(34, 197, 94, 30)
            border = QColor(34, 197, 94, 80)
            text_color = QColor(34, 197, 94)
            text = "0"

        font.setPixelSize(10)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        badge_w = fm.horizontalAdvance(text) + 14
        badge_h = 18
        badge_x = w - badge_w - 28
        badge_y = (h - badge_h) / 2
        painter.setPen(QPen(border, 1))
        painter.setBrush(badge_color)
        painter.drawRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 9, 9)
        painter.setPen(text_color)
        painter.drawText(
            QRectF(badge_x, badge_y, badge_w, badge_h),
            Qt.AlignmentFlag.AlignCenter,
            text,
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


class _HealthRing(QWidget):
    """Compact circular health gauge: dim track + colored progress arc + score."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._score = 100
        self.setFixedSize(44, 44)

    def set_score(self, score):
        self._score = max(0, min(100, int(score)))
        self.update()

    def _color(self):
        if self._score >= 85:
            return QColor("#22C55E")
        if self._score >= 60:
            return QColor("#F59E0B")
        return QColor("#EF4444")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen_w = 5
        rect = QRectF(pen_w / 2 + 1, pen_w / 2 + 1, w - pen_w - 2, h - pen_w - 2)

        painter.setPen(QPen(QColor(255, 255, 255, 22), pen_w))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        color = self._color()
        pen = QPen(color, pen_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        span = -360.0 * (self._score / 100.0)
        painter.drawArc(rect, 90 * 16, int(span * 16))

        font = painter.font()
        font.setPixelSize(15)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(color.lighter(120))
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, str(self._score))
        painter.end()


class _DistributionBar(QWidget):
    """Thin proportional bar showing the per-source package share."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._counts = {}
        self._colors = {
            "pacman": QColor("#3B82F6"),
            "AUR": QColor("#F59E0B"),
            "Flatpak": QColor("#10B981"),
            "npm": QColor("#EF4444"),
        }
        self.setFixedHeight(6)
        self.setMinimumWidth(0)

    def set_counts(self, counts):
        self._counts = {k: max(int(v or 0), 0) for k, v in (counts or {}).items()}
        self.setVisible(bool(self._counts))
        self.update()

    def paintEvent(self, event):
        total = sum(self._counts.values())
        if total <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        x = 0.0
        for name, count in self._counts.items():
            if count <= 0:
                continue
            seg_w = w * count / total
            if seg_w <= 0:
                continue
            painter.setBrush(self._colors.get(name, QColor("#6B7280")))
            painter.drawRect(QRectF(x + 1, 0, max(seg_w - 2, 1), h))
            x += seg_w
        painter.end()


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
    health_action = pyqtSignal(str)
    maintenance_action = pyqtSignal(str)

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
        self.setAutoFillBackground(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._build_header(layout)
        layout.addStretch(1)
        self._build_sources_container(layout)
        layout.addStretch(1)
        self._build_health(layout)
        layout.addStretch(1)
        self._build_search_mode(layout)
        layout.addStretch(1)
        self._build_status_filter(layout)
        layout.addStretch(1)
        self._build_sort(layout)
        layout.addStretch(1)
        self._build_storage(layout)
        layout.addStretch(1)
        self._build_stats(layout)
        layout.addStretch(1)
        self._build_quick_actions(layout)
        layout.addStretch(1)
        self._build_actions(layout)
        layout.addStretch(1)
        self._build_summary(layout)

        for w in (self.sources_container, self.health_widget, self.search_mode_widget,
                  self.status_widget, self.sort_widget, self.storage_widget,
                  self.stats_widget, self.quick_actions_widget, self.actions_widget,
                  self.summary_widget):
            w.setSizePolicy(w.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Maximum)

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

    def _build_header(self, layout):
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 4)

        title = QLabel("Sources")
        title.setObjectName("sourceCardTitle")
        title.setStyleSheet("""
            QLabel#sourceCardTitle {
                color: #EDEDEF;
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
                color: #3B82F6;
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
        self.sources_layout.setContentsMargins(12, 4, 12, 6)
        self.sources_layout.setSpacing(4)
        layout.addWidget(self.sources_container)

    def _build_health(self, layout):
        self.health_widget = QWidget()
        self.health_widget.setObjectName("healthWidget")
        health_layout = QVBoxLayout(self.health_widget)
        health_layout.setContentsMargins(16, 10, 16, 8)
        health_layout.setSpacing(6)

        health_layout.addWidget(self._section_header("System Health"))

        top = QHBoxLayout()
        top.setSpacing(14)

        self.health_ring = _HealthRing()
        top.addWidget(self.health_ring, 0, Qt.AlignmentFlag.AlignVCenter)

        status_col = QVBoxLayout()
        status_col.setSpacing(4)
        self.health_status_title = QLabel("System Healthy")
        self.health_status_title.setStyleSheet("""
            color: #22C55E;
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.health_status_subtitle = QLabel("All checks passed")
        self.health_status_subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 11px;
            font-weight: 400;
            background: transparent;
            border: none;
            padding: 0;
        """)
        status_col.addWidget(self.health_status_title)
        status_col.addWidget(self.health_status_subtitle)
        top.addLayout(status_col, 1)

        health_layout.addLayout(top)

        self.distribution_bar = _DistributionBar()
        health_layout.addWidget(self.distribution_bar)

        self._health_rows = {}
        row_defs = [
            ("orphans", "Orphaned Packages", "#F59E0B"),
            ("pacnew", "Config Files (.pacnew)", "#FB923C"),
            ("outdated", "Outdated Packages", "#3B82F6"),
        ]
        for key, title, color in row_defs:
            row = _HealthRow(title, color)
            row.clicked.connect(lambda k=key: self.health_action.emit(k))
            health_layout.addWidget(row)
            self._health_rows[key] = row

        self.health_widget.setStyleSheet(self._section_stylesheet())
        self.health_widget.setVisible(False)
        layout.addWidget(self.health_widget)

    def set_health(self, orphans=0, pacnew=0, outdated=0):
        orphans = int(orphans or 0)
        pacnew = int(pacnew or 0)
        outdated = int(outdated or 0)
        self._health_rows["orphans"].set_count(orphans)
        self._health_rows["pacnew"].set_count(pacnew)
        self._health_rows["outdated"].set_count(outdated)
        issues = orphans + pacnew + outdated
        score = max(10, 100 - round(issues * 100 / 150))
        self.health_ring.set_score(score)
        if issues == 0:
            self.health_status_title.setText("System Healthy")
            self.health_status_title.setStyleSheet(self._health_title_style("#22C55E"))
            self.health_status_subtitle.setText("All checks passed")
        elif score >= 60:
            self.health_status_title.setText("Needs Attention")
            self.health_status_title.setStyleSheet(self._health_title_style("#F59E0B"))
            self.health_status_subtitle.setText(f"{issues} item{'s' if issues != 1 else ''} found")
        else:
            self.health_status_title.setText("Action Recommended")
            self.health_status_title.setStyleSheet(self._health_title_style("#EF4444"))
            self.health_status_subtitle.setText(f"{issues} issues need resolving")

    def _health_title_style(self, color):
        return f"""
            color: {color};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding: 0;
        """

    def set_distribution(self, counts):
        self.distribution_bar.set_counts(counts)

    def _build_search_mode(self, layout):
        self.search_mode_widget = QWidget()
        self.search_mode_widget.setObjectName("searchModeWidget")
        search_layout = QVBoxLayout(self.search_mode_widget)
        search_layout.setContentsMargins(16, 6, 16, 4)
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
        self.summary_widget.setMinimumHeight(44)
        s_layout = QHBoxLayout(self.summary_widget)
        s_layout.setContentsMargins(16, 8, 16, 8)
        s_layout.setSpacing(0)

        self.summary_count_label = QLabel("0")
        self.summary_count_label.setStyleSheet("""
            color: #EDEDEF;
            font-size: 17px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.summary_count_caption = QLabel("")
        self.summary_count_caption.setStyleSheet("""
            color: #6B7280;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.summary_count_caption.setMinimumWidth(0)

        count_col = QVBoxLayout()
        count_col.setSpacing(1)
        count_col.setContentsMargins(0, 0, 0, 0)
        count_col.addWidget(self.summary_count_label)
        count_col.addWidget(self.summary_count_caption)
        s_layout.addLayout(count_col)

        s_layout.addStretch()

        self.summary_size_label = QLabel("")
        self.summary_size_label.setStyleSheet("""
            color: #3B82F6;
            font-size: 17px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.summary_size_caption = QLabel("")
        self.summary_size_caption.setStyleSheet("""
            color: #6B7280;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.summary_size_caption.setMinimumWidth(0)

        size_col = QVBoxLayout()
        size_col.setSpacing(1)
        size_col.setContentsMargins(0, 0, 0, 0)
        size_col.addWidget(self.summary_size_label, 0, Qt.AlignmentFlag.AlignRight)
        size_col.addWidget(self.summary_size_caption, 0, Qt.AlignmentFlag.AlignRight)
        s_layout.addLayout(size_col)

        self.summary_widget.setStyleSheet("""
            QWidget#summaryWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.04);
                background: rgba(255, 255, 255, 0.02);
            }
        """)
        self.summary_widget.setVisible(False)
        layout.addWidget(self.summary_widget)

    def set_summary(self, count, size_text=None, noun="updates available", size_label=None):
        if count is None:
            self.summary_widget.setVisible(False)
            return
        self.summary_widget.setVisible(True)
        if isinstance(count, (int, float)):
            self.summary_count_label.setText(f"{int(count):,}")
        else:
            self.summary_count_label.setText(str(count))
        self.summary_count_caption.setText((noun or "").upper())
        if size_text:
            self.summary_size_label.setText(str(size_text))
            self.summary_size_caption.setText((size_label or "download size").upper())
            self.summary_size_label.setVisible(True)
            self.summary_size_caption.setVisible(True)
        else:
            self.summary_size_label.setVisible(False)
            self.summary_size_caption.setVisible(False)

    def _build_status_filter(self, layout):
        self.status_widget = QWidget()
        self.status_widget.setObjectName("statusWidget")
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setContentsMargins(16, 6, 16, 4)
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
        sort_layout.setContentsMargins(16, 6, 16, 4)
        sort_layout.setSpacing(6)

        sort_layout.addWidget(self._section_header("Sort By"))

        self.sort_btn = QPushButton()
        self.sort_btn.setObjectName("sortBtn")
        self.sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_btn.setFixedHeight(24)
        self.sort_btn.setStyleSheet(self._sort_btn_style())
        self.sort_btn.clicked.connect(self._open_sort_menu)
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
                color: #EDEDEF;
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
        self._sort_methods = [
            ("name", True, "Name A-Z"),
            ("name", False, "Name Z-A"),
            ("size", True, "Size (Smallest)"),
            ("size", False, "Size (Largest)"),
            ("version", True, "Version (Oldest)"),
            ("version", False, "Version (Latest)"),
            ("status", True, "Type A-Z"),
            ("status", False, "Type Z-A"),
            ("date", False, "Date Installed (Newest)"),
            ("date", True, "Date Installed (Oldest)"),
            ("source", True, "Source A-Z"),
            ("source", False, "Source Z-A"),
        ]
        self._sort_actions = {}
        last_field = None
        for field, asc, text in self._sort_methods:
            if last_field is not None and field != last_field:
                self.sort_menu.addSeparator()
            last_field = field
            act = self.sort_menu.addAction(text)
            act.setCheckable(True)
            act.setChecked(field == self.sort_field and asc == self.sort_asc)
            act.triggered.connect(lambda checked=False, f=field, a=asc: self._on_sort_menu(f, a))
            self._sort_actions[(field, asc)] = act

        self._update_sort_btn_text()
        self.sort_widget.setStyleSheet(self._section_stylesheet())
        self.sort_widget.setVisible(False)
        layout.addWidget(self.sort_widget)

    def _build_storage(self, layout):
        self.storage_widget = QWidget()
        self.storage_widget.setObjectName("storageWidget")
        storage_layout = QVBoxLayout(self.storage_widget)
        storage_layout.setContentsMargins(16, 8, 16, 6)
        storage_layout.setSpacing(4)

        storage_layout.addWidget(self._section_header("Storage"))

        self.disk_row = QHBoxLayout()
        self.disk_row.setSpacing(8)
        disk_label = QLabel("Root Filesystem")
        disk_label.setStyleSheet("""
            color: #EDEDEF;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.disk_used_label = QLabel("")
        self.disk_used_label.setStyleSheet("""
            color: #A7B1C2;
            font-size: 11px;
            font-weight: 500;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.disk_used_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.disk_row.addWidget(disk_label, 1)
        self.disk_row.addWidget(self.disk_used_label, 0)
        storage_layout.addLayout(self.disk_row)

        self.disk_bar = _DiskBar()
        self.disk_bar.setFixedHeight(6)
        self.disk_bar.setObjectName("diskBar")
        self._disk_percent = 0.0
        storage_layout.addWidget(self.disk_bar)

        cache_row = QHBoxLayout()
        cache_row.setSpacing(8)
        cache_label = QLabel("Package Cache")
        cache_label.setStyleSheet("""
            color: #EDEDEF;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.cache_size_label = QLabel("")
        self.cache_size_label.setStyleSheet("""
            color: #3B82F6;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
        """)
        self.clear_cache_btn = QPushButton("Clear")
        self.clear_cache_btn.setObjectName("clearCacheBtn")
        self.clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_cache_btn.setFixedHeight(22)
        self.clear_cache_btn.setStyleSheet("""
            QPushButton#clearCacheBtn {
                color: #3B82F6;
                background: rgba(59, 130, 246, 0.10);
                border: 1px solid rgba(59, 130, 246, 0.25);
                border-radius: 11px;
                font-size: 10px;
                font-weight: 600;
                padding: 0 10px;
            }
            QPushButton#clearCacheBtn:hover {
                background: rgba(59, 130, 246, 0.20);
                border-color: rgba(59, 130, 246, 0.40);
            }
        """)
        self.clear_cache_btn.clicked.connect(lambda: self.maintenance_action.emit("purge_cache"))
        cache_row.addWidget(cache_label, 1)
        cache_row.addWidget(self.cache_size_label, 0)
        cache_row.addWidget(self.clear_cache_btn, 0)
        storage_layout.addLayout(cache_row)

        self.storage_widget.setStyleSheet(self._section_stylesheet())
        self.storage_widget.setVisible(False)
        layout.addWidget(self.storage_widget)

    def set_storage(self, disk=None, cache_size=None):
        if disk and disk.get('total'):
            total = disk['total']
            used = min(disk.get('used', 0), total)
            self._disk_percent = used / total
            self.disk_used_label.setText(
                f"{_fmt_bytes(used)} / {_fmt_bytes(total)}")
            self.disk_used_label.setVisible(True)
        else:
            self._disk_percent = 0.0
            self.disk_used_label.setText("")
            self.disk_used_label.setVisible(False)
        if cache_size is not None:
            self.cache_size_label.setText(_fmt_bytes(cache_size) if cache_size else "0 B")
            self.cache_size_label.setVisible(True)
        else:
            self.cache_size_label.setText("")
            self.cache_size_label.setVisible(False)
        self.disk_bar.set_percent(self._disk_percent)

    def _build_stats(self, layout):
        self.stats_widget = QWidget()
        self.stats_widget.setObjectName("statsWidget")
        st_layout = QVBoxLayout(self.stats_widget)
        st_layout.setContentsMargins(16, 8, 16, 6)
        st_layout.setSpacing(2)

        st_layout.addWidget(self._section_header("Package Stats"))

        self._stat_labels = {}
        defs = [
            ("explicit", "Explicit"),
            ("deps", "Dependencies"),
            ("outdated", "Updates Available"),
        ]
        for key, title in defs:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(title)
            lbl.setStyleSheet("color: #A7B1C2; font-size: 11px; font-weight: 500;"
                              "background: transparent; border: none; padding: 0;")
            val = QLabel("0")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet("color: #EDEDEF; font-size: 12px; font-weight: 600;"
                              "background: transparent; border: none; padding: 0;")
            row.addWidget(lbl, 1)
            row.addWidget(val, 0)
            st_layout.addLayout(row)
            self._stat_labels[key] = val

        self.stats_widget.setStyleSheet(self._section_stylesheet())
        self.stats_widget.setVisible(False)
        layout.addWidget(self.stats_widget)

    def set_stats(self, explicit=None, deps=None, outdated=None):
        if explicit is not None:
            self._stat_labels["explicit"].setText(f"{int(explicit):,}")
        if deps is not None:
            self._stat_labels["deps"].setText(f"{int(deps):,}")
        if outdated is not None:
            label = self._stat_labels["outdated"]
            label.setText(f"{int(outdated):,}")
            label.setStyleSheet(
                "color: #60A5FA; font-size: 12px; font-weight: 700;"
                "background: transparent; border: none; padding: 0;"
            )

    def _build_quick_actions(self, layout):
        self.quick_actions_widget = QWidget()
        self.quick_actions_widget.setObjectName("quickActionsWidget")
        qa_layout = QVBoxLayout(self.quick_actions_widget)
        qa_layout.setContentsMargins(16, 8, 16, 6)
        qa_layout.setSpacing(4)

        qa_layout.addWidget(self._section_header("Quick Actions"))

        self._quick_action_rows = {}
        defs = [
            ("update_all", "Update All", "\u21BB"),
            ("clean_orphans", "Clean Orphans", "\u232B"),
        ]
        for key, title, icon in defs:
            row = _ActionRow(title, icon)
            row.clicked.connect(lambda k=key: self.maintenance_action.emit(k))
            qa_layout.addWidget(row)
            self._quick_action_rows[key] = row

        self.quick_actions_widget.setStyleSheet(self._section_stylesheet())
        self.quick_actions_widget.setVisible(False)
        layout.addWidget(self.quick_actions_widget)

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
                color: #EDEDEF;
            }
        """

    def _sort_label(self, field, asc):
        for f, a, text in self._sort_methods:
            if f == field and a == asc:
                return text
        return "Name A-Z"

    def _update_sort_btn_text(self):
        self.sort_btn.setText(f"Sort: {self._sort_label(self.sort_field, self.sort_asc)} \u25be")

    def _open_sort_menu(self):
        pos = self.sort_btn.mapToGlobal(self.sort_btn.rect().bottomLeft())
        self.sort_menu.setUpdatesEnabled(False)
        self.sort_menu.popup(pos)
        self.sort_menu.setUpdatesEnabled(True)

    def _on_sort_menu(self, field, asc):
        self.sort_field = field
        self.sort_asc = asc
        for (f, a), act in self._sort_actions.items():
            act.blockSignals(True)
            act.setChecked(f == field and a == asc)
            act.blockSignals(False)
        self._update_sort_btn_text()
        self.sort_changed.emit(field)

    def _build_actions(self, layout):
        self.actions_widget = QWidget()
        self.actions_widget.setObjectName("actionsWidget")
        actions_layout = QVBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(16, 6, 16, 4)
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
                color: #EDEDEF;
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
                color: #EDEDEF;
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
            QWidget#statusWidget, QWidget#sortWidget, QWidget#actionsWidget, QWidget#summaryWidget, QWidget#healthWidget {
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

    def set_sort(self, field, ascending=True):
        self.sort_field = field
        self.sort_asc = ascending
        for (f, a), act in self._sort_actions.items():
            act.blockSignals(True)
            act.setChecked(f == field and a == ascending)
            act.blockSignals(False)
        self._update_sort_btn_text()

    def get_sort(self):
        return self.sort_field

    def get_sort_asc(self):
        return self.sort_asc

    def get_active_statuses(self):
        return set(self._active_statuses)

    def configure_sections(self, show_status=False, show_sort=False, show_actions=False,
                           show_summary=False, show_search=True, show_counts=False,
                           show_health=False, show_storage=False, show_quick_actions=False,
                           show_stats=False):
        self.status_widget.setVisible(show_status)
        self.sort_widget.setVisible(show_sort)
        self.actions_widget.setVisible(show_actions)
        self.summary_widget.setVisible(show_summary)
        self.search_mode_widget.setVisible(show_search)
        self.health_widget.setVisible(show_health)
        self.storage_widget.setVisible(show_storage)
        self.quick_actions_widget.setVisible(show_quick_actions)
        self.stats_widget.setVisible(show_stats)
        self._balance_sections()
        if not show_counts:
            for item in self.sources.values():
                item.count_label.setVisible(False)

    def _balance_sections(self):
        """Distribute leftover vertical space evenly between visible sections."""
        layout = self.layout()
        layout_order = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is not None:
                layout_order.append((i, "widget", item.widget()))
            elif item.spacerItem() is not None:
                layout_order.append((i, "spacer", None))
        for idx, _, _ in layout_order:
            layout.setStretch(idx, 0)
        visible = [w for _, kind, w in layout_order if kind == "widget" and w.isVisible()]
        if len(visible) < 2:
            return
        for idx, kind, w in layout_order:
            if kind != "widget" or w is not visible[-1]:
                continue
            for j in range(idx + 1, layout.count()):
                item = layout.itemAt(j)
                if item.widget() is not None:
                    break
                if item.spacerItem() is not None:
                    layout.setStretch(j, 1)
                    break

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
