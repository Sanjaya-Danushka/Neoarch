"""Icon and style utilities mixin for the main window.

Provides SVG icon rendering with caching, source-specific icons,
checkbox styling, drop shadows, and related utilities.
"""

import os
import subprocess

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon, QImage
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QLabel
from PyQt6.QtSvg import QSvgRenderer

from neoarch.resources.paths import PROJECT_ROOT

_BASE_DIR = str(PROJECT_ROOT)
_DISCOVER_ICON_DIR = os.path.join(_BASE_DIR, "assets", "icons", "discover")


def _build_window_icon(icon_path: str) -> QIcon:
    try:
        icon = QIcon()
        if not os.path.exists(icon_path):
            return icon
        ext = os.path.splitext(icon_path)[1].lower()
        if ext == ".svg":
            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                for sz in (32, 64, 256):
                    pm = QPixmap(sz, sz)
                    pm.fill(Qt.GlobalColor.transparent)
                    p = QPainter(pm)
                    renderer.render(p)
                    p.end()
                    icon.addPixmap(pm)
                return icon
            return QIcon(icon_path)
        base = QPixmap(icon_path)
        if base.isNull():
            return QIcon(icon_path)
        try:
            img = base.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            w, h = img.width(), img.height()
            min_x, min_y = w, h
            max_x, max_y = -1, -1
            for y in range(h):
                for x in range(w):
                    if img.pixelColor(x, y).alpha() > 0:
                        if x < min_x: min_x = x
                        if y < min_y: min_y = y
                        if x > max_x: max_x = x
                        if y > max_y: max_y = y
            if max_x >= min_x and max_y >= min_y:
                base = base.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        except Exception:
            pass
        icon.addPixmap(base)
        return icon
    except Exception:
        return QIcon(icon_path)


class _IconsMixin:
    def get_fallback_icon(self, icon_path):
        if "discover" in icon_path:
            return "\U0001f50d"
        elif "updates" in icon_path:
            return "\u2b06\ufe0f"
        elif "installed" in icon_path:
            return "\U0001f4e6"
        elif "local" in icon_path or "bundles" in icon_path:
            return "\U0001f381"
        elif "settings" in icon_path:
            return "\u2699\ufe0f"
        elif "docker" in icon_path.lower():
            return "\U0001f433"
        else:
            return "\U0001f4e6"

    def get_source_icon(self, source, size=18):
        icon_dir = _DISCOVER_ICON_DIR
        source_colors = {
            "pacman": "#4FC3F7",
            "AUR": "#FF8A65",
            "Flatpak": "#26A69A",
            "npm": "#E53935",
            "Docker": "#2496ED",
        }
        mapping = {
            "pacman": "pacman.svg",
            "AUR": "aur.svg",
            "Flatpak": "flatpack.svg",
            "npm": "node.svg",
        }
        filename = mapping.get(source, "packagename.svg")
        icon_path = os.path.join(icon_dir, filename)
        try:
            cache = getattr(self, "_source_icon_cache", None)
            if isinstance(cache, dict):
                key = (source, int(size))
                cached = cache.get(key)
                if cached is not None and not cached.isNull():
                    return cached
        except Exception:
            pass

        try:
            pixmap = QPixmap(size, size)
            if pixmap.isNull() or not pixmap.size().isValid():
                return QIcon()

            pixmap.fill(Qt.GlobalColor.transparent)

            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                painter = QPainter(pixmap)
                if not painter.isActive():
                    return QIcon()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                renderer.render(painter, QRectF(pixmap.rect()))
                painter.end()
                icon = QIcon(pixmap)
            else:
                color = source_colors.get(source, "#8B8D97")
                pm = QPixmap(size, size)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(color))
                margin = size // 4
                p.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
                p.end()
                icon = QIcon(pm)

            try:
                if isinstance(getattr(self, "_source_icon_cache", None), dict):
                    self._source_icon_cache[(source, int(size))] = icon
            except Exception:
                pass
            return icon
        except Exception:
            return QIcon()

    def get_svg_icon(self, icon_path, size=18):
        try:
            cache = getattr(self, "_icon_cache", None)
            if isinstance(cache, dict):
                key = (os.path.abspath(icon_path), int(size))
                cached = cache.get(key)
                if cached is not None and not cached.isNull():
                    return cached
        except Exception:
            pass

        try:
            ext = os.path.splitext(icon_path)[1].lower()
            if ext != ".svg":
                icon = QIcon(icon_path)
            else:
                pixmap = QPixmap(size, size)
                if pixmap.isNull() or not pixmap.size().isValid():
                    return QIcon()

                pixmap.fill(Qt.GlobalColor.transparent)

                painter = QPainter(pixmap)
                if not painter.isActive():
                    return QIcon()

                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

                renderer = QSvgRenderer(icon_path)
                if renderer.isValid():
                    renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    icon = QIcon(pixmap)
                else:
                    painter.end()
                    icon = QIcon(icon_path)

            try:
                if isinstance(getattr(self, "_icon_cache", None), dict):
                    self._icon_cache[(os.path.abspath(icon_path), int(size))] = icon
            except Exception:
                pass
            return icon
        except Exception:
            return QIcon()

    def get_source_accent(self, source):
        m = {
            "pacman": "#4FC3F7",
            "AUR": "#FF8A65",
            "Flatpak": "#26A69A",
            "npm": "#E53935",
        }
        return m.get(source, "#00BFAE")

    def apply_checkbox_accent(self, checkbox, source):
        hex_color = self.get_source_accent(source)
        c = QColor(hex_color)
        r, g, b = c.red(), c.green(), c.blue()
        checkbox.setStyleSheet(
            f"""
            QCheckBox#tableCheckbox {{
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox#tableCheckbox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid rgba({r}, {g}, {b}, 0.35);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 42, 48, 0.9),
                    stop:1 rgba(28, 30, 36, 0.9));
            }}
            QCheckBox#tableCheckbox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {hex_color},
                    stop:1 rgba({r//2}, {g//2}, {b//2}, 1));
                border: 2px solid {hex_color};
            }}
            QCheckBox#tableCheckbox::indicator:hover {{
                border-color: rgba({r}, {g}, {b}, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(50, 52, 58, 0.9),
                    stop:1 rgba(34, 36, 42, 0.9));
            }}
            """
        )

    def _apply_neumorphic_shadow(self, widget):
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(18)
        s.setColor(QColor(0, 0, 0, 160))
        s.setOffset(3, 4)
        widget.setGraphicsEffect(s)

    def ensure_flathub_user_remote(self):
        try:
            result = subprocess.run([
                "flatpak", "--user", "remotes"
            ], capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or "flathub" not in (result.stdout or ""):
                subprocess.run([
                    "flatpak", "--user", "remote-add", "--if-not-exists",
                    "flathub", "https://flathub.org/repo/flathub.flatpakrepo"
                ], capture_output=True, text=True, timeout=30)
        except Exception:
            pass
        try:
            self._flathub_checked = True
        except Exception:
            pass
