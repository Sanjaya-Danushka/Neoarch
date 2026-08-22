"""
About page for NeoArch — full-page view with left sidebar navigation,
mirroring the Settings page design language.
"""

import os
import subprocess
import platform as _platform

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QApplication, QStackedWidget,
)

from neoarch.frontend.tokens import Colors, Fonts, Radii, QSS
from neoarch.resources.paths import (
    ASSETS_DIR, APP_VERSION, APP_EDITION, PROJECT_ROOT,
)

__all__ = ["AboutTab"]

_REPO_URL = "https://github.com/Sanjaya-Danushka/Neoarch"
_SPONSORS_URL = "https://github.com/sponsors/Sanjaya-Danushka"
_BUYMEACOFFEE_URL = "https://www.buymeacoffee.com/sanjayadanushka"
_WEBSITE_URL = "https://neoarch.netlify.app"
_AUR_URL = "https://aur.archlinux.org/packages/neoarch-git"

_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _open_url(url):
    import webbrowser
    if not isinstance(url, str):
        return
    webbrowser.open(url)


def _run_cmd(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _git_log_count():
    c = _run_cmd(["git", "-C", str(PROJECT_ROOT), "rev-list", "--count", "HEAD"])
    return int(c) if c else 0


def _git_tags():
    out = _run_cmd(["git", "-C", str(PROJECT_ROOT), "tag", "-l",
                     "--sort=-version:refname"])
    if not out:
        return []
    return [t.strip() for t in out.splitlines() if t.strip()]


def _git_recent_log(n=10):
    out = _run_cmd([
        "git", "-C", str(PROJECT_ROOT), "log",
        f"-{n}", "--format=%h|%s|%an|%ad", "--date=short"
    ])
    if not out:
        return []
    result = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            result.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
            })
    return result


# ── Shared helpers (match Settings page pattern) ────────────────────

def _page_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
        f" color: {Colors.TEXT}; letter-spacing: -0.5px;"
        " background: transparent; border: none;")
    return lbl


def _page_subtitle(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
        " background: transparent; border: none;")
    return lbl


def _card():
    card = QFrame()
    card.setStyleSheet(QSS.CARD)
    return card


def _card_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
        f" color: {Colors.TEXT}; border: none; background: transparent;")
    return lbl


def _card_body(text):
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
        " background: transparent; border: none;")
    return lbl


def _accent_btn(text, on_click):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.06);
            color: {Colors.TEXT};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 8px 18px;
            font-size: {Fonts.BASE};
            font-weight: {Fonts.MEDIUM};
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.1);
            border-color: rgba(0, 191, 174, 0.4);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.14);
        }}
    """)
    btn.clicked.connect(lambda checked=False: on_click())
    return btn


def _secondary_btn(text, on_click):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {Colors.TEXT_2};
            border: 1px solid {Colors.BORDER};
            border-radius: 10px;
            padding: 8px 18px;
            font-size: {Fonts.BASE};
            font-weight: {Fonts.MEDIUM};
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.08);
            border-color: {Colors.BORDER_HOVER};
            color: {Colors.TEXT};
        }}
    """)
    btn.clicked.connect(lambda checked=False: on_click())
    return btn


def _link_btn(text, on_click):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {Colors.ACCENT};
            border: none;
            font-size: {Fonts.SM};
            font-weight: {Fonts.SEMI};
            padding: 0;
        }}
        QPushButton:hover {{ color: {Colors.ACCENT_HOVER}; }}
    """)
    btn.clicked.connect(lambda checked=False: on_click())
    return btn


def _scroll_area():
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
    return scroll


def _sep():
    """Thin horizontal separator line."""
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {Colors.BORDER}; border: none;")
    return f


def _mac_icon_pixmap(svg_body, size=16, color="#FFFFFF"):
    """Render an inline stroke-SVG as a monochrome SF-Symbols-style pixmap."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
        ' fill="none" stroke="{c}" stroke-width="2"'
        ' stroke-linecap="round" stroke-linejoin="round">{b}</svg>'
    ).format(c=color, b=svg_body)
    r = QSvgRenderer(svg.encode("utf-8"))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    if r.isValid():
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r.render(p, QRectF(0, 0, size, size))
        p.end()
    return pm


def _icon_title_row(svg_body, title):
    """Card title row with a white macOS-style line-icon badge."""
    row = QHBoxLayout()
    row.setSpacing(10)

    badge = QLabel()
    badge.setFixedSize(28, 28)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"background: {Colors.SURFACE_2}; border: none;"
        f"border-radius: {Radii.SM}px;")
    badge.setPixmap(_mac_icon_pixmap(svg_body, 15))
    row.addWidget(badge)

    lbl = _card_title(title)
    row.addWidget(lbl)
    row.addStretch()
    return row


# White macOS-style section icons (stroke paths, 24x24 viewBox)
_ICON_SPARKLES = (
    '<path d="M12 4l1.7 4.6a2 2 0 0 0 1.2 1.2L19.5 11.5l-4.6 1.7'
    'a2 2 0 0 0-1.2 1.2L12 19l-1.7-4.6a2 2 0 0 0-1.2-1.2L4.5 11.5'
    'l4.6-1.7a2 2 0 0 0 1.2-1.2L12 4z"/>'
    '<path d="M18.5 3v3"/><path d="M17 4.5h3"/>'
    '<path d="M5.5 17v3"/><path d="M4 18.5h3"/>'
)
_ICON_WRENCH = (
    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0'
    'l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3'
    'l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
)
_ICON_ARROW_UP_CIRCLE = (
    '<circle cx="12" cy="12" r="9"/>'
    '<path d="m8.5 12.5 3.5-3.5 3.5 3.5"/><path d="M12 15V9"/>'
)


