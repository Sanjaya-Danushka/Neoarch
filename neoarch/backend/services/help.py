"""Help and about dialog services for the application.

Provides comprehensive help documentation with tabbed interface
and an about dialog with application info.
"""

import os
import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTextEdit, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

from neoarch.resources.paths import ASSETS_DIR, PROJECT_ROOT

__all__ = ["_make_text_tab", "show_help", "show_about"]


def _make_text_tab(text: str) -> QWidget:
    """Create a read-only text editor tab for help content."""
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(12, 12, 12, 12)
    edit = QTextEdit()
    edit.setReadOnly(True)
    edit.setText(text)
    v.addWidget(edit)
    return w


def show_help(parent, current_view: str):
    """Show the help dialog with overview, usage, and tips tabs."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Help & Documentation")
    dlg.setModal(True)
    dlg.setMinimumSize(780, 560)

    icon_path = ASSETS_DIR / "icons" / "about.svg"
    if icon_path.exists():
        dlg.setWindowIcon(QIcon(str(icon_path)))

    root = QVBoxLayout(dlg)
    tabs = QTabWidget()

    overview = (
        "NeoArch - Your All-in-One Package Manager!\n\n"
        "NeoArch simplifies software management on Arch Linux by bringing everything into one place:\n\n"
        "WHAT YOU CAN DO:\n"
        "- Search and install from multiple sources (official repos, AUR, Flatpak, npm) in one search\n"
        "- Create bundles of your favorite apps to install on new systems\n"
        "- Keep everything updated with one click\n"
        "- Install system tools and utilities from the Plugins section\n"
        "- Install from GitHub repos or Docker containers directly\n"
        "- Create system snapshots before major updates (requires Timeshift)\n\n"
        "HOW TO USE:\n"
        "- Discover: Search for packages across all sources\n"
        "- Updates: View and apply available updates\n"
        "- Installed: Browse all installed packages\n"
        "- Bundles: Create and manage package collections\n"
        "- Plugins: Install tools and community plugins\n"
        "- Settings: Configure NeoArch to your preferences\n"
    )
    tabs.addTab(_make_text_tab(overview), "Overview")

    usage = (
        "USAGE GUIDE\n\n"
        "SEARCHING:\n"
        "- Type in the search bar to search across all sources simultaneously\n"
        "- Results from pacman, AUR, Flatpak, and npm are shown together\n\n"
        "INSTALLING:\n"
        "- Select packages using the checkboxes and click Install Selected\n"
        "- You can install from multiple sources at once\n"
        "- AUR packages require sudo/authentication\n\n"
        "UPDATING:\n"
        "- Switch to the Updates view to see all available updates\n"
        "- Click 'Update All' to update everything\n"
        "- Or select specific packages and click 'Update Selected'\n\n"
        "BUNDLES:\n"
        "- Create bundles of packages for bulk installation\n"
        "- Export/import bundles as JSON files\n"
        "- Share bundles with the community\n\n"
        "PLUGINS:\n"
        "- Browse and install system tools (BleachBit, Timeshift, etc.)\n"
        "- Install community plugins for extended functionality\n"
        "- Create your own plugins using the plugin template\n\n"
        "GIT & DOCKER:\n"
        "- Clone and build projects from Git repositories\n"
        "- Run applications from Docker images\n"
        "- Manage containers and repositories\n"
    )
    tabs.addTab(_make_text_tab(usage), "Usage Guide")

    tips = (
        "TIPS & TRICKS\n\n"
        "SHORTCUTS:\n"
        "- Press Ctrl+F to focus the search bar\n"
        "- Press Escape to clear selection or close dialogs\n\n"
        "PERFORMANCE:\n"
        "- The app loads plugins lazily for faster startup\n"
        "- Package tables use pagination (Load More) for large lists\n"
        "- Background threads keep the UI responsive during operations\n\n"
        "TROUBLESHOOTING:\n"
        "- If AUR installation fails, ensure kdialog/zenity/yad is installed\n"
        "- For permission issues with npm, try installing with sudo mode\n"
        "- If Flatpak isn't working, ensure Flathub remote is configured\n"
        "- Check the console output at the bottom of the window for details\n\n"
        "SECURITY:\n"
        "- AUR packages are community-maintained - review PKGBUILDs\n"
        "- Use Timeshift snapshots before major system updates\n"
        "- Configure auto-updates carefully in Settings\n"
    )
    tabs.addTab(_make_text_tab(tips), "Tips & Tricks")

    about_tab_text = (
        "ABOUT NeoArch\n\n"
        f"Version: 1.2-beta\n"
        f"Platform: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n\n"
        "NeoArch - Elevate Your Arch Experience\n\n"
        "A modern graphical package manager for Arch Linux with AUR support.\n"
        "Built with PyQt6 for a responsive, native-feeling interface.\n\n"
        "Features:\n"
        "- Multi-source package management (pacman, AUR, Flatpak, npm)\n"
        "- Bundle management for bulk operations\n"
        "- Git repository cloning and building\n"
        "- Docker container management\n"
        "- Timeshift snapshot integration\n"
        "- Plugin system with community sharing\n"
        "- Desktop-environment-aware authentication\n\n"
        "Repository: https://github.com/Sanjaya-Danushka/Neoarch\n"
        "License: MIT\n"
    )
    tabs.addTab(_make_text_tab(about_tab_text), "About")

    root.addWidget(tabs)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    dlg.exec()


def show_about(parent):
    """Show the about dialog with application information."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("About NeoArch")
    dlg.setMinimumSize(400, 500)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(12)

    logo_path = ASSETS_DIR / "icons" / "NeoarchLogo.svg"
    if logo_path.exists():
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo_label = QLabel()
            logo_label.setPixmap(pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

    title = QLabel("NeoArch")
    title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00BFAE;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)

    subtitle = QLabel("Elevate Your Arch Experience")
    subtitle.setStyleSheet("font-size: 14px; color: #C9C9C9;")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(subtitle)

    version = QLabel("Version 1.2-beta")
    version.setStyleSheet("font-size: 12px; color: #888;")
    version.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(version)

    layout.addSpacing(20)

    desc = QLabel(
        "A modern graphical package manager for Arch Linux\n"
        "with AUR support, bundle management, and more.\n\n"
        "Built with PyQt6\n"
        "Repository: github.com/Sanjaya-Danushka/Neoarch"
    )
    desc.setStyleSheet("font-size: 12px; color: #aaa; line-height: 1.5;")
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setWordWrap(True)
    layout.addWidget(desc)

    layout.addStretch()

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    dlg.exec()
