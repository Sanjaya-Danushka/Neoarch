import os
import platform
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PyQt6.QtSvg import QSvgRenderer


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About NeoArch")
        self.setModal(True)
        self.setMinimumSize(880, 560)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "about.svg")
        icon_path = os.path.normpath(icon_path)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        card = QFrame()
        card.setObjectName("aboutCard")
        card_l = QGridLayout(card)
        card_l.setContentsMargins(28, 28, 28, 28)
        card_l.setHorizontalSpacing(36)
        card_l.setVerticalSpacing(20)

        left = self._make_left_column()
        right = self._make_right_column()
        divider = QFrame()
        divider.setObjectName("vsep")
        divider.setFixedWidth(1)
        card_l.addWidget(left, 0, 0)
        card_l.addWidget(divider, 0, 1)
        card_l.addWidget(right, 0, 2)
        card_l.setColumnStretch(0, 1)
        card_l.setColumnStretch(2, 1)

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(28)
        effect.setOffset(0, 6)
        effect.setColor(QColor(0, 0, 0, 180))
        card.setGraphicsEffect(effect)

        root.addWidget(card)

        btns = QHBoxLayout()
        btns.addStretch()
        ok_btn = QPushButton("Close")
        ok_btn.clicked.connect(self.accept)
        btns.addWidget(ok_btn)
        root.addLayout(btns)

        self.setStyleSheet(self._stylesheet())

    def _make_left_column(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        about_h = QLabel("About")
        about_h.setObjectName("aboutTitle")
        v.addWidget(about_h)

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        avatar_wrap = QFrame()
        avatar_wrap.setObjectName("avatarWrap")
        avatar_wrap.setFixedSize(116, 116)
        avatar_l = QVBoxLayout(avatar_wrap)
        avatar_l.setContentsMargins(10, 10, 10, 10)

        avatar = QLabel()
        avatar.setObjectName("avatarImg")
        avatar.setFixedSize(96, 96)
        rp = self._render_logo(96)
        if not rp.isNull():
            avatar.setPixmap(rp)
        header_row.addWidget(avatar_wrap, 0, Qt.AlignmentFlag.AlignTop)
        avatar_l.addWidget(avatar, 0, Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        project_label = QLabel("Whale Lab Presents")
        project_label.setObjectName("projectLabel")
        text_col.addWidget(project_label)

        proj = QLabel("NeoArch")
        proj.setObjectName("projectName")
        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)
        proj_row.addWidget(proj)
        beta_chip = QLabel("BETA")
        beta_chip.setObjectName("betaChip")
        proj_row.addWidget(beta_chip)
        proj_row.addStretch()
        text_col.addLayout(proj_row)

        version = QLabel("Version: 1.0 (Beta)")
        version.setObjectName("versionLabel")
        text_col.addWidget(version)

        blurb = QLabel(
            "The all‑in‑one package hub for Arch Linux. Discover, install, update, and manage across pacman, AUR, Flatpak, and npm."
        )
        blurb.setWordWrap(True)
        blurb.setObjectName("desc")
        text_col.addWidget(blurb)
        text_col.addStretch()

        header_row.addLayout(text_col)
        v.addLayout(header_row)

        return w

    def _round_pixmap(self, path: str, size: int) -> QPixmap:
        try:
            pm = QPixmap(path)
            if pm.isNull():
                return QPixmap()
            pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            out = QPixmap(size, size)
            out.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip = QPainterPath()
            clip.addEllipse(0, 0, size, size)
            painter.setClipPath(clip)
            painter.fillPath(clip, QColor("white"))
            painter.drawPixmap(0, 0, pm)
            painter.end()
            return out
        except Exception:
            return QPixmap()

    def _render_logo(self, size: int) -> QPixmap:
        try:
            base = os.path.dirname(__file__)
            candidates = [
                os.path.normpath(os.path.join(base, "..", "assets", "icons", "NeoarchLogo.svg")),
                os.path.normpath(os.path.join(base, "..", "assets", "icons", "discover", "logo1.png")),
                os.path.normpath(os.path.join(base, "..", "assets", "icons", "discover.svg")),
                os.path.normpath(os.path.join(base, "..", "assets", "icons", "about.svg")),
                os.path.normpath(os.path.join(base, "..", "assets", "about", "user.jpg")),
            ]
            logo_pm = QPixmap()
            used_svg = False
            for p in candidates:
                if os.path.exists(p):
                    if p.lower().endswith(".svg"):
                        renderer = QSvgRenderer(p)
                        if renderer.isValid():
                            used_svg = True
                            logo_size = int(size * 0.78)
                            tmp = QPixmap(logo_size, logo_size)
                            tmp.fill(Qt.GlobalColor.transparent)
                            painter = QPainter(tmp)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                            renderer.render(painter, QRectF(0, 0, logo_size, logo_size))
                            painter.end()
                            logo_pm = tmp
                            break
                    else:
                        pm = QPixmap(p)
                        if not pm.isNull():
                            logo_size = int(size * 0.78)
                            logo_pm = pm.scaled(logo_size, logo_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            break

            if logo_pm.isNull():
                return QPixmap()

            out = QPixmap(size, size)
            out.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            circle = QPainterPath()
            circle.addEllipse(0, 0, size, size)
            painter.fillPath(circle, QColor("white"))
            pen = QPen(QColor(220, 225, 230, 200))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawEllipse(0, 0, size-1, size-1)
            x = (size - logo_pm.width()) // 2
            y = (size - logo_pm.height()) // 2
            painter.drawPixmap(x, y, logo_pm)
            painter.end()
            return out
        except Exception:
            return QPixmap()

    def _make_right_column(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        sponsor_t = QLabel("Support NeoArch")
        sponsor_t.setObjectName("sectionTitle")
        v.addWidget(sponsor_t)

        qr_row = QHBoxLayout()
        qr_row.setSpacing(16)
        qr_tile = QFrame()
        qr_tile.setObjectName("qrTile")
        qr_tile_l = QVBoxLayout(qr_tile)
        qr_tile_l.setContentsMargins(12, 12, 12, 12)
        qr_tile_l.setSpacing(0)
        qr_label = QLabel()
        qr_label.setObjectName("qrImg")
        qr_label.setMinimumSize(200, 200)
        qr_label.setScaledContents(False)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_path = os.path.join(os.path.dirname(__file__), "..", "assets", "about", "sponsor.png")
        qr_path = os.path.normpath(qr_path)
        if os.path.exists(qr_path):
            pm = QPixmap(qr_path)
            if not pm.isNull():
                target = 240
                pm = pm.scaled(target, target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                qr_label.setPixmap(pm)
                qr_label.setFixedSize(pm.size())
        qr_tile_l.addWidget(qr_label, 0, Qt.AlignmentFlag.AlignCenter)
        qr_row.addWidget(qr_tile, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        sponsor_page = QLabel("Buy me a coffee")
        sponsor_page.setObjectName("supportTitle")
        text_col.addWidget(sponsor_page)
        help_text = QLabel("We don't have sponsors yet. If NeoArch helps you, kindly buy me a coffee by scanning the QR. Thank you!")
        help_text.setWordWrap(True)
        help_text.setObjectName("muted")
        text_col.addWidget(help_text)
        qr_row.addLayout(text_col)
        qr_row.addStretch()
        v.addLayout(qr_row)

        dev_t = QLabel("Developed by")
        dev_t.setObjectName("sectionTitle")
        v.addWidget(dev_t)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(18)

        dev_col = QVBoxLayout()
        dev_name = QLabel("Sanjaya Danushka")
        dev_name.setObjectName("devName")
        dev_col.addWidget(dev_name)

        links = QLabel(
            '<a href="https://github.com/Sanjaya-Danushka">GitHub</a>  ·  '
            '<a href="https://www.linkedin.com/in/sanjaya-danushka-4484292a0">LinkedIn</a>  ·  '
            '<a href="https://www.facebook.com/sanjaya.danushka.186">Facebook</a>'
        )
        links.setTextFormat(Qt.TextFormat.RichText)
        links.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        links.setOpenExternalLinks(True)
        links.setObjectName("links")
        dev_col.addWidget(links)
        dev_row.addLayout(dev_col)
        dev_row.addStretch()
        v.addLayout(dev_row)

        lab = QLabel("NeoArch • Developed by Whale Lab")
        lab.setObjectName("footerTag")
        v.addWidget(lab)
        v.addStretch()

        return w

    def _stylesheet(self) -> str:
        return (
            "AboutDialog {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "    stop:0 #0F1218, stop:1 #0B0E14);"
            "}"
            "QLabel#aboutTitle { color: #EAF6F5; font-size: 22px; font-weight: 700; margin-bottom: 4px; }"
            "QFrame#aboutCard {"
            "  background: rgba(20,22,28,0.92);"
            "  border: 1px solid rgba(0, 191, 174, 0.18);"
            "  border-radius: 22px;"
            "}"
            "QLabel#projectLabel { color: #AEB4C2; font-size: 12px; }"
            "QLabel#projectName { color: #F6F7FB; font-size: 18px; font-weight: 600; }"
            "QLabel#versionLabel { color: #9CA6B4; }"
            "QLabel#muted { color: #9CA6B4; }"
            "QLabel#desc { color: #C9D1D9; }"
            "QLabel#sectionTitle { color: #E8F1F0; font-weight: 600; }"
            "QLabel#supportTitle { color: #F6F7FB; font-size: 15px; font-weight: 600; }"
            "QLabel#devName { color: #F6F7FB; font-size: 15px; font-weight: 600; }"
            "QLabel#links { color: #8EDBD4; }"
            "QLabel#footerTag { color: #AEB4C2; margin-top: 8px; }"
            "QLabel#betaChip { color: #FFD369; background-color: rgba(255,193,7,0.14); border: 1px solid rgba(255,193,7,0.42); border-radius: 10px; padding: 2px 8px; font-weight: 700; letter-spacing: 0.6px; }"
            "QFrame#avatarWrap {"
            "  background: qradialgradient(cx:0.5, cy:0.5, radius:0.7,"
            "    stop:0 rgba(0,191,174,0.55), stop:0.6 rgba(0,191,174,0.18), stop:1 rgba(0,191,174,0.04));"
            "  border-radius: 58px;"
            "}"
            "QFrame#vsep { background-color: rgba(255,255,255,0.08); min-width:1px; max-width:1px; }"
            "QLabel#avatarImg { border-radius: 48px; }"
            "QFrame#qrTile { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; }"
            "QLabel#qrImg { background: transparent; }"
        )
