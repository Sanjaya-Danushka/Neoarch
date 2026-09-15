"""Appearance settings — theme selector with live preview."""

from typing import Any

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider,
)
from PyQt6.QtSvg import QSvgRenderer

from neoarch.frontend.tokens import Colors, Fonts, Radii, QSS
from neoarch.backend.services.i18n import _
from neoarch.frontend.themes import THEMES
from neoarch.frontend.components.toggle_switch import ToggleSwitch

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_PALETTE = (
    '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688'
    ' 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668'
    'h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>'
    '<circle cx="13.5" cy="6.5" r=".75"/><circle cx="17.5" cy="10.5" r=".75"/>'
    '<circle cx="8.5" cy="7.5" r=".75"/><circle cx="6.5" cy="12.5" r=".75"/>'
)
_ICON_MONITOR = (
    '<rect x="2" y="3" width="20" height="14" rx="2"/>'
    '<line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
)

_SLIDER_QSS = f"""
    QSlider {{
        background: transparent;
        height: 22px;
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: rgba(255, 255, 255, 0.12);
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {Colors.ACCENT};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
        background: #FFFFFF;
        border: none;
    }}
    QSlider::handle:horizontal:hover {{
        background: #D9F2EF;
    }}
    QSlider::handle:horizontal:pressed {{
        background: #C6E7E3;
    }}
"""


class _Swatch(QWidget):
    """28x28 rounded color chip: the theme palette drawn as slim strips."""

    def __init__(self, theme_data, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._c = theme_data["colors"]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 8
        outer = QPainterPath()
        outer.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._c["BG"]))
        p.drawPath(outer)

        strips = [
            (QColor(self._c["ACCENT"]), 4),
            (QColor(self._c["SURFACE"]), 4),
            (QColor(self._c["TEXT"]), 3),
        ]
        y = 5
        for color, h in strips:
            p.setBrush(color)
            p.drawRoundedRect(QRectF(8, y, 12, h), 2, 2)
            y += h + 3

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(self._c["BORDER"]), 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                          radius, radius)
        p.end()


