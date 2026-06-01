"""Custom frameless title bar for NeoArch main window."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from neoarch.resources.paths import PROJECT_ROOT

_BASE_DIR = str(PROJECT_ROOT)


def _get_brand_icon_path():
    base_dir = _BASE_DIR
    candidates = [
        os.path.join(base_dir, "assets", "icons", "icon.png"),
        os.path.join(base_dir, "assets", "icons", "NeoarchLogo.svg"),
        os.path.join(base_dir, "assets", "icons", "brand", "neoarch.svg"),
        os.path.join(base_dir, "assets", "icons", "brand", "neoarch.png"),
        os.path.join(base_dir, "assets", "icons", "discover", "logo.svg"),
        os.path.join(base_dir, "assets", "icons", "discover", "logo1.svg"),
        os.path.join(base_dir, "assets", "icons", "discover", "logo1.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]


class _TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appTitleBar")
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(6)

        icon_label = QLabel()
        icon_label.setFixedSize(18, 18)
        icon_path = _get_brand_icon_path()
        if os.path.exists(icon_path):
            pm = QPixmap(icon_path).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pm)
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(icon_label)

        title = QLabel("NeoArch")
        title.setObjectName("titleBarLabel")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)

        layout.addStretch()

        self.min_btn = self._create_traffic_light("\u2500", "titleBarMinBtn")
        self.max_btn = self._create_traffic_light("\u25a1", "titleBarMaxBtn")
        self.close_btn = self._create_traffic_light("\u2715", "titleBarCloseBtn")

        self.min_btn.clicked.connect(self._minimize)
        self.max_btn.clicked.connect(self._maximize)
        self.close_btn.clicked.connect(self._close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    def _create_traffic_light(self, symbol, obj_name):
        btn = QPushButton(symbol)
        btn.setObjectName(obj_name)
        btn.setFixedSize(14, 14)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _minimize(self):
        self.window().showMinimized()

    def _maximize(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    def _close(self):
        self.window().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.window().windowHandle()
            if w:
                w.startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.window()
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