# ── Tab: Overview ──────────────────────────────────────────────────

class _OverviewTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        layout.addWidget(_page_title("Overview"))
        layout.addWidget(_page_subtitle(
            "Version information, links, and system details"))

        scroll = _scroll_area()
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(20)

        # Hero card
        hero = _card()
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 24, 24, 24)
        hl.setSpacing(16)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(16)
        logo_lbl = QLabel()
        pm = QPixmap()
        for logo_name in (
            os.path.join("icons", "app", "logo.png"),
            os.path.join("icons", "app", "icon.png"),
            os.path.join("icons", "app.png"),
            os.path.join("icons", "NeoarchLogo.svg"),
        ):
            logo_path = os.path.join(str(ASSETS_DIR), logo_name)
            if os.path.exists(logo_path):
                candidate = QPixmap(logo_path)
                if not candidate.isNull():
                    pm = candidate
                    break
        if not pm.isNull():
            logo_lbl.setPixmap(pm.scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            logo_lbl.setText("NA")
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_lbl.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: 28px; font-weight: 800;"
                "background: transparent; border: none;")
        logo_lbl.setFixedSize(64, 64)
        logo_row.addWidget(logo_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        name_lbl = QLabel("NeoArch")
        name_lbl.setStyleSheet(
            f"font-size: {Fonts.HERO}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        title_col.addWidget(name_lbl)
        ed_lbl = QLabel(f"{APP_EDITION} Edition")
        ed_lbl.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
            " background: transparent; border: none;")
        title_col.addWidget(ed_lbl)
        logo_row.addLayout(title_col, 1)
        hl.addLayout(logo_row)

        desc = QLabel(
            "A modern graphical package manager for Arch Linux — search, install, "
            "and manage packages from pacman, AUR, Flatpak, and npm in one place. "
            "Create bundles, manage Git projects, run Docker containers, and sync "
            "your setup across devices."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " background: transparent; border: none;")
        hl.addWidget(desc)

        links_row = QHBoxLayout()
        links_row.setSpacing(8)
        for label, url in [
            ("\u2197 Website", _WEBSITE_URL),
            ("\u2197 Repository", _REPO_URL),
            ("\u2197 AUR Package", _AUR_URL),
        ]:
            links_row.addWidget(_accent_btn(label, lambda u=url: _open_url(u)))
        links_row.addStretch()
        hl.addLayout(links_row)

        cl.addWidget(hero)

        # Info cards grid
        grid = QGridLayout()
        grid.setSpacing(12)
        cards_data = [
            ("Version", APP_VERSION, f"{APP_EDITION} Edition", Colors.TEXT),
            ("License", "MIT", "Open Source", Colors.GREEN),
            ("Platform", f"{_platform.system()} {_platform.release()}",
             _platform.machine(), Colors.TEXT),
            ("Python", _platform.python_version(), "Runtime", Colors.TEXT),
            ("Qt", "6 (PyQt6)", "GUI Framework", Colors.TEXT),
            ("Commits", str(_git_log_count()), "Total commits", Colors.TEXT),
        ]
        for i, (title, value, sub, color) in enumerate(cards_data):
            card = _card()
            cl_inner = QVBoxLayout(card)
            cl_inner.setContentsMargins(20, 18, 20, 20)
            cl_inner.setSpacing(4)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(
                f"font-size: {Fonts.SM}; font-weight: {Fonts.MEDIUM};"
                f" color: {Colors.TEXT_2}; background: transparent; border: none;")
            cl_inner.addWidget(t_lbl)
            v_lbl = QLabel(str(value))
            v_lbl.setWordWrap(True)
            v_lbl.setStyleSheet(
                f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.BOLD};"
                f" color: {color}; background: transparent; border: none;")
            cl_inner.addWidget(v_lbl)
            s_lbl = QLabel(sub)
            s_lbl.setStyleSheet(
                f"font-size: {Fonts.XS}; color: {Colors.TEXT_3};"
                " background: transparent; border: none;")
            cl_inner.addWidget(s_lbl)
            grid.addWidget(card, i // 3, i % 3)
        cl.addLayout(grid)

        # Developer attribution
        dev_card = _card()
        dv = QVBoxLayout(dev_card)
        dv.setContentsMargins(20, 14, 20, 14)
        dv.setSpacing(8)

        quote = QLabel(
            "\u201CUnified system design is not about hiding complex "
            "settings; it is about providing power users with reliable "
            "tools that simplify technical friction.\u201D"
        )
        quote.setWordWrap(True)
        quote.setStyleSheet(
            f"font-size: {Fonts.SM}; font-weight: {Fonts.MEDIUM};"
            f" color: {Colors.TEXT_2}; font-style: italic;"
            " background: transparent; border: none;")
        dv.addWidget(quote)

        dv.addWidget(_sep())

        author_row = QHBoxLayout()
        author_row.setSpacing(10)

        avatar = QLabel()
        avatar.setFixedSize(32, 32)
        avatar.setStyleSheet(
            f"border-radius: 16px; border: none;"
            f" background: {Colors.SURFACE_2};")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dev_img_path = os.path.join(
            str(ASSETS_DIR), "icons", "app", "developer.png")
        if os.path.exists(dev_img_path):
            dev_pm = QPixmap(dev_img_path)
            if not dev_pm.isNull():
                scaled = dev_pm.scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                avatar.setPixmap(scaled)
            else:
                avatar.setText("SD")
                avatar.setStyleSheet(
                    f"border-radius: 16px; border: none;"
                    f" background: {Colors.ACCENT_SOFT};"
                    f" color: {Colors.ACCENT}; font-size: {Fonts.SM};"
                    f" font-weight: {Fonts.BOLD};")
        else:
            avatar.setText("SD")
            avatar.setStyleSheet(
                f"border-radius: 16px; border: none;"
                f" background: {Colors.ACCENT_SOFT};"
                f" color: {Colors.ACCENT}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.BOLD};")
        author_row.addWidget(avatar)

        author_info = QVBoxLayout()
        author_info.setSpacing(1)
        author_name = QLabel("Sanjaya Danushka")
        author_name.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        author_info.addWidget(author_name)
        author_role = QLabel("NeoArch Core Architectural Manifesto")
        author_role.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.TEXT_3};"
            " background: transparent; border: none;")
        author_info.addWidget(author_role)
        author_row.addLayout(author_info, 1)

        author_row.addStretch()
        dv.addLayout(author_row)

        cl.addWidget(dev_card)

        cl.addStretch(1)
        scroll.setWidget(content)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        layout.addLayout(outer, 1)


# ── Tab: Release Notes ─────────────────────────────────────────────

class _ReleaseNotesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        layout.addWidget(_page_title("Release Notes"))
        layout.addWidget(_page_subtitle("Version history and changes"))

        scroll = _scroll_area()
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(20)

        # Current version card
        ver_card = _card()
        vl = QVBoxLayout(ver_card)
        vl.setContentsMargins(20, 18, 20, 20)
        vl.addWidget(_card_title(f"Current Version: {APP_VERSION}"))
        cl.addWidget(ver_card)

        recent = _git_recent_log(20)
        if recent:
            features = [r for r in recent if any(k in r["message"].lower()
                        for k in ["add", "feat", "new", "redesign", "create"])]
            fixes = [r for r in recent if any(k in r["message"].lower()
                     for k in ["fix", "bug", "patch", "crash"])]
            improvements = [r for r in recent if any(k in r["message"].lower()
                           for k in ["improve", "update", "refactor",
                                     "upgrade", "clean", "reorganize"])]
            if not features:
                features = recent[:5]
            if not fixes:
                fixes = recent[:3]

            for icon, title, items in [
                (_ICON_SPARKLES, "New Features", features[:8]),
                (_ICON_WRENCH, "Bug Fixes", fixes[:6]),
                (_ICON_ARROW_UP_CIRCLE, "Improvements", improvements[:6]),
            ]:
                if not items:
                    continue
                card = _card()
                ccl = QVBoxLayout(card)
                ccl.setContentsMargins(20, 18, 20, 20)
                ccl.setSpacing(12)
                ccl.addLayout(_icon_title_row(icon, title))
                for item in items:
                    row = QHBoxLayout()
                    row.setSpacing(12)
                    hash_lbl = QLabel(item["hash"])
                    hash_lbl.setStyleSheet(
                        f"color: {Colors.ACCENT}; font-size: {Fonts.SM};"
                        f" font-family: {Fonts.MONO};"
                        " background: transparent; border: none;")
                    hash_lbl.setFixedWidth(55)
                    row.addWidget(hash_lbl)
                    msg = QLabel(item["message"])
                    msg.setWordWrap(True)
                    msg.setStyleSheet(
                        f"font-size: {Fonts.BASE}; color: {Colors.TEXT};"
                        " background: transparent; border: none;")
                    row.addWidget(msg, 1)
                    date_lbl = QLabel(item["date"])
                    date_lbl.setStyleSheet(
                        f"font-size: {Fonts.XS}; color: {Colors.TEXT_3};"
                        " background: transparent; border: none;")
                    row.addWidget(date_lbl)
                    ccl.addLayout(row)
                    ccl.addWidget(_sep())
                # remove trailing separator
                last = ccl.takeAt(ccl.count() - 1)
                if last:
                    w = last.widget()
                    if w:
                        w.deleteLater()
                cl.addWidget(card)

        # Tags
        tags = _git_tags()
        if tags:
            tag_card = _card()
            tcl = QVBoxLayout(tag_card)
            tcl.setContentsMargins(20, 18, 20, 20)
            tcl.setSpacing(10)
            tcl.addWidget(_card_title("Releases"))
            for tag in tags:
                row = QHBoxLayout()
                row.setSpacing(8)
                t = QLabel(tag)
                t.setStyleSheet(
                    f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
                    f" color: {Colors.TEXT}; background: transparent; border: none;")
                row.addWidget(t)
                row.addStretch()
                release_url = f"{_REPO_URL}/releases/tag/{tag}"
                row.addWidget(_link_btn(
                    "\u2197 View Release",
                    lambda u=release_url: _open_url(u)))
                tcl.addLayout(row)
                tcl.addWidget(_sep())
            last = tcl.takeAt(tcl.count() - 1)
            if last:
                w = last.widget()
                if w:
                    w.deleteLater()
            cl.addWidget(tag_card)

        cl.addWidget(_accent_btn(
            "View All Releases on GitHub \u2197",
            lambda: _open_url(f"{_REPO_URL}/releases")))

        cl.addStretch(1)
        scroll.setWidget(content)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        layout.addLayout(outer, 1)


# ── Tab: Documentation ─────────────────────────────────────────────

_DOC_CHECK = '<path d="M5 13l4 4L19 7"/>'

# (section, [(num, title, purpose, [(feature, description), ...]), ...])
_DOC_SECTIONS = [
    ("Getting Started", [
        ("01", "Welcome",
         "NeoArch brings every package source and system workflow on Arch "
         "Linux together in one fast, friendly interface.",
         [
             ("Multi-source manager",
              "Search pacman, AUR, Flatpak and npm side by side"),
             ("Unified workflows",
              "Packages, Git, Docker, AppImages and bundles in one app"),
             ("Companion CLI",
              "Automate NeoArch from the terminal with neoarch-cli"),
             ("Instant theming",
              "Switch appearance anytime from Settings"),
         ]),
    ]),
    ("Package Management", [
        ("02", "Home",
         "Your starting point — search every source and watch what "
         "happens on your system.",
         [
             ("Hero search", "Live results across every source as you type"),
             ("Quick actions", "Update All, refresh databases, clean cache"),
             ("Stat cards", "Installed count, pending updates, source totals"),
             ("Recent activity", "Latest installs and upgrades at a glance"),
             ("Grid or table view", "Toggle how search results are shown"),
             ("Package details", "Inspect any package before installing"),
         ], [
             ("Type what you are looking for — results stream in "
              "from every source", False),
             ("Tick one or many packages right in the results table", False),
             ("Install Selected installs them immediately, grouped by source",
              False),
             ("Or press Add to Bundle to save them into the active bundle",
              False),
             ("Click any row to open the detail card before deciding", False),
         ]),
        ("03", "Installed",
         "Browse and manage every package currently installed on your machine.",
         [
             ("Full inventory", "Complete table of installed packages"),
             ("Bulk uninstall", "Remove several selected packages safely"),
             ("Ignore updates", "Pin packages you never want upgraded"),
             ("Source filters", "Narrow the list by repository"),
             ("Maintenance tools",
              "Remove orphans, manage .pacnew files, purge cache"),
         ]),
        ("04", "Updates",
         "Keep Arch rolling with fast, controlled system updates.",
         [
             ("Update All", "Apply every pending update in one click"),
             ("Selective updates", "Pick exactly which packages to upgrade"),
             ("Sudo session", "Authenticate once, install smoothly after"),
             ("Update badges", "Pending counts stay visible in the sidebar"),
             ("Safe cancellations", "Stop running installations anytime"),
         ]),
        ("05", "Bundles",
         "Group packages into shareable collections and rebuild setups "
         "anywhere.",
         [
             ("Create bundles", "Collect favourite packages into groups"),
             ("Share codes", "Generate codes others import instantly"),
             ("Import & export", "Move bundles via JSON files"),
             ("One-click install", "Set up an entire bundle at once"),
             ("Cloud sync", "Back up bundles to your NeoArch account"),
         ], [
             ("Open Bundles — your first visit creates My Bundle "
              "automatically", False),
             ("Make new bundles anytime with the + button beside BUNDLES",
              False),
             ("In Home, tick packages and press Add to Bundle — items join "
              "the active bundle (switch it in the sidebar here first)",
              False),
             ("Every change auto-saves locally — no save button needed",
              False),
             ("Install Bundle sets up everything offline, grouped by source",
              False),
             ("Share codes and cloud Sync work once you are signed in", True),
         ]),
    ]),
    ("Tools & Workflows", [
        ("06", "Sources",
         "Discover plugins and helper tools that extend what NeoArch can do.",
         [
             ("Plugin catalog", "Browse installable tools as cards"),
             ("One-click states", "Install, open or uninstall each entry"),
             ("Status filters", "Show available or installed only"),
             ("Batch install", "Queue several plugins together"),
         ]),
        ("07", "Git Projects",
         "Clone, build and maintain projects straight from Git repositories.",
         [
             ("Clone dialog", "Fetch any repository by URL"),
             ("Pull & build", "Keep projects current and compiled"),
             ("Build history", "Review recent builds per project"),
             ("Storage overview", "Donut chart of project disk usage"),
             ("Grid or list view", "Organise projects your way"),
         ]),
        ("08", "Docker",
         "Manage containers, images, volumes and networks without the terminal.",
         [
             ("Run container", "Launch containers from any image"),
             ("Lifecycle control", "Start, stop and remove containers"),
             ("Image manager", "Pull images and clear unused ones"),
             ("Volumes & networks", "Create and inspect Docker resources"),
             ("Live logs", "Follow container output and resource usage"),
         ]),
        ("09", "AppImages",
         "Keep your local AppImage library tidy and up to date.",
         [
             ("Add from file or URL", "Import AppImages either way"),
             ("Update checks", "See when an app has a newer release"),
             ("Quick actions", "Open, update or remove entries"),
             ("Search & sort", "Find apps in large libraries fast"),
         ]),
    ]),
    ("System & Account", [
        ("10", "Settings",
         "Configure every part of NeoArch across seven focused categories.",
         [
             ("General", "Language, AUR helper, paths, settings transfer"),
             ("Appearance", "Theme picker applied instantly"),
             ("Auto Update", "Schedules, pre-update backups, Timeshift"),
             ("Notifications", "Channels, events and cooldowns"),
             ("Proxy & Network", "Timeouts, SSL verify, parallel downloads"),
             ("Maintenance", "Orphans, .pacnew, cache hygiene, Arch news"),
         ]),
        ("11", "User Account",
         "Sign in to unlock cloud sync across your devices.",
         [
             ("Cloud sign-in", "Secure browser-based authentication"),
             ("Sync favourites", "Carry starred packages anywhere"),
             ("Cloud bundles", "Back up collections online"),
             ("System info", "Quick view of your machine profile"),
         ], [
             ("Tap your avatar at the bottom of the left sidebar", False),
             ("Choose Sign In — your browser handles secure login, "
              "then NeoArch continues automatically", True),
             ("Use Cloud Bundles from the same menu to restore backups",
              True),
             ("In Bundles, press Sync to upload the active bundle", True),
             ("Manage Bundles in the menu jumps to your local collections",
              False),
         ]),
        ("12", "Help & About",
         "Everything about the app itself — versions, health and the "
         "people behind it.",
         [
             ("Overview", "Version, edition and project links"),
             ("Release notes", "Changelog built from Git history"),
             ("Diagnostics", "Verify tools and plugin health"),
             ("Contributors & sponsors", "Meet and support the community"),
         ]),
    ]),
]


def _doc_feature_card(name, desc):
    f = QFrame()
    f.setObjectName("docFeat")
    f.setStyleSheet(
        f"QFrame#docFeat {{ background: {Colors.SURFACE_2};"
        f" border-radius: {Radii.MD}px; }}")
    lay = QHBoxLayout(f)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(10)

    ic = QLabel()
    ic.setPixmap(_mac_icon_pixmap(_DOC_CHECK, 12))
    ic.setFixedSize(12, 12)
    ic.setStyleSheet("background: transparent; border: none;")
    lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)

    col = QVBoxLayout()
    col.setSpacing(1)
    n = QLabel(name)
    n.setWordWrap(True)
    n.setStyleSheet(
        f"font-size: {Fonts.SM}; font-weight: {Fonts.SEMI};"
        f" color: {Colors.TEXT}; background: transparent; border: none;")
    col.addWidget(n)
    d = QLabel(desc)
    d.setWordWrap(True)
    d.setStyleSheet(
        f"font-size: {Fonts.XS}; color: {Colors.TEXT_3};"
        " background: transparent; border: none;")
    col.addWidget(d)
    lay.addLayout(col, 1)
    return f


def _doc_step_row(idx, text, account=False):
    row = QHBoxLayout()
    row.setSpacing(10)

    badge = QLabel(str(idx))
    badge.setFixedSize(20, 20)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"background: {Colors.ACCENT_SOFT}; color: {Colors.ACCENT};"
        f" border-radius: 10px; font-size: {Fonts.XS};"
        f" font-weight: {Fonts.BOLD};")
    row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"font-size: {Fonts.SM}; color: {Colors.TEXT_2};"
        " background: transparent; border: none;")
    row.addWidget(lbl, 1)

    if account:
        tag = QLabel("SIGN-IN")
        tag.setStyleSheet(
            f"color: {Colors.ORANGE};"
            " background: rgba(255, 159, 28, 0.12);"
            f" border-radius: 6px; padding: 2px 7px;"
            f" font-size: {Fonts.XS}; font-weight: {Fonts.SEMI};")
        row.addWidget(tag, 0, Qt.AlignmentFlag.AlignVCenter)
    return row


def _doc_chapter_page(num, title, purpose, features, steps=None):
    scroll = _scroll_area()
    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(32, 26, 32, 26)
    cl.setSpacing(12)

    num_lbl = QLabel(f"CHAPTER {num}")
    num_lbl.setStyleSheet(
        f"color: {Colors.ACCENT}; font-size: {Fonts.XS};"
        f" font-weight: {Fonts.BOLD}; letter-spacing: 2px;"
        " background: transparent; border: none;")
    cl.addWidget(num_lbl)

    t_lbl = QLabel(title)
    t_lbl.setStyleSheet(
        f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
        " letter-spacing: -0.5px;"
        f" color: {Colors.TEXT}; background: transparent; border: none;")
    cl.addWidget(t_lbl)

    p_lbl = QLabel(purpose)
    p_lbl.setWordWrap(True)
    p_lbl.setStyleSheet(
        f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
        " background: transparent; border: none;")
    cl.addWidget(p_lbl)

    cl.addSpacing(6)
    cl.addWidget(_sep())
    cl.addSpacing(6)

    fh_lbl = QLabel("WHAT YOU CAN DO")
    fh_lbl.setStyleSheet(
        f"color: {Colors.TEXT_3}; font-size: {Fonts.XS};"
        f" font-weight: {Fonts.BOLD}; letter-spacing: 1.2px;"
        " background: transparent; border: none;")
    cl.addWidget(fh_lbl)

    grid = QGridLayout()
    grid.setContentsMargins(0, 6, 0, 0)
    grid.setSpacing(10)
    for i, (name, desc) in enumerate(features):
        grid.addWidget(_doc_feature_card(name, desc), i // 2, i % 2)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    cl.addLayout(grid)

    if steps:
        cl.addSpacing(6)
        sh_lbl = QLabel("HOW IT WORKS")
        sh_lbl.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.XS};"
            f" font-weight: {Fonts.BOLD}; letter-spacing: 1.2px;"
            " background: transparent; border: none;")
        cl.addWidget(sh_lbl)

        steps_box = QVBoxLayout()
        steps_box.setContentsMargins(0, 6, 0, 0)
        steps_box.setSpacing(8)
        for i, step in enumerate(steps, 1):
            text, acct = step if isinstance(step, tuple) else (step, False)
            steps_box.addLayout(_doc_step_row(i, text, acct))
        cl.addLayout(steps_box)

    cl.addStretch(1)
    scroll.setWidget(content)
    return scroll


class _DocumentationTab(QWidget):
    """Book-style guide: contents index on the left, one chapter page
    per NeoArch screen on the right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nav_btns = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        layout.addWidget(_page_title("Documentation"))
        layout.addWidget(_page_subtitle(
            "A field guide to every NeoArch page"))

        book = _card()
        bl = QHBoxLayout(book)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        toc_scroll = _scroll_area()
        toc_scroll.setFixedWidth(236)
        toc_widget = QWidget()
        tl = QVBoxLayout(toc_widget)
        tl.setContentsMargins(14, 16, 10, 16)
        tl.setSpacing(2)

        self._stack = QStackedWidget()
        idx = 0
        first_section = True
        for section, chapters in _DOC_SECTIONS:
            if not first_section:
                tl.addSpacing(10)
            hdr = QLabel(section.upper())
            hdr.setStyleSheet(
                f"color: {Colors.TEXT_3}; font-size: {Fonts.XS};"
                f" font-weight: {Fonts.BOLD}; letter-spacing: 1.2px;"
                " padding: 6px 12px 4px 12px;"
                " background: transparent; border: none;")
            tl.addWidget(hdr)
            first_section = False

            for num, title, purpose, feats, *rest in chapters:
                tl.addWidget(self._toc_btn(num, title, idx))
                self._stack.addWidget(
                    _doc_chapter_page(num, title, purpose, feats,
                                      rest[0] if rest else None))
                idx += 1

        tl.addStretch(1)
        toc_scroll.setWidget(toc_widget)
        bl.addWidget(toc_scroll)

        edge = QFrame()
        edge.setFixedWidth(1)
        edge.setStyleSheet(f"background: {Colors.BORDER}; border: none;")
        bl.addWidget(edge)

        bl.addWidget(self._stack, 1)

        layout.addWidget(book, 1)
        self._goto(0)

    def _toc_btn(self, num, title, index):
        btn = QPushButton(f"{num}   {title}")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 7px 12px;
                border: none;
                background-color: transparent;
                color: {Colors.TEXT_2};
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
                border-radius: {Radii.SM}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_SOFT};
                color: {Colors.ACCENT};
                font-weight: {Fonts.SEMI};
            }}
        """)
        btn.clicked.connect(lambda _, i=index: self._goto(i))
        self._nav_btns.append(btn)
        return btn

    def _goto(self, index):
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._nav_btns):
            b.setChecked(i == index)


# ── Tab: Diagnostics ───────────────────────────────────────────────

class _DiagWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        results = []
        checks = [
            ("NeoArch Version", APP_VERSION, "ok"),
            ("Python", _platform.python_version(), "ok"),
            ("Platform", f"{_platform.system()} {_platform.release()}", "ok"),
            ("Architecture", _platform.machine(), "ok"),
        ]
        for name, val, status in checks:
            results.append((name, val, status))

        pac_ver = _run_cmd(["pacman", "--version"])
        if pac_ver:
            results.append(("pacman", pac_ver.splitlines()[0], "ok"))
        else:
            results.append(("pacman", "Not found", "error"))

        yay_ver = _run_cmd(["yay", "--version"])
        if yay_ver:
            results.append(("yay (AUR helper)", yay_ver.splitlines()[0], "ok"))
        else:
            results.append(("yay (AUR helper)", "Not installed", "warn"))

        fp_ver = _run_cmd(["flatpak", "--version"])
        results.append(("Flatpak", fp_ver or "Not installed",
                        "ok" if fp_ver else "warn"))

        npm_ver = _run_cmd(["npm", "--version"])
        results.append(("npm", f"v{npm_ver}" if npm_ver else "Not installed",
                        "ok" if npm_ver else "warn"))

        docker_ver = _run_cmd(["docker", "--version"])
        results.append(("Docker", docker_ver or "Not installed",
                        "ok" if docker_ver else "warn"))

        plugins_dir = os.path.expanduser(
            os.path.join("~", ".config", "neoarch", "plugins"))
        plugin_count = 0
        if os.path.isdir(plugins_dir):
            plugin_count = len([
                f for f in os.listdir(plugins_dir) if f.endswith(".py")
            ])
        results.append(("Plugins", f"{plugin_count} installed",
                        "ok" if plugin_count else "warn"))

        self.finished.emit(results)


class _StatusDot(QLabel):
    def __init__(self, status, parent=None):
        super().__init__(parent)
        color_map = {
            "ok": Colors.GREEN,
            "warn": Colors.ORANGE,
            "error": Colors.RED,
            "info": Colors.TEXT_2,
        }
        c = color_map.get(status, Colors.TEXT_2)
        self.setText(f"\u2022 {status.upper()}")
        self.setStyleSheet(
            f"color: {c}; font-size: {Fonts.XS}; font-weight: {Fonts.SEMI};"
            " background: transparent; border: none;")


class _DiagnosticsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        layout.addWidget(_page_title("Diagnostics"))
        layout.addWidget(_page_subtitle("System checks and diagnostic information"))

        scroll = _scroll_area()
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(20)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addWidget(_accent_btn("Run Diagnostics", lambda: None))
        btn_row.addWidget(_secondary_btn("Copy Report", lambda: None))
        btn_row.addWidget(_secondary_btn(
            "Report a Bug \u2197",
            lambda: _open_url(f"{_REPO_URL}/issues/new")))
        btn_row.addStretch()
        cl.addLayout(btn_row)

        self._results_card = _card()
        self._results_layout = QVBoxLayout(self._results_card)
        self._results_layout.setContentsMargins(20, 18, 20, 20)
        self._results_layout.setSpacing(10)

        placeholder = QLabel("Click \"Run Diagnostics\" to check your system")
        placeholder.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_3};"
            " background: transparent; border: none;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_layout.addWidget(placeholder)
        cl.addWidget(self._results_card)

        self._worker = None
        self._report_text = ""
        self._report_lines = []

        run_btn = btn_row.itemAt(0).widget()
        copy_btn = btn_row.itemAt(1).widget()

        def _run_diag():
            if self._worker and self._worker.isRunning():
                self._worker.finished.disconnect()
                self._worker.quit()
                self._worker.wait(2000)
            while self._results_layout.count():
                item = self._results_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            loading = QLabel("Running diagnostics\u2026")
            loading.setStyleSheet(
                f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
                " background: transparent; border: none;")
            loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(loading)
            self._worker = _DiagWorker()
            self._worker.finished.connect(
                lambda r: self._on_results(r, loading))
            self._worker.start()

        run_btn.clicked.disconnect()
        run_btn.clicked.connect(_run_diag)

        def _copy_report():
            if self._report_text and QApplication.instance():
                QApplication.clipboard().setText(self._report_text)

        copy_btn.clicked.disconnect()
        copy_btn.clicked.connect(_copy_report)

        cl.addStretch(1)
        scroll.setWidget(content)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        layout.addLayout(outer, 1)

    def _on_results(self, results, loading_lbl):
        try:
            self._results_layout.removeWidget(loading_lbl)
            loading_lbl.deleteLater()
        except Exception:
            pass

        self._report_lines = []
        for name, value, status in results:
            row = QHBoxLayout()
            row.setSpacing(12)
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(
                f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
                f" color: {Colors.TEXT}; background: transparent; border: none;")
            name_lbl.setFixedWidth(170)
            row.addWidget(name_lbl)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(
                f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
                " background: transparent; border: none;")
            row.addWidget(val_lbl, 1)
            row.addWidget(_StatusDot(status))
            self._results_layout.addLayout(row)
            self._report_lines.append(
                f"{name}: {value} [{status.upper()}]")

        self._report_text = "\n".join(self._report_lines)


# ── Tab: Community ─────────────────────────────────────────────────

class _CommunityTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        layout.addWidget(_page_title("Community"))
        layout.addWidget(_page_subtitle(
            "The people behind NeoArch and how to support it"))

        scroll = _scroll_area()
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(20)

        # ── Founder card ──
        founder = _card()
        fl = QHBoxLayout(founder)
        fl.setContentsMargins(24, 22, 24, 22)
        fl.setSpacing(16)

        avatar = QLabel()
        avatar.setFixedSize(56, 56)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dev_img = os.path.join(
            str(ASSETS_DIR), "icons", "app", "developer.png")
        pm = QPixmap(dev_img) if os.path.exists(dev_img) else QPixmap()
        if not pm.isNull():
            avatar.setPixmap(pm.scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            avatar.setStyleSheet("border-radius: 28px; border: none;")
        else:
            avatar.setText("SD")
            avatar.setStyleSheet(
                f"border-radius: 28px; border: none;"
                f" background: {Colors.ACCENT_SOFT};"
                f" color: {Colors.ACCENT}; font-size: {Fonts.XL};"
                f" font-weight: {Fonts.BOLD};")
        fl.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel("Sanjaya Danushka")
        name_lbl.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; background: transparent; border: none;")
        info.addWidget(name_lbl)
        role_lbl = QLabel("Founder \u00b7 Lead Developer")
        role_lbl.setStyleSheet(
            f"font-size: {Fonts.SM}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.ACCENT}; background: transparent;"
            " border: none;")
        info.addWidget(role_lbl)
        bio_lbl = QLabel(
            "Designs, builds and maintains every part of NeoArch.")
        bio_lbl.setWordWrap(True)
        bio_lbl.setStyleSheet(
            f"font-size: {Fonts.SM}; color: {Colors.TEXT_3};"
            " background: transparent; border: none;")
        info.addWidget(bio_lbl)
        fl.addLayout(info, 1)

        fl.addWidget(_secondary_btn(
            "\u2197 GitHub",
            lambda: _open_url("https://github.com/Sanjaya-Danushka")))
        cl.addWidget(founder)

        # ── Support card with QR ──
        support = _card()
        sl = QHBoxLayout(support)
        sl.setContentsMargins(24, 22, 24, 22)
        sl.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(_card_title("Support NeoArch"))
        left.addWidget(_card_body(
            "NeoArch is free, open-source and developed independently by "
            "one person. If it saves you time, consider supporting its "
            "continued development."))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        bmc_icon = os.path.join(
            str(ASSETS_DIR), "icons", "ui", "buymeacoffee.svg")
        for label, url, color, bg, icon_path in [
            ("\u2665  GitHub Sponsors", _SPONSORS_URL,
             "#FF6464", "rgba(255,100,100,", None),
            ("Buy Me a Coffee", _BUYMEACOFFEE_URL,
             "#FFC832", "rgba(255,200,50,", bmc_icon),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if icon_path and os.path.exists(icon_path):
                b.setIcon(QIcon(icon_path))
                b.setIconSize(QSize(15, 15))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}0.12);
                    color: {color};
                    border: 1px solid {bg}0.25);
                    border-radius: {Radii.MD}px;
                    padding: 0 16px;
                    font-size: {Fonts.BASE};
                    font-weight: {Fonts.SEMI};
                }}
                QPushButton:hover {{
                    background: {bg}0.20);
                }}
            """)
            b.clicked.connect(lambda checked=False, u=url: _open_url(u))
            btn_row.addWidget(b)
        btn_row.addStretch()
        left.addLayout(btn_row)

        qr = QLabel()
        qr_path = os.path.join(str(ASSETS_DIR), "icons", "app", "qr-code.png")
        qpm = QPixmap(qr_path) if os.path.exists(qr_path) else QPixmap()
        if not qpm.isNull():
            qr_frame = QVBoxLayout()
            qr_frame.addWidget(qr, 0, Qt.AlignmentFlag.AlignCenter)
            cap = QLabel("Scan to buy me a coffee")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap.setStyleSheet(
                f"font-size: {Fonts.XS}; color: {Colors.TEXT_3};"
                " background: transparent; border: none;")
            qr_frame.addWidget(cap)
        else:
            note = QLabel(
                "Coffee fund \u2615\nEvery cup keeps development going.")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note.setWordWrap(True)
            note.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {Colors.TEXT_2};"
                f" background: {Colors.ACCENT_SOFT};"
                f" border-radius: {Radii.MD}px; padding: 14px;")
            qr_frame = QVBoxLayout()
            qr_frame.addWidget(note)

        if not qpm.isNull():
            qr.setPixmap(qpm.scaled(
                140, 140, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr.setStyleSheet(
                "background: #FFFFFF; border-radius:"
                f" {Radii.MD}px; padding: 6px;")

        sl.addLayout(left, 1)
        sl.addLayout(qr_frame, 0)
        cl.addWidget(support)

        # ── Contributing line ──
        contrib = _card()
        cvl = QHBoxLayout(contrib)
        cvl.setContentsMargins(20, 16, 20, 16)
        cvl.setSpacing(12)
        ct = QLabel("Want to improve NeoArch?")
        ct.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; background: transparent;"
            " border: none;")
        cvl.addWidget(ct)
        cvl.addStretch()
        cvl.addWidget(_link_btn(
            "Contributing Guide \u2197",
            lambda: _open_url(f"{_REPO_URL}?tab=contributing-ov-file")))
        cl.addWidget(contrib)

        cl.addStretch(1)
        scroll.setWidget(content)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        layout.addLayout(outer, 1)


# ── Main AboutTab ──────────────────────────────────────────────────

class AboutTab(QWidget):
    """Full-page About view — mirrors Settings left-sidebar layout."""

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._nav_btns = []
        self._init_ui()

    def _make_nav_btn(self, label, index):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, i=index: self._switch_tab(i))
        self._nav_btns.append(btn)
        return btn

    def _switch_tab(self, index):
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._nav_btns):
            b.setChecked(i == index)

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left nav sidebar (identical to Settings) ──
        sidebar = QFrame()
        sidebar.setObjectName("aboutSidebar")
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(268)
        sidebar.setStyleSheet(f"""
            QFrame#aboutSidebar {{
                background-color: {Colors.BG};
                border-right: 1px solid {Colors.BORDER};
            }}
            QPushButton {{
                text-align: left;
                padding: 10px 16px;
                border: none;
                background-color: transparent;
                color: {Colors.TEXT_2};
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
                border-radius: {Radii.MD}px;
                margin: 1px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_SOFT};
                color: {Colors.ACCENT};
                font-weight: {Fonts.SEMI};
            }}
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(1)

        header = QLabel("ABOUT")
        header.setStyleSheet(f"""
            color: {Colors.TEXT_3};
            font-size: {Fonts.SM};
            font-weight: {Fonts.BOLD};
            letter-spacing: 1.2px;
            padding: 6px 16px 8px 16px;
        """)
        sidebar_layout.addWidget(header)

        tab_labels = [
            "Overview",
            "Release Notes",
            "Documentation",
            "Diagnostics",
            "Community",
        ]
        for i, label in enumerate(tab_labels):
            sidebar_layout.addWidget(self._make_nav_btn(label, i))

        sidebar_layout.addStretch()

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(16, 4, 16, 8)
        meta_row.setSpacing(0)

        meta_label = QLabel(f"NeoArch {APP_VERSION} \u00b7")
        meta_label.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.XS};"
            f" font-weight: {Fonts.MEDIUM};"
            " background: transparent; border: none;")
        meta_row.addWidget(meta_label)

        meta_row.addSpacing(8)

        ed_badge = QLabel(APP_EDITION)
        ed_badge.setStyleSheet(f"""
            color: {Colors.ACCENT};
            background-color: rgba(0, 191, 174, 0.08);
            border: 1px solid rgba(0, 191, 174, 0.18);
            font-size: {Fonts.XS};
            font-weight: {Fonts.SEMI};
            letter-spacing: 0.3px;
            padding: 2px 7px;
            border-radius: 6px;
        """)
        ed_badge.setFixedHeight(16)
        meta_row.addWidget(ed_badge)

        meta_row.addStretch()
        sidebar_layout.addLayout(meta_row)

        root.addWidget(sidebar)

        # ── Right content ──
        content = QFrame()
        content.setObjectName("aboutContent")
        content.setStyleSheet(
            f"QFrame#aboutContent {{ background-color: {Colors.BG}; }}")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.setSpacing(0)

        self._stack = QStackedWidget()
        tab_classes = [
            _OverviewTab, _ReleaseNotesTab, _DocumentationTab,
            _DiagnosticsTab, _CommunityTab,
        ]
        for cls in tab_classes:
            self._stack.addWidget(cls())
        content_layout.addWidget(self._stack)

        root.addWidget(content, 1)

        self._switch_tab(0)