class _SelectionDot(QFrame):
    """Small teal dot shown on the active theme row."""

    def __init__(self, active, disabled=False, parent=None):
        super().__init__(parent)
        self._active = active
        self._disabled = disabled
        self.setFixedSize(16, 16)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._disabled:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 0))
            return
        if self._active:
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
            p.setBrush(QColor(Colors.ACCENT))
        else:
            p.setPen(QPen(QColor(Colors.BORDER), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(1.5, 1.5, 13, 13))
        p.end()


class _ThemeRow(QFrame):
    """One theme as a settings row: swatch + name/desc + select dot."""

    def __init__(self, theme_id, theme_data, selected, on_select,
                 disabled=False, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self._on_select = on_select
        self._disabled = disabled
        if not disabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setStyleSheet(
                "QFrame { background: transparent; border: none;"
                " border-radius: 10px; }")
        else:
            self.setStyleSheet(
                "QFrame { background: transparent; border: none;"
                " border-radius: 10px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(_Swatch(theme_data))

        texts = QVBoxLayout()
        texts.setSpacing(2)
        name = QLabel(theme_data["name"])
        if disabled:
            name_color = Colors.TEXT_3
        elif selected:
            name_color = Colors.ACCENT
        else:
            name_color = Colors.TEXT
        name.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {name_color}; border: none; background: transparent;")
        texts.addWidget(name)

        desc = QLabel(theme_data["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"font-size: {Fonts.SM};"
            f" color: {Colors.TEXT_3 if disabled else Colors.TEXT_2};"
            " border: none; background: transparent;")
        texts.addWidget(desc)
        layout.addLayout(texts, 1)

        if disabled:
            badge = QLabel(_("Coming soon"))
            badge.setStyleSheet(
                f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI}; border: none; background: transparent;")
            layout.addWidget(badge)
            layout.addWidget(_SelectionDot(False, disabled=True))
        else:
            layout.addWidget(_SelectionDot(selected))

    def _set_hover(self, hovered):
        if self._disabled:
            return
        bg = "rgba(255, 255, 255, 0.05)" if hovered else "transparent"
        border = "rgba(255, 255, 255, 0.10)" if hovered else "transparent"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border};"
            " border-radius: 10px; }")

    def enterEvent(self, event):
        self._set_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_hover(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self._disabled:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_select(self.theme_id)


class AppearanceSettingsWidget(QWidget):
    """Appearance settings with theme selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self._cards = {}
        self.setup_ui()

    # ── building blocks (About-page pattern) ────────────────────────

    @staticmethod
    def _icon_pixmap(svg_body, size=14, color="#EDEDEF"):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
            ' fill="none" stroke="{c}" stroke-width="2"'
            ' stroke-linecap="round" stroke-linejoin="round">{b}</svg>'
        ).format(c=color, b=svg_body)
        renderer = QSvgRenderer(svg.encode("utf-8"))
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        if renderer.isValid():
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
        return pm

    def _make_card(self, title_text, svg_body=None):
        """A flat settings card, exactly like the General tab / About page."""
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(QSS.CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 16)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        if svg_body is not None:
            badge = QLabel()
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background: {Colors.SURFACE_2}; border: none;"
                f" border-radius: {Radii.SM}px;")
            badge.setPixmap(self._icon_pixmap(svg_body, 15))
            header.addWidget(badge)
        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)

        pad = QWidget()
        pad.setStyleSheet("background: transparent;")
        pad.setFixedHeight(4)
        card_layout.addWidget(pad)
        return card, card_layout

    @staticmethod
    def _row(title_text, subtitle_text=None, control=None):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setSpacing(16)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)

        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        texts.addWidget(title)

        if subtitle_text:
            subtitle = QLabel(subtitle_text)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.TEXT_2};"
                " border: none; background: transparent;")
            texts.addWidget(subtitle)

        row.addLayout(texts, 1)
        if control is not None:
            row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row_widget

    @staticmethod
    def _sep():
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(
            f"background: {Colors.BORDER}; border: none; margin: 4px 0;")
        return line

    # ── UI ─────────────────────────────────────────────────────────

    def setup_ui(self):
        title = QLabel(_("Appearance"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Choose a theme for NeoArch. Changes apply instantly."))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent;")
        self.layout.addWidget(subtitle)

        # ── Themes ──
        theme_card, theme_layout = self._make_card(_("Themes"), _ICON_PALETTE)

        current = getattr(self.app, '_theme_manager', None)
        current_id = current.current_id if current else "dark"

        theme_ids = list(THEMES.keys())
        for i, theme_id in enumerate(theme_ids):
            if i > 0:
                theme_layout.addWidget(self._sep())
            option = _ThemeRow(
                theme_id, THEMES[theme_id],
                selected=(theme_id == current_id),
                on_select=self._apply_theme,
                disabled=THEMES[theme_id].get("coming_soon", False),
            )
            self._cards[theme_id] = option
            theme_layout.addWidget(option)

        self.layout.addWidget(theme_card)

        # ── Window frame ──
        window_card, window_layout = self._make_card(_("Window frame"), _ICON_MONITOR)

        self._glow_toggle = ToggleSwitch(self, _("Glow border around the window"))
        self._glow_toggle.setChecked(
            bool(self.app.settings.get('window_glow', False)), animate=False)
        self._glow_toggle.toggled.connect(self._on_glow_toggled)
        window_layout.addWidget(self._row(
            _("Glow border around the window"),
            _("Decorative teal rim on the translucent window frame."),
            control=self._glow_toggle))
        window_layout.addWidget(self._sep())

        # Radius slider
        slider_box = QWidget()
        slider_box.setStyleSheet("background: transparent;")
        slider_box.setFixedWidth(220)
        slider_lay = QHBoxLayout(slider_box)
        slider_lay.setContentsMargins(0, 0, 0, 0)
        slider_lay.setSpacing(10)
        self._radius_slider = QSlider(Qt.Orientation.Horizontal)
        self._radius_slider.setRange(4, 14)
        self._radius_slider.setSingleStep(2)
        self._radius_slider.setPageStep(2)
        self._radius_slider.setStyleSheet(_SLIDER_QSS)
        self._radius_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        slider_lay.addWidget(self._radius_slider, 1)
        self._radius_value = QLabel()
        self._radius_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._radius_value.setFixedWidth(40)
        self._radius_value.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.SEMI}; border: none; background: transparent;")
        slider_lay.addWidget(self._radius_value)

        current_radius = self.app.settings.get('window_radius', 8)
        self._radius_slider.setValue(int(current_radius) if current_radius else 8)
        self._radius_slider.valueChanged.connect(self._on_radius_changed)
        self._radius_slider.sliderReleased.connect(self._on_radius_released)
        self._update_radius_label()

        window_layout.addWidget(self._row(
            _("Window corner radius"),
            _("Rounded corners on the translucent window frame."),
            control=slider_box))

        self.layout.addWidget(window_card)

        self.layout.addStretch()

    def _update_radius_label(self):
        self._radius_value.setText(_("%(n)d px") % {"n": self._radius_slider.value()})

    def _on_glow_toggled(self, checked):
        self.app.update_setting('window_glow', bool(checked))
        self.app.apply_window_effects()

    def _on_radius_changed(self, value):
        self._update_radius_label()
        self.app.update_setting('window_radius', int(value))

    def _on_radius_released(self):
        self.app.apply_window_effects()

    def _apply_theme(self, theme_id):
        manager = getattr(self.app, '_theme_manager', None)
        if manager:
            manager.apply_theme(theme_id)
            # Rebuild settings UI to reflect new theme
            self.app.build_settings_ui()