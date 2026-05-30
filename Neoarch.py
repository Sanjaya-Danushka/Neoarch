#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportMissingModuleSource=false
# cSpell:disable
from __future__ import annotations

import sys
import os
import subprocess
import time
import json
import re
import shutil
import tempfile
import importlib.util
import traceback
from threading import Thread, Event
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit,
                             QLabel, QFileDialog, QMessageBox, QHeaderView, QFrame, QSplitter,
                             QScrollArea, QCheckBox, QListWidget, QListWidgetItem, QSizePolicy,
                             QDialog, QTabWidget, QGroupBox, QGridLayout, QRadioButton, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize, QTimer, QRectF, QItemSelectionModel, qInstallMessageHandler, QtMsgType
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QImage
from PyQt6.QtSvg import QSvgRenderer # type: ignore
from collections import Counter
from typing import Any


# === utils: workers.py ===
import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal


def get_auth_command(env=None):
    """Get the appropriate authentication command based on desktop environment"""
    if env is None:
        env = os.environ
    
    desktop = env.get('XDG_CURRENT_DESKTOP', '').lower()
    session_type = env.get('XDG_SESSION_TYPE', '').lower()
    wayland_display = env.get('WAYLAND_DISPLAY', '')
    hyprland_instance = env.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    
    # Check if polkit agent is running
    try:
        polkit_agent_running = subprocess.run(['pgrep', '-f', 'polkit.*agent'], capture_output=True).returncode == 0
    except Exception:
        polkit_agent_running = False
    
    # Better Hyprland detection - check multiple indicators
    is_hyprland = (
        'hyprland' in desktop or 
        hyprland_instance or 
        (session_type == 'wayland' and 'hypr' in wayland_display.lower())
    )
    
    # For Hyprland - always prefer sudo with askpass due to pkexec terminal issues
    if is_hyprland:
        if 'SUDO_ASKPASS' in env:
            return ["sudo", "-A"]
        else:
            # Force askpass setup for Hyprland even if not set
            return ["sudo", "-A"]
    
    # For minimal Wayland compositors without polkit agent
    elif session_type == 'wayland' and not polkit_agent_running:
        if 'SUDO_ASKPASS' in env:
            return ["sudo", "-A"]
        else:
            return ["pkexec"]
    
    # For GNOME, KDE, XFCE with polkit agents - but test pkexec first
    elif polkit_agent_running:
        # Test if pkexec works (avoid terminal issues)
        try:
            test_result = subprocess.run(['pkexec', '--version'], 
                                       capture_output=True, timeout=5)
            if test_result.returncode == 0:
                if desktop in ['gnome', 'kde', 'xfce']:
                    return ["pkexec"]
                else:
                    return ["pkexec", "--disable-internal-agent"]
            else:
                # pkexec failed, fallback to sudo
                if 'SUDO_ASKPASS' in env:
                    return ["sudo", "-A"]
                else:
                    return ["sudo", "-A"]
        except Exception:
            # pkexec test failed, use sudo
            if 'SUDO_ASKPASS' in env:
                return ["sudo", "-A"]
            else:
                return ["sudo", "-A"]
    
    # Fallback: try sudo with askpass if available
    elif 'SUDO_ASKPASS' in env:
        return ["sudo", "-A"]
    
    # Final fallback
    else:
        return ["sudo", "-A"]


class PackageLoaderWorker(QObject):
    packages_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, command):
        super().__init__()
        self.command = command
    
    def run(self):
        try:
            result = subprocess.run(self.command, capture_output=True, text=True, timeout=60)
            packages = []
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                'name': parts[0],
                                'version': parts[1],
                                'id': parts[0]
                            })
            self.packages_loaded.emit(packages)
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()


class CommandWorker(QObject):
    finished = pyqtSignal()
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, command, sudo=False, env=None):
        super().__init__()
        self.command = command
        self.sudo = sudo
        self.env = env if env is not None else os.environ.copy()
    
    def run(self):
        try:
            if self.sudo:
                auth_cmd = get_auth_command(self.env)
                self.command = auth_cmd + self.command
                
                # If using sudo -A, ensure SUDO_ASKPASS is set
                if auth_cmd == ["sudo", "-A"] and 'SUDO_ASKPASS' not in self.env:
                    # Import here to avoid circular imports
                    pass  # inlined
                    self.env, _ = prepare_askpass_env()
            
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
                env=self.env
            )
            
            assert process.stdout is not None
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.output.emit(line.strip())
            
            _, stderr = process.communicate()
            if stderr and process.returncode != 0:
                self.error.emit(f"Error: {stderr}")
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Error running command: {str(e)}")
            self.finished.emit()
    
    def _command_exists(self, cmd):
        """Check if a command exists in PATH"""
        return subprocess.run(['which', cmd], capture_output=True).returncode == 0

# === utils: config_utils.py ===
import os
import json

def get_ignore_file_path():
    cfg = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        pass
    return os.path.join(cfg, 'ignored_updates.json')


def load_ignored_updates():
    p = get_ignore_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def save_ignored_updates(items):
    p = get_ignore_file_path()
    try:
        with open(p, 'w') as f:
            json.dump(sorted(list(items)), f)
    except Exception:
        pass


def get_local_updates_file_path():
    cfg = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        pass
    return os.path.join(cfg, 'local_updates.json')


def load_local_update_entries():
    p = get_local_updates_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

# === utils: sys_utils.py ===
import shutil
import os
from typing import Tuple

def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def get_available_aur_helpers() -> list:
    """Get list of available AUR helpers in order of preference."""
    helpers = ['yay', 'paru', 'trizen', 'pikaur']
    return [h for h in helpers if cmd_exists(h)]


def get_aur_helper(preferred: str | None = None) -> str | None:
    """Get the AUR helper to use.
    
    Args:
        preferred: Preferred AUR helper name. If None or not available,
                   will return the first available helper.
    
    Returns:
        Name of the AUR helper to use, or None if none available.
    """
    available = get_available_aur_helpers()
    if not available:
        return None
    
    # If preferred is specified and available, use it
    if preferred and preferred in available:
        return preferred
    
    # Otherwise return the first available
    return available[0]


def get_missing_dependencies() -> list:
    missing = []
    if not cmd_exists("flatpak"):
        missing.append("flatpak")
    if not cmd_exists("git"):
        missing.append("git")
    if not cmd_exists("node"):
        missing.append("nodejs")
    if not cmd_exists("npm"):
        missing.append("npm")
    if not cmd_exists("docker"):
        missing.append("docker")
    # Check if any AUR helper is available
    if not get_available_aur_helpers():
        missing.append("yay or paru")
    return missing


def get_missing_auth_tools() -> list:
    """Get list of missing GUI authentication tools needed for AUR packages"""
    auth_tools = ['kdialog', 'zenity', 'yad']
    available = [tool for tool in auth_tools if cmd_exists(tool)]
    if not available:
        return auth_tools
    return []


def check_aur_authentication_support() -> Tuple[bool, str]:
    """Check if AUR authentication is properly supported
    
    Returns:
        tuple: (is_supported, message)
    """
    missing_auth = get_missing_auth_tools()
    if missing_auth:
        message = (
            "Warning: No GUI authentication tools found for AUR packages.\n"
            f"Please install one of: {', '.join(missing_auth)}\n"
            "Example: sudo pacman -S kdialog (or zenity/yad)"
        )
        return False, message
    return True, "AUR authentication is properly configured"

# === utils: networking.py ===
import subprocess
import json
from threading import Thread

class Networking:
    @staticmethod
    def search_pacman(query, callback):
        def search():
            packages = []
            result = subprocess.run(["pacman", "-Ss", query], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                i = 0
                while i < len(lines):
                    if lines[i].strip() and '/' in lines[i]:
                        parts = lines[i].split()
                        if len(parts) >= 2:
                            name = parts[0].split('/')[-1]
                            version = parts[1]
                            packages.append({
                                'name': name,
                                'version': version,
                                'id': name,
                                'source': 'pacman',
                                'has_update': False
                            })
                    i += 1
            callback(packages)
        Thread(target=search, daemon=True).start()

    @staticmethod
    def search_aur(query, callback):
        def search():
            packages = []
            result_aur = subprocess.run(["curl", "-s", f"https://aur.archlinux.org/rpc/?v=5&type=search&by=name&arg={query}"], capture_output=True, text=True, timeout=10)
            if result_aur.returncode == 0:
                try:
                    data = json.loads(result_aur.stdout)
                    if data.get('results'):
                        for pkg in data['results']:
                            packages.append({
                                'name': pkg.get('Name', ''),
                                'version': pkg.get('Version', ''),
                                'id': pkg.get('Name', ''),
                                'source': 'AUR',
                                'has_update': False,
                                'description': pkg.get('Description', ''),
                                'tags': ', '.join(pkg.get('Keywords', []))
                            })
                except (KeyError, TypeError):
                    # Handle malformed API response data gracefully
                    pass
            callback(packages)
        Thread(target=search, daemon=True).start()

# === utils: styles.py ===
# styles.py - Styles component for Aurora application

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1E1E1E;
    color: #F0F0F0;
}

QWidget {
    background-color: #1E1E1E;
    color: #F0F0F0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QLineEdit {
    background-color: rgba(42, 45, 51, 0.8);
    color: #F0F0F0;
    border: 2px solid rgba(0, 191, 174, 0.2);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 14px;
    selection-background-color: #00BFAE;
}

QLineEdit:focus {
    background-color: rgba(42, 45, 51, 0.9);
    border: 2px solid #00BFAE;
    outline: none;
}

QPushButton {
    background-color: rgba(42, 45, 51, 0.6);
    color: #F0F0F0;
    border: 1px solid rgba(0, 191, 174, 0.2);
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: rgba(42, 45, 51, 0.8);
    border-color: rgba(0, 191, 174, 0.4);
}

QPushButton:pressed {
    background-color: rgba(42, 45, 51, 0.9);
}

QPushButton#sidebarBtn {
    background-color: transparent;
    border: none;
    color: #C9C9C9;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-radius: 6px;
}

QPushButton#sidebarBtn:hover {
    background-color: rgba(42, 45, 51, 0.5);
    color: #F0F0F0;
}

QPushButton#navBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    padding: 0px;
    margin: 8px 0px;
    min-height: 100px;
    max-width: 150px;
    text-align: center;
}

QPushButton#navBtn:hover {
    background-color: rgba(0, 191, 174, 0.1);
    border: none;
}

QPushButton#navBtn:checked {
    background-color: rgba(0, 191, 174, 0.15);
    border: none;
}

QPushButton#navBtn:pressed {
}

QLabel#navIcon {
    background-color: transparent;
    border-radius: 8px;
    font-size: 26px;
    color: #e1e5e9;
}

/* Nav icon container and badge */
QWidget#navIconContainer {
    background-color: transparent;
}

QLabel#navBadge {
    background-color: #E53935;
    color: #FFFFFF;
    border-radius: 9px; /* keep circular for 18px height, will expand width */
    padding: 0px 4px; /* allow dynamic width for multi-digit counts */
    min-width: 18px;
    min-height: 18px;
}

QPushButton#navBtn:hover QLabel#navIcon {
    background-color: transparent;
    color: #ffffff;
}

QPushButton#navBtn:checked QLabel#navIcon {
    background-color: transparent;
    color: #ffffff;
}

QLabel#navText {
    color: #e1e5e9;
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.8px;
    margin-top: 4px;
    text-transform: uppercase;
}

QPushButton#bottomCardBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    padding: 0px;
    margin: 0px;
    min-height: 60px;
    max-width: 150px;
    text-align: center;
}

QPushButton#bottomCardBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
}

QPushButton#bottomCardBtn:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}

QPushButton#bottomCardBtn QLabel {
    color: #ffffff;
}

QLabel#bottomCardIcon {
    background-color: transparent;
    border-radius: 6px;
    font-size: 18px;
    color: #ffffff;
}

QPushButton#bottomCardBtn:hover QLabel#bottomCardIcon {
    background-color: transparent;
}

QLabel#bottomCardText {
    color: #e1e5e9;
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.8px;
    margin-top: 4px;
    text-transform: uppercase;
}

QPushButton#bottomCardBtn:hover QLabel#bottomCardText {
    color: #ffffff;
}

QWidget#sidebar {
    border-right: 1px solid rgba(0, 191, 174, 0.1);
}

QLabel#sidebarHeader {
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 1px;
    text-align: center;
    padding: 10px 0;
    margin-bottom: 10px;
}

QTableWidget {
    background-color: rgba(42, 45, 51, 0.8);
    alternate-background-color: #2B2E34;
    gridline-color: rgba(0, 191, 174, 0.1);
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 8px;
    selection-background-color: rgba(0, 191, 174, 0.3);
    selection-color: #F0F0F0;
}

QTableWidget::item {
    padding: 12px 8px;
    border: none;
    border-bottom: 1px solid rgba(0, 191, 174, 0.05);
}

QTableWidget::item:selected {
    background-color: rgba(0, 191, 174, 0.2);
    color: #F0F0F0;
}

QTableWidget::item:alternate {
    background-color: #25282E;
}

QHeaderView::section {
    background-color: #33373E;
    color: #00BFAE;
    padding: 12px 8px;
    border: none;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid rgba(0, 191, 174, 0.2);
}

QTextEdit {
    background-color: rgba(42, 45, 51, 0.8);
    color: #C9C9C9;
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 6px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 8px;
}

QLabel {
    color: #F0F0F0;
}

QLabel#headerLabel {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
}

QLabel#sectionLabel {
    color: #00BFAE;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QFrame {
    background-color: transparent;
    border: none;
}

QCheckBox {
    color: #F0F0F0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item:hover {
    background-color: rgba(0, 191, 174, 0.1);
}

QListWidget::item:selected {
    background-color: rgba(0, 191, 174, 0.2);
    color: #00BFAE;
}

/* Discover section specific styling */
QTableWidget#discoverTable {
    background-color: #2A2D33;
    alternate-background-color: #2B2E34;
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 4px;
    box-shadow: none;
}

QTableWidget#discoverTable::item {
    padding: 16px 14px;
    border-bottom: 1px solid rgba(0, 191, 174, 0.05);
}

QTableWidget#discoverTable::item:hover {
    background-color: rgba(0, 191, 174, 0.05);
}

QTableWidget#discoverTable::item:alternate {
    background-color: #25282E;
}

QTableWidget#discoverTable::item:selected {
background-color: rgba(0, 191, 174, 0.1);
border-left: 2px solid #00BFAE;
}

QHeaderView::section {
background-color: transparent;
color: #C9C9C9;
padding: 8px 12px;
border: none;
font-weight: 500;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 0.5px;
border-bottom: 1px solid rgba(0, 191, 174, 0.1);
border-radius: 0px;
}

QWidget#sourceChip {
background-color: rgba(0, 191, 174, 0.12);
border: 1px solid rgba(0, 191, 174, 0.35);
border-radius: 12px;
}

QWidget#sourceChip QLabel {
color: #EAF6F5;
font-size: 12px;
padding: 0px;
margin: 0px;
}

QCheckBox#tableCheckbox {
    color: #F0F0F0;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox#tableCheckbox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#tableCheckbox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox#tableCheckbox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#tableCheckbox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

/* Progress bar styling */
QProgressBar {
border: 2px solid rgba(0, 191, 174, 0.2);
border-radius: 4px;
text-align: center;
background-color: rgba(42, 45, 51, 0.6);
    background-color: rgba(42, 45, 51, 0.6);
}

QProgressBar::chunk {
    background-color: #00BFAE;
    border-radius: 2px;
}

/* Loading spinner styles */
QWidget#loadingSpinner {
    background-color: transparent;
    border: none;
}

QWidget#loadingSpinner QLabel {
    background-color: transparent;
    color: #00BFAE;
    font-size: 14px;
    font-weight: 500;
}

/* SourceItem component styles */
SourceItem {
    background-color: transparent;
    border-radius: 8px;
    margin: 2px 0px;
}

SourceItem:hover {
    background-color: rgba(0, 191, 174, 0.05);
    border-radius: 8px;
}

QWidget#sourceIconContainer {
    background-color: rgba(0, 191, 174, 0.1);
    border: 1px solid rgba(0, 191, 174, 0.3);
    border-radius: 8px;
}

QWidget#sourceIconContainer:checked {
    background-color: rgba(0, 191, 174, 0.2);
    border-color: rgba(0, 191, 174, 0.6);
}

QCheckBox#sourceCheckbox {
    color: #F0F0F0;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox#sourceCheckbox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#sourceCheckbox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox#sourceCheckbox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#sourceCheckbox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

/* SourceSelector component styles */
SourceSelector {
    background-color: rgba(42, 45, 51, 0.3);
    border-radius: 10px;
    border: 1px solid rgba(0, 191, 174, 0.1);
}

QLabel#sourceSelectorTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 0px;
}

QPushButton#selectAllBtn {
    background-color: transparent;
    color: #00BFAE;
    border: 1px solid rgba(0, 191, 174, 0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QPushButton#selectAllBtn:hover {
    background-color: rgba(0, 191, 174, 0.1);
    border-color: rgba(0, 191, 174, 0.5);
}

QPushButton#selectAllBtn:pressed {
    background-color: rgba(0, 191, 174, 0.2);
}

/* SourceCard component styles */
SourceCard {
    background-color: rgba(42, 45, 51, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(0, 191, 174, 0.2);
    margin: 4px 0px;
}

QLabel#sourceCardTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* FilterCard component styles */
FilterCard {
    background-color: rgba(42, 45, 51, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(0, 191, 174, 0.2);
    margin: 4px 0px;
}

QLabel#filterCardTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Scroll Bar Styling - Dark Rounded */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: rgba(60, 60, 60, 0.7);
    border-radius: 6px;
    min-height: 20px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(80, 80, 80, 0.9);
}

QScrollBar::handle:vertical:pressed {
    background: rgba(100, 100, 100, 1);
}

QScrollBar::add-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::sub-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    border: none;
    width: 0px;
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(60, 60, 60, 0.7);
    border-radius: 6px;
    min-width: 20px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(80, 80, 80, 0.9);
}

QScrollBar::handle:horizontal:pressed {
    background: rgba(100, 100, 100, 1);
}

QScrollBar::add-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::sub-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
    border: none;
    width: 0px;
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

QScrollArea::corner {
    background: transparent;
    border: none;
}
"""


class Styles:
    """Styles component for managing application styling"""

    @staticmethod
    def get_dark_stylesheet():
        """Return the main dark theme stylesheet"""
        return DARK_STYLESHEET

    @staticmethod
    def get_header_stylesheet():
        """Return stylesheet for header frame"""
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20232A, stop:1 #1E1E1E);
                border-bottom: 1px solid rgba(0, 191, 174, 0.1);
            }
        """

    @staticmethod
    def get_filters_panel_stylesheet():
        """Return stylesheet for filters panel"""
        return """
            QFrame {
                background-color: #0f0f0f;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
        """

    @staticmethod
    def get_separator_stylesheet():
        """Return stylesheet for visual separator"""
        return """
            QFrame {
                color: rgba(0, 191, 174, 0.2);
                background-color: rgba(0, 191, 174, 0.1);
                margin: 8px 0;
                max-height: 1px;
            }
        """

    @staticmethod
    def get_spinner_label_stylesheet():
        """Return stylesheet for spinner label"""
        return """
            QLabel {
                font-size: 32px;
                color: #00BFAE;
            }
        """

# === stores: plugin_store.py ===
"""
NeoArch Plugin Store
Community plugin sharing and discovery system
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional

# Optional import for requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available. Community plugin features will be limited.")

class PluginStore:
    """Manages community plugin sharing and discovery"""

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'aurora'
        self.plugins_dir = self.config_dir / 'plugins'
        self.store_cache = self.config_dir / 'plugin_store_cache.json'

        # Community plugin repository
        self.repo_url = "https://raw.githubusercontent.com/Sanjaya-Danushka/Aurora/main/community_plugins/"
        self.local_plugins = {}

        self._load_cache()

    def _load_cache(self):
        """Load cached plugin information"""
        try:
            if self.store_cache.exists():
                with open(self.store_cache, 'r') as f:
                    self.local_plugins = json.load(f)
        except Exception:
            self.local_plugins = {}

    def _save_cache(self):
        """Save plugin cache"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.store_cache, 'w') as f:
                json.dump(self.local_plugins, f, indent=2)
        except Exception:
            pass

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins"""
        if not REQUESTS_AVAILABLE:
            print("Community plugin discovery requires the 'requests' module.")
            print("Install with: pip install requests")
            return list(self.local_plugins.values())
        assert requests is not None
        
        try:
            # Try to fetch from GitHub repository
            response = requests.get(f"{self.repo_url}index.json", timeout=10)
            if response.status_code == 200:
                remote_plugins = response.json()
                self.local_plugins.update(remote_plugins)
                self._save_cache()
                return list(remote_plugins.values())
        except Exception as e:
            print(f"Failed to fetch community plugins: {e}")
        
        # Fallback to cached plugins
        return list(self.local_plugins.values())

    def install_community_plugin(self, plugin_id: str) -> bool:
        """Install a plugin from the community repository"""
        if not REQUESTS_AVAILABLE:
            print("Community plugin installation requires the 'requests' module.")
            print("Install with: pip install requests")
            return False
        assert requests is not None
        
        try:
            # Get plugin metadata
            plugins = self.discover_plugins()
            plugin_info = None

            for plugin in plugins:
                if plugin.get('id') == plugin_id:
                    plugin_info = plugin
                    break

            if not plugin_info:
                return False

            # Download plugin file
            plugin_url = plugin_info.get('url')
            if plugin_url:
                response = requests.get(plugin_url, timeout=30)
                if response.status_code == 200:
                    # Save to user plugins directory
                    plugin_filename = f"{plugin_id}.py"
                    plugin_path = self.plugins_dir / plugin_filename

                    self.plugins_dir.mkdir(parents=True, exist_ok=True)
                    with open(plugin_path, 'w') as f:
                        f.write(response.text)

                    return True

            # Alternative: use direct GitHub raw URL
            github_url = f"{self.repo_url}{plugin_id}.py"
            response = requests.get(github_url, timeout=30)
            if response.status_code == 200:
                plugin_path = self.plugins_dir / f"{plugin_id}.py"
                self.plugins_dir.mkdir(parents=True, exist_ok=True)
                with open(plugin_path, 'w') as f:
                    f.write(response.text)
                return True

        except Exception as e:
            print(f"Failed to install community plugin {plugin_id}: {e}")

        return False

    def create_plugin_template(self, plugin_name: str, description: str = "") -> str:
        """Create a plugin template for users to customize"""
        template = f'''"""
{plugin_name} - NeoArch Plugin
{description}

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """
    Called when NeoArch starts up
    Use this to initialize your plugin
    """
    try:
        print(f"🚀 {plugin_name} plugin loaded!")
        # Add your startup code here

    except Exception as e:
        print(f"Error in {plugin_name} startup: {{e}}")

def on_tick(app):
    """
    Called periodically (every 60 seconds)
    Use this for background tasks
    """
    try:
        # Add your periodic tasks here
        pass
    except Exception as e:
        print(f"Error in {plugin_name} tick: {{e}}")

def on_view_changed(app, view_id):
    """
    Called when user switches between views
    view_id can be: "discover", "updates", "installed", "bundles", "plugins", "settings"
    """
    try:
        if view_id == "discover":
            # User switched to discover page
            pass
        elif view_id == "plugins":
            # User switched to plugins page
            pass
    except Exception as e:
        print(f"Error in {plugin_name} view change: {{e}}")

# Add your custom functions below
def my_custom_function(app, param=None):
    """
    Example custom function
    You can call this from other parts of your plugin
    """
    try:
        print(f"{plugin_name}: Custom function called with param: {{param}}")
        # Add your custom logic here
    except Exception as e:
        print(f"Error in {plugin_name} custom function: {{e}}")
'''
        return template

    def validate_plugin(self, plugin_path: str) -> Dict:
        """Validate a plugin file and extract metadata"""
        try:
            with open(plugin_path, 'r') as f:
                content = f.read()

            # Extract basic metadata
            metadata = {
                'name': 'Unknown Plugin',
                'description': '',
                'author': 'Unknown',
                'version': '1.0.0',
                'functions': []
            }

            # Parse docstring for name and description
            lines = content.split('\n')
            in_docstring = False
            docstring_lines = []

            for line in lines[:20]:  # Check first 20 lines
                if '"""' in line:
                    if not in_docstring:
                        in_docstring = True
                    else:
                        break
                elif in_docstring:
                    docstring_lines.append(line.strip())

            if docstring_lines:
                metadata['name'] = docstring_lines[0] if docstring_lines else 'Unknown Plugin'
                if len(docstring_lines) > 1:
                    metadata['description'] = ' '.join(docstring_lines[1:])

            # Extract function names
            import ast
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata['functions'].append(node.name)

            return metadata

        except Exception as e:
            return {'error': str(e)}

    def share_plugin(self, plugin_path: str, metadata: Dict) -> bool:
        """Prepare plugin for sharing (creates shareable package)"""
        try:
            # Create a shareable package
            share_dir = self.config_dir / 'shared_plugins'
            share_dir.mkdir(parents=True, exist_ok=True)

            plugin_name = metadata.get('name', 'unknown').replace(' ', '_').lower()
            package_dir = share_dir / plugin_name
            package_dir.mkdir(exist_ok=True)

            # Copy plugin file
            import shutil
            plugin_filename = os.path.basename(plugin_path)
            shutil.copy2(plugin_path, package_dir / plugin_filename)

            # Create metadata file
            with open(package_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # Create README
            readme_content = f"""# {metadata.get('name', 'Plugin')}

{metadata.get('description', '')}

## Installation

Copy the `.py` file to your NeoArch plugins directory:
```
~/.config/aurora/plugins/
```

Then enable it in Settings → Plugins.

## Author

{metadata.get('author', 'Unknown')}

## Version

{metadata.get('version', '1.0.0')}
"""
            with open(package_dir / 'README.md', 'w') as f:
                f.write(readme_content)

            print(f"Plugin prepared for sharing: {package_dir}")
            return True

        except Exception as e:
            print(f"Failed to prepare plugin for sharing: {e}")
            return False

# Example usage in NeoArch plugin
def plugin_store_example(app):
    """Example of how to integrate PluginStore into NeoArch"""

    store = PluginStore()

    # Discover available plugins
    community_plugins = store.discover_plugins()

    # Install a community plugin
    if store.install_community_plugin("example_plugin"):
        app.log("Successfully installed community plugin!")
        app.reload_plugins()

    # Create a new plugin template
    template = store.create_plugin_template(
        "My Custom Plugin",
        "A plugin that does amazing things"
    )

    # Save template to file
    template_path = store.plugins_dir / "my_custom_plugin_template.py"
    with open(template_path, 'w') as f:
        f.write(template)

    app.log(f"Plugin template created: {template_path}")

# === stores: mongo_store.py ===
"""
MongoDB-backed Plugin Store for Aurora/NeoArch
- Discovers plugins from a MongoDB collection
- Installs plugin code either from a stored "code" field or a URL (if available)
- No icon handling

Config:
- AURORA_MONGO_URI: full MongoDB URI (recommended)
- AURORA_MONGO_DB: database name (default: neoarch)
- AURORA_MONGO_COLLECTION: collection name (default: community_plugins)

Fallback config file if env var is not set:
- ~/.config/aurora/mongo_uri.txt containing the URI

Dependencies:
- pymongo (required)
- requests (optional, only if plugins provide a URL to fetch code)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

# Optional imports
try:
    from pymongo import MongoClient as _MongoClient
    MONGO_AVAILABLE = True
except Exception:
    _MongoClient = None  # type: ignore
    MONGO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    requests = None  # type: ignore
    REQUESTS_AVAILABLE = False


class MongoPluginStore:
    """Manages community plugin discovery via MongoDB."""

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "aurora"
        self.plugins_dir = self.config_dir / "plugins"

        self.mongo_uri = os.environ.get("AURORA_MONGO_URI") or self._read_uri_from_file()
        self.db_name = os.environ.get("AURORA_MONGO_DB", "neoarch")
        self.collection_name = os.environ.get("AURORA_MONGO_COLLECTION", "community_plugins")

        self.client: Any = None
        self.db: Any = None
        self.col: Any = None

        if MONGO_AVAILABLE and self.mongo_uri:
            assert _MongoClient is not None
            try:
                self.client = _MongoClient(self.mongo_uri, serverSelectionTimeoutMS=4000)
                # Trigger a simple ping to validate connection
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                self.col = self.db[self.collection_name]
            except Exception:
                self.client = None
                self.db = None
                self.col = None

    def _read_uri_from_file(self) -> Optional[str]:
        try:
            p = self.config_dir / "mongo_uri.txt"
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return None

    def is_configured(self) -> bool:
        return bool(MONGO_AVAILABLE and self.col is not None)

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins from MongoDB.

        Expected document shape (flexible):
        {
          id: str,            # required unique id/slug
          name: str,          # display name
          author: str,        # developer/maintainer
          version: str,       # semantic version
          description: str,   # short description
          code: str,          # optional: plugin script content
          url: str,           # optional: URL to raw .py
          downloads: int,     # optional
          updated_at: any     # optional (for sorting)
        }
        """
        if not self.is_configured():
            return []
        try:
            # Prefer most popular/recent first
            cursor = self.col.find({}, {
                "_id": 1,
                "id": 1,
                "name": 1,
                "author": 1,
                "version": 1,
                "description": 1,
                "downloads": 1,
                "url": 1,
                "code": 1,
                "updated_at": 1,
            }).sort([
                ("downloads", -1),
                ("updated_at", -1),
                ("name", 1),
            ])
            items: List[Dict] = []
            for doc in cursor:
                pid = (doc.get("id") or str(doc.get("_id") or "")).strip()
                if not pid:
                    # Skip records without a stable id
                    continue
                items.append({
                    "id": pid,
                    "name": doc.get("name") or pid,
                    "author": doc.get("author") or "Unknown",
                    "version": doc.get("version") or "1.0.0",
                    "description": doc.get("description") or "",
                    "downloads": int(doc.get("downloads") or 0),
                    # keep url/code for install stage
                    "url": doc.get("url"),
                    "code": doc.get("code"),
                })
            return items
        except Exception:
            return []

    def install_community_plugin(self, plugin_id: str) -> bool:
        """Install a plugin by id.
        - If a 'code' field exists, write it directly.
        - Else if a 'url' exists, fetch it (requires requests).
        """
        if not self.is_configured():
            return False
        try:
            doc = self.col.find_one({"id": plugin_id}) or self.col.find_one({"_id": plugin_id})
            if not doc:
                return False

            code_text: Optional[str] = None
            if isinstance(doc.get("code"), str) and doc.get("code").strip():
                code_text = doc.get("code").strip()
            elif isinstance(doc.get("url"), str) and doc.get("url").strip():
                if not REQUESTS_AVAILABLE:
                    return False
                assert requests is not None
                resp = requests.get(doc.get("url").strip(), timeout=30)
                if resp.status_code == 200:
                    code_text = resp.text

            if not code_text:
                return False

            # Write the plugin file
            safe_id = self._safe_id(plugin_id)
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            plugin_path = self.plugins_dir / f"{safe_id}.py"
            with open(plugin_path, "w", encoding="utf-8") as f:
                f.write(code_text)

            # Increment downloads counter (best-effort)
            try:
                if doc.get("_id") is not None:
                    self.col.update_one({"_id": doc["_id"]}, {"$inc": {"downloads": 1}})
                else:
                    self.col.update_one({"id": plugin_id}, {"$inc": {"downloads": 1}})
            except Exception:
                pass
            return True
        except Exception:
            return False

    def create_plugin_template(self, plugin_name: str, description: str = "") -> str:
        """Generate a plugin template (kept for UI compatibility)."""
        # Define template variables to avoid undefined variable errors
        e = "example_error"
        param = "example_param"
        
        template = f'''"""
{plugin_name} - NeoArch Plugin
{description}

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """
    Called when NeoArch starts up
    Use this to initialize your plugin
    """
    try:
        print(f"🚀 {plugin_name} plugin loaded!")
        # Add your startup code here

    except Exception as e:
        print(f"Error in {plugin_name} startup: {e}")

def on_tick(app):
    """
    Called periodically (every 60 seconds)
    Use this for background tasks
    """
    try:
        # Add your periodic tasks here
        pass
    except Exception as e:
        print(f"Error in {plugin_name} tick: {e}")

def on_view_changed(app, view_id):
    """
    Called when user switches between views
    view_id can be: "discover", "updates", "installed", "bundles", "plugins", "settings"
    """
    try:
        if view_id == "discover":
            # User switched to discover page
            pass
        elif view_id == "plugins":
            # User switched to plugins page
            pass
    except Exception as e:
        print(f"Error in {plugin_name} view change: {e}")

# Add your custom functions below
def my_custom_function(app, param=None):
    """
    Example custom function
    You can call this from other parts of your plugin
    """
    try:
        print(f"{plugin_name}: Custom function called with param: {param}")
        # Add your custom logic here
    except Exception as e:
        print(f"Error in {plugin_name} custom function: {e}")
'''

        return template

    def _safe_id(self, s: str) -> str:
        return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in (s or "").strip())

# === managers: git_manager.py ===
# git_manager.py - Git repository management component for Aurora

import os
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
from PyQt6.QtSvg import QSvgRenderer
from typing import Any


class GitManager(QObject):
    """Git repository management component for Aurora"""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent  # Reference to main window

        # UI elements that will be created
        self.git_section = None  # Reference to the git section widget
        self.recent_repos_label: Any = None
        self.recent_repos_list: Any = None

        # Initialize the Git section UI
        self.create_git_section()

    def create_git_section(self):
        """Create and add the Git section to the sources layout"""
        # Remove previous section if it exists (avoid duplicates after navigation)
        try:
            if self.git_section is not None:
                try:
                    self.git_section.setParent(None)
                except Exception:
                    pass
                self.git_section.deleteLater()
        except Exception:
            pass

        self.git_section = QWidget()
        git_layout = QVBoxLayout(self.git_section)
        git_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin for spacing
        git_layout.setSpacing(10)  # Increase spacing between elements

        # Git section label
        git_label = QLabel("Git Repositories")
        git_label.setObjectName("sectionLabel")
        git_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        git_layout.addWidget(git_label)

        # Main Install from Git button (separate at top)
        install_git_container = QWidget()
        install_git_layout = QHBoxLayout(install_git_container)
        install_git_layout.setContentsMargins(0, 0, 0, 0)
        install_git_layout.setSpacing(8)

        # Git icon
        git_icon_label = QLabel()
        git_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "git.svg")
        try:
            svg_renderer = QSvgRenderer(git_icon_path)
            if svg_renderer.isValid():
                pixmap = QPixmap(20, 20)
                if pixmap.isNull():
                    git_icon_label.setText("📦")
                    git_icon_label.setStyleSheet("font-size: 14px; color: white;")
                else:
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    from PyQt6.QtCore import QRectF
                    svg_renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    git_icon_label.setPixmap(pixmap)
            else:
                git_icon_label.setText("📦")
        except OSError:
            # Handle file loading or parsing errors
            git_icon_label.setText("📦")

        install_git_layout.addWidget(git_icon_label)

        # Install button
        install_git_btn = QPushButton("Install from Git")
        install_git_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        install_git_btn.clicked.connect(self.install_from_git)
        install_git_layout.addWidget(install_git_btn)

        git_layout.addWidget(install_git_container)

        # Secondary buttons widget (at bottom)
        secondary_buttons_widget = QWidget()
        secondary_layout = QHBoxLayout(secondary_buttons_widget)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setSpacing(4)

        # Open Repos button
        open_repos_btn = QPushButton("📁 Open")
        open_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #00BFAE;
            }
        """)
        open_repos_btn.clicked.connect(self.open_git_repos_dir)
        secondary_layout.addWidget(open_repos_btn)

        # Update All button
        update_repos_btn = QPushButton("🔄 Update")
        update_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #00BFAE;
            }
        """)
        update_repos_btn.clicked.connect(self.update_all_git_repos)
        secondary_layout.addWidget(update_repos_btn)

        # Clean button
        clean_repos_btn = QPushButton("🗑️ Clean")
        clean_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #FF6B6B;
            }
        """)
        clean_repos_btn.clicked.connect(self.clean_git_repos)
        secondary_layout.addWidget(clean_repos_btn)

        git_layout.addWidget(secondary_buttons_widget)

        # Recent repos list (compact)
        self.recent_repos_label = QLabel("Recent:")
        self.recent_repos_label.setStyleSheet("color: #C9C9C9; font-size: 10px; margin-top: 4px;")
        git_layout.addWidget(self.recent_repos_label)

        self.recent_repos_list = QListWidget()
        self.recent_repos_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(42, 45, 51, 0.4);
                border: 1px solid rgba(0, 191, 174, 0.15);
                color: #F0F0F0;
                font-size: 10px;
                max-height: 85px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 191, 174, 0.15);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        self.recent_repos_list.itemDoubleClicked.connect(self.open_repo_directory)
        self.recent_repos_list.setVisible(False)  # Initially hidden
        git_layout.addWidget(self.recent_repos_list)

        try:
            insert_at = 2 if self.sources_layout.count() >= 2 else self.sources_layout.count()
            self.sources_layout.insertWidget(insert_at, self.git_section)
        except Exception:
            self.sources_layout.addWidget(self.git_section)

        # Load recent repos on startup
        self.load_recent_git_repos()

    def install_from_git(self):
        """Create a dialog to ask for Git URL"""
        dialog = QDialog()
        dialog.setWindowTitle("Install from Git Repository")
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.2);
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Install Application from Git Repository")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00BFAE;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Enter the Git repository URL to clone and install the application:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # URL input
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://github.com/user/repo.git")
        url_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(42, 45, 51, 0.8);
                color: #F0F0F0;
                border: 2px solid rgba(0, 191, 174, 0.2);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00BFAE;
            }
        """)
        layout.addWidget(url_input)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(42, 45, 51, 0.6);
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.2);
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(42, 45, 51, 0.8);
            }
        """)
        buttons_layout.addWidget(cancel_btn)

        install_btn = QPushButton("Clone & Install")
        install_btn.setDefault(True)
        install_btn.clicked.connect(lambda: self.proceed_git_install(url_input.text().strip(), dialog))
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BFAE;
                color: #1E1E1E;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #00C4B0;
            }
        """)
        buttons_layout.addWidget(install_btn)

        layout.addLayout(buttons_layout)

        dialog.exec()

    def proceed_git_install(self, git_url, dialog):
        """Handle the actual Git cloning and installation process"""
        if not git_url:
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL.")
            return

        # Validate URL format
        if not (git_url.startswith("http://") or git_url.startswith("https://") or git_url.startswith("git@")):
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL (starting with http://, https://, or git@).")
            return

        dialog.accept()

        # Extract repo name from URL
        repo_name = git_url.split('/')[-1].replace('.git', '')

        self.log_signal.emit(f"Starting installation from Git repository: {git_url}")

        def install_from_git_thread():
            try:
                # Clone to user's home directory instead of temp
                home_dir = os.path.expanduser("~")
                git_repos_dir = os.path.join(home_dir, "git-repos")
                os.makedirs(git_repos_dir, exist_ok=True)
                clone_path = os.path.join(git_repos_dir, repo_name)

                # Check if directory already exists
                if os.path.exists(clone_path):
                    self.log_signal.emit(f"Directory {clone_path} already exists. Pulling latest changes...")
                    pull_cmd = ["git", "-C", clone_path, "pull"]
                    pull_result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=60)
                    if pull_result.returncode != 0:
                        self.log_signal.emit(f"Failed to pull latest changes: {pull_result.stderr}")
                        self.show_message.emit("Git Update Failed", f"Failed to update repository: {pull_result.stderr}")
                        return
                    self.log_signal.emit("Repository updated successfully")
                else:
                    # Clone the repository
                    self.log_signal.emit("Cloning repository...")
                    clone_cmd = ["git", "clone", git_url, clone_path]
                    clone_result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)

                    if clone_result.returncode != 0:
                        self.log_signal.emit(f"Failed to clone repository: {clone_result.stderr}")
                        self.show_message.emit("Git Installation Failed", f"Failed to clone repository: {clone_result.stderr}")
                        return

                    self.log_signal.emit("Repository cloned successfully")

                # Change to clone directory
                os.chdir(clone_path)

                # Check for Rust project
                if os.path.exists(os.path.join(clone_path, "Cargo.toml")):
                    self.log_signal.emit("Detected Rust project, installing with cargo...")
                    install_cmd = ["cargo", "install", "--path", clone_path]
                    install_result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600)

                    if install_result.returncode == 0:
                        self.log_signal.emit("Rust package installed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully installed {repo_name} from Git")
                    else:
                        self.log_signal.emit(f"Failed to install Rust package: {install_result.stderr}")
                        self.show_message.emit("Installation Failed", f"Failed to install Rust package: {install_result.stderr}")

                # Check for other common build systems (like autotools)
                elif os.path.exists(os.path.join(clone_path, "configure.ac")) or os.path.exists(os.path.join(clone_path, "configure.in")):
                    self.log_signal.emit("Detected autotools project, building...")
                    configure_cmds = []

                    # Check for autogen.sh
                    if os.path.exists(os.path.join(clone_path, "autogen.sh")):
                        self.log_signal.emit("Running autogen.sh...")
                        configure_cmds.append(["./autogen.sh"])

                    # Run configure
                    if os.path.exists(os.path.join(clone_path, "configure")):
                        self.log_signal.emit("Running configure...")
                        configure_cmds.append(["./configure", "--prefix=/usr/local"])

                    # Run make
                    if os.path.exists(os.path.join(clone_path, "Makefile")):
                        self.log_signal.emit("Running make...")
                        configure_cmds.append(["make", "-j$(nproc)"])
                        self.log_signal.emit("Running make install...")
                        configure_cmds.append(["sudo", "make", "install"])

                    success = True
                    for cmd in configure_cmds:
                        result = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                        if result.returncode != 0:
                            self.log_signal.emit(f"Command failed: {' '.join(cmd)}")
                            self.log_signal.emit(f"Error: {result.stderr}")
                            success = False
                            break

                    if success:
                        self.log_signal.emit("Autotools build completed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully built and installed {repo_name}")

                    else:
                        self.show_message.emit("Build Failed", "Check console output for build errors")

                # Check for Makefile (generic)
                elif os.path.exists(os.path.join(clone_path, "Makefile")):
                    self.log_signal.emit("Detected Makefile, building and installing...")

                    # Try common build patterns
                    build_cmds = [
                        ["make", "-j$(nproc)"],  # Build
                        ["sudo", "make", "install"]  # Install
                    ]

                    success = True
                    for cmd in build_cmds:
                        self.log_signal.emit(f"Running: {' '.join(cmd)}")
                        result = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                        if result.returncode != 0:
                            self.log_signal.emit(f"Command failed: {' '.join(cmd)}")
                            self.log_signal.emit(f"Error: {result.stderr}")
                            success = False
                            break

                    if success:
                        self.log_signal.emit("Build and installation completed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully built and installed {repo_name}")
                    else:
                        self.show_message.emit("Build Failed", "Check console output for build errors")

                else:
                    # No automatic installation detected
                    self.log_signal.emit(f"Repository cloned to: {clone_path}")
                    self.log_signal.emit("No automatic installation method detected.")
                    self.log_signal.emit("To manually build and install:")
                    self.log_signal.emit(f"  cd {clone_path}")
                    self.log_signal.emit("  ls -la  # Check for build files")
                    self.log_signal.emit("  # Common build commands:")
                    self.log_signal.emit("  # ./configure && make && sudo make install")
                    self.log_signal.emit("  # OR")
                    self.log_signal.emit("  # make && sudo make install")
                    self.log_signal.emit("  # OR")
                    self.log_signal.emit("  # cargo install --path .")

                    self.show_message.emit("Git Clone Complete", f"Repository cloned to {clone_path}. Check console for build instructions.")

                # Refresh recent repos list after successful clone
                self.load_recent_git_repos()

            except Exception as e:
                self.log_signal.emit(f"Error during Git installation: {str(e)}")
                self.show_message.emit("Installation Failed", f"Error during installation: {str(e)}")

        Thread(target=install_from_git_thread, daemon=True).start()

    def open_git_repos_dir(self):
        """Open the git-repos directory in file manager"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        try:
            if os.path.exists(git_repos_dir):
                subprocess.run(["xdg-open", git_repos_dir], check=True)
                self.log_signal.emit("Opened git-repos directory")
            else:
                self.log_signal.emit("git-repos directory doesn't exist yet")
                QMessageBox.information(None, "No Repos Yet", "You haven't cloned any Git repositories yet.\nUse 'Install from Git' to get started!")
        except Exception as e:
            self.log_signal.emit(f"Failed to open directory: {e}")

    def update_all_git_repos(self):
        """Update all Git repositories in ~/git-repos"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            self.log_signal.emit("No git-repos directory found")
            return

        repos = [d for d in os.listdir(git_repos_dir)
                if os.path.isdir(os.path.join(git_repos_dir, d)) and
                os.path.exists(os.path.join(git_repos_dir, d, ".git"))]

        if not repos:
            self.log_signal.emit("No Git repositories found")
            return

        self.log_signal.emit(f"Updating {len(repos)} Git repositories...")

        def update_thread():
            updated = 0
            failed = 0
            for repo in repos:
                repo_path = os.path.join(git_repos_dir, repo)
                try:
                    self.log_signal.emit(f"Updating {repo}...")
                    result = subprocess.run(["git", "-C", repo_path, "pull"],
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        updated += 1
                        self.log_signal.emit(f"✓ Updated {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"✗ Failed to update {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"✗ Error updating {repo}: {e}")

            self.log_signal.emit(f"Update complete: {updated} updated, {failed} failed")
            # Emit signal from main thread instead of worker thread
            if updated > 0 or failed > 0:
                # Use QTimer to emit from main thread
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Update Complete", f"Updated {updated} repos, {failed} failed"))

        Thread(target=update_thread, daemon=True).start()

    def clean_git_repos(self):
        """Clean up Git repositories (remove build artifacts, etc.)"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            self.log_signal.emit("No git-repos directory found")
            return

        repos = [d for d in os.listdir(git_repos_dir)
                if os.path.isdir(os.path.join(git_repos_dir, d)) and
                os.path.exists(os.path.join(git_repos_dir, d, ".git"))]

        if not repos:
            self.log_signal.emit("No Git repositories found")
            return

        # Ask for confirmation
        reply = QMessageBox.question(
            None, "Clean Git Repositories",
            f"This will clean build artifacts from {len(repos)} repositories.\n\n"
            "This will run 'git clean -fdx' and remove untracked and ignored files.\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log_signal.emit(f"Cleaning {len(repos)} Git repositories...")

        def clean_thread():
            cleaned = 0
            failed = 0
            for repo in repos:
                repo_path = os.path.join(git_repos_dir, repo)
                try:
                    self.log_signal.emit(f"Cleaning {repo}...")
                    result = subprocess.run(["git", "-C", repo_path, "clean", "-fdx"],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        cleaned += 1
                        self.log_signal.emit(f"✓ Cleaned {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"✗ Failed to clean {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"✗ Error cleaning {repo}: {e}")

            self.log_signal.emit(f"Clean complete: {cleaned} cleaned, {failed} failed")
            if cleaned > 0 or failed > 0:
                # Use QTimer to emit from main thread
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Clean Complete", f"Cleaned {cleaned} repos, {failed} failed"))

        Thread(target=clean_thread, daemon=True).start()

    def load_recent_git_repos(self):
        """Load and display recently cloned Git repositories"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            if self.recent_repos_label:
                self.recent_repos_label.setVisible(False)
            if self.recent_repos_list:
                self.recent_repos_list.setVisible(False)
            return

        repos = []
        try:
            for item in os.listdir(git_repos_dir):
                repo_path = os.path.join(git_repos_dir, item)
                if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
                    # Get last modified time
                    mtime = os.path.getmtime(repo_path)
                    repos.append((item, mtime, repo_path))

            # Sort by modification time (most recent first)
            repos.sort(key=lambda x: x[1], reverse=True)

            # Show only recent 5
            recent_repos = repos[:5]

            if recent_repos and self.recent_repos_list:
                self.recent_repos_list.clear()
                for repo_name, _, repo_path in recent_repos:
                    item = QListWidgetItem(f"📁 {repo_name}")
                    item.setToolTip(f"Double-click to open: {repo_path}")
                    item.setData(Qt.ItemDataRole.UserRole, repo_path)
                    self.recent_repos_list.addItem(item)

                if self.recent_repos_label:
                    self.recent_repos_label.setVisible(True)
                self.recent_repos_list.setVisible(True)
            else:
                if self.recent_repos_label:
                    self.recent_repos_label.setVisible(False)
                if self.recent_repos_list:
                    self.recent_repos_list.setVisible(False)

        except Exception as e:
            self.log_signal.emit(f"Error loading recent repos: {e}")
            if self.recent_repos_label:
                self.recent_repos_label.setVisible(False)
            if self.recent_repos_list:
                self.recent_repos_list.setVisible(False)

    def open_repo_directory(self, item):
        """Open the selected repository directory"""
        repo_path = item.data(Qt.ItemDataRole.UserRole)
        if repo_path and os.path.exists(repo_path):
            try:
                subprocess.run(["xdg-open", repo_path], check=True)
                self.log_signal.emit(f"Opened repository: {os.path.basename(repo_path)}")
            except Exception as e:
                self.log_signal.emit(f"Failed to open repository: {e}")

# === managers: docker_manager.py ===
# docker_manager.py - Docker container management component for Aurora

import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox,
                             QPlainTextEdit, QComboBox, QCheckBox, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor, QCursor
from PyQt6.QtSvg import QSvgRenderer


class DockerManager(QObject):
    """Docker container management component for Aurora"""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent  # Reference to main window

        # UI elements that will be created
        self.docker_section: Any = None  # Reference to the docker section widget
        self.recent_containers_label: Any = None
        self.recent_containers_list: Any = None

        # Initialize the Docker section UI
        self.create_docker_section()

    def create_docker_section(self):
        """Create and add the Docker section to the sources layout"""
        self.docker_section = QWidget()
        docker_layout = QVBoxLayout(self.docker_section)
        docker_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin for spacing
        docker_layout.setSpacing(10)  # Increase spacing between elements

        # Docker section label
        docker_label = QLabel("Docker Containers")
        docker_label.setObjectName("sectionLabel")
        docker_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        docker_layout.addWidget(docker_label)

        # Main Run from Docker button (separate at top)
        install_docker_container = QWidget()
        install_docker_layout = QHBoxLayout(install_docker_container)
        install_docker_layout.setContentsMargins(0, 0, 0, 0)
        install_docker_layout.setSpacing(8)

        # Docker icon
        docker_icon_label = QLabel()
        docker_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "docker.svg")
        try:
            svg_renderer = QSvgRenderer(docker_icon_path)
            if svg_renderer.isValid():
                pixmap = QPixmap(20, 20)
                if pixmap.isNull():
                    docker_icon_label.setText("🐳")
                    docker_icon_label.setStyleSheet("font-size: 14px; color: white;")
                else:
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    from PyQt6.QtCore import QRectF
                    svg_renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    docker_icon_label.setPixmap(pixmap)
            else:
                docker_icon_label.setText("🐳")
        except OSError:
            # Handle file loading or parsing errors
            docker_icon_label.setText("🐳")

        install_docker_layout.addWidget(docker_icon_label)

        # Install button
        install_docker_btn = QPushButton("Run from Docker")
        install_docker_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        install_docker_btn.clicked.connect(self.install_from_docker)
        install_docker_layout.addWidget(install_docker_btn)

        docker_layout.addWidget(install_docker_container)

        # Secondary buttons widget (at bottom)
        secondary_buttons_widget = QWidget()
        secondary_layout = QHBoxLayout(secondary_buttons_widget)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setSpacing(4)

        # List containers button
        list_containers_btn = QPushButton("📋 List")
        list_containers_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #00BFAE;
            }
        """)
        list_containers_btn.clicked.connect(self.list_docker_containers)
        secondary_layout.addWidget(list_containers_btn)

        # Stop containers button
        stop_containers_btn = QPushButton("⏹️ Stop")
        stop_containers_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #FF6B6B;
            }
        """)
        stop_containers_btn.clicked.connect(self.show_stop_menu)
        secondary_layout.addWidget(stop_containers_btn)

        # Clean containers button
        clean_containers_btn = QPushButton("🗑️ Clean")
        clean_containers_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #FF6B6B;
            }
        """)
        clean_containers_btn.clicked.connect(self.clean_docker_containers)
        secondary_layout.addWidget(clean_containers_btn)

        docker_layout.addWidget(secondary_buttons_widget)

        # Recent containers list (compact)
        self.recent_containers_label = QLabel("Containers:")
        self.recent_containers_label.setStyleSheet("color: #C9C9C9; font-size: 10px; margin-top: 4px;")
        docker_layout.addWidget(self.recent_containers_label)

        self.recent_containers_list = QListWidget()
        self.recent_containers_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(42, 45, 51, 0.4);
                border: 1px solid rgba(0, 191, 174, 0.15);
                color: #F0F0F0;
                font-size: 10px;
                max-height: 85px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 191, 174, 0.15);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        self.recent_containers_list.itemDoubleClicked.connect(self.open_container_logs)
        self.recent_containers_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_containers_list.customContextMenuRequested.connect(self.show_container_menu)
        try:
            self.recent_containers_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        except Exception:
            pass
        self.recent_containers_list.setVisible(False)  # Initially hidden
        docker_layout.addWidget(self.recent_containers_list)

        self.sources_layout.addWidget(self.docker_section)

        # Load containers on startup
        self.load_containers(include_all=True)

    def install_from_docker(self):
        self.show_advanced_run_dialog()

    def show_advanced_run_dialog(self):
        import shlex
        dialog = QDialog()
        dialog.setWindowTitle("Run Container from Docker Image")
        dialog.setModal(True)
        dialog.setStyleSheet("QDialog { background-color: #1E1E1E; color: #F0F0F0; border: 1px solid rgba(0, 191, 174, 0.2); }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Run Application from Docker Image")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00BFAE;")
        layout.addWidget(title)
        image_input = QLineEdit()
        image_input.setPlaceholderText("nginx:latest or user/app:v1.0")
        image_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:8px 12px; font-size:14px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Image"))
        layout.addWidget(image_input)
        name_input = QLineEdit()
        name_input.setPlaceholderText("optional container name")
        name_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:6px 10px; font-size:12px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Name"))
        layout.addWidget(name_input)
        ports_edit = QPlainTextEdit()
        ports_edit.setPlaceholderText("8080:80\n127.0.0.1:2222:22/tcp")
        ports_edit.setFixedHeight(70)
        ports_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Ports (one per line: host:container[/proto])"))
        layout.addWidget(ports_edit)
        vols_edit = QPlainTextEdit()
        vols_edit.setPlaceholderText("/host/path:/container/path:ro\n~/data:/var/lib/data:rw")
        vols_edit.setFixedHeight(80)
        vols_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Volumes (one per line: host:container[:ro|rw])"))
        layout.addWidget(vols_edit)
        env_edit = QPlainTextEdit()
        env_edit.setPlaceholderText("KEY=value\nMODE=prod")
        env_edit.setFixedHeight(80)
        env_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Environment (one per line: KEY=VALUE)"))
        layout.addWidget(env_edit)
        opt_row = QHBoxLayout()
        restart_combo = QComboBox()
        restart_combo.addItems(["no", "always", "unless-stopped", "on-failure"])
        detach_chk = QCheckBox("Detach")
        detach_chk.setChecked(True)
        priv_chk = QCheckBox("Privileged")
        gpu_chk = QCheckBox("GPU")
        opt_row.addWidget(QLabel("Restart"))
        opt_row.addWidget(restart_combo)
        opt_row.addStretch()
        opt_row.addWidget(detach_chk)
        opt_row.addWidget(priv_chk)
        opt_row.addWidget(gpu_chk)
        layout.addLayout(opt_row)
        cmd_input = QLineEdit()
        cmd_input.setPlaceholderText("optional command and args")
        cmd_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:6px 10px; font-size:12px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Command"))
        layout.addWidget(cmd_input)
        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setFixedHeight(80)
        preview.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.6); color:#CFCFCF; border:1px solid rgba(0,191,174,0.15); border-radius:6px; }")
        layout.addWidget(QLabel("Preview"))
        layout.addWidget(preview)
        def build_preview():
            image = image_input.text().strip()
            name = name_input.text().strip()
            cmd = ["docker", "run"]
            if detach_chk.isChecked():
                cmd.append("-d")
            if name:
                cmd += ["--name", name]
            rp = restart_combo.currentText()
            if rp != "no":
                cmd += ["--restart", rp]
            if priv_chk.isChecked():
                cmd.append("--privileged")
            if gpu_chk.isChecked():
                cmd += ["--gpus", "all"]
            for ln in ports_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-p", t]
            for ln in vols_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-v", t]
            for ln in env_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-e", t]
            if image:
                cmd.append(image)
            extra = cmd_input.text().strip()
            if extra:
                try:
                    cmd += shlex.split(extra)
                except Exception:
                    cmd.append(extra)
            preview.setPlainText(" ".join(shlex.quote(x) for x in cmd))
        for w in [image_input, name_input, ports_edit, vols_edit, env_edit, restart_combo, detach_chk, priv_chk, gpu_chk, cmd_input]:
            try:
                if hasattr(w, 'textChanged'):
                    w.textChanged.connect(build_preview)
                elif hasattr(w, 'currentIndexChanged'):
                    w.currentIndexChanged.connect(build_preview)
                elif hasattr(w, 'stateChanged'):
                    w.stateChanged.connect(build_preview)
            except Exception:
                pass
        build_preview()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        run_btn = QPushButton("Run Container")
        run_btn.setDefault(True)
        def on_run():
            image = image_input.text().strip()
            name = name_input.text().strip()
            ports = [ln.strip() for ln in ports_edit.toPlainText().splitlines() if ln.strip()]
            vols = [ln.strip() for ln in vols_edit.toPlainText().splitlines() if ln.strip()]
            envs = [ln.strip() for ln in env_edit.toPlainText().splitlines() if ln.strip()]
            rp = restart_combo.currentText().strip()
            detach = detach_chk.isChecked()
            priv = priv_chk.isChecked()
            gpu = gpu_chk.isChecked()
            extra = cmd_input.text().strip()
            self.proceed_advanced_run(image, name, ports, vols, envs, rp, detach, priv, gpu, extra, dialog)
        run_btn.clicked.connect(on_run)
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def ensure_image_local(self, image):
        try:
            r = subprocess.run(["docker", "image", "inspect", image], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True
        except Exception:
            pass
        self.log_signal.emit(f"Pulling image: {image}")
        try:
            p = subprocess.Popen(["docker", "pull", image], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                line = p.stdout.readline() if p.stdout else ""
                if not line and p.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line.strip())
            _, err = p.communicate()
            if p.returncode != 0:
                if err:
                    self.log_signal.emit(err.strip())
                self.show_message.emit("Docker Pull Failed", f"Failed to pull {image}")
                return False
            self.show_message.emit("Docker", f"Pulled {image}")
            return True
        except Exception as e:
            self.log_signal.emit(str(e))
            self.show_message.emit("Docker Pull Failed", str(e))
            return False

    def proceed_advanced_run(self, image, name, ports, vols, envs, restart_policy, detach, privileged, use_gpu, extra_cmd, dialog):
        import shlex
        if not image:
            QMessageBox.warning(None, "Invalid Image", "Please enter a valid Docker image name.")
            return
        dialog.accept()
        self.log_signal.emit(f"Starting Docker container from image: {image}")
        def run_thread():
            try:
                if not self.ensure_image_local(image):
                    return
                cmd = ["docker", "run"]
                if detach:
                    cmd.append("-d")
                if name:
                    cmd += ["--name", name]
                if restart_policy and restart_policy != "no":
                    cmd += ["--restart", restart_policy]
                if privileged:
                    cmd.append("--privileged")
                if use_gpu:
                    cmd += ["--gpus", "all"]
                for p in ports:
                    cmd += ["-p", p]
                for v in vols:
                    hv = v
                    try:
                        parts = v.split(":")
                        if len(parts) >= 2:
                            host = os.path.expanduser(parts[0])
                            cont = parts[1]
                            mode = parts[2] if len(parts) > 2 else None
                            hv = host + ":" + cont + (":" + mode if mode else "")
                    except Exception:
                        hv = v
                    cmd += ["-v", hv]
                for e in envs:
                    cmd += ["-e", e]
                cmd.append(image)
                if extra_cmd:
                    try:
                        cmd += shlex.split(extra_cmd)
                    except Exception:
                        cmd.append(extra_cmd)
                self.log_signal.emit("Running command: " + " ".join(shlex.quote(x) for x in cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    cid = (result.stdout or "").strip()
                    if cid:
                        self.log_signal.emit(f"Container started: {cid}")
                    self.show_message.emit("Container Started", f"Started container from {image}")
                    self.load_containers(include_all=True)
                else:
                    self.log_signal.emit((result.stderr or "Failed").strip())
                    self.show_message.emit("Container Start Failed", (result.stderr or "Failed").strip())
            except Exception as e:
                self.log_signal.emit(f"Error running Docker container: {str(e)}")
                self.show_message.emit("Container Start Failed", f"Error: {str(e)}")
        Thread(target=run_thread, daemon=True).start()

    def proceed_docker_run(self, image_name, port_mapping, dialog):
        """Handle the actual Docker container running process"""
        if not image_name:
            QMessageBox.warning(None, "Invalid Image", "Please enter a valid Docker image name.")
            return

        dialog.accept()

        self.log_signal.emit(f"Starting Docker container from image: {image_name}")

        def run_docker_thread():
            try:
                # Build the docker run command
                cmd = ["docker", "run", "-d", "--name", f"aurora-{image_name.replace('/', '-').replace(':', '-')}-{os.urandom(4).hex()}"]

                # Add port mapping if specified
                if port_mapping:
                    cmd.extend(["-p", port_mapping])

                cmd.append(image_name)

                self.log_signal.emit(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    self.log_signal.emit(f"Container started successfully with ID: {container_id}")
                    self.show_message.emit("Container Started", f"Successfully started container from {image_name}")
                    # Refresh containers list
                    self.load_containers(include_all=True)
                else:
                    self.log_signal.emit(f"Failed to start container: {result.stderr}")
                    self.show_message.emit("Container Start Failed", f"Failed to start container: {result.stderr}")

            except Exception as e:
                self.log_signal.emit(f"Error running Docker container: {str(e)}")
                self.show_message.emit("Container Start Failed", f"Error: {str(e)}")

        Thread(target=run_docker_thread, daemon=True).start()

    def list_docker_containers(self):
        """List all Docker containers"""
        try:
            result = subprocess.run(["docker", "ps", "-a", "--format", "table {{.Names}}\\t{{.Image}}\\t{{.Status}}"],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.log_signal.emit("Docker containers:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        self.log_signal.emit(f"  {line}")
            else:
                self.log_signal.emit(f"Failed to list containers: {result.stderr}")
        except Exception as e:
            self.log_signal.emit(f"Error listing containers: {str(e)}")

    def stop_docker_containers(self):
        """Stop running Docker containers"""
        try:
            # Get running containers
            result = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split('\n')
                self.log_signal.emit(f"Stopping {len(containers)} containers...")

                for container_id in containers:
                    stop_result = subprocess.run(["docker", "stop", container_id], capture_output=True, text=True, timeout=30)
                    if stop_result.returncode == 0:
                        self.log_signal.emit(f"Stopped container: {container_id}")
                    else:
                        self.log_signal.emit(f"Failed to stop container {container_id}: {stop_result.stderr}")

                self.show_message.emit("Containers Stopped", f"Stopped {len(containers)} containers")
                # Refresh containers list
                self.load_containers(include_all=True)
        except Exception as e:
            self.log_signal.emit(f"Error stopping containers: {str(e)}")

    def start_container(self, name):
        try:
            r = subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Started {name}")
            else:
                self.show_message.emit("Docker", f"Failed to start {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error starting {name}: {e}")
        self.load_containers(include_all=True)

    def stop_container(self, name):
        try:
            r = subprocess.run(["docker", "stop", name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Stopped {name}")
            else:
                self.show_message.emit("Docker", f"Failed to stop {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error stopping {name}: {e}")
        self.load_containers(include_all=True)

    def restart_container(self, name):
        try:
            r = subprocess.run(["docker", "restart", name], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Restarted {name}")
            else:
                self.show_message.emit("Docker", f"Failed to restart {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error restarting {name}: {e}")
        self.load_containers(include_all=True)

    def remove_container(self, name):
        try:
            r = subprocess.run(["docker", "rm", name], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Removed {name}")
            else:
                self.show_message.emit("Docker", f"Failed to remove {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error removing {name}: {e}")
        self.load_containers(include_all=True)

    def remove_all_exited(self):
        try:
            r = subprocess.run(["docker", "container", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", "Removed exited containers")
            else:
                self.show_message.emit("Docker", f"Failed to prune: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error pruning: {e}")
        self.load_containers(include_all=True)

    def show_stop_menu(self):
        container_list = self.recent_containers_list
        if container_list is None:
            return
        sender = self.sender()
        menu = QMenu()
        selected = [it.data(Qt.ItemDataRole.UserRole) for it in container_list.selectedItems()]
        act_start = menu.addAction("Start Selected")
        act_stop = menu.addAction("Stop Selected")
        act_restart = menu.addAction("Restart Selected")
        act_remove = menu.addAction("Remove Selected")
        act_shell_sel = menu.addAction("Open Shell in Selected")
        menu.addSeparator()
        act_stop_all = menu.addAction("Stop All")
        act_remove_exited = menu.addAction("Remove All Exited")
        # Enable rules
        has_sel = bool(selected)
        act_start.setEnabled(has_sel)
        act_stop.setEnabled(has_sel)
        act_restart.setEnabled(has_sel)
        act_remove.setEnabled(has_sel)
        act_shell_sel.setEnabled(has_sel)
        # Exec menu
        pos = sender.mapToGlobal(QPoint(0, sender.height())) if hasattr(sender, 'mapToGlobal') else QCursor.pos()
        action = menu.exec(pos)
        if action is None:
            return
        if action == act_start:
            for n in selected:
                self.start_container(n)
        elif action == act_stop:
            for n in selected:
                self.stop_container(n)
        elif action == act_restart:
            for n in selected:
                self.restart_container(n)
        elif action == act_remove:
            for n in selected:
                self.remove_container(n)
        elif action == act_stop_all:
            self.stop_docker_containers()
        elif action == act_remove_exited:
            self.remove_all_exited()
        elif action == act_shell_sel:
            for n in selected:
                self.open_shell_in_container(n)

    def show_container_menu(self, pos):
        container_list = self.recent_containers_list
        if container_list is None:
            return
        item = container_list.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        act_logs = menu.addAction("View Logs")
        act_shell = menu.addAction("Open Shell")
        act_start = menu.addAction("Start")
        act_stop = menu.addAction("Stop")
        act_restart = menu.addAction("Restart")
        act_remove = menu.addAction("Remove")
        action = menu.exec(container_list.mapToGlobal(pos))
        if action is None:
            return
        if action == act_logs:
            self.open_container_logs(item)
        elif action == act_shell:
            self.open_shell_in_container(name)
        elif action == act_start:
            self.start_container(name)
        elif action == act_stop:
            self.stop_container(name)
        elif action == act_restart:
            self.restart_container(name)
        elif action == act_remove:
            self.remove_container(name)

    def _find_terminal_emulator(self):
        candidates = [
            "gnome-terminal",
            "konsole",
            "alacritty",
            "kitty",
            "xfce4-terminal",
            "tilix",
            "wezterm",
            "footclient",
            "xterm",
            "lxterminal",
        ]
        for name in candidates:
            if shutil.which(name):
                return name
        return None

    def _build_terminal_args(self, term: str, command: str, title: str | None = None):
        # Run command inside bash -lc to interpret; keep window open after exit
        if term == "gnome-terminal":
            args = [term, "--", "bash", "-lc", command]
            if title:
                args.insert(1, "--title=%s" % title)
            return args
        if term == "konsole":
            args = [term, "-e", "bash", "-lc", command]
            if title:
                args.extend(["--title", title])
            return args
        if term in ("alacritty", "tilix"):
            return [term, "-e", "bash", "-lc", command]
        if term == "kitty":
            return [term, "bash", "-lc", command]
        if term == "wezterm":
            return [term, "start", "--", "bash", "-lc", command]
        if term == "footclient":
            return [term, "bash", "-lc", command]
        if term == "xterm":
            return [term, "-e", "bash", "-lc", command]
        if term == "xfce4-terminal" or term == "lxterminal":
            # These expect a single string for -e
            return [term, "-e", f"bash -lc \"{command}\""]
        # Fallback: try to run in xterm-like
        return [term, "-e", "bash", "-lc", command]

    def open_shell_in_container(self, name: str):
        import shlex
        name_q = shlex.quote(name)
        inner = f"docker exec -it {name_q} bash || docker exec -it {name_q} sh"
        cmd = inner + "; echo; echo 'Shell exited.'; echo 'Press Enter to close...'; read"
        term = self._find_terminal_emulator()
        if not term:
            self.show_message.emit("Docker", "No terminal emulator found. Install gnome-terminal/konsole/xterm/kitty/etc.")
            return
        try:
            args = self._build_terminal_args(term, cmd, title=f"Container: {name}")
            subprocess.Popen(args)
            self.show_message.emit("Docker", f"Opening shell in {name}...")
        except Exception as e:
            self.show_message.emit("Docker", f"Failed to open shell: {e}")

    def remove_docker_section(self):
        """Remove the Docker section from the sources layout"""
        if self.docker_section and self.sources_layout:
            self.sources_layout.removeWidget(self.docker_section)
            self.docker_section.setParent(None)
            self.docker_section.deleteLater()
            self.docker_section = None
            self.log_signal.emit("Docker section removed from sources panel")
            # Clear the reference in parent so it can be recreated
            if self.parent:
                self.parent.docker_manager = None

    def clean_docker_containers(self):
        """Clean up Docker containers and images"""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                None, "Clean Docker",
                "This will remove stopped containers and unused images.\n\nAre you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            self.log_signal.emit("Cleaning Docker containers and images...")

            # Remove stopped containers
            clean_result = subprocess.run(["docker", "container", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if clean_result.returncode == 0:
                self.log_signal.emit("Removed stopped containers")
            else:
                self.log_signal.emit(f"Failed to clean containers: {clean_result.stderr}")

            # Remove unused images
            image_result = subprocess.run(["docker", "image", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if image_result.returncode == 0:
                self.log_signal.emit("Removed unused images")
            else:
                self.log_signal.emit(f"Failed to clean images: {image_result.stderr}")

            self.show_message.emit("Docker Clean Complete", "Cleaned containers and images")

        except Exception as e:
            self.log_signal.emit(f"Error cleaning Docker: {str(e)}")

    def load_containers(self, include_all: bool = True):
        """Load and display Docker containers (running or all)"""
        container_list = self.recent_containers_list
        container_label = self.recent_containers_label
        if container_list is None or container_label is None:
            return
        try:
            base = ["docker", "ps"]
            if include_all:
                base.append("-a")
            base += ["--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"]
            result = subprocess.run(base, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout is not None:
                containers = []
                for line in [l for l in result.stdout.strip().split('\n') if l.strip()]:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        name = parts[0]
                        image = parts[1]
                        status = parts[2]
                        ports = parts[3] if len(parts) > 3 else ""
                        containers.append((name, image, status, ports))

                container_list.clear()
                if containers:
                    for name, image, status, ports in containers:
                        status_info = f" - {status}" if status else ""
                        port_info = f" ({ports})" if ports else ""
                        item = QListWidgetItem(f"🐳 {name} - {image}{status_info}{port_info}")
                        item.setToolTip(f"Container: {name}\nImage: {image}\nStatus: {status}\nPorts: {ports}")
                        item.setData(Qt.ItemDataRole.UserRole, name)
                        container_list.addItem(item)
                    container_label.setVisible(True)
                    container_list.setVisible(True)
                else:
                    container_label.setVisible(False)
                    container_list.setVisible(False)
            else:
                container_label.setVisible(False)
                container_list.setVisible(False)

        except Exception as e:
            self.log_signal.emit(f"Error loading containers: {e}")
            container_label.setVisible(False)
            container_list.setVisible(False)

    def open_container_logs(self, item):
        """Show logs for the selected container"""
        container_name = item.data(Qt.ItemDataRole.UserRole)
        if container_name:
            try:
                result = subprocess.run(["docker", "logs", "--tail", "50", container_name],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.log_signal.emit(f"Logs for container '{container_name}':")
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            self.log_signal.emit(f"  {line}")
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip():
                                self.log_signal.emit(f"  [ERR] {line}")
                else:
                    self.log_signal.emit(f"Failed to get logs for {container_name}: {result.stderr}")
            except Exception as e:
                self.log_signal.emit(f"Error getting container logs: {str(e)}")

# === managers: plugin_manager.py ===
import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer


class PluginsManager:
    def __init__(self, app):
        self.app = app

    def install_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            # Already installed?
            if plugins_view.is_installed(spec):
                self._message("Plugins", f"{spec.get('name')} is already installed")
                QTimer.singleShot(0, plugins_view.refresh_all)
                return
            pkg = spec.get('pkg')
            if not pkg:
                self._message("Plugins", "No package specified for installation")
                return
            pass  # inlined
            auth_cmd = get_auth_command()
            cmd = auth_cmd + ["pacman", "-S", "--noconfirm", pkg]
            self._log(f"Installing plugin package: {' '.join(cmd)}")

            def _run():
                try:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:  # type: ignore
                        if line:
                            self._log(line.rstrip())
                    rc = proc.wait()
                    if rc == 0:
                        self._message("Plugins", f"Installed {spec.get('name')}")
                    else:
                        self._message("Plugins", f"Install failed (code {rc})")
                except Exception as e:
                    self._message("Plugins", f"Install failed: {e}")
                finally:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, False))
                    QTimer.singleShot(200, plugins_view.refresh_all)

            Thread(target=_run, daemon=True).start()
        except Exception as e:
            self._message("Plugins", f"Install error: {e}")

    def launch_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            cmd = spec.get('cmd')
            if not cmd:
                self._message("Plugins", "No launch command defined")
                return
            use_pkexec = plugin_id in ("timeshift",)
            terminal_apps = ["htop", "btop", "nvtop"]
            use_terminal = cmd in terminal_apps
            argv = [cmd]
            if use_pkexec:
                pass  # inlined
                auth_cmd = get_auth_command()
                argv = auth_cmd + argv
            if use_terminal:
                terminal_cmd = self._get_terminal_command()
                if terminal_cmd:
                    argv = terminal_cmd + argv
            self._log(f"Launching: {' '.join(argv)}")
            try:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            except Exception as e:
                self._message("Plugins", f"Launch failed: {e}")
        except Exception as e:
            self._message("Plugins", f"Launch error: {e}")

    def uninstall_by_id(self, plugins_view, plugin_id):
        try:
            spec = plugins_view.get_plugin(plugin_id)
            if not spec:
                return
            pkg = spec.get('pkg')
            if not pkg:
                self._message("Plugins", "No package specified for uninstall")
                return
            # If not installed, just refresh UI
            if not plugins_view.is_installed(spec):
                QTimer.singleShot(0, plugins_view.refresh_all)
                return
            pass  # inlined
            auth_cmd = get_auth_command()
            cmd = auth_cmd + ["pacman", "-R", "--noconfirm", pkg]
            self._log(f"Uninstalling plugin package: {' '.join(cmd)}")

            def _run():
                try:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, True))
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:  # type: ignore
                        if line:
                            self._log(line.rstrip())
                    rc = proc.wait()
                    if rc == 0:
                        self._message("Plugins", f"Uninstalled {spec.get('name')}")
                    else:
                        self._message("Plugins", f"Uninstall failed (code {rc})")
                except Exception as e:
                    self._message("Plugins", f"Uninstall failed: {e}")
                finally:
                    QTimer.singleShot(0, lambda: plugins_view.set_installing(plugin_id, False))
                    QTimer.singleShot(200, plugins_view.refresh_all)

            Thread(target=_run, daemon=True).start()
        except Exception as e:
            self._message("Plugins", f"Uninstall error: {e}")

    def open_plugins_folder(self):
        try:
            folder = self.app.get_user_plugins_dir()
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
            subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._message("Plugins", f"Cannot open folder: {e}")

    def _log(self, msg):
        try:
            self.app.log_signal.emit(msg)
        except Exception:
            pass

    @staticmethod
    def _get_terminal_command():
        terminals = ["kitty", "alacritty", "gnome-terminal", "konsole", "xterm"]
        for term in terminals:
            if shutil.which(term):
                if term == "kitty":
                    return [term, "-e"]
                elif term == "alacritty":
                    return [term, "-e"]
                elif term == "gnome-terminal":
                    return [term, "--", "bash", "-c"]
                elif term == "konsole":
                    return [term, "-e"]
                elif term == "xterm":
                    return [term, "-e"]
        return None

    def _message(self, title, text):
        try:
            self.app.show_message.emit(title, text)
        except Exception:
            pass

# === services: install_service.py ===
import os
import re
import subprocess
import time
from threading import Thread, Event


def install_packages(app, packages_by_source: dict):
    """Install packages from multiple sources.
    
    Note: This function has high cyclomatic complexity (76) due to handling
    multiple package sources (pacman, AUR, Flatpak, npm, pip, cargo, snap).
    TODO: Consider refactoring into separate handler functions per source.
    """
    def install():
        app.install_cancel_event = Event()
        app.installation_progress.emit("start", True)
        app.log_signal.emit("Installation thread started")

        success = True
        current_download_info = ""

        total_packages = sum(len(pkgs) for pkgs in packages_by_source.values())
        total_sources = len(packages_by_source)
        completed_packages = 0
        completed_sources = 0
        force_sudo = bool(getattr(app, 'force_sudo_install', False))

        def update_progress_message(msg: str = ""):
            base_msg = f"Installing: {completed_packages}/{total_packages} packages"
            try:
                if current_download_info and msg:
                    app.ui_call.emit(lambda: app.loading_widget.set_message(f"{base_msg}\n{current_download_info}"))
                elif current_download_info:
                    app.ui_call.emit(lambda: app.loading_widget.set_message(f"{base_msg}\n{current_download_info}"))
                elif msg:
                    app.ui_call.emit(lambda: app.loading_widget.set_message(f"{base_msg}\n{msg}"))
                else:
                    app.ui_call.emit(lambda: app.loading_widget.set_message(base_msg))
            except Exception:
                pass

        def parse_output_line(line: str):
            nonlocal current_download_info
            if "downloading" in line.lower() and ("mib" in line.lower() or "kib" in line.lower() or "gib" in line.lower()):
                size_match = re.search(r'\(([-\d.]+)\s*(MiB|KiB|GiB|B)\)', line)
                if size_match:
                    size, unit = size_match.groups()
                    current_download_info = f"Downloading {size} {unit}"
                    update_progress_message("")
            elif re.search(r'\[.*\]\s*\d+%', line):
                progress_match = re.search(r'(\d+)%', line)
                if progress_match:
                    percentage = progress_match.group(1)
                    if current_download_info:
                        current_download_info = f"{current_download_info} - {percentage}%"
                    else:
                        current_download_info = f"Downloading... {percentage}%"
                    update_progress_message("")
            elif "installed" in line.lower() or "upgraded" in line.lower():
                current_download_info = ""
                update_progress_message("")

        try:
            for source, packages in packages_by_source.items():
                if app.install_cancel_event.is_set():
                    app.log_signal.emit("Installation cancelled by user")
                    app.installation_progress.emit("cancelled", False)
                    return

                update_progress_message(f"Installing from {source}...")

                # Prepare default environment (can be overridden per-source)
                env = os.environ.copy()

                if source == 'pacman':
                    cmd = ["pacman", "-S", "--noconfirm"] + packages
                elif source == 'AUR':
                    # Get the configured AUR helper
                    preferred = app.settings.get('aur_helper', 'auto')
                    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
                    if not aur_helper:
                        app.log_signal.emit("Error: No AUR helper available. Install yay, paru, trizen, or pikaur.")
                        success = False
                        break
                    
                    # Configure AUR helper - use pkexec for proper GUI authentication
                    cmd = [aur_helper, "-S", "--noconfirm"] + packages
                elif source == 'Flatpak':
                    try:
                        app.ensure_flathub_user_remote()
                    except Exception:
                        pass
                    # In sudo mode install system-wide; otherwise user-scoped
                    if force_sudo:
                        cmd = ["flatpak", "install", "-y", "--noninteractive", "flathub"] + packages
                    else:
                        cmd = ["flatpak", "--user", "install", "-y", "--noninteractive", "flathub"] + packages
                elif source == 'npm':
                    if not force_sudo:
                        try:
                            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                            os.makedirs(npm_prefix, exist_ok=True)
                            env['npm_config_prefix'] = npm_prefix
                            env['NPM_CONFIG_PREFIX'] = npm_prefix
                            env['PREFIX'] = npm_prefix
                            env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
                        except Exception:
                            pass
                    cmd = ["npm", "install", "-g"] + packages
                else:
                    app.log_signal.emit(f"Unknown source {source} for packages {packages}")
                    continue

                app.log_signal.emit(f"Running command for {source}: {' '.join(cmd)}")

                if app.install_cancel_event.is_set():
                    app.log_signal.emit("Installation cancelled by user")
                    app.installation_progress.emit("cancelled", False)
                    return

                # For AUR, prepare askpass environment but DON'T use pkexec/sudo wrapper
                # AUR helpers MUST run as normal user for security
                # The helper will internally use sudo when needed (e.g., for pacman -U)
                if source == 'AUR':
                    app.log_signal.emit(f"AUR install (as user): {' '.join(cmd)}")
                    # Setup askpass so the AUR helper can authenticate internally
                    if not env.get('SUDO_ASKPASS'):
                        env, cleanup_path = app.prepare_askpass_env()
                
                # For Flatpak with sudo, ensure proper authentication
                if source == 'Flatpak' and force_sudo:
                    # Flatpak system-wide installation needs polkit authentication
                    if not env.get('SUDO_ASKPASS'):
                        env, cleanup_path = app.prepare_askpass_env()
                
                worker = CommandWorker(cmd, sudo=False, env=env)
                worker.output.connect(lambda msg: app.log_signal.emit(msg))
                worker.error.connect(lambda msg: app.log_signal.emit(msg))
                worker.output.connect(parse_output_line)

                try:
                    exec_cmd = worker.command
                    # Use appropriate auth command based on environment
                    if source == 'pacman':
                        pass  # inlined
                        auth_cmd = get_auth_command(worker.env)
                        exec_cmd = auth_cmd + exec_cmd
                        app.log_signal.emit(f"Pacman command with {auth_cmd[0]}: {' '.join(exec_cmd)}")
                    elif force_sudo and source in ('Flatpak', 'npm'):
                        pass  # inlined
                        auth_cmd = get_auth_command(worker.env)
                        exec_cmd = auth_cmd + exec_cmd
                    
                    # Ensure DISPLAY and other GUI environment variables are set
                    # For pacman: pkexec needs these to show GUI password dialog
                    # For AUR: the helper needs these for its own GUI dialogs and sudo prompts
                    if source in ('pacman', 'AUR'):
                        if 'DISPLAY' not in worker.env and 'DISPLAY' in os.environ:
                            worker.env['DISPLAY'] = os.environ['DISPLAY']
                        if 'XAUTHORITY' not in worker.env and 'XAUTHORITY' in os.environ:
                            worker.env['XAUTHORITY'] = os.environ['XAUTHORITY']
                        if 'WAYLAND_DISPLAY' not in worker.env and 'WAYLAND_DISPLAY' in os.environ:
                            worker.env['WAYLAND_DISPLAY'] = os.environ['WAYLAND_DISPLAY']
                        if 'DBUS_SESSION_BUS_ADDRESS' not in worker.env and 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                            worker.env['DBUS_SESSION_BUS_ADDRESS'] = os.environ['DBUS_SESSION_BUS_ADDRESS']
                    
                    # Only pacman with pkexec needs to avoid setsid (breaks D-Bus connection)
                    # AUR runs as normal user so it can use setsid
                    use_setsid = source not in ('pacman',)
                    
                    process = subprocess.Popen(
                        exec_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        bufsize=1,
                        preexec_fn=os.setsid if use_setsid else None,
                        env=worker.env
                    )

                    while True:
                        if app.install_cancel_event.is_set():
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                            app.log_signal.emit("Installation cancelled by user")
                            app.installation_progress.emit("cancelled", False)
                            return

                        if process.poll() is not None:
                            break

                        if process.stdout:
                            line = process.stdout.readline()
                            if line:
                                line = line.strip()
                                parse_output_line(line)
                                worker.output.emit(line)

                        time.sleep(0.1)

                    if process.returncode == 0:
                        completed_packages += len(packages)
                        completed_sources += 1
                        update_progress_message(f"Completed {source} packages")
                        app.log_signal.emit(f"Successfully installed {len(packages)} {source} package(s)")
                    else:
                        success = False
                        if process.stderr:
                            error_output = process.stderr.read()
                            if error_output:
                                app.log_signal.emit(f"Process stderr: {error_output}")
                                # Check if user cancelled password dialog or if authentication failed
                                if source == 'AUR' and ("cancelled" in error_output.lower() or "authentication failed" in error_output.lower() or process.returncode == 1):
                                    # Check if this might be due to missing authentication tools
                                    if "sudo: no askpass program specified" in error_output.lower() or "authentication agent" in error_output.lower():
                                        app.log_signal.emit("Error: Authentication failed - no GUI password dialog available")
                                        app.log_signal.emit("This usually means you need to install a GUI authentication tool.")
                                        app.log_signal.emit("Please install: sudo pacman -S kdialog (or zenity/yad)")
                                    else:
                                        app.log_signal.emit("AUR installation cancelled by user")
                                    app.installation_progress.emit("cancelled", False)
                                    return
                                # Fallback: npm EACCES -> try with system privileges (polkit)
                                if source == 'npm' and ("EACCES" in error_output or "permission denied" in error_output.lower()):
                                    try:
                                        app.log_signal.emit("Permission denied installing npm package(s). Retrying with system privileges (polkit)...")
                                        env2 = os.environ.copy()
                                        pass  # inlined
                                        auth_cmd2 = get_auth_command(env2)
                                        exec_cmd2 = auth_cmd2 + ["npm", "install", "-g"] + packages
                                        process2 = subprocess.Popen(
                                            exec_cmd2,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            stdin=subprocess.DEVNULL,
                                            text=True,
                                            bufsize=1,
                                            preexec_fn=os.setsid,
                                            env=env2
                                        )
                                        while True:
                                            if app.install_cancel_event.is_set():
                                                process2.terminate()
                                                try:
                                                    process2.wait(timeout=5)
                                                except subprocess.TimeoutExpired:
                                                    process2.kill()
                                                app.log_signal.emit("Installation cancelled by user")
                                                app.installation_progress.emit("cancelled", False)
                                                return
                                            if process2.poll() is not None:
                                                break
                                            if process2.stdout:
                                                line2 = process2.stdout.readline()
                                                if line2:
                                                    line2 = line2.strip()
                                                    parse_output_line(line2)
                                                    worker.output.emit(line2)
                                            time.sleep(0.1)
                                        if process2.returncode == 0:
                                            success = True
                                            completed_packages += len(packages)
                                            completed_sources += 1
                                            update_progress_message(f"Completed {source} packages (elevated)")
                                            app.log_signal.emit(f"Successfully installed {len(packages)} {source} package(s) with system privileges")
                                        else:
                                            err2 = process2.stderr.read() if process2.stderr else ''
                                            worker.error.emit(f"Error: {err2 or error_output}")
                                        continue
                                    except Exception as _e:
                                        worker.error.emit(f"Error: {str(_e)}")
                                
                                error_text = f"Error: {error_output}"
                                if "Cannot change ownership" in error_output and "Value too large for defined data type" in error_output:
                                    error_text += "\n\nThis error occurs when tar tries to set file ownership to UIDs/GIDs that don't exist in the current environment.\n"
                                    error_text += "To fix this, you can modify packaging/PKGBUILD to add '--no-same-owner' to the tar command.\n"
                                    error_text += "For example, change 'tar -xzf file.tar.gz' to 'tar -xzf file.tar.gz --no-same-owner'"
                                worker.error.emit(error_text)
                finally:
                    # Cleanup askpass script if used for Flatpak
                    if source == 'Flatpak' and 'cleanup_path' in locals() and cleanup_path and os.path.exists(cleanup_path):
                        try:
                            os.remove(cleanup_path)
                        except Exception:
                            pass

            if success and not app.install_cancel_event.is_set():
                update_progress_message("Installation complete!")
                app.log_signal.emit("Install completed")
                app.show_message.emit("Installation Complete", f"Successfully installed {total_packages} package(s).")
                app.installation_progress.emit("success", False)
            elif not success and not app.install_cancel_event.is_set():
                app.log_signal.emit("Install failed")
                app.installation_progress.emit("failed", False)

        except Exception as e:
            app.log_signal.emit(f"Error in installation thread: {str(e)}")
            app.installation_progress.emit("failed", False)
        finally:
            try:
                # Reset sudo mode flag if set by caller
                if hasattr(app, 'force_sudo_install'):
                    app.force_sudo_install = False
            except Exception:
                pass
            if hasattr(app, 'install_cancel_event'):
                delattr(app, 'install_cancel_event')

    Thread(target=install, daemon=True).start()

# === services: bundle_service.py ===
import os
import json
import subprocess
from threading import Thread
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QLabel, QInputDialog, QMessageBox


def add_selected_to_bundle(app):
    items = []
    for row in range(app.package_table.rowCount()):
        checkbox = app.get_row_checkbox(row)
        if checkbox is not None and checkbox.isChecked():
            info = app.get_row_info(row)
            if info.get("name") and info.get("source"):
                items.append(info)
    if not items:
        app.log("No selected rows to add to bundle")
        return
    existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
    added = 0
    for it in items:
        key = (it.get('source'), it.get('id') or it.get('name'))
        if key not in existing:
            app.bundle_items.append(it)
            existing.add(key)
            added += 1
    app.log(f"Added {added} item(s) to bundle")
    if app.current_view == "bundles":
        refresh_bundles_table(app)


def refresh_bundles_table(app):
    if app.current_view != "bundles":
        return
    app.package_table.setRowCount(0)
    app.package_table.setUpdatesEnabled(False)
    for it in app.bundle_items:
        pkg = {
            'name': it.get('name', ''),
            'id': it.get('id') or it.get('name', ''),
            'version': it.get('version', ''),
            'source': it.get('source', ''),
        }
        app.add_discover_row(pkg)
    app.package_table.setUpdatesEnabled(True)
    try:
        app.package_table.clearSelection()
    except Exception:
        pass
    app.load_more_btn.setVisible(False)
    try:
        app.package_table.setVisible(True)
    except Exception:
        pass


def export_bundle(app):
    if not app.bundle_items:
        app.display_message("Export Bundle", "Bundle is empty")
        return
    path, _ = QFileDialog.getSaveFileName(app, "Export Bundle", os.path.expanduser("~"), "Bundle JSON (*.json)")
    if not path:
        return
    data = {"app": "NeoArch", "items": app.bundle_items}
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        app.display_message("Export Bundle", f"Saved {len(app.bundle_items)} items to {path}")
    except Exception as e:
        app.display_message("Export Bundle", f"Failed: {e}")


def import_bundle(app):
    path, _ = QFileDialog.getOpenFileName(app, "Import Bundle", os.path.expanduser("~"), "Bundle JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list):
            app.display_message("Import Bundle", "Invalid bundle file")
            return
        existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            src = (it.get('source') or '').strip()
            nm = (it.get('name') or '').strip()
            pkg_id = (it.get('id') or nm).strip()
            if not src or not nm:
                continue
            key = (src, pkg_id or nm)
            if key not in existing:
                app.bundle_items.append({
                    'name': nm,
                    'id': pkg_id or nm,
                    'version': (it.get('version') or '').strip(),
                    'source': src,
                })
                existing.add(key)
                added += 1
        app.display_message("Import Bundle", f"Added {added} items")
        if app.current_view == "bundles":
            refresh_bundles_table(app)
    except Exception as e:
        app.display_message("Import Bundle", f"Failed: {e}")


def remove_selected_from_bundle(app):
    if app.current_view != "bundles":
        return
    keys_to_remove = []
    for row in range(app.package_table.rowCount()):
        chk = app.get_row_checkbox(row)
        if chk is not None and chk.isChecked():
            info = app.get_row_info(row, view_id='bundles')
            keys_to_remove.append((info.get('source'), info.get('id') or info.get('name')))
    if not keys_to_remove:
        app.log("No selected items to remove from bundle")
        return
    before = len(app.bundle_items)
    app.bundle_items = [it for it in app.bundle_items if (it.get('source'), it.get('id') or it.get('name')) not in keys_to_remove]
    removed = before - len(app.bundle_items)
    app.log(f"Removed {removed} items from bundle")
    refresh_bundles_table(app)


def clear_bundle(app):
    if not app.bundle_items:
        return
    app.bundle_items = []
    refresh_bundles_table(app)


def install_bundle(app):
    if not app.bundle_items:
        app.display_message("Install Bundle", "Bundle is empty")
        return
    by_src = {}
    for it in list(app.bundle_items):
        src = it.get('source') or 'pacman'
        name = it.get('name') or ''
        pkg_id = it.get('id') or name
        if not name:
            continue
        token = pkg_id if src == 'Flatpak' else name
        by_src.setdefault(src, []).append(token)
    if not by_src:
        app.display_message("Install Bundle", "No valid items to install")
        return
    install_service.install_packages(app, by_src)


def add_selected_to_community(app):
    """Add selected bundle items to community hub"""
    if app.current_view != "bundles":
        app.display_message("Add to Community", "This feature is only available in bundles view")
        return
    
    # Get selected items
    selected_items = []
    for row in range(app.package_table.rowCount()):
        checkbox = app.get_row_checkbox(row)
        if checkbox is not None and checkbox.isChecked():
            info = app.get_row_info(row, view_id='bundles')
            if info.get("name") and info.get("source"):
                selected_items.append(info)
    
    if not selected_items:
        app.display_message("Add to Community", "No items selected. Please select items to share with the community.")
        return
    
    # Get bundle name from user
    bundle_name, ok = QInputDialog.getText(
        app, 
        "Share Bundle with Community", 
        f"Enter a name for this bundle ({len(selected_items)} items):",
        text=f"My Bundle ({len(selected_items)} packages)"
    )
    
    if not ok or not bundle_name.strip():
        return
    
    bundle_name = bundle_name.strip()
    
    # Get bundle description from user
    description, ok = QInputDialog.getText(
        app,
        "Bundle Description",
        "Enter a description for this bundle (optional):",
        text=f"A collection of {len(selected_items)} useful packages"
    )
    
    if not ok:
        return
    
    description = description.strip() if description else f"A bundle containing {len(selected_items)} packages"
    
    try:
        # Create bundle data structure
        bundle_data = {
            "name": bundle_name,
            "description": description,
            "items": selected_items,
            "item_count": len(selected_items),
            "created_by": "NeoArch User",
            "bundle_type": "community_shared",
            "version": "1.0.0"
        }
        
        # Save to community bundles directory
        community_dir = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "community_bundles")
        os.makedirs(community_dir, exist_ok=True)
        
        # Create safe filename
        safe_name = "".join(c for c in bundle_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        bundle_file = os.path.join(community_dir, f"{safe_name}.json")
        
        # Check if file already exists
        counter = 1
        original_file = bundle_file
        while os.path.exists(bundle_file):
            name_part = os.path.splitext(original_file)[0]
            bundle_file = f"{name_part}_{counter}.json"
            counter += 1
        
        # Save bundle file
        with open(bundle_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_data, f, indent=2, ensure_ascii=False)
        
        # Show success message with option to open community hub
        reply = QMessageBox.question(
            app,
            "Bundle Shared Successfully",
            f"Bundle '{bundle_name}' has been shared with the community!\n\n"
            f"Items shared: {len(selected_items)}\n"
            f"Saved to: {bundle_file}\n\n"
            "Would you like to open the Community Hub to see shared bundles?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            app.show_community_hub()
        
        app.log(f"Successfully shared bundle '{bundle_name}' with {len(selected_items)} items to community")
        
    except Exception as e:
        app.display_message("Add to Community", f"Failed to share bundle: {str(e)}")
        app.log(f"Error sharing bundle to community: {e}")


def list_community_bundles():
    """List all community shared bundles"""
    community_dir = os.path.join(os.path.expanduser("~"), ".config", "neoarch", "community_bundles")
    bundles = []
    
    if not os.path.exists(community_dir):
        return bundles
    
    try:
        for filename in os.listdir(community_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(community_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        bundle_data = json.load(f)
                        bundle_data['file_path'] = filepath
                        bundle_data['file_name'] = filename
                        bundles.append(bundle_data)
                except Exception as e:
                    print(f"Error reading bundle file {filename}: {e}")
    except Exception as e:
        print(f"Error listing community bundles: {e}")
    
    return bundles


def import_community_bundle(app, bundle_data):
    """Import a community bundle into the current bundle"""
    if not isinstance(bundle_data, dict) or 'items' not in bundle_data:
        app.display_message("Import Community Bundle", "Invalid bundle data")
        return
    
    items = bundle_data.get('items', [])
    if not items:
        app.display_message("Import Community Bundle", "Bundle contains no items")
        return
    
    # Add items to current bundle
    existing = {(i.get('source'), i.get('id') or i.get('name')) for i in app.bundle_items}
    added = 0
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        src = (item.get('source') or '').strip()
        name = (item.get('name') or '').strip()
        pkg_id = (item.get('id') or name).strip()
        
        if not src or not name:
            continue
        
        key = (src, pkg_id or name)
        if key not in existing:
            app.bundle_items.append({
                'name': name,
                'id': pkg_id or name,
                'version': (item.get('version') or '').strip(),
                'source': src,
            })
            existing.add(key)
            added += 1
    
    bundle_name = bundle_data.get('name', 'Community Bundle')
    app.display_message("Import Community Bundle", f"Added {added} items from '{bundle_name}' to your bundle")
    
    if app.current_view == "bundles":
        refresh_bundles_table(app)
    
    app.log(f"Imported {added} items from community bundle '{bundle_name}'")

# === services: filters_service.py ===
def apply_filters(app):
    if app.current_view != "installed":
        return
    base = getattr(app, 'installed_all', []) or []
    selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True, "Local": True}
    if hasattr(app, 'source_card') and app.source_card:
        try:
            selected_sources.update(app.source_card.get_selected_sources())
        except Exception:
            pass
    filtered_by_source = []
    for pkg in base:
        s = pkg.get('source')
        if s in selected_sources and selected_sources.get(s, True):
            filtered_by_source.append(pkg)
    selected_filters = {"Updates available": True, "Installed": True}
    if hasattr(app, 'filter_card') and app.filter_card:
        try:
            selected_filters = app.filter_card.get_selected_filters()
        except Exception:
            pass
    show_updates = selected_filters.get("Updates available", True)
    show_installed = selected_filters.get("Installed", True)
    final = []
    for pkg in filtered_by_source:
        if pkg.get('has_update') and show_updates:
            final.append(pkg)
        elif not pkg.get('has_update') and show_installed:
            final.append(pkg)
    app.all_packages = final
    app.current_page = 0
    app.package_table.setRowCount(0)
    app.display_page()


def apply_update_filters(app):
    if app.current_view != "updates" or not app.all_packages:
        return
    selected_sources = {}
    if hasattr(app, 'source_card') and app.source_card:
        try:
            selected_sources = app.source_card.get_selected_sources()
        except Exception:
            selected_sources = {}
    if not selected_sources:
        selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True, "Local": True}
    show_pacman = selected_sources.get("pacman", True)
    show_aur = selected_sources.get("AUR", True)
    show_flatpak = selected_sources.get("Flatpak", True)
    show_npm = selected_sources.get("npm", True)
    show_local = selected_sources.get("Local", True)
    filtered = []
    for pkg in app.all_packages:
        src = pkg.get('source')
        if src == 'pacman' and show_pacman:
            filtered.append(pkg)
        elif src == 'AUR' and show_aur:
            filtered.append(pkg)
        elif src == 'Flatpak' and show_flatpak:
            filtered.append(pkg)
        elif src == 'npm' and show_npm:
            filtered.append(pkg)
        elif src == 'Local' and show_local:
            filtered.append(pkg)
    app.all_packages = filtered
    app.current_page = 0
    app.package_table.setRowCount(0)
    app.display_page()
    

# === services: help_service.py ===
import os
import platform
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon


def _make_text_tab(text: str) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(12, 12, 12, 12)
    edit = QTextEdit()
    edit.setReadOnly(True)
    edit.setText(text)
    v.addWidget(edit)
    return w


def show_help(parent, current_view: str):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Help & Documentation")
    dlg.setModal(True)
    dlg.setMinimumSize(780, 560)

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg")
    if os.path.exists(icon_path):
        dlg.setWindowIcon(QIcon(icon_path))

    root = QVBoxLayout(dlg)
    tabs = QTabWidget()

    overview = (
        "🚀 Welcome to NeoArch - Your All-in-One Package Manager!\n\n"
        "NeoArch simplifies software management on Arch Linux by bringing everything into one place:\n\n"
        "📦 WHAT YOU CAN DO:\n"
        "• Search and install from multiple sources (official repos, AUR, Flatpak, npm) in one search\n"
        "• Create bundles of your favorite apps to install on new systems\n"
        "• Keep everything updated with one click\n"
        "• Install system tools and utilities from the Plugins section\n"
        "• Install from GitHub repos or Docker containers directly\n"
        "• Create system snapshots before major updates (requires Timeshift)\n\n"
        "🎯 HOW TO GET STARTED:\n"
        "1. Click 'Discover' in the left sidebar to search for software\n"
        "2. Type what you want (e.g., 'firefox', 'discord', 'code editor')\n"
        "3. Select packages and click 'Install selected packages'\n"
        "4. Use 'Updates' to keep your system current\n\n"
        "💡 TIP: Click the terminal icon (bottom-right) to see what's happening behind the scenes!"
    )
    tabs.addTab(_make_text_tab(overview), "Overview")

    discover = (
        "🔍 Discover - Find and Install Software\n\n"
        "This is where you find new software for your system. It searches across:\n"
        "• Official Arch repositories (pacman) - Core system software\n"
        "• AUR (Arch User Repository) - Community packages\n"
        "• Flatpak - Sandboxed applications\n"
        "• npm - Node.js packages and tools\n\n"
        "📝 HOW TO USE:\n"
        "1. Type at least 3 characters of what you want (e.g., 'chrom' for Chrome)\n"
        "2. Browse results from all sources in one list\n"
        "3. Check boxes next to packages you want\n"
        "4. Click 'Install selected packages' - we handle passwords and permissions\n\n"
        "🎁 SPECIAL FEATURES:\n"
        "• 'Add selected to Bundle' - Save packages to install later or on other computers\n"
        "• 'Install via GitHub' - Install directly from GitHub repositories\n"
        "• 'Install via Docker' - Set up Docker containers\n"
        "• 'Install with Sudo Privileges' - For packages needing admin rights\n\n"
        "✨ The search is smart - try terms like 'photo editor', 'music player', or 'development tools'!"
    )
    tabs.addTab(_make_text_tab(discover), "Discover")

    updates = (
        "🔄 Updates - Keep Your System Current\n\n"
        "Stay secure and get new features by keeping your software updated.\n\n"
        "📋 WHAT YOU'LL SEE:\n"
        "• All available updates from all sources in one place\n"
        "• Current version vs. new version for each package\n"
        "• Source (pacman, AUR, Flatpak, npm) for each update\n\n"
        "⚡ QUICK ACTIONS:\n"
        "• 'Update Selected' - Choose which packages to update\n"
        "• 'Ignore Selected' - Hide updates you don't want (like beta versions)\n"
        "• 'Manage Ignored' - See and restore previously ignored updates\n"
        "• 'Update Tools' - Update the update tools themselves (yay, flatpak, npm)\n\n"
        "🛡️ SAFETY FIRST:\n"
        "• Enable snapshots in Settings to auto-backup before updates\n"
        "• Updates are applied safely with proper dependency handling\n"
        "• You can cancel running updates if needed\n\n"
        "💡 TIP: Run updates regularly (weekly) to stay secure and get bug fixes!"
    )
    tabs.addTab(_make_text_tab(updates), "Updates")

    installed = (
        "📦 Installed - Manage Your Software\n\n"
        "See everything installed on your system and manage it easily.\n\n"
        "👀 WHAT YOU CAN VIEW:\n"
        "• All installed packages from all sources (pacman, AUR, Flatpak, npm)\n"
        "• Which packages have updates available (highlighted)\n"
        "• Package versions, descriptions, and installation source\n\n"
        "🔧 MANAGEMENT ACTIONS:\n"
        "• 'Update Selected' - Update specific packages that have newer versions\n"
        "• 'Uninstall Selected' - Safely remove packages you no longer need\n"
        "• 'Add selected to Bundle' - Create a list of your favorite packages\n\n"
        "🎯 SMART FILTERING:\n"
        "• Filter by source: See only AUR packages, only Flatpaks, etc.\n"
        "• Filter by status: Show only packages with updates, or only up-to-date ones\n"
        "• Search by name to quickly find specific software\n\n"
        "💡 TIP: Use bundles to recreate your setup on a new computer - just export and import!"
    )
    tabs.addTab(_make_text_tab(installed), "Installed")

    bundles = (
        "🎁 Bundles - Your Personal Software Collections\n\n"
        "Think of bundles as shopping lists for software - perfect for setting up new computers or sharing your favorite apps with friends!\n\n"
        "✨ WHAT ARE BUNDLES FOR:\n"
        "• Setting up a new computer with all your favorite software\n"
        "• Sharing your developer setup with teammates\n"
        "• Creating themed collections (e.g., 'Photo Editing', 'Gaming', 'Programming')\n"
        "• Backing up your software choices\n\n"
        "🔨 HOW TO USE BUNDLES:\n"
        "1. Go to Discover or Installed and click 'Add selected to Bundle'\n"
        "2. Build your collection by adding more packages\n"
        "3. Click 'Install Bundle' to install everything at once\n"
        "4. Use 'Export Bundle' to save/share your bundle as a file\n"
        "5. Use 'Import Bundle' to load someone else's bundle\n\n"
        "🎯 BUNDLE MANAGEMENT:\n"
        "• 'Remove Selected' - Take items out of your current bundle\n"
        "• 'Clear Bundle' - Start fresh with an empty bundle\n"
        "• Auto-save (Settings) - Automatically save your bundle as you build it\n\n"
        "💡 EXAMPLE: Create a 'New Developer Setup' bundle with VS Code, Git, Node.js, and Docker!"
    )
    tabs.addTab(_make_text_tab(bundles), "Bundles")

    plugins = (
        "🔌 Plugins - System Tools and Utilities\n\n"
        "Pre-configured system tools and utilities that you can install and launch directly.\n\n"
        "🛠️ WHAT YOU'LL FIND:\n"
        "• System cleaners (BleachBit) - Free up disk space\n"
        "• Backup tools (Timeshift) - Create system snapshots\n"
        "• Development tools - IDEs, editors, and utilities\n"
        "• System utilities - File managers, terminals, monitors\n\n"
        "🎮 HOW TO USE:\n"
        "1. Browse available plugins or use the search filter (left sidebar)\n"
        "2. Filter by category (Cleaner, Backup, Development, etc.)\n"
        "3. Click 'Install' on plugins you want\n"
        "4. Once installed, click 'Launch' to run the tool\n"
        "5. Use 'Uninstall' to remove plugins you no longer need\n\n"
        "🎯 SMART FEATURES:\n"
        "• Filter by installation status (installed/not installed)\n"
        "• Search by name to find specific tools\n"
        "• Category filtering to browse by purpose\n"
        "• One-click launch for installed tools\n\n"
        "💡 TIP: Try BleachBit to clean up disk space and Timeshift for system backups!"
    )
    tabs.addTab(_make_text_tab(plugins), "Plugins")

    settings_help = (
        "⚙️ Settings - Customize Your Experience\n\n"
        "Make NeoArch work exactly how you want it.\n\n"
        "🔄 AUTO-UPDATE SETTINGS:\n"
        "• Enable automatic update checks - NeoArch will check for updates in the background\n"
        "• Set check interval - How often to look for updates (in minutes)\n"
        "• Scheduled updates - Get prompted to update your system regularly\n\n"
        "🛡️ SNAPSHOT SETTINGS (Safety First!):\n"
        "• 'Create snapshot before updates' - Auto-backup before any system changes\n"
        "• Manual snapshot controls - Create, restore, or delete system snapshots\n"
        "• Requires Timeshift to be installed (available in Plugins section)\n\n"
        "🎁 BUNDLE SETTINGS:\n"
        "• Auto-save bundles - Automatically save your bundle as you build it\n"
        "• Default save location - Where to save your bundle files\n\n"
        "🔌 PLUGIN MANAGEMENT:\n"
        "• View and manage installed plugins\n"
        "• Enable/disable specific plugins\n"
        "• Reset to default plugin set\n\n"
        "💡 RECOMMENDED: Enable snapshots and auto-update checks for the best experience!"
    )
    tabs.addTab(_make_text_tab(settings_help), "Settings")

    advanced = (
        "🔧 Advanced Features\n\n"
        "Power user features and behind-the-scenes functionality.\n\n"
        "📺 CONSOLE (Debug & Monitoring):\n"
        "• Click the terminal icon (bottom-right) to show/hide the console\n"
        "• See real-time logs of installations, updates, and operations\n"
        "• Debug issues by checking console output\n"
        "• Copy error messages for troubleshooting\n\n"
        "⏹️ INSTALLATION CONTROL:\n"
        "• Cancel button appears during installations - stop anytime\n"
        "• Progress bars show download progress and installation status\n"
        "• Safe cancellation won't leave your system in a broken state\n\n"
        "🔐 PERMISSION HANDLING (Automatic):\n"
        "• System packages (pacman): Uses pkexec for secure admin access\n"
        "• AUR packages: Uses askpass for user authentication\n"
        "• No need to run NeoArch as root - we handle permissions properly\n\n"
        "🌐 FLATPAK INTEGRATION:\n"
        "• Flathub repository automatically configured for your user account\n"
        "• No manual setup needed for Flatpak applications\n\n"
        "⏰ SCHEDULED UPDATES:\n"
        "• Background service can remind you to update regularly\n"
        "• Automatic snapshot creation before scheduled updates\n"
        "• Configurable update intervals and notification preferences"
    )
    tabs.addTab(_make_text_tab(advanced), "Advanced")

    if isinstance(current_view, str):
        index_by_name = {
            "discover": 1,
            "updates": 2,
            "installed": 3,
            "bundles": 4,
            "plugins": 5,
            "settings": 6,
        }
        if current_view in index_by_name:
            tabs.setCurrentIndex(index_by_name[current_view])

    root.addWidget(tabs)

    btns = QHBoxLayout()
    btns.addStretch()
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    btns.addWidget(close_btn)
    root.addLayout(btns)

    dlg.exec()


def show_about(parent):
    dlg = AboutDialog(parent)
    dlg.exec()

# === services: ignore_service.py ===
import subprocess
from PyQt6.QtCore import QTimer, QThread, QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QTableWidget, QHeaderView,
    QWidget, QHBoxLayout, QCheckBox, QPushButton, QTableWidgetItem, QSizePolicy,
    QStyledItemDelegate, QStyle
)


class IgnoredMetaWorker(QObject):
    finished = pyqtSignal(object, object, object)

    def run(self):
        installed = {}
        try:
            r = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout:
                for ln in r.stdout.strip().split('\n'):
                    ps = ln.split()
                    if len(ps) >= 2:
                        installed[ps[0]] = ps[1]
        except Exception:
            pass
        aur_set = set()
        try:
            r = subprocess.run(["pacman", "-Qm"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout:
                for ln in r.stdout.strip().split('\n'):
                    ps = ln.split()
                    if ps:
                        aur_set.add(ps[0])
        except Exception:
            pass
        new_versions = {}
        try:
            r = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout:
                for ln in r.stdout.strip().split('\n'):
                    if ' -> ' in ln:
                        left, nv = ln.split(' -> ', 1)
                        nm = left.split()[0]
                        new_versions[nm] = nv.strip()
        except Exception:
            pass
        try:
            r = subprocess.run(["yay", "-Qua"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout:
                for ln in r.stdout.strip().split('\n'):
                    if ' -> ' in ln:
                        left, nv = ln.split(' -> ', 1)
                        nm = left.split()[0]
                        new_versions[nm] = nv.strip()
        except Exception:
            pass
        self.finished.emit(installed, aur_set, new_versions)


def ignore_selected(app):
    items = []
    for row in range(app.package_table.rowCount()):
        checkbox = app.get_row_checkbox(row)
        if checkbox is not None and checkbox.isChecked():
            name_item = app.package_table.item(row, 1)
            if name_item:
                items.append(name_item.text().strip())
    if not items:
        app.log("No packages selected to ignore")
        return
    ignored = app.load_ignored_updates()
    for n in items:
        ignored.add(n)
    app.save_ignored_updates(ignored)
    app.log(f"Ignored {len(items)} package(s)")
    if app.current_view == "updates":
        app.load_updates()


def manage_ignored(app):
    ignored = sorted(app.load_ignored_updates())
    dlg = QDialog(app)
    dlg.setWindowTitle("Manage Ignored Updates")
    v = QVBoxLayout()
    hdr = QLabel(f"Ignored packages: {len(ignored)}")
    v.addWidget(hdr)
    search = QLineEdit()
    search.setPlaceholderText("Filter packages...")
    v.addWidget(search)
    tbl = QTableWidget()
    tbl.setColumnCount(5)
    tbl.setHorizontalHeaderLabels(["", "Package", "Source", "Installed", "Available"])
    tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    try:
        tbl.verticalHeader().setDefaultSectionSize(36)
        tbl.horizontalHeader().setMinimumSectionSize(36)
        tbl.setColumnWidth(0, 44)
    except Exception:
        pass
    try:
        tbl.verticalHeader().setHighlightSections(False)
        tbl.horizontalHeader().setHighlightSections(False)
    except Exception:
        pass
    try:
        tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setStyleSheet(
            """
            QTableView { outline: none; }
            QTableWidget { outline: none; }
            QTableView::item:selected { background: transparent; }
            QTableWidget::item:selected { background: transparent; }
            QTableView::item:selected:active { background: transparent; border: none; }
            QTableWidget::item:selected:active { background: transparent; border: none; }
            QTableView::item:selected:!active { background: transparent; border: none; }
            QTableWidget::item:selected:!active { background: transparent; border: none; }
            QTableView::item:focus { outline: none; }
            QTableWidget::item:focus { outline: none; }
            QTableView::item:hover { background: transparent; }
            QTableWidget::item:hover { background: transparent; }
            QTableView::item { padding: 0px; margin: 0px; border: none; }
            QTableWidget::item { padding: 0px; margin: 0px; border: none; }
            """
        )
    except Exception:
        pass
    try:
        tbl.setShowGrid(False)
    except Exception:
        pass
    tbl.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    v.addWidget(tbl)
    try:
        class _NoFocusDelegate(QStyledItemDelegate):
            def paint(self, painter, option, index):
                if option.state & QStyle.StateFlag.State_HasFocus:
                    option.state &= ~QStyle.StateFlag.State_HasFocus
                super().paint(painter, option, index)
        tbl.setItemDelegate(_NoFocusDelegate(tbl))
    except Exception:
        pass
    row = QWidget()
    h = QHBoxLayout(row)
    btn_unignore = QPushButton("Unignore Selected")
    btn_unall = QPushButton("Unignore All")
    btn_close = QPushButton("Close")
    h.addWidget(btn_unignore)
    h.addWidget(btn_unall)
    h.addStretch()
    h.addWidget(btn_close)
    v.addWidget(row)

    tbl.setRowCount(len(ignored))
    for i, name in enumerate(ignored):
        cb = QCheckBox()
        cb.setObjectName("ignoredCheckbox")
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass
        cb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        cb.setStyleSheet(
            """
            QCheckBox#ignoredCheckbox { padding: 0px; margin: 0px; }
            QCheckBox#ignoredCheckbox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 3px;
                border: 2px solid rgba(0, 191, 174, 0.4);
                background-color: transparent;
                margin: 0px;
            }
            QCheckBox#ignoredCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.8);
            }
            QCheckBox#ignoredCheckbox::indicator:checked {
                background-color: #00BFAE;
                border: 2px solid #00BFAE;
            }
            """
        )
        try:
            cb.setMinimumSize(24, 24)
        except Exception:
            pass
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        try:
            lay.addWidget(cb, 0, Qt.AlignmentFlag.AlignCenter)
        except Exception:
            lay.addWidget(cb)
        tbl.setCellWidget(i, 0, w)
        tbl.setItem(i, 1, QTableWidgetItem(name))
        tbl.setItem(i, 2, QTableWidgetItem("—"))
        tbl.setItem(i, 3, QTableWidgetItem("—"))
        tbl.setItem(i, 4, QTableWidgetItem("—"))

    def finalize(installed, aur_set, new_versions):
        for i, name in enumerate(ignored):
            src = "AUR" if name in aur_set else "pacman"
            tbl.setItem(i, 2, QTableWidgetItem(src))
            tbl.setItem(i, 3, QTableWidgetItem(installed.get(name, "")))
            tbl.setItem(i, 4, QTableWidgetItem(new_versions.get(name, "")))

    worker_thread = QThread()
    worker = IgnoredMetaWorker()
    worker.moveToThread(worker_thread)
    worker_thread.started.connect(worker.run)
    def _on_finished(installed, aur_set, new_versions):
        finalize(installed, aur_set, new_versions)
    worker.finished.connect(_on_finished)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(worker_thread.deleteLater)
    worker_thread.start()

    try:
        QTimer.singleShot(0, lambda: (tbl.clearSelection(), tbl.clearFocus()))
    except Exception:
        pass

    def on_cell_clicked(row, col):
        w = tbl.cellWidget(row, 0)
        if isinstance(w, QCheckBox):
            w.setChecked(not w.isChecked())
    try:
        tbl.cellClicked.connect(on_cell_clicked)
    except Exception:
        pass

    def apply_filter(text):
        t = text.strip().lower()
        for r in range(tbl.rowCount()):
            nm = tbl.item(r,1).text().lower() if tbl.item(r,1) else ""
            tbl.setRowHidden(r, t not in nm)
    search.textChanged.connect(apply_filter)

    def unignore_selected():
        sel = []
        for r in range(tbl.rowCount()):
            w = tbl.cellWidget(r, 0)
            if not w:
                continue
            checked = False
            if isinstance(w, QCheckBox):
                checked = w.isChecked()
            else:
                chks = w.findChildren(QCheckBox)
                checked = bool(chks and chks[0].isChecked())
            if checked:
                nm = tbl.item(r,1).text()
                sel.append(nm)
        if sel:
            s = app.load_ignored_updates()
            for nm in sel:
                s.discard(nm)
            app.save_ignored_updates(s)
            for r in reversed(range(tbl.rowCount())):
                w = tbl.cellWidget(r,0)
                if not w:
                    continue
                checked = False
                if isinstance(w, QCheckBox):
                    checked = w.isChecked()
                else:
                    chks = w.findChildren(QCheckBox)
                    checked = bool(chks and chks[0].isChecked())
                if checked:
                    tbl.removeRow(r)
            QTimer.singleShot(0, app.refresh_packages)
    btn_unignore.clicked.connect(unignore_selected)

    def unignore_all():
        app.save_ignored_updates(set())
        tbl.setRowCount(0)
        QTimer.singleShot(0, app.refresh_packages)
    btn_unall.clicked.connect(unignore_all)

    btn_close.clicked.connect(dlg.accept)
    dlg.setLayout(v)
    dlg.resize(820, 520)
    dlg.exec()

# === services: packages_service.py ===
import os
import json
import subprocess
from threading import Thread


def load_updates(app):
    try:
        app._updates_loading = True
    except Exception:
        pass
    app.package_table.setRowCount(0)
    app.all_packages = []
    app.current_page = 0
    app.cancel_update_load = False
    app.loading_context = "updates"

    app.loading_widget.setVisible(True)
    try:
        app.loading_widget.set_message("Checking for updates...")
    except Exception:
        pass
    app.package_table.setVisible(False)
    app.load_more_btn.setVisible(False)
    app.loading_widget.start_animation()
    try:
        if hasattr(app, 'loading_container'):
            app.loading_container.setVisible(True)
    except Exception:
        pass
    try:
        app.cancel_install_btn.setVisible(False)
    except Exception:
        pass
    try:
        if hasattr(app, 'console_toggle_btn'):
            app.console_toggle_btn.setVisible(True)
            app.console_toggle_btn.setToolTip("Show Console")
    except Exception:
        pass

    def load_in_thread():
        try:
            packages = []

            # Sync package database first to get latest updates
            try:
                app.log("Syncing package database...")
                env, _ = app.prepare_askpass_env()
                sync_result = subprocess.run(["sudo", "-A", "pacman", "-Sy", "--noconfirm"], 
                                            capture_output=True, text=True, timeout=120, env=env)
                if sync_result.returncode == 0:
                    app.log("Package database synced successfully")
                else:
                    err = sync_result.stderr or ""
                    app.log(f"Warning: Database sync failed: {err}")
                    low = err.lower()
                    if ("could not lock database" in low) or ("unable to lock database" in low):
                        try:
                            app.ui_call.emit(lambda: app.show_busy_pm_warning(err))
                        except Exception:
                            pass
            except Exception as e:
                app.log(f"Warning: Could not sync database: {str(e)}")

            result = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        if ' -> ' in line:
                            parts = line.split(' -> ')
                            if len(parts) == 2:
                                package_info = parts[0].strip().split()
                                new_version = parts[1].strip()
                                if len(package_info) >= 2:
                                    package_name = package_info[0]
                                    current_version = package_info[1]
                                    packages.append({
                                        'name': package_name,
                                        'version': current_version,
                                        'new_version': new_version,
                                        'id': package_name,
                                        'source': 'pacman'
                                    })

            try:
                result_aur = subprocess.run(["yay", "-Qua"], capture_output=True, text=True, timeout=60)
                if result_aur.returncode == 0 and result_aur.stdout:
                    for line in result_aur.stdout.strip().split('\n'):
                        if line.strip() and ' -> ' in line:
                            parts = line.split(' -> ')
                            if len(parts) == 2:
                                package_info = parts[0].strip().split()
                                new_version = parts[1].strip()
                                if len(package_info) >= 2:
                                    package_name = package_info[0]
                                    current_version = package_info[1]
                                    packages.append({
                                        'name': package_name,
                                        'version': current_version,
                                        'new_version': new_version,
                                        'id': package_name,
                                        'source': 'AUR'
                                    })
            except (subprocess.CalledProcessError, FileNotFoundError):
                for aur_helper in ['paru', 'trizen', 'pikaur']:
                    try:
                        result_aur = subprocess.run([aur_helper, "-Qua"], capture_output=True, text=True, timeout=60)
                        if result_aur.returncode == 0 and result_aur.stdout:
                            for line in result_aur.stdout.strip().split('\n'):
                                if line.strip() and ' -> ' in line:
                                    parts = line.split(' -> ')
                                    if len(parts) == 2:
                                        package_info = parts[0].strip().split()
                                        new_version = parts[1].strip()
                                        if len(package_info) >= 2:
                                            package_name = package_info[0]
                                            current_version = package_info[1]
                                            packages.append({
                                                'name': package_name,
                                                'version': current_version,
                                                'new_version': new_version,
                                                'id': package_name,
                                                'source': 'AUR'
                                            })
                            break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            added_flatpak = False
            try:
                installed_map = {}
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application,version"]
                        li = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if li.returncode == 0 and li.stdout:
                            for ln in [x for x in li.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                if c and c[0].strip():
                                    installed_map[c[0].strip()] = (c[1].strip() if len(c) > 1 else '')
                    except Exception:
                        continue

                seen_apps = set()
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
                        fp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if fp.returncode == 0 and fp.stdout:
                            for line in [l for l in fp.stdout.strip().split('\n') if l.strip()]:
                                cols = line.split('\t')
                                app_id = cols[0].strip() if len(cols) > 0 else ''
                                inst = cols[1].strip() if len(cols) > 1 else ''
                                if app_id and app_id not in seen_apps:
                                    packages.append({
                                        'name': app_id,
                                        'version': inst or installed_map.get(app_id, ''),
                                        'new_version': '',
                                        'id': app_id,
                                        'source': 'Flatpak'
                                    })
                                    seen_apps.add(app_id)
                                    added_flatpak = True
                    except Exception:
                        continue

                if not added_flatpak:
                    try:
                        rl = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], capture_output=True, text=True, timeout=60)
                        if rl.returncode == 0 and rl.stdout:
                            for ln in [x for x in rl.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                app_id = c[0].strip() if len(c) > 0 else ''
                                latest = c[1].strip() if len(c) > 1 else ''
                                if app_id and app_id in installed_map and app_id not in seen_apps:
                                    packages.append({
                                        'name': app_id,
                                        'version': installed_map.get(app_id, ''),
                                        'new_version': latest,
                                        'id': app_id,
                                        'source': 'Flatpak'
                                    })
                                    seen_apps.add(app_id)
                                    added_flatpak = True
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                seen = set()
                for code, out in results:
                    if code in (0, 1) and out and out.strip():
                        try:
                            data = json.loads(out)
                            if isinstance(data, dict):
                                for name, info in data.items():
                                    cur = (info.get('current') or info.get('installed') or '').strip()
                                    lat = (info.get('latest') or '').strip()
                                    key = (name, cur, lat)
                                    if name and cur and lat and cur != lat and key not in seen:
                                        packages.append({
                                            'name': name,
                                            'version': cur,
                                            'new_version': lat,
                                            'id': name,
                                            'source': 'npm'
                                        })
                                        seen.add(key)
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                entries = app.load_local_update_entries()
                for e in entries:
                    name = (e.get('name') or '').strip()
                    if not name:
                        continue
                    installed = (e.get('installed_version') or '').strip()
                    if not installed and e.get('installed_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['installed_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0:
                                installed = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            installed = ''
                    latest = (e.get('latest_version') or '').strip()
                    if not latest and e.get('latest_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['latest_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0:
                                latest = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            latest = ''
                    if installed and latest and installed != latest:
                        packages.append({
                            'name': name,
                            'version': installed,
                            'new_version': latest,
                            'id': (e.get('id') or name),
                            'source': 'Local'
                        })
            except Exception:
                pass

            try:
                ignored = app.load_ignored_updates()
                if ignored:
                    packages = [p for p in packages if p.get('name') not in ignored]
            except Exception:
                pass

            if not app.cancel_update_load and app.loading_context == 'updates' and app.current_view == 'updates':
                try:
                    app._updates_loading = False
                except Exception:
                    pass
                app.packages_ready.emit(packages)
        except Exception as e:
            app.log(f"Error: {str(e)}")
            try:
                app._updates_loading = False
            except Exception:
                pass
            app.load_error.emit()

    Thread(target=load_in_thread, daemon=True).start()



def load_installed_packages(app):
    app.package_table.setRowCount(0)
    app.all_packages = []
    app.current_page = 0
    app.loading_context = "installed"

    def load_in_thread():
        try:
            result = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=60)
            packages = []
            updates = {}

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                'name': parts[0],
                                'version': parts[1],
                                'id': parts[0],
                                'source': 'pacman',
                                'has_update': False
                            })
                    if i % 100 == 0 and i > 0:
                        import time
                        time.sleep(0.01)

            result_updates = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True, timeout=30)
            if result_updates.returncode == 0 and result_updates.stdout:
                for line in result_updates.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            updates[parts[0]] = parts[2] if len(parts) > 2 else parts[1]

            for pkg in packages:
                if pkg['name'] in updates:
                    pkg['has_update'] = True
                    pkg['new_version'] = updates[pkg['name']]

            result_aur = subprocess.run(["pacman", "-Qm"], capture_output=True, text=True, timeout=30)
            aur_packages = set()
            if result_aur.returncode == 0 and result_aur.stdout:
                for line in result_aur.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            aur_packages.add(parts[0])

            for pkg in packages:
                if pkg['name'] in aur_packages:
                    pkg['source'] = 'AUR'

            try:
                aur_updates = {}
                helper = None
                for h in ['yay', 'paru', 'trizen', 'pikaur']:
                    try:
                        r = subprocess.run([h, "-Qua"], capture_output=True, text=True, timeout=60)
                        if r.returncode in (0, 1):
                            helper = h
                            output = (r.stdout or '').strip()
                            if output:
                                for ln in [x for x in output.split('\n') if x.strip()]:
                                    parts = ln.split()
                                    if len(parts) >= 2:
                                        name = parts[0]
                                        if '->' in ln:
                                            try:
                                                new_v = parts[-1]
                                            except Exception:
                                                new_v = ''
                                        else:
                                            new_v = parts[1]
                                        aur_updates[name] = new_v
                            break
                    except Exception:
                        continue
                if aur_updates:
                    for pkg in packages:
                        if pkg.get('source') == 'AUR' and pkg['name'] in aur_updates:
                            pkg['has_update'] = True
                            pkg['new_version'] = aur_updates.get(pkg['name'], pkg.get('new_version', ''))
            except Exception:
                pass

            try:
                installed_map = {}
                seen = set()
                for scope in ([], ["--user"], ["--system"]):
                    cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application,version"]
                    fp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if fp.returncode == 0 and fp.stdout:
                        for ln in [x for x in fp.stdout.strip().split('\n') if x.strip()]:
                            c = ln.split('\t')
                            app_id = c[0].strip() if len(c) > 0 else ''
                            ver = c[1].strip() if len(c) > 1 else ''
                            if app_id:
                                installed_map[app_id] = ver
                            if app_id and app_id not in seen:
                                packages.append({
                                    'name': app_id,
                                    'version': ver,
                                    'id': app_id,
                                    'source': 'Flatpak',
                                    'has_update': False
                                })
                                seen.add(app_id)
            except Exception:
                pass

            try:
                update_ids = set()
                for scope in ([], ["--user"], ["--system"]):
                    cmdu = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
                    fu = subprocess.run(cmdu, capture_output=True, text=True, timeout=60)
                    if fu.returncode == 0 and fu.stdout:
                        for ln in [x for x in fu.stdout.strip().split('\n') if x.strip()]:
                            cols = ln.split('\t')
                            if cols:
                                update_ids.add(cols[0].strip())
                if not update_ids:
                    try:
                        rl = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], capture_output=True, text=True, timeout=60)
                        if rl.returncode == 0 and rl.stdout:
                            for ln in [x for x in rl.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                app_id = c[0].strip() if len(c) > 0 else ''
                                latest = c[1].strip() if len(c) > 1 else ''
                                if app_id and app_id in installed_map:
                                    update_ids.add(app_id)
                                    for pkg in packages:
                                        if pkg.get('source') == 'Flatpak' and pkg.get('name') == app_id:
                                            if latest:
                                                pkg['new_version'] = latest
                    except Exception:
                        pass
                if update_ids:
                    for pkg in packages:
                        if pkg.get('source') == 'Flatpak' and pkg.get('name') in update_ids:
                            pkg['has_update'] = True
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                seen = set()
                for code, out in results:
                    if code == 0 and out and out.strip():
                        try:
                            data = json.loads(out)
                            deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                            for name, info in deps.items():
                                ver = (info.get('version') or '').strip()
                                if name and ver and (name, ver) not in seen:
                                    packages.append({
                                        'name': name,
                                        'version': ver,
                                        'id': name,
                                        'source': 'npm',
                                        'has_update': False
                                    })
                                    seen.add((name, ver))
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                outdated = {}
                for code, out in results:
                    if code in (0, 1) and out and out.strip():
                        try:
                            data = json.loads(out)
                            if isinstance(data, dict):
                                for name, info in data.items():
                                    lat = (info.get('latest') or '').strip()
                                    cur = (info.get('current') or info.get('installed') or '').strip()
                                    if name and lat and cur and cur != lat:
                                        outdated[name] = lat
                        except Exception:
                            pass
                if outdated:
                    for pkg in packages:
                        if pkg.get('source') == 'npm' and pkg.get('name') in outdated:
                            pkg['has_update'] = True
                            pkg['new_version'] = outdated[pkg['name']]
            except Exception:
                pass

            try:
                entries = app.load_local_update_entries()
                for e in entries:
                    name = (e.get('name') or '').strip()
                    if not name:
                        continue
                    installed = (e.get('installed_version') or '').strip()
                    if not installed and e.get('installed_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['installed_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0 and r.stdout:
                                installed = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            installed = ''
                    latest = (e.get('latest_version') or '').strip()
                    if not latest and e.get('latest_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['latest_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0 and r.stdout:
                                latest = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            latest = ''
                    if installed:
                        pkg = {
                            'name': name,
                            'version': installed,
                            'new_version': latest or installed,
                            'id': (e.get('id') or name),
                            'source': 'Local',
                            'has_update': (bool(latest) and latest != installed)
                        }
                        packages.append(pkg)
            except Exception:
                pass

            try:
                ignored = app.load_ignored_updates()
                if ignored:
                    for pkg in packages:
                        if pkg.get('name') in ignored and pkg.get('has_update'):
                            pkg['has_update'] = False
            except Exception:
                pass

            app.packages_ready.emit(packages)
        except Exception as e:
            app.log(f"Error: {str(e)}")
            app.load_error.emit()

    Thread(target=load_in_thread, daemon=True).start()

# === services: settings_service.py ===
import os
import json
from PyQt6.QtWidgets import QFileDialog

def load_settings():
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora')
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, 'settings.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        default = {
            'auto_check_updates': True,
            'npm_user_mode': True,
            'include_local_source': True,
            'enabled_plugins': [],
            'bundle_autosave': True,
            'bundle_autosave_path': os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json'),
            'auto_refresh_updates_minutes': 0,
            'auto_update_enabled': False,
            'auto_update_interval_days': 7,
            'snapshot_before_update': False,
            'aur_helper': 'auto'  # auto, yay, paru, trizen, or pikaur
        }
        default.update(data if isinstance(data, dict) else {})
        return default
    except Exception:
        return {
            'auto_check_updates': True,
            'npm_user_mode': True,
            'include_local_source': True,
            'enabled_plugins': [],
            'bundle_autosave': True,
            'bundle_autosave_path': os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json'),
            'auto_refresh_updates_minutes': 0,
            'auto_update_enabled': False,
            'auto_update_interval_days': 7,
            'snapshot_before_update': False,
            'aur_helper': 'auto'  # auto, yay, paru, trizen, or pikaur
        }


def save_settings(settings, log=None):
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora')
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, 'settings.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        if log:
            log(f"Settings save error: {str(e)}")


def export_settings(app):
    path, _ = QFileDialog.getSaveFileName(app, "Export Settings", os.path.expanduser('~'), "Settings JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(app.settings, f, indent=2)
        app._show_message("Export Settings", f"Saved to {path}")
    except Exception as e:
        app._show_message("Export Settings", f"Failed: {e}")


def import_settings(app):
    path, _ = QFileDialog.getOpenFileName(app, "Import Settings", os.path.expanduser('~'), "Settings JSON (*.json)")
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            app.settings.update(data)
            save_settings(app.settings, app.log)
            app.build_settings_ui()
            app._show_message("Import Settings", "Imported")
    except Exception as e:
        app._show_message("Import Settings", f"Failed: {e}")

# === services: snapshot_service.py ===
import subprocess
from threading import Thread
from PyQt6.QtWidgets import QMessageBox, QLabel, QComboBox, QVBoxLayout, QDialog, QDialogButtonBox
from PyQt6.QtCore import QTimer


def create_snapshot(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed. Please install Timeshift to use snapshot functionality.\n\nInstall with: sudo pacman -S timeshift")
        return

    reply = QMessageBox.question(app, "Create Snapshot",
                                 "Create a system snapshot before proceeding with updates?\n\nThis will take some time.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.Yes)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Creating snapshot...")
    app.loading_widget.start_animation()

    def do_create():
        try:
            timestamp = subprocess.run(["date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True).stdout.strip()
            comment = f"NeoArch manual snapshot {timestamp}"
            result = subprocess.run(["pkexec", "timeshift", "--create", "--comments", comment],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", f"Snapshot created successfully: {comment}")
            else:
                app.show_message.emit("Snapshot", f"Failed to create snapshot: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error creating snapshot: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_create, daemon=True).start()


def revert_to_snapshot(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed. Please install Timeshift to use snapshot functionality.")
        return

    try:
        result = subprocess.run(["timeshift", "--list"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            QMessageBox.warning(app, "No Snapshots", "No snapshots found or Timeshift error.")
            return

        snapshots = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.strip() and not line.startswith('Num') and not line.startswith('---'):
                parts = line.split()
                if len(parts) >= 4:
                    snapshots.append({
                        'num': parts[0],
                        'date': parts[1],
                        'time': parts[2],
                        'comment': ' '.join(parts[3:])
                    })

        if not snapshots:
            QMessageBox.information(app, "No Snapshots", "No snapshots available for restoration.")
            return

        dialog = QDialog(app)
        dialog.setWindowTitle("Select Snapshot to Restore")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a snapshot to restore the system to:"))

        combo = QComboBox()
        for snap in snapshots:
            combo.addItem(f"{snap['date']} {snap['time']} - {snap['comment']}", snap['num'])
        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_num = combo.currentData()
            if selected_num:
                restore_snapshot(app, selected_num)

    except Exception as e:
        QMessageBox.warning(app, "Error", f"Failed to list snapshots: {str(e)}")


def restore_snapshot(app, snapshot_num):
    reply = QMessageBox.warning(app, "Confirm Restoration",
                                f"This will restore your system to snapshot #{snapshot_num}.\n\n"
                                "The system will reboot after restoration.\n\n"
                                "Are you sure you want to proceed?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Restoring snapshot...")
    app.loading_widget.start_animation()

    def do_restore():
        try:
            result = subprocess.run(["pkexec", "timeshift", "--restore", "--snapshot", snapshot_num],
                                    capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", "Snapshot restoration initiated. System will reboot.")
                QTimer.singleShot(3000, lambda: subprocess.run(["pkexec", "reboot"]))
            else:
                app.show_message.emit("Snapshot", f"Failed to restore snapshot: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error restoring snapshot: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_restore, daemon=True).start()


def delete_snapshots(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed.")
        return

    reply = QMessageBox.question(app, "Delete Snapshots",
                                 "This will delete old snapshots to free up disk space.\n\n"
                                 "Keep only the 2 most recent snapshots?\n\n"
                                 "This action cannot be undone.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Deleting old snapshots...")
    app.loading_widget.start_animation()

    def do_delete():
        try:
            result = subprocess.run(["pkexec", "timeshift", "--delete-all", "--skip", "2"],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", "Old snapshots deleted successfully")
            else:
                app.show_message.emit("Snapshot", f"Failed to delete snapshots: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error deleting snapshots: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_delete, daemon=True).start()

# === services: uninstall_service.py ===
import os
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer


def uninstall_packages(app, packages_by_source: dict):
    def uninstall():
        app.log("Uninstallation thread started")
        try:
            for source, pkgs in packages_by_source.items():
                if not pkgs:
                    continue
                if source in ('pacman', 'AUR'):
                    cmd = ["pacman", "-R", "--noconfirm"] + pkgs
                    app.log(f"Running: {' '.join(cmd)}")
                    worker = CommandWorker(cmd, sudo=True)
                    worker.output.connect(app.log)
                    worker.error.connect(app.log)
                    worker.run()
                elif source == 'Flatpak':
                    cmd = ["flatpak", "uninstall", "-y", "--noninteractive"] + pkgs
                    app.log(f"Running: {' '.join(cmd)}")
                    worker = CommandWorker(cmd, sudo=False)
                    worker.output.connect(app.log)
                    worker.error.connect(app.log)
                    worker.run()
                elif source == 'npm':
                    # Try to uninstall from both user and system global locations as needed
                    def _build_user_env():
                        e = os.environ.copy()
                        try:
                            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                            os.makedirs(npm_prefix, exist_ok=True)
                            e['npm_config_prefix'] = npm_prefix
                            e['NPM_CONFIG_PREFIX'] = npm_prefix
                            e['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + e.get('PATH', '')
                        except Exception:
                            pass
                        return e

                    def _list_installed(env=None):
                        try:
                            r = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env, timeout=30)
                            if r.returncode == 0 and r.stdout and r.stdout.strip():
                                import json
                                data = json.loads(r.stdout)
                                deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                return set(deps.keys())
                        except Exception:
                            pass
                        return set()

                    def _npm_root_writable(env=None):
                        try:
                            r = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, env=env, timeout=10)
                            root = (r.stdout or '').strip()
                            return bool(root) and os.access(root, os.W_OK)
                        except Exception:
                            return False

                    # User global
                    user_env = _build_user_env()
                    user_pkgs = _list_installed(env=user_env)
                    targets = [p for p in pkgs if p in user_pkgs]
                    if targets:
                        cmd = ["npm", "uninstall", "-g"] + targets
                        app.log(f"Running: {' '.join(cmd)} (user)")
                        worker = CommandWorker(cmd, sudo=False, env=user_env)
                        worker.output.connect(app.log)
                        worker.error.connect(app.log)
                        worker.run()

                    # System/global prefix
                    sys_pkgs = _list_installed(env=os.environ.copy())
                    targets_sys = [p for p in pkgs if p in sys_pkgs]
                    if targets_sys:
                        sudo_needed = not _npm_root_writable(env=os.environ.copy())
                        cmd = ["npm", "uninstall", "-g"] + targets_sys
                        app.log(f"Running: {' '.join(cmd)} ({'sudo' if sudo_needed else 'no-sudo'})")
                        worker = CommandWorker(cmd, sudo=sudo_needed, env=os.environ.copy())
                        worker.output.connect(app.log)
                        worker.error.connect(app.log)
                        worker.run()
            app.show_message.emit("Uninstallation Complete", f"Successfully processed {sum(len(v) for v in packages_by_source.values())} package(s).")
            QTimer.singleShot(0, app.load_installed_packages)
        except Exception as e:
            app.log(f"Error in uninstallation thread: {str(e)}")
    Thread(target=uninstall, daemon=True).start()

# === services: update_service.py ===
import os
import json
import subprocess
from threading import Thread
from PyQt6.QtCore import QTimer


def update_packages(app, packages_by_source: dict):
    def update():
        try:
            overall_success = True
            lock_detected = False
            lock_details = ""
            for source, pkgs in packages_by_source.items():
                if source == 'pacman':
                    cmd = ["pacman", "-S", "--noconfirm"] + pkgs
                    worker = CommandWorker(cmd, sudo=True)
                    worker.output.connect(app.log)
                    def _on_err(msg):
                        nonlocal overall_success, lock_detected, lock_details
                        app.log(msg)
                        m = (msg or '').lower()
                        if 'could not lock database' in m or 'unable to lock database' in m:
                            lock_detected = True
                            lock_details = msg
                        overall_success = False
                    worker.error.connect(_on_err)
                    worker.run()
                elif source == 'AUR':
                    # Get the configured AUR helper
                    preferred = app.settings.get('aur_helper', 'auto')
                    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
                    if not aur_helper:
                        app.log("Error: No AUR helper available. Install yay, paru, trizen, or pikaur.")
                        overall_success = False
                        continue
                    
                    env, _ = app.prepare_askpass_env()
                    cmd = [aur_helper, "-S", "--noconfirm"] + pkgs
                    worker = CommandWorker(cmd, sudo=False, env=env)
                    worker.output.connect(app.log)
                    def _on_err_aur(msg):
                        nonlocal overall_success
                        app.log(msg)
                        overall_success = False
                    worker.error.connect(_on_err_aur)
                    worker.run()
                elif source == 'Flatpak':
                    cmd = ["flatpak", "update", "-y", "--noninteractive"] + pkgs
                    worker = CommandWorker(cmd, sudo=False)
                    worker.output.connect(app.log)
                    def _on_err_fp(msg):
                        nonlocal overall_success
                        app.log(msg)
                        overall_success = False
                    worker.error.connect(_on_err_fp)
                    worker.run()
                elif source == 'npm':
                    # Determine where each package is installed and update in that scope
                    env_user = os.environ.copy()
                    try:
                        npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                        os.makedirs(npm_prefix, exist_ok=True)
                        env_user['npm_config_prefix'] = npm_prefix
                        env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                        env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                    except Exception:
                        pass
                    env_sys = os.environ.copy()

                    user_pkgs, sys_pkgs, unknown_pkgs = [], [], []
                    for name in pkgs:
                        placed = False
                        try:
                            r_user = subprocess.run(["npm", "ls", "-g", name, "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=30)
                            if r_user.returncode in (0, 1) and r_user.stdout:
                                try:
                                    data = json.loads(r_user.stdout)
                                    deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                    if name in deps:
                                        user_pkgs.append(name)
                                        placed = True
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        if placed:
                            continue
                        try:
                            r_sys = subprocess.run(["npm", "ls", "-g", name, "--depth=0", "--json"], capture_output=True, text=True, timeout=30)
                            if r_sys.returncode in (0, 1) and r_sys.stdout:
                                try:
                                    data = json.loads(r_sys.stdout)
                                    deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                                    if name in deps:
                                        sys_pkgs.append(name)
                                        placed = True
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        if not placed:
                            # Default to user scope if location unknown
                            user_pkgs.append(name)

                    if user_pkgs:
                        cmd_u = ["npm", "update", "-g"] + user_pkgs
                        w_u = CommandWorker(cmd_u, sudo=False, env=env_user)
                        w_u.output.connect(app.log)
                        def _on_err_np_u(msg):
                            nonlocal overall_success
                            app.log(msg)
                            overall_success = False
                        w_u.error.connect(_on_err_np_u)
                        w_u.run()
                    if sys_pkgs:
                        cmd_s = ["npm", "update", "-g"] + sys_pkgs
                        # Use pkexec (sudo=True) for system-global updates
                        w_s = CommandWorker(cmd_s, sudo=True, env=env_sys)
                        w_s.output.connect(app.log)
                        def _on_err_np_s(msg):
                            nonlocal overall_success
                            app.log(msg)
                            overall_success = False
                        w_s.error.connect(_on_err_np_s)
                        w_s.run()
                elif source == 'Local':
                    entries = { (e.get('id') or e.get('name')): e for e in app.load_local_update_entries() }
                    for token in pkgs:
                        e = entries.get(token) or entries.get(token.strip())
                        if not e:
                            continue
                        upd = e.get('update_cmd')
                        if not upd:
                            continue
                        try:
                            process = subprocess.Popen(["bash", "-lc", upd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            while True:
                                line = process.stdout.readline() if process.stdout else ""
                                if not line and process.poll() is not None:
                                    break
                                if line:
                                    app.log(line.strip())
                            _, stderr = process.communicate()
                            if process.returncode != 0 and stderr:
                                app.log(f"Error: {stderr}")
                                overall_success = False
                        except Exception as ex:
                            app.log(str(ex))
            if lock_detected:
                try:
                    app.ui_call.emit(lambda: app.show_busy_pm_warning(lock_details, retry_action=lambda: update_packages(app, packages_by_source)))
                except Exception:
                    pass
            if overall_success:
                app.show_message.emit("Update Complete", f"Successfully updated {sum(len(v) for v in packages_by_source.values())} package(s).")
            else:
                app.show_message.emit("Update Failed", "Some updates failed. See console for details.")
            try:
                app.ui_call.emit(app.refresh_packages)
            except Exception:
                pass
        except Exception as e:
            app.log(f"Error in update thread: {str(e)}")
    Thread(target=update, daemon=True).start()


def update_core_tools(app):
    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Updating tools...")
    app.loading_widget.start_animation()

    def do_update():
        try:
            # Update system packages first
            _update_system_packages(app)
            
            # Update individual tools
            _update_flatpak(app)
            _update_npm(app)
            _update_aur(app)
            
            app.show_message.emit("Environment", "Tools updated")
        except Exception as e:
            app.show_message.emit("Environment", f"Update failed: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_update, daemon=True).start()

def _update_system_packages(app):
    """Update system packages with pacman."""
    deps = ["flatpak", "git", "nodejs", "npm", "docker"]
    if app.cmd_exists("pacman"):
        w1 = CommandWorker(["pacman", "-Syu", "--noconfirm"] + deps, sudo=True)
        w1.output.connect(app.log)
        w1.error.connect(app.log)
        w1.run()

def _update_flatpak(app):
    """Update Flatpak and ensure remote is configured."""
    try:
        app.ensure_flathub_user_remote()
    except Exception:
        pass
    
    # Check for updates but don't mark packages (needs refactoring)
    try:
        update_ids = set()
        for scope in ([], ["--user"], ["--system"]):
            cmdu = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
            fu = subprocess.run(cmdu, capture_output=True, text=True, timeout=60, check=False)
            if fu.returncode == 0 and fu.stdout:
                for ln in [x for x in fu.stdout.strip().split('\n') if x.strip()]:
                    cols = ln.split('\t')
                    if cols:
                        update_ids.add(cols[0].strip())
        # Note: Package marking would need access to the packages list
        # This functionality should be moved to a place where packages are available
    except Exception:
        pass
    
    if app.cmd_exists("flatpak"):
        w2 = CommandWorker(["flatpak", "--user", "update", "-y"], sudo=False)
        w2.output.connect(app.log)
        w2.error.connect(app.log)
        w2.run()

def _update_npm(app):
    """Update npm global packages."""
    if app.cmd_exists("npm"):
        env = os.environ.copy()
        try:
            npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
            os.makedirs(npm_prefix, exist_ok=True)
            env['npm_config_prefix'] = npm_prefix
            env['NPM_CONFIG_PREFIX'] = npm_prefix
            env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
        except Exception:
            pass
        w3 = CommandWorker(["npm", "update", "-g"], sudo=False, env=env)
        w3.output.connect(app.log)
        w3.error.connect(app.log)
        w3.run()

def _update_aur(app):
    """Update AUR packages."""
    # Get the configured AUR helper
    preferred = app.settings.get('aur_helper', 'auto')
    aur_helper = sys_utils.get_aur_helper(None if preferred == 'auto' else preferred)
    if aur_helper:
        env, _ = app.prepare_askpass_env()
        w4 = CommandWorker([aur_helper, "-Syu", "--noconfirm", "--sudoflags", "-A"], sudo=False, env=env)
        w4.output.connect(app.log)
        w4.error.connect(app.log)
        w4.run()
    else:
        app.log("No AUR helper available. Install yay, paru, trizen, or pikaur.")

# === services: askpass_service.py ===
import os
import shutil
import tempfile


def get_sudo_askpass():
    candidates = [
        "ksshaskpass",
        "ssh-askpass",
        "qt5-askpass",
        "lxqt-openssh-askpass",
    ]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return None


def prepare_askpass_env():
    env = os.environ.copy()
    cleanup_path = None
    
    # Check if any GUI dialog tools are available
    available_tools = []
    for tool in ["kdialog", "zenity", "yad"]:
        if shutil.which(tool):
            available_tools.append(tool)
    
    # If no GUI tools available, return None to indicate failure
    if not available_tools:
        print("Warning: No GUI authentication tools found (kdialog, zenity, yad)")
        return env, None
    
    # Ensure DISPLAY is set for GUI dialogs
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    
    try:
        script = """#!/bin/sh
# Single-attempt password dialog - no retries
title=${NEOARCH_ASKPASS_TITLE:-"NeoArch - AUR Install"}
text=${NEOARCH_ASKPASS_TEXT:-"AUR packages are community-maintained and may be unsafe.\nEnter your password to proceed."}
icon=${NEOARCH_ASKPASS_ICON:-"dialog-password"}

# Debug logging
echo "NeoArch askpass called: $title" >> /tmp/neoarch-askpass.log

# Ensure DISPLAY is set
export DISPLAY="${DISPLAY:-:0}"

# Try different dialog tools, exit immediately on cancellation
if command -v kdialog >/dev/null 2>&1; then
  echo "Using kdialog for password prompt" >> /tmp/neoarch-askpass.log
  result=$(kdialog --title "$title" --icon "$icon" --password "$text" 2>/dev/null)
  exit_code=$?
elif command -v zenity >/dev/null 2>&1; then
  echo "Using zenity for password prompt" >> /tmp/neoarch-askpass.log
  result=$(zenity --password --title="$title" --text="$text" --window-icon="$icon" 2>/dev/null)
  exit_code=$?
elif command -v yad >/dev/null 2>&1; then
  echo "Using yad for password prompt" >> /tmp/neoarch-askpass.log
  result=$(yad --title="$title" --text="$text" --entry --hide-text --window-icon="$icon" 2>/dev/null)
  exit_code=$?
else
  # Fallback to terminal-based password prompt if no GUI available
  echo "Using terminal fallback for password prompt" >> /tmp/neoarch-askpass.log
  echo "$text" >&2
  read -s -p "Password: " result
  echo >&2
  exit_code=$?
fi

# Log result
echo "Password prompt result: exit_code=$exit_code, has_result=$([ -n "$result" ] && echo yes || echo no)" >> /tmp/neoarch-askpass.log

# If cancelled or failed, exit with error code
if [ $exit_code -ne 0 ] || [ -z "$result" ]; then
  echo "Password prompt cancelled or failed" >> /tmp/neoarch-askpass.log
  exit 1
fi

# Output the password and exit successfully
echo "Password prompt successful" >> /tmp/neoarch-askpass.log
echo "$result"
exit 0
"""
        # Try to create temp file in user's temp directory first
        temp_dir = os.path.expanduser("~/.cache")
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                temp_dir = None
        
        if temp_dir and os.access(temp_dir, os.W_OK):
            fd, path = tempfile.mkstemp(prefix="neoarch-askpass-", suffix=".sh", dir=temp_dir)
        else:
            fd, path = tempfile.mkstemp(prefix="neoarch-askpass-", suffix=".sh")
            
        with os.fdopen(fd, "w") as f:
            f.write(script)
        os.chmod(path, 0o700)
        cleanup_path = path
        env["SUDO_ASKPASS"] = path
        env["SSH_ASKPASS"] = path
        env["SUDO_ASKPASS_REQUIRE"] = "force"
    except Exception as e:
        # If we can't create the askpass script, log the error but continue
        print(f"Warning: Could not create askpass script: {e}")
    
    return env, cleanup_path

# === components: plugins_data.py ===
import os
import random

def get_plugins_data():
    """Return initial plugin specifications (fast loading)"""
    plugins_items_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "plugins-items"))

    return [
        # Popular/System Tools (Load First - 8 items)
        {
            'id': 'bleachbit',
            'name': 'BleachBit',
            'desc': 'System cleaner to free disk space and guard your privacy.',
            'pkg': 'bleachbit',
            'cmd': 'bleachbit',
            'icon': os.path.join(plugins_items_dir, 'BleachBit.png'),
            'category': 'System',
        },
        {
            'id': 'gparted',
            'name': 'GParted',
            'desc': 'Partition editor for graphically managing disk partitions.',
            'pkg': 'gparted',
            'cmd': 'gparted',
            'icon': os.path.join(plugins_items_dir, 'gparted.jpeg'),
            'category': 'System',
        },
        {
            'id': 'btop',
            'name': 'btop',
            'desc': 'Modern resource monitor for CPU, memory, disks, network.',
            'pkg': 'btop',
            'cmd': 'btop',
            'icon': os.path.join(plugins_items_dir, 'btop.png'),
            'category': 'Monitor',
        },
        {
            'id': 'code',
            'name': 'Visual Studio Code',
            'desc': 'Powerful source code editor with IntelliSense and debugging.',
            'pkg': 'code',
            'cmd': 'code',
            'icon': os.path.join(plugins_items_dir, 'vscode.png'),
            'category': 'Development',
        },
        {
            'id': 'firefox',
            'name': 'Firefox',
            'desc': 'Fast, private & safe web browser from Mozilla.',
            'pkg': 'firefox',
            'cmd': 'firefox',
            'icon': os.path.join(plugins_items_dir, 'firefox.png'),
            'category': 'Internet',
        },
        {
            'id': 'vlc',
            'name': 'VLC Media Player',
            'desc': 'Universal multimedia player for all formats.',
            'pkg': 'vlc',
            'cmd': 'vlc',
            'icon': os.path.join(plugins_items_dir, 'vlc.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'steam',
            'name': 'Steam',
            'desc': 'Digital distribution platform for PC gaming.',
            'pkg': 'steam',
            'cmd': 'steam',
            'icon': os.path.join(plugins_items_dir, 'steam.png'),
            'category': 'Games',
        },
        {
            'id': 'libreoffice',
            'name': 'LibreOffice',
            'desc': 'Free and open-source office productivity software suite.',
            'pkg': 'libreoffice-fresh',
            'cmd': 'libreoffice',
            'icon': os.path.join(plugins_items_dir, 'libreoffice.png'),
            'category': 'Office',
        },
    ]

def get_all_plugins_data():
    """Return all plugin specifications (lazy loading)"""
    plugins_items_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "plugins-items"))

    plugins = [
        # System Tools
        {
            'id': 'bleachbit',
            'name': 'BleachBit',
            'desc': 'System cleaner to free disk space and guard your privacy.',
            'pkg': 'bleachbit',
            'cmd': 'bleachbit',
            'icon': os.path.join(plugins_items_dir, 'BleachBit.png'),
            'category': 'System',
        },
        {
            'id': 'timeshift',
            'name': 'Timeshift',
            'desc': 'System restore utility for Linux.',
            'pkg': 'timeshift',
            'cmd': 'timeshift-gtk',
            'icon': os.path.join(plugins_items_dir, 'timeshift.png'),
            'category': 'Backup',
        },
        {
            'id': 'baobab',
            'name': 'Disk Usage Analyzer',
            'desc': 'Visualize disk usage and identify large folders/files.',
            'pkg': 'baobab',
            'cmd': 'baobab',
            'icon': os.path.join(plugins_items_dir, 'diskusageanalyzer.png'),
            'category': 'System',
        },
        {
            'id': 'deja-dup',
            'name': 'Déjà Dup (Backups)',
            'desc': 'Simple backups for GNOME with cloud support.',
            'pkg': 'deja-dup',
            'cmd': 'deja-dup',
            'icon': os.path.join(plugins_items_dir, 'DejaDup.png'),
            'category': 'Backup',
        },
        {
            'id': 'gparted',
            'name': 'GParted',
            'desc': 'Partition editor for graphically managing disk partitions.',
            'pkg': 'gparted',
            'cmd': 'gparted',
            'icon': os.path.join(plugins_items_dir, 'gparted.jpeg'),
            'category': 'System',
        },
        {
            'id': 'gnome-disk-utility',
            'name': 'GNOME Disks',
            'desc': 'Manage disks and media — partition, format and benchmark.',
            'pkg': 'gnome-disk-utility',
            'cmd': 'gnome-disks',
            'icon': os.path.join(plugins_items_dir, 'gnomedisk.jpeg'),
            'category': 'System',
        },
        {
            'id': 'pavucontrol',
            'name': 'PulseAudio Volume Control',
            'desc': 'Advanced audio mixer for PulseAudio.',
            'pkg': 'pavucontrol',
            'cmd': 'pavucontrol',
            'icon': os.path.join(plugins_items_dir, 'pulseaudio.png'),
            'category': 'System',
        },
        {
            'id': 'system-config-printer',
            'name': 'Printers',
            'desc': 'Configure printers and manage print jobs.',
            'pkg': 'system-config-printer',
            'cmd': 'system-config-printer',
            'icon': os.path.join(plugins_items_dir, 'printers.png'),
            'category': 'System',
        },

        # System Monitoring
        {
            'id': 'btop',
            'name': 'btop',
            'desc': 'Modern resource monitor for CPU, memory, disks, network.',
            'pkg': 'btop',
            'cmd': 'btop',
            'icon': os.path.join(plugins_items_dir, 'btop.png'),
            'category': 'Monitor',
        },
        {
            'id': 'htop',
            'name': 'htop',
            'desc': 'Interactive process viewer and system monitor.',
            'pkg': 'htop',
            'cmd': 'htop',
            'icon': os.path.join(plugins_items_dir, 'htop.png'),
            'category': 'Monitor',
        },
        {
            'id': 'gnome-system-monitor',
            'name': 'GNOME System Monitor',
            'desc': 'Graphical system monitor for processes and resources.',
            'pkg': 'gnome-system-monitor',
            'cmd': 'gnome-system-monitor',
            'icon': os.path.join(plugins_items_dir, 'gnomesystem.jpeg'),
            'category': 'Monitor',
        },

        # GPU Tools
        {
            'id': 'nvidia-settings',
            'name': 'NVIDIA Settings',
            'desc': 'Configure NVIDIA drivers and GPU options.',
            'pkg': 'nvidia-settings',
            'cmd': 'nvidia-settings',
            'icon': os.path.join(plugins_items_dir, 'nvideasettings.jpeg'),
            'category': 'GPU',
        },
        {
            'id': 'nvtop',
            'name': 'nvtop',
            'desc': 'NVIDIA/AMD Intel GPU process monitor (requires supported GPU).',
            'pkg': 'nvtop',
            'cmd': 'nvtop',
            'icon': os.path.join(plugins_items_dir, 'nvtop.png'),
            'category': 'GPU',
        },

        # Utilities
        {
            'id': 'simple-scan',
            'name': 'Document Scanner',
            'desc': 'Scan documents and photos with a simple interface.',
            'pkg': 'simple-scan',
            'cmd': 'simple-scan',
            'icon': os.path.join(plugins_items_dir, 'documentscanner.png'),
            'category': 'Utility',
        },
        {
            'id': 'file-roller',
            'name': 'Archive Manager',
            'desc': 'Create and extract archives (zip, tar, etc.).',
            'pkg': 'file-roller',
            'cmd': 'file-roller',
            'icon': os.path.join(plugins_items_dir, 'achive.png'),
            'category': 'Utility',
        },
        {
            'id': 'calibre',
            'name': 'Calibre',
            'desc': 'Powerful and easy to use e-book manager.',
            'pkg': 'calibre',
            'cmd': 'calibre',
            'icon': os.path.join(plugins_items_dir, 'calibre.png'),
            'category': 'Utility',
        },

        # Multimedia
        {
            'id': 'vlc',
            'name': 'VLC Media Player',
            'desc': 'Universal multimedia player for all formats.',
            'pkg': 'vlc',
            'cmd': 'vlc',
            'icon': os.path.join(plugins_items_dir, 'vlc.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'audacity',
            'name': 'Audacity',
            'desc': 'Free audio editor and recorder for all platforms.',
            'pkg': 'audacity',
            'cmd': 'audacity',
            'icon': os.path.join(plugins_items_dir, 'audacity.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'obs-studio',
            'name': 'OBS Studio',
            'desc': 'Free and open source software for video recording.',
            'pkg': 'obs-studio',
            'cmd': 'obs',
            'icon': os.path.join(plugins_items_dir, 'obs.png'),
            'category': 'Multimedia',
        },

        # Graphics
        {
            'id': 'gimp',
            'name': 'GIMP',
            'desc': 'GNU Image Manipulation Program for photo editing.',
            'pkg': 'gimp',
            'cmd': 'gimp',
            'icon': os.path.join(plugins_items_dir, 'gimp.png'),
            'category': 'Graphics',
        },
        {
            'id': 'blender',
            'name': 'Blender',
            'desc': '3D modeling, animation, and rendering software.',
            'pkg': 'blender',
            'cmd': 'blender',
            'icon': os.path.join(plugins_items_dir, 'blender.png'),
            'category': 'Graphics',
        },

        # Internet & Communication
        {
            'id': 'thunderbird',
            'name': 'Thunderbird',
            'desc': 'Free email client and news reader.',
            'pkg': 'thunderbird',
            'cmd': 'thunderbird',
            'icon': os.path.join(plugins_items_dir, 'thunderbird.png'),
            'category': 'Internet',
        },
        {
            'id': 'transmission',
            'name': 'Transmission',
            'desc': 'Fast, easy, and free BitTorrent client.',
            'pkg': 'transmission-gtk',
            'cmd': 'transmission-gtk',
            'icon': os.path.join(plugins_items_dir, 'transmission.png'),
            'category': 'Internet',
        },
        {
            'id': 'qbittorrent',
            'name': 'qBittorrent',
            'desc': 'Open source BitTorrent client written in C++.',
            'pkg': 'qbittorrent',
            'cmd': 'qbittorrent',
            'icon': os.path.join(plugins_items_dir, 'qbittorrent.png'),
            'category': 'Internet',
        },

        # Development Tools
        {
            'id': 'code',
            'name': 'Visual Studio Code',
            'desc': 'Powerful source code editor with IntelliSense and debugging.',
            'pkg': 'code',
            'cmd': 'code',
            'icon': os.path.join(plugins_items_dir, 'vscode.png'),
            'category': 'Development',
        },
        {
            'id': 'git',
            'name': 'Git',
            'desc': 'Distributed version control system for tracking changes.',
            'pkg': 'git',
            'cmd': 'git',
            'icon': os.path.join(plugins_items_dir, 'git.png'),
            'category': 'Development',
        },
        {
            'id': 'nodejs',
            'name': 'Node.js',
            'desc': 'JavaScript runtime built on Chrome\'s V8 JavaScript engine.',
            'pkg': 'nodejs',
            'cmd': 'node',
            'icon': os.path.join(plugins_items_dir, 'nodejs.png'),
            'category': 'Development',
        },
        {
            'id': 'python',
            'name': 'Python',
            'desc': 'High-level programming language for general-purpose programming.',
            'pkg': 'python',
            'cmd': 'python',
            'icon': os.path.join(plugins_items_dir, 'python.png'),
            'category': 'Development',
        },

        # Office & Productivity
        {
            'id': 'libreoffice',
            'name': 'LibreOffice',
            'desc': 'Free and open-source office productivity software suite.',
            'pkg': 'libreoffice-fresh',
            'cmd': 'libreoffice',
            'icon': os.path.join(plugins_items_dir, 'libreoffice.png'),
            'category': 'Office',
        },
        {
            'id': 'onlyoffice',
            'name': 'OnlyOffice',
            'desc': 'Complete office suite with document, spreadsheet and presentation editors.',
            'pkg': 'onlyoffice-bin',
            'cmd': 'onlyoffice-desktopeditors',
            'icon': os.path.join(plugins_items_dir, 'onlyoffice.png'),
            'category': 'Office',
        },
        {
            'id': 'notion',
            'name': 'Notion',
            'desc': 'All-in-one workspace for notes, tasks, wikis, and databases.',
            'pkg': 'notion-app',
            'cmd': 'notion-app',
            'icon': os.path.join(plugins_items_dir, 'notion.png'),
            'category': 'Office',
        },

        # Games
        {
            'id': 'steam',
            'name': 'Steam',
            'desc': 'Digital distribution platform for PC gaming.',
            'pkg': 'steam',
            'cmd': 'steam',
            'icon': os.path.join(plugins_items_dir, 'steam.png'),
            'category': 'Games',
        },
        {
            'id': 'lutris',
            'name': 'Lutris',
            'desc': 'Gaming platform for Linux with Wine and Proton support.',
            'pkg': 'lutris',
            'cmd': 'lutris',
            'icon': os.path.join(plugins_items_dir, 'lutris.png'),
            'category': 'Games',
        },
        {
            'id': 'heroic',
            'name': 'Heroic Games Launcher',
            'desc': 'Native GOG, Epic Games and Amazon Prime Games launcher.',
            'pkg': 'heroic-games-launcher-bin',
            'cmd': 'heroic',
            'icon': os.path.join(plugins_items_dir, 'heroic.png'),
            'category': 'Games',
        },

        # Security & Privacy
        {
            'id': 'keepassxc',
            'name': 'KeePassXC',
            'desc': 'Cross-platform community-driven port of KeePass password manager.',
            'pkg': 'keepassxc',
            'cmd': 'keepassxc',
            'icon': os.path.join(plugins_items_dir, 'keepassxc.png'),
            'category': 'Security',
        },
        {
            'id': 'bitwarden',
            'name': 'Bitwarden',
            'desc': 'Secure and free password manager for all of your devices.',
            'pkg': 'bitwarden',
            'cmd': 'bitwarden',
            'icon': os.path.join(plugins_items_dir, 'bitwarden.png'),
            'category': 'Security',
        },
        {
            'id': 'tor-browser',
            'name': 'Tor Browser',
            'desc': 'Private web browser that protects your anonymity.',
            'pkg': 'tor-browser',
            'cmd': 'tor-browser',
            'icon': os.path.join(plugins_items_dir, 'tor.png'),
            'category': 'Security',
        },

        # Communication
        {
            'id': 'discord',
            'name': 'Discord',
            'desc': 'Voice, video and text chat app for communities and friends.',
            'pkg': 'discord',
            'cmd': 'discord',
            'icon': os.path.join(plugins_items_dir, 'discord.png'),
            'category': 'Communication',
        },
        {
            'id': 'telegram',
            'name': 'Telegram Desktop',
            'desc': 'Fast and secure desktop messaging app.',
            'pkg': 'telegram-desktop',
            'cmd': 'telegram-desktop',
            'icon': os.path.join(plugins_items_dir, 'telegram.png'),
            'category': 'Communication',
        },
        {
            'id': 'signal',
            'name': 'Signal',
            'desc': 'Private messenger with end-to-end encryption.',
            'pkg': 'signal-desktop',
            'cmd': 'signal-desktop',
            'icon': os.path.join(plugins_items_dir, 'signal.png'),
            'category': 'Communication',
        },
        {
            'id': 'zoom',
            'name': 'Zoom',
            'desc': 'Video conferencing and web conferencing service.',
            'pkg': 'zoom',
            'cmd': 'zoom',
            'icon': os.path.join(plugins_items_dir, 'zoom.png'),
            'category': 'Communication',
        },

        # Education & Learning
        {
            'id': 'anki',
            'name': 'Anki',
            'desc': 'Powerful, intelligent flash cards for effective learning.',
            'pkg': 'anki',
            'cmd': 'anki',
            'icon': os.path.join(plugins_items_dir, 'anki.png'),
            'category': 'Education',
        },
        {
            'id': 'geogebra',
            'name': 'GeoGebra',
            'desc': 'Dynamic mathematics software for all levels of education.',
            'pkg': 'geogebra',
            'cmd': 'geogebra',
            'icon': os.path.join(plugins_items_dir, 'geogebra.png'),
            'category': 'Education',
        },

        # Customization
        {
            'id': 'latte-dock',
            'name': 'Latte Dock',
            'desc': 'Dock based on Plasma frameworks for an elegant desktop.',
            'pkg': 'latte-dock',
            'cmd': 'latte-dock',
            'icon': os.path.join(plugins_items_dir, 'latte.png'),
            'category': 'Customization',
        },
        {
            'id': 'conky',
            'name': 'Conky',
            'desc': 'Light-weight system monitor for X windows.',
            'pkg': 'conky',
            'cmd': 'conky',
            'icon': os.path.join(plugins_items_dir, 'conky.png'),
            'category': 'Customization',
        },
        {
            'id': 'neofetch',
            'name': 'Neofetch',
            'desc': 'Command-line system information tool with ASCII art.',
            'pkg': 'neofetch',
            'cmd': 'neofetch',
            'icon': os.path.join(plugins_items_dir, 'neofetch.png'),
            'category': 'Customization',
        },
        {
            'id': 'polybar',
            'name': 'Polybar',
            'desc': 'Fast and easy-to-use status bar for tiling window managers.',
            'pkg': 'polybar',
            'cmd': 'polybar',
            'icon': os.path.join(plugins_items_dir, 'polybar.png'),
            'category': 'Customization',
        },

        # Web Browsers
        {
            'id': 'firefox',
            'name': 'Firefox',
            'desc': 'Fast, private & safe web browser from Mozilla.',
            'pkg': 'firefox',
            'cmd': 'firefox',
            'icon': os.path.join(plugins_items_dir, 'firefox.png'),
            'category': 'Internet',
        },
        {
            'id': 'chromium',
            'name': 'Chromium',
            'desc': 'Open-source web browser project from Google.',
            'pkg': 'chromium',
            'cmd': 'chromium',
            'icon': os.path.join(plugins_items_dir, 'chromium.png'),
            'category': 'Internet',
        },
        {
            'id': 'brave',
            'name': 'Brave Browser',
            'desc': 'Privacy-focused web browser with built-in ad blocker.',
            'pkg': 'brave-bin',
            'cmd': 'brave',
            'icon': os.path.join(plugins_items_dir, 'brave.png'),
            'category': 'Internet',
        },
        {
            'id': 'opera',
            'name': 'Opera',
            'desc': 'Fast, secure, easy-to-use browser with built-in VPN.',
            'pkg': 'opera',
            'cmd': 'opera',
            'icon': os.path.join(plugins_items_dir, 'opera.png'),
            'category': 'Internet',
        },

        # Text Editors & IDEs
        {
            'id': 'vim',
            'name': 'Vim',
            'desc': 'Highly configurable text editor built to enable efficient text editing.',
            'pkg': 'vim',
            'cmd': 'vim',
            'icon': os.path.join(plugins_items_dir, 'vim.png'),
            'category': 'Development',
        },
        {
            'id': 'neovim',
            'name': 'Neovim',
            'desc': 'Hyperextensible Vim-based text editor.',
            'pkg': 'neovim',
            'cmd': 'nvim',
            'icon': os.path.join(plugins_items_dir, 'neovim.png'),
            'category': 'Development',
        },
        {
            'id': 'sublime-text',
            'name': 'Sublime Text',
            'desc': 'Sophisticated text editor for code, markup and prose.',
            'pkg': 'sublime-text-4',
            'cmd': 'subl',
            'icon': os.path.join(plugins_items_dir, 'sublime.png'),
            'category': 'Development',
        },
        {
            'id': 'atom',
            'name': 'Atom',
            'desc': 'Hackable text editor for the 21st Century.',
            'pkg': 'atom',
            'cmd': 'atom',
            'icon': os.path.join(plugins_items_dir, 'atom.png'),
            'category': 'Development',
        },
        {
            'id': 'intellij-idea',
            'name': 'IntelliJ IDEA',
            'desc': 'Powerful IDE for Java and other JVM languages.',
            'pkg': 'intellij-idea-community-edition',
            'cmd': 'idea',
            'icon': os.path.join(plugins_items_dir, 'intellij.png'),
            'category': 'Development',
        },

        # Media & Entertainment
        {
            'id': 'spotify',
            'name': 'Spotify',
            'desc': 'Digital music streaming service with millions of songs.',
            'pkg': 'spotify',
            'cmd': 'spotify',
            'icon': os.path.join(plugins_items_dir, 'spotify.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'mpv',
            'name': 'MPV',
            'desc': 'Free, open source, and cross-platform media player.',
            'pkg': 'mpv',
            'cmd': 'mpv',
            'icon': os.path.join(plugins_items_dir, 'mpv.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'kdenlive',
            'name': 'Kdenlive',
            'desc': 'Free and open-source video editing software.',
            'pkg': 'kdenlive',
            'cmd': 'kdenlive',
            'icon': os.path.join(plugins_items_dir, 'kdenlive.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'handbrake',
            'name': 'HandBrake',
            'desc': 'Open-source video transcoder for converting video files.',
            'pkg': 'handbrake',
            'cmd': 'ghb',
            'icon': os.path.join(plugins_items_dir, 'handbrake.png'),
            'category': 'Multimedia',
        },

        # Graphics & Design
        {
            'id': 'inkscape',
            'name': 'Inkscape',
            'desc': 'Professional vector graphics editor for creating scalable graphics.',
            'pkg': 'inkscape',
            'cmd': 'inkscape',
            'icon': os.path.join(plugins_items_dir, 'inkscape.png'),
            'category': 'Graphics',
        },
        {
            'id': 'krita',
            'name': 'Krita',
            'desc': 'Professional FREE and open source painting program.',
            'pkg': 'krita',
            'cmd': 'krita',
            'icon': os.path.join(plugins_items_dir, 'krita.png'),
            'category': 'Graphics',
        },
        {
            'id': 'darktable',
            'name': 'Darktable',
            'desc': 'Open source photography workflow application and RAW developer.',
            'pkg': 'darktable',
            'cmd': 'darktable',
            'icon': os.path.join(plugins_items_dir, 'darktable.png'),
            'category': 'Graphics',
        },
        {
            'id': 'rawtherapee',
            'name': 'RawTherapee',
            'desc': 'Powerful cross-platform raw photo processing program.',
            'pkg': 'rawtherapee',
            'cmd': 'rawtherapee',
            'icon': os.path.join(plugins_items_dir, 'rawtherapee.png'),
            'category': 'Graphics',
        },

        # File Management
        {
            'id': 'nautilus',
            'name': 'Nautilus',
            'desc': 'GNOME file manager with clean and simple interface.',
            'pkg': 'nautilus',
            'cmd': 'nautilus',
            'icon': os.path.join(plugins_items_dir, 'nautilus.png'),
            'category': 'Utility',
        },
        {
            'id': 'thunar',
            'name': 'Thunar',
            'desc': 'Fast and easy to use file manager for Xfce desktop.',
            'pkg': 'thunar',
            'cmd': 'thunar',
            'icon': os.path.join(plugins_items_dir, 'thunar.png'),
            'category': 'Utility',
        },
        {
            'id': 'ranger',
            'name': 'Ranger',
            'desc': 'Console file manager with VI key bindings.',
            'pkg': 'ranger',
            'cmd': 'ranger',
            'icon': os.path.join(plugins_items_dir, 'ranger.png'),
            'category': 'Utility',
        },

        # Terminal Emulators
        {
            'id': 'kitty',
            'name': 'Kitty',
            'desc': 'Fast, feature-rich, GPU based terminal emulator.',
            'pkg': 'kitty',
            'cmd': 'kitty',
            'icon': os.path.join(plugins_items_dir, 'kitty.png'),
            'category': 'System',
        },
        {
            'id': 'alacritty',
            'name': 'Alacritty',
            'desc': 'Cross-platform, GPU-accelerated terminal emulator.',
            'pkg': 'alacritty',
            'cmd': 'alacritty',
            'icon': os.path.join(plugins_items_dir, 'alacritty.png'),
            'category': 'System',
        },
        {
            'id': 'terminator',
            'name': 'Terminator',
            'desc': 'Terminal emulator with support for multiple terminals in one window.',
            'pkg': 'terminator',
            'cmd': 'terminator',
            'icon': os.path.join(plugins_items_dir, 'terminator.png'),
            'category': 'System',
        },

        # Productivity & Notes
        {
            'id': 'obsidian',
            'name': 'Obsidian',
            'desc': 'Powerful knowledge base that works on top of local folder of plain text files.',
            'pkg': 'obsidian',
            'cmd': 'obsidian',
            'icon': os.path.join(plugins_items_dir, 'obsidian.png'),
            'category': 'Office',
        },
        {
            'id': 'joplin',
            'name': 'Joplin',
            'desc': 'Free, open source note taking and to-do application.',
            'pkg': 'joplin-appimage',
            'cmd': 'joplin',
            'icon': os.path.join(plugins_items_dir, 'joplin.png'),
            'category': 'Office',
        },
        {
            'id': 'typora',
            'name': 'Typora',
            'desc': 'Minimal markdown editor with live preview.',
            'pkg': 'typora',
            'cmd': 'typora',
            'icon': os.path.join(plugins_items_dir, 'typora.png'),
            'category': 'Office',
        },

        # Virtualization
        {
            'id': 'virtualbox',
            'name': 'VirtualBox',
            'desc': 'Powerful x86 and AMD64/Intel64 virtualization product.',
            'pkg': 'virtualbox',
            'cmd': 'virtualbox',
            'icon': os.path.join(plugins_items_dir, 'virtualbox.png'),
            'category': 'System',
        },
        {
            'id': 'qemu',
            'name': 'QEMU',
            'desc': 'Generic and open source machine emulator and virtualizer.',
            'pkg': 'qemu-full',
            'cmd': 'qemu-system-x86_64',
            'icon': os.path.join(plugins_items_dir, 'qemu.png'),
            'category': 'System',
        },

        # Network Tools
        {
            'id': 'wireshark',
            'name': 'Wireshark',
            'desc': 'Network protocol analyzer for troubleshooting and analysis.',
            'pkg': 'wireshark-qt',
            'cmd': 'wireshark',
            'icon': os.path.join(plugins_items_dir, 'wireshark.png'),
            'category': 'Security',
        },
        {
            'id': 'nmap',
            'name': 'Nmap',
            'desc': 'Network discovery and security auditing utility.',
            'pkg': 'nmap',
            'cmd': 'nmap',
            'icon': os.path.join(plugins_items_dir, 'nmap.png'),
            'category': 'Security',
        },

        # More Games
        {
            'id': 'minecraft',
            'name': 'Minecraft Launcher',
            'desc': 'Official launcher for the popular sandbox game.',
            'pkg': 'minecraft-launcher',
            'cmd': 'minecraft-launcher',
            'icon': os.path.join(plugins_items_dir, 'minecraft.png'),
            'category': 'Games',
        },
        {
            'id': 'retroarch',
            'name': 'RetroArch',
            'desc': 'Frontend for emulators, game engines and media players.',
            'pkg': 'retroarch',
            'cmd': 'retroarch',
            'icon': os.path.join(plugins_items_dir, 'retroarch.png'),
            'category': 'Games',
        },

        # Database Tools
        {
            'id': 'dbeaver',
            'name': 'DBeaver',
            'desc': 'Universal database tool for developers and database administrators.',
            'pkg': 'dbeaver',
            'cmd': 'dbeaver',
            'icon': os.path.join(plugins_items_dir, 'dbeaver.png'),
            'category': 'Development',
        },

        # More Education
        {
            'id': 'stellarium',
            'name': 'Stellarium',
            'desc': 'Free open source planetarium for your computer.',
            'pkg': 'stellarium',
            'cmd': 'stellarium',
            'icon': os.path.join(plugins_items_dir, 'stellarium.png'),
            'category': 'Education',
        },
        {
            'id': 'kstars',
            'name': 'KStars',
            'desc': 'Desktop planetarium showing accurate night sky simulation.',
            'pkg': 'kstars',
            'cmd': 'kstars',
            'icon': os.path.join(plugins_items_dir, 'kstars.png'),
            'category': 'Education',
        },

        # AUR Packages
        {
            'id': 'yay',
            'name': 'Yay',
            'desc': 'AUR helper written in Go for easy AUR package management.',
            'pkg': 'aur/yay',
            'cmd': 'yay',
            'icon': os.path.join(plugins_items_dir, 'yay.png'),
            'category': 'Development',
        },
        {
            'id': 'paru',
            'name': 'Paru',
            'desc': 'Feature-rich AUR helper with pacman-like interface.',
            'pkg': 'aur/paru',
            'cmd': 'paru',
            'icon': os.path.join(plugins_items_dir, 'paru.png'),
            'category': 'Development',
        },
        {
            'id': 'visual-studio-code-bin',
            'name': 'VS Code (Binary)',
            'desc': 'Official VS Code binary from Microsoft via AUR.',
            'pkg': 'aur/visual-studio-code-bin',
            'cmd': 'code',
            'icon': os.path.join(plugins_items_dir, 'vscode.png'),
            'category': 'Development',
        },
        {
            'id': 'discord-bin',
            'name': 'Discord (Binary)',
            'desc': 'Official Discord binary from AUR.',
            'pkg': 'aur/discord-bin',
            'cmd': 'discord',
            'icon': os.path.join(plugins_items_dir, 'discord.png'),
            'category': 'Communication',
        },
        {
            'id': 'spotify-bin',
            'name': 'Spotify (Binary)',
            'desc': 'Official Spotify binary from AUR.',
            'pkg': 'aur/spotify-bin',
            'cmd': 'spotify',
            'icon': os.path.join(plugins_items_dir, 'spotify.png'),
            'category': 'Multimedia',
        },

        # Flatpak Packages
        {
            'id': 'org.gnome.Evolution',
            'name': 'Evolution',
            'desc': 'GNOME email and calendar application.',
            'pkg': 'org.gnome.Evolution.flatpak',
            'cmd': 'evolution',
            'icon': os.path.join(plugins_items_dir, 'evolution.png'),
            'category': 'Internet',
        },
        {
            'id': 'org.gnome.Boxes',
            'name': 'GNOME Boxes',
            'desc': 'Simple GNOME application to access remote or virtual systems.',
            'pkg': 'org.gnome.Boxes.flatpak',
            'cmd': 'gnome-boxes',
            'icon': os.path.join(plugins_items_dir, 'boxes.png'),
            'category': 'System',
        },
        {
            'id': 'com.github.tchx84.Flatseal',
            'name': 'Flatseal',
            'desc': 'Manage Flatpak permissions graphically.',
            'pkg': 'com.github.tchx84.Flatseal.flatpak',
            'cmd': 'flatseal',
            'icon': os.path.join(plugins_items_dir, 'flatseal.png'),
            'category': 'Utility',
        },
        {
            'id': 'org.kde.kdenlive',
            'name': 'Kdenlive (Flatpak)',
            'desc': 'Free and open-source video editing software (Flatpak version).',
            'pkg': 'org.kde.kdenlive.flatpak',
            'cmd': 'kdenlive',
            'icon': os.path.join(plugins_items_dir, 'kdenlive.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'org.gimp.GIMP',
            'name': 'GIMP (Flatpak)',
            'desc': 'GNU Image Manipulation Program (Flatpak version).',
            'pkg': 'org.gimp.GIMP.flatpak',
            'cmd': 'gimp',
            'icon': os.path.join(plugins_items_dir, 'gimp.png'),
            'category': 'Graphics',
        },

        # NPM Packages
        {
            'id': 'npm-http-server',
            'name': 'HTTP Server',
            'desc': 'Simple zero-configuration command-line HTTP server.',
            'pkg': 'npm-http-server',
            'cmd': 'http-server',
            'icon': os.path.join(plugins_items_dir, 'nodejs.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-typescript',
            'name': 'TypeScript',
            'desc': 'TypeScript is a typed superset of JavaScript.',
            'pkg': 'npm-typescript',
            'cmd': 'tsc',
            'icon': os.path.join(plugins_items_dir, 'typescript.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-webpack',
            'name': 'Webpack',
            'desc': 'Module bundler for JavaScript applications.',
            'pkg': 'npm-webpack',
            'cmd': 'webpack',
            'icon': os.path.join(plugins_items_dir, 'webpack.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-eslint',
            'name': 'ESLint',
            'desc': 'Pluggable JavaScript linter for identifying and reporting patterns.',
            'pkg': 'npm-eslint',
            'cmd': 'eslint',
            'icon': os.path.join(plugins_items_dir, 'eslint.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-prettier',
            'name': 'Prettier',
            'desc': 'Code formatter for JavaScript, CSS, JSON and more.',
            'pkg': 'npm-prettier',
            'cmd': 'prettier',
            'icon': os.path.join(plugins_items_dir, 'prettier.png'),
            'category': 'Development',
        },

        # More AUR Packages
        {
            'id': 'google-chrome',
            'name': 'Google Chrome',
            'desc': 'Fast, secure web browser from Google.',
            'pkg': 'aur/google-chrome',
            'cmd': 'google-chrome',
            'icon': os.path.join(plugins_items_dir, 'chrome.png'),
            'category': 'Internet',
        },
        {
            'id': 'slack-desktop',
            'name': 'Slack',
            'desc': 'Team messaging and collaboration platform.',
            'pkg': 'aur/slack-desktop',
            'cmd': 'slack',
            'icon': os.path.join(plugins_items_dir, 'slack.png'),
            'category': 'Communication',
        },
        {
            'id': 'teams',
            'name': 'Microsoft Teams',
            'desc': 'Microsoft Teams for Linux.',
            'pkg': 'aur/teams',
            'cmd': 'teams',
            'icon': os.path.join(plugins_items_dir, 'teams.png'),
            'category': 'Communication',
        },
        {
            'id': 'postman',
            'name': 'Postman',
            'desc': 'API development and testing platform.',
            'pkg': 'aur/postman-bin',
            'cmd': 'postman',
            'icon': os.path.join(plugins_items_dir, 'postman.png'),
            'category': 'Development',
        },
        {
            'id': 'mongodb-compass',
            'name': 'MongoDB Compass',
            'desc': 'MongoDB GUI for exploring and manipulating data.',
            'pkg': 'aur/mongodb-compass',
            'cmd': 'mongodb-compass',
            'icon': os.path.join(plugins_items_dir, 'mongodb.png'),
            'category': 'Development',
        },

        # More Flatpak Packages
        {
            'id': 'org.mozilla.firefox',
            'name': 'Firefox (Flatpak)',
            'desc': 'Fast, private & safe web browser (Flatpak version).',
            'pkg': 'org.mozilla.firefox.flatpak',
            'cmd': 'firefox',
            'icon': os.path.join(plugins_items_dir, 'firefox.png'),
            'category': 'Internet',
        },
        {
            'id': 'org.blender.Blender',
            'name': 'Blender (Flatpak)',
            'desc': '3D modeling and animation software (Flatpak version).',
            'pkg': 'org.blender.Blender.flatpak',
            'cmd': 'blender',
            'icon': os.path.join(plugins_items_dir, 'blender.png'),
            'category': 'Graphics',
        },
        {
            'id': 'org.inkscape.Inkscape',
            'name': 'Inkscape (Flatpak)',
            'desc': 'Vector graphics editor (Flatpak version).',
            'pkg': 'org.inkscape.Inkscape.flatpak',
            'cmd': 'inkscape',
            'icon': os.path.join(plugins_items_dir, 'inkscape.png'),
            'category': 'Graphics',
        },
        {
            'id': 'org.audacityteam.Audacity',
            'name': 'Audacity (Flatpak)',
            'desc': 'Audio editor and recorder (Flatpak version).',
            'pkg': 'org.audacityteam.Audacity.flatpak',
            'cmd': 'audacity',
            'icon': os.path.join(plugins_items_dir, 'audacity.png'),
            'category': 'Multimedia',
        },
        {
            'id': 'org.libreoffice.LibreOffice',
            'name': 'LibreOffice (Flatpak)',
            'desc': 'Office suite (Flatpak version).',
            'pkg': 'org.libreoffice.LibreOffice.flatpak',
            'cmd': 'libreoffice',
            'icon': os.path.join(plugins_items_dir, 'libreoffice.png'),
            'category': 'Office',
        },

        # More NPM Packages
        {
            'id': 'npm-react',
            'name': 'React',
            'desc': 'JavaScript library for building user interfaces.',
            'pkg': 'npm-react',
            'cmd': 'react',
            'icon': os.path.join(plugins_items_dir, 'react.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-vue',
            'name': 'Vue.js',
            'desc': 'Progressive JavaScript framework for building UIs.',
            'pkg': 'npm-vue',
            'cmd': 'vue',
            'icon': os.path.join(plugins_items_dir, 'vue.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-angular',
            'name': 'Angular',
            'desc': 'Platform for building mobile and desktop web applications.',
            'pkg': 'npm-angular',
            'cmd': 'ng',
            'icon': os.path.join(plugins_items_dir, 'angular.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-express',
            'name': 'Express.js',
            'desc': 'Fast, unopinionated web framework for Node.js.',
            'pkg': 'npm-express',
            'cmd': 'express',
            'icon': os.path.join(plugins_items_dir, 'express.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-jest',
            'name': 'Jest',
            'desc': 'JavaScript testing framework with focus on simplicity.',
            'pkg': 'npm-jest',
            'cmd': 'jest',
            'icon': os.path.join(plugins_items_dir, 'jest.png'),
            'category': 'Development',
        },
        # More AUR Packages
        {
            'id': 'visual-studio-code-insiders',
            'name': 'VS Code Insiders',
            'desc': 'Insiders build of Visual Studio Code.',
            'pkg': 'aur/visual-studio-code-insiders-bin',
            'cmd': 'code-insiders',
            'icon': os.path.join(plugins_items_dir, 'vscode.png'),
            'category': 'Development',
        },
        {
            'id': 'jetbrains-toolbox',
            'name': 'JetBrains Toolbox',
            'desc': 'JetBrains IDE management tool.',
            'pkg': 'aur/jetbrains-toolbox',
            'cmd': 'jetbrains-toolbox',
            'icon': os.path.join(plugins_items_dir, 'jetbrains.png'),
            'category': 'Development',
        },
        {
            'id': 'docker-desktop',
            'name': 'Docker Desktop',
            'desc': 'Docker containerization platform.',
            'pkg': 'aur/docker-desktop',
            'cmd': 'docker',
            'icon': os.path.join(plugins_items_dir, 'docker.png'),
            'category': 'Development',
        },
        {
            'id': 'figma',
            'name': 'Figma',
            'desc': 'Collaborative design and prototyping tool.',
            'pkg': 'aur/figma-linux',
            'cmd': 'figma',
            'icon': os.path.join(plugins_items_dir, 'figma.png'),
            'category': 'Graphics',
        },
        # More Flatpak Packages
        {
            'id': 'org.gnome.Calendar',
            'name': 'GNOME Calendar',
            'desc': 'Simple calendar application (Flatpak).',
            'pkg': 'org.gnome.Calendar.flatpak',
            'cmd': 'gnome-calendar',
            'icon': os.path.join(plugins_items_dir, 'calendar.png'),
            'category': 'Office',
        },
        {
            'id': 'org.gnome.Maps',
            'name': 'GNOME Maps',
            'desc': 'Map application (Flatpak).',
            'pkg': 'org.gnome.Maps.flatpak',
            'cmd': 'gnome-maps',
            'icon': os.path.join(plugins_items_dir, 'maps.png'),
            'category': 'Utility',
        },
        {
            'id': 'org.gnome.Weather',
            'name': 'GNOME Weather',
            'desc': 'Weather application (Flatpak).',
            'pkg': 'org.gnome.Weather.flatpak',
            'cmd': 'gnome-weather',
            'icon': os.path.join(plugins_items_dir, 'weather.png'),
            'category': 'Utility',
        },
        {
            'id': 'org.gnome.Photos',
            'name': 'GNOME Photos',
            'desc': 'Photo management application (Flatpak).',
            'pkg': 'org.gnome.Photos.flatpak',
            'cmd': 'gnome-photos',
            'icon': os.path.join(plugins_items_dir, 'photos.png'),
            'category': 'Graphics',
        },
        {
            'id': 'org.gnome.Music',
            'name': 'GNOME Music',
            'desc': 'Music player application (Flatpak).',
            'pkg': 'org.gnome.Music.flatpak',
            'cmd': 'gnome-music',
            'icon': os.path.join(plugins_items_dir, 'music.png'),
            'category': 'Multimedia',
        },
        # More NPM Packages
        {
            'id': 'npm-next',
            'name': 'Next.js',
            'desc': 'React framework for production applications.',
            'pkg': 'npm-next',
            'cmd': 'next',
            'icon': os.path.join(plugins_items_dir, 'nextjs.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-nuxt',
            'name': 'Nuxt.js',
            'desc': 'Vue.js framework for production applications.',
            'pkg': 'npm-nuxt',
            'cmd': 'nuxt',
            'icon': os.path.join(plugins_items_dir, 'nuxt.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-gatsby',
            'name': 'Gatsby',
            'desc': 'Static site generator with React.',
            'pkg': 'npm-gatsby',
            'cmd': 'gatsby',
            'icon': os.path.join(plugins_items_dir, 'gatsby.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-svelte',
            'name': 'Svelte',
            'desc': 'Compiler for building UI components.',
            'pkg': 'npm-svelte',
            'cmd': 'svelte',
            'icon': os.path.join(plugins_items_dir, 'svelte.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-tailwindcss',
            'name': 'Tailwind CSS',
            'desc': 'Utility-first CSS framework.',
            'pkg': 'npm-tailwindcss',
            'cmd': 'tailwindcss',
            'icon': os.path.join(plugins_items_dir, 'tailwind.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-bootstrap',
            'name': 'Bootstrap',
            'desc': 'Popular CSS framework for responsive design.',
            'pkg': 'npm-bootstrap',
            'cmd': 'bootstrap',
            'icon': os.path.join(plugins_items_dir, 'bootstrap.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-graphql',
            'name': 'GraphQL',
            'desc': 'Query language for APIs.',
            'pkg': 'npm-graphql',
            'cmd': 'graphql',
            'icon': os.path.join(plugins_items_dir, 'graphql.png'),
            'category': 'Development',
        },
        {
            'id': 'npm-mongodb',
            'name': 'MongoDB Driver',
            'desc': 'MongoDB Node.js driver.',
            'pkg': 'npm-mongodb',
            'cmd': 'mongo',
            'icon': os.path.join(plugins_items_dir, 'mongodb.png'),
            'category': 'Development',
        },
    ]
    return _shuffle_plugins(plugins)


def _shuffle_plugins(plugins):
    """Shuffle plugins while keeping initial popular items at the top"""
    if len(plugins) <= 8:
        return plugins
    # Keep first 8 items (popular), shuffle the rest
    popular = plugins[:8]
    rest = plugins[8:]
    random.shuffle(rest)
    return popular + rest

# === components: source_item.py ===
"""
SourceItem Component - Individual source selection widget
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtSvg import QSvgRenderer


class SourceItem(QWidget):
    """Component for individual source selection with icon and checkbox"""

    def __init__(self, source_name, icon_path, parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self.icon_path = icon_path
        self.checked = True
        self.init_ui()

    def init_ui(self):
        """Initialize the source item UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon container with better styling
        self.icon_container = QWidget()
        self.icon_container.setFixedSize(40, 40)
        self.icon_container.setObjectName("sourceIconContainer")

        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_icon(self.icon_path)
        icon_layout.addWidget(self.icon_label)

        # Checkbox with better styling
        self.checkbox = QCheckBox(self.source_name)
        self.checkbox.setChecked(self.checked)
        self.checkbox.setObjectName("sourceCheckbox")

        layout.addWidget(self.icon_container)
        layout.addWidget(self.checkbox, 1)

        # Connect signals
        self.checkbox.stateChanged.connect(self.on_state_changed)

        # Accent and interactivity
        self.accent_hex = self.get_accent_color(self.source_name)
        self.accent_color = QColor(self.accent_hex)
        self.apply_accent_styles()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(f"Search {self.source_name}")

        # Subtle shadow for icon
        try:
            shadow = QGraphicsDropShadowEffect(self.icon_container)
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 2)
            c = QColor(self.accent_color)
            c.setAlpha(80)
            shadow.setColor(c)
            self.icon_container.setGraphicsEffect(shadow)
        except ImportError:
            # Handle missing graphics effect support gracefully
            pass

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())
        self.update_visual_state()

    def set_icon(self, icon_path):
        """Set the icon for this source item"""
        # Use reliable styled text icons that match your SVG colors
        icon_styles = {
            "pacman": {
                "text": "●",  # Solid circle for Pac-Man
                "color": "#0073e1",  # Your exact blue color
                "size": "16px",
                "bg_color": "rgba(0, 115, 225, 0.15)"
            },
            "aur": {
                "text": "▲",  # Triangle for AUR
                "color": "#ff9955",  # Your exact orange color
                "size": "14px",
                "bg_color": "rgba(255, 153, 85, 0.15)"
            },
            "flatpak": {
                "text": "📦",  # Package box
                "color": "#4CAF50",  # Green color matching the SVG
                "size": "14px",
                "bg_color": "rgba(76, 175, 80, 0.15)"
            },
            "npm": {
                "text": "◆",  # Diamond shape
                "color": "#cb3837",  # npm red
                "size": "14px",
                "bg_color": "rgba(203, 56, 55, 0.15)"
            },
            "local": {
                "text": "🏠",  # House for local
                "color": "#00BFAE",
                "size": "14px",
                "bg_color": "rgba(0, 191, 174, 0.15)"
            }
        }
        
        source_key = self.source_name.lower()
        if source_key in icon_styles:
            style = icon_styles[source_key]
            self.icon_label.setText(style["text"])
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {style["size"]};
                    color: {style["color"]};
                    font-weight: bold;
                    background-color: {style["bg_color"]};
                    border-radius: 12px;
                    padding: 4px;
                    border: 1px solid {style["color"]};
                    text-align: center;
                }}
            """)
        else:
            self._set_fallback_icon()
        
        # Now that we know SVG works, let's try loading it properly
        if self._try_load_svg_properly(icon_path):
            return
    
    def _try_load_svg(self, icon_path):
        """Try to load and render the actual SVG file"""
        try:
            if not os.path.exists(icon_path):
                print(f"SVG file not found: {icon_path}")
                return False
                
            # Read SVG content and clean it up more thoroughly
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Remove problematic Inkscape elements that cause rendering issues
            import re
            
            # Remove Inkscape-specific namespaces and elements
            svg_content = re.sub(r'xmlns:inkscape="[^"]*"', '', svg_content)
            svg_content = re.sub(r'xmlns:sodipodi="[^"]*"', '', svg_content)
            svg_content = re.sub(r'<sodipodi:namedview[^>]*>.*?</sodipodi:namedview>', '', svg_content, flags=re.DOTALL)
            svg_content = re.sub(r'<defs[^>]*>\s*</defs>', '', svg_content)
            svg_content = re.sub(r'inkscape:[^=]*="[^"]*"', '', svg_content)
            svg_content = re.sub(r'sodipodi:[^=]*="[^"]*"', '', svg_content)
            
            # Create SVG renderer from cleaned content
            svg_renderer = QSvgRenderer()
            if not svg_renderer.load(svg_content.encode('utf-8')):
                print(f"Failed to load cleaned SVG: {self.source_name}")
                return False
                
            if svg_renderer.isValid():
                # Create pixmap with white background first to test
                size = 32
                pixmap = QPixmap(size, size)
                pixmap.fill(QColor(255, 255, 255, 0))  # Fully transparent

                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
                
                # Set composition mode to ensure proper alpha blending
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

                # Render SVG to pixmap with proper bounds
                svg_renderer.render(painter, QRectF(0, 0, size, size))
                painter.end()

                # Scale to final size
                final_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, 
                                           Qt.TransformationMode.SmoothTransformation)
                
                if not final_pixmap.isNull():
                    self.icon_label.setPixmap(final_pixmap)
                    # Set label background to transparent to avoid black box
                    self.icon_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            border: none;
                        }
                    """)
                    return True
                    
            return False
            
        except Exception as e:
            return False
    
    
    def _try_load_svg_properly(self, icon_path):
        """Load SVG with proper display handling"""
        try:
            if not os.path.exists(icon_path):
                return False
                
            # Simple, direct SVG loading
            svg_renderer = QSvgRenderer(icon_path)
            if not svg_renderer.isValid():
                return False
                
            # Create pixmap
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            svg_renderer.render(painter)
            painter.end()
            
            # Scale to final size
            final_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
            
            if not final_pixmap.isNull():
                # Clear any text content first
                self.icon_label.setText("")
                
                # Set the pixmap
                self.icon_label.setPixmap(final_pixmap)
                
                # Override any background styling that might cause black box
                self.icon_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
                
                return True
                
            return False
            
        except Exception as e:
            return False
    
    def _set_fallback_icon(self):
        """Set fallback emoji icon when SVG loading fails"""
        emoji_map = {
            "pacman": "📦",
            "aur": "🧡", 
            "flatpak": "📱",
            "npm": "💚",
            "node": "💚",
        }
        fallback_emoji = emoji_map.get(self.source_name.lower(), "📦")
        self.icon_label.setText(fallback_emoji)
        self.icon_label.setStyleSheet("font-size: 16px; color: white;")
    
    def _try_svg_fallback(self, icon_path):
        """Try to load SVG as a fallback if text icons don't work"""
        try:
            if not os.path.exists(icon_path):
                return
                
            # Create a simple colored rectangle as a test
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            # Set color based on source type
            color_map = {
                "pacman": QColor("#0073e1"),
                "aur": QColor("#ff9955"),
                "flatpak": QColor("#4A90E2"),
                "npm": QColor("#68A063")
            }
            
            color = color_map.get(self.source_name.lower(), QColor("#ffffff"))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw a simple shape based on source
            if self.source_name.lower() == "pacman":
                painter.drawEllipse(2, 2, 20, 20)
                painter.setBrush(QColor("#000000"))
                painter.drawPie(2, 2, 20, 20, 0, 90 * 16)  # Pac-man mouth
            elif self.source_name.lower() == "aur":
                # Draw triangle
                from PyQt6.QtGui import QPolygon
                from PyQt6.QtCore import QPoint
                triangle = QPolygon([QPoint(12, 2), QPoint(22, 20), QPoint(2, 20)])
                painter.drawPolygon(triangle)
            elif self.source_name.lower() == "npm":
                painter.drawRoundedRect(2, 2, 20, 20, 4, 4)
            else:
                painter.drawRoundedRect(2, 2, 20, 20, 2, 2)
            
            painter.end()
            
            # Only use this if it's not null and we want to override text
            # For now, keep the text icons as primary
            # self.icon_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"SVG fallback failed for {self.source_name}: {e}")
            pass

    def on_state_changed(self, state):
        """Handle checkbox state changes"""
        self.checked = state == Qt.CheckState.Checked
        self.update_visual_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()
            # Toggle only when clicking outside the checkbox to avoid double toggles
            if not self.checkbox.geometry().contains(pos):
                self.checkbox.toggle()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Avoid double toggle when the checkbox itself has focus
            if not self.checkbox.hasFocus():
                self.checkbox.toggle()
                return
        super().keyPressEvent(event)

    def get_accent_color(self, name):
        n = name.lower()
        mapping = {
            "pacman": "#4FC3F7",
            "aur": "#FF8A65",
            "flatpak": "#26A69A",
            "npm": "#E53935",
        }
        return mapping.get(n, "#00BFAE")

    def apply_accent_styles(self):
        r, g, b = self.accent_color.red(), self.accent_color.green(), self.accent_color.blue()
        self.checkbox.setStyleSheet(
            f"""
            QCheckBox#sourceCheckbox {{
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox#sourceCheckbox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid rgba({r}, {g}, {b}, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }}
            QCheckBox#sourceCheckbox::indicator:checked {{
                background-color: {self.accent_hex};
                border: 2px solid {self.accent_hex};
            }}
            QCheckBox#sourceCheckbox::indicator:hover {{
                border-color: rgba({r}, {g}, {b}, 0.8);
            }}
            """
        )

    def update_visual_state(self):
        """Update visual appearance based on checked state"""
        if self.checked:
            r, g, b = self.accent_color.red(), self.accent_color.green(), self.accent_color.blue()
            self.icon_container.setStyleSheet(
                f"""
                QWidget#sourceIconContainer {{
                    background-color: rgba({r}, {g}, {b}, 0.14);
                    border: 1px solid rgba({r}, {g}, {b}, 0.4);
                    border-radius: 12px;
                }}
                """
            )
        else:
            self.icon_container.setStyleSheet("""
                QWidget#sourceIconContainer {
                    background-color: rgba(42, 45, 51, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }
            """)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            SourceItem {
                background-color: transparent;
                border-radius: 12px;
                margin: 2px 0px;
            }

            SourceItem:hover {
                background-color: rgba(0, 191, 174, 0.05);
                border-radius: 12px;
            }

            QCheckBox#sourceCheckbox {
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }

            QCheckBox#sourceCheckbox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid rgba(0, 191, 174, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#sourceCheckbox::indicator:checked {
                background-color: #00BFAE;
                border: 2px solid #00BFAE;
            }

            QCheckBox#sourceCheckbox::indicator:unchecked {
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#sourceCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.8);
            }

            QWidget#sourceIconContainer {
                background-color: rgba(0, 191, 174, 0.1);
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 12px;
            }
        """

    def is_checked(self):
        """Return whether this source is checked"""
        return self.checked

    def set_checked(self, checked):
        """Set the checked state"""
        self.checked = checked
        self.checkbox.setChecked(checked)
        self.update_visual_state()

# === components: source_card.py ===
"""
SourceCard Component - Card-style container for source selection
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup, QGraphicsDropShadowEffect
from PyQt6.QtCore import pyqtSignal


class SourceCard(QWidget):
    """Card component for source selection with select/deselect functionality"""

    source_changed = pyqtSignal(dict)  # Emits dict of source_name -> is_checked
    search_mode_changed = pyqtSignal(str)  # Emits search mode: 'name', 'id', or 'both'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sources = {}
        self.search_mode = 'both'  # Default search mode
        self.radio_group = None
        self.init_ui()

    def init_ui(self):
        """Initialize the source card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header with select/deselect button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Sources")
        title_label.setObjectName("sourceCardTitle")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        header_layout.addWidget(self.select_all_btn)

        layout.addWidget(header_widget)

        # Container for source items
        self.sources_container = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_layout.setContentsMargins(6, 4, 6, 4)
        self.sources_layout.setSpacing(6)

        layout.addWidget(self.sources_container)

        # Search Mode Section
        search_mode_widget = QWidget()
        search_layout = QVBoxLayout(search_mode_widget)
        search_layout.setContentsMargins(12, 8, 12, 8)
        search_layout.setSpacing(6)

        search_title = QLabel("Search Mode")
        search_title.setObjectName("searchModeTitle")
        search_layout.addWidget(search_title)

        # Radio button container
        radio_container = QWidget()
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(12)

        # Create button group for radio buttons
        self.radio_group = QButtonGroup(self)

        # Name radio button
        self.name_radio = QRadioButton("Name")
        self.name_radio.setObjectName("searchModeRadio")
        self.radio_group.addButton(self.name_radio, 0)
        radio_layout.addWidget(self.name_radio)

        # Package ID radio button
        self.id_radio = QRadioButton("Package ID")
        self.id_radio.setObjectName("searchModeRadio")
        self.radio_group.addButton(self.id_radio, 1)
        radio_layout.addWidget(self.id_radio)

        # Both radio button (default)
        self.both_radio = QRadioButton("Both")
        self.both_radio.setObjectName("searchModeRadio")
        self.both_radio.setChecked(True)  # Default selection
        self.radio_group.addButton(self.both_radio, 2)
        radio_layout.addWidget(self.both_radio)

        radio_layout.addStretch()
        search_layout.addWidget(radio_container)

        layout.addWidget(search_mode_widget)

        # Connect radio button signals
        self.radio_group.buttonClicked.connect(self.on_search_mode_changed)

        # Subtle drop shadow for the entire card
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 2)
            from PyQt6.QtGui import QColor as _QColor
            shadow.setColor(_QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
        except ImportError:
            # Handle missing graphics effect support gracefully
            pass

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())

    def add_source(self, source_name, icon_path):
        """Add a source to the card"""
        source_item = SourceItem(source_name, icon_path, self)
        source_item.checkbox.stateChanged.connect(lambda: self.on_source_changed())
        self.sources[source_name] = source_item
        self.sources_layout.addWidget(source_item)

        # Initial state change emission
        self.on_source_changed()

    def on_source_changed(self):
        """Handle when any source selection changes"""
        states = {name: item.checkbox.isChecked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_select_all_button()

    def update_select_all_button(self):
        """Update the select all button text based on current state"""
        checked_count = sum(1 for item in self.sources.values() if item.checkbox.isChecked())
        total_count = len(self.sources)

        if checked_count == total_count:
            self.select_all_btn.setText("Deselect All")
        elif checked_count == 0:
            self.select_all_btn.setText("Select All")
        else:
            self.select_all_btn.setText(f"Selected ({checked_count}/{total_count})")

    def toggle_select_all(self):
        """Toggle select all/deselect all"""
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)

        # Block signals during bulk changes
        for item in self.sources.values():
            item.checkbox.blockSignals(True)
        
        if checked_count == total_count:
            # All selected, deselect all
            for item in self.sources.values():
                item.set_checked(False)
        else:
            # Not all selected, select all
            for item in self.sources.values():
                item.set_checked(True)
        
        # Unblock signals
        for item in self.sources.values():
            item.checkbox.blockSignals(False)
        
        # Emit signal once with final state
        states = {name: item.checkbox.isChecked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_select_all_button()

    def get_selected_sources(self):
        """Return dict of selected sources"""
        return {name: item.checkbox.isChecked() for name, item in self.sources.items()}

    def on_search_mode_changed(self, button):
        """Handle search mode radio button changes"""
        if button == self.name_radio:
            self.search_mode = 'name'
        elif button == self.id_radio:
            self.search_mode = 'id'
        elif button == self.both_radio:
            self.search_mode = 'both'

        self.search_mode_changed.emit(self.search_mode)

    def get_search_mode(self):
        """Return the current search mode"""
        return self.search_mode

    def set_search_mode(self, mode):
        """Set the search mode"""
        self.search_mode = mode
        if mode == 'name':
            self.name_radio.setChecked(True)
        elif mode == 'id':
            self.id_radio.setChecked(True)
        elif mode == 'both':
            self.both_radio.setChecked(True)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            SourceCard {
                background-color: #0f0f0f;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                margin: 4px 0px;
            }

            QLabel#sourceCardTitle {
                color: #00BFAE;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            QLabel#searchModeTitle {
                color: #00BFAE;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }

            QPushButton#selectAllBtn {
                background-color: transparent;
                color: #00BFAE;
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            QPushButton#selectAllBtn:hover {
                background-color: rgba(0, 191, 174, 0.1);
                border-color: rgba(0, 191, 174, 0.5);
            }

            QPushButton#selectAllBtn:pressed {
                background-color: rgba(0, 191, 174, 0.2);
            }

            QRadioButton#searchModeRadio {
                color: #F0F0F0;
                font-size: 12px;
                font-weight: 500;
                spacing: 8px;
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #0f0f0f;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }

            QRadioButton#searchModeRadio:hover {
                background-color: #121212;
                border-color: rgba(0, 191, 174, 0.4);
            }

            QRadioButton#searchModeRadio:checked {
                background-color: #121212;
                border-color: #00BFAE;
                color: #00BFAE;
                font-weight: 600;
            }

            QRadioButton#searchModeRadio::indicator {
                width: 0px;
                height: 0px;
                margin: 0px;
            }
        """

# === components: filter_card.py ===
"""
FilterCard Component - Card-style container for filter options
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import pyqtSignal


class FilterCard(QWidget):
    """Card component for filter options"""

    filter_changed = pyqtSignal(dict)  # Emits dict of filter_name -> is_checked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        """Initialize the filter card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Filters")
        title_label.setObjectName("filterCardTitle")
        header_layout.addWidget(title_label)

        layout.addWidget(header_widget)

        # Container for filter items
        self.filters_container = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_container)
        self.filters_layout.setContentsMargins(12, 0, 12, 8)
        self.filters_layout.setSpacing(6)

        layout.addWidget(self.filters_container)

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())

    def add_filter(self, filter_name, checked=True):
        """Add a filter to the card"""
        checkbox = QCheckBox(filter_name)
        checkbox.setChecked(checked)
        checkbox.setObjectName("filterCheckbox")
        checkbox.stateChanged.connect(lambda: self.on_filter_changed())

        self.filters[filter_name] = checkbox
        self.filters_layout.addWidget(checkbox)

        # Initial state change emission
        self.on_filter_changed()

    def on_filter_changed(self):
        """Handle when any filter selection changes"""
        states = {name: checkbox.isChecked() for name, checkbox in self.filters.items()}
        self.filter_changed.emit(states)

    def get_selected_filters(self):
        """Return dict of selected filters"""
        return {name: checkbox.isChecked() for name, checkbox in self.filters.items()}

    def set_selected_filters(self, selected_dict):
        """Set which filters are selected"""
        for name, checked in selected_dict.items():
            if name in self.filters:
                self.filters[name].setChecked(checked)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            FilterCard {
                background-color: rgba(42, 45, 51, 0.4);
                border-radius: 12px;
                border: 1px solid rgba(0, 191, 174, 0.2);
                margin: 4px 0px;
            }

            QLabel#filterCardTitle {
                color: #00BFAE;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            QCheckBox#filterCheckbox {
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
                padding: 4px 8px;
                border-radius: 6px;
            }

            QCheckBox#filterCheckbox:hover {
                background-color: rgba(0, 191, 174, 0.05);
                border-radius: 6px;
            }

            QCheckBox#filterCheckbox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid rgba(0, 191, 174, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#filterCheckbox::indicator:checked {
                background-color: #00BFAE;
                border: 2px solid #00BFAE;
            }

            QCheckBox#filterCheckbox::indicator:unchecked {
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#filterCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.8);
            }
        """

# === components: large_search_box.py ===
"""
LargeSearchBox Component - Large search box for package discovery
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QFrame, QGridLayout, QProgressBar, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor, QResizeEvent
from PyQt6.QtSvg import QSvgRenderer
import os
import psutil
import platform
import subprocess
import datetime
import re


class LargeSearchBox(QWidget):
    """Large search box component for discover page"""

    search_requested = pyqtSignal(str)  # Emits query for auto-search
    search_submitted = pyqtSignal(str)  # Emits query for explicit submit (enter/button)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_timer = QTimer()
        self.search_timer.setInterval(800)  # Faster response
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_auto_search)
        self.highlight_widgets: list = []
        self.compact_mode = False
        self.is_maximized_layout = False
        self.current_width = 0
        self.main_layout: Any = None
        self.hero_card: Any = None
        self.expanded_sections: Any = None
        self.cpu_value_label: Any = None
        self.memory_progress: Any = None
        self.memory_percentage_label: Any = None
        self.cpu_progress: Any = None
        self.disk_progress: Any = None
        self.disk_percentage_label: Any = None
        self.system_update_timer = QTimer()
        self.progress_animations: list = []
        self.recent_updates_container: Any = None
        self.recent_updates_layout: Any = None
        self.recent_updates: list = []
        self.system_data_cache: dict = {}
        self.cache_timestamp = 0
        self.cache_duration = 30  # Cache for 30 seconds
        self.layout_switching = False
        self.updates_timer: Any = None
        self.system_update_timer.setInterval(2000)  # Update every 2 seconds
        self.system_update_timer.timeout.connect(self.update_system_health)
        self.init_ui()

    def init_ui(self):
        """Initialize the large search box UI with responsive design"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 30, 20, 30)
        self.main_layout.setSpacing(20)
        
        # Create main hero card
        self.create_hero_card()
        
        # Create expanded sections (initially hidden)
        self.create_expanded_sections()
        
        # Set initial layout - force compact mode initially
        self.current_width = 800  # Start with a typical window width
        self.is_maximized_layout = False
        self.rebuild_layout()
        self.setStyleSheet(self.get_stylesheet())

    def create_hero_card(self):
        """Create the main search card"""
        self.hero_card = QFrame()
        self.hero_card.setObjectName("largeSearchCard")
        self.hero_card_layout = QVBoxLayout(self.hero_card)
        
        # Initial layout - will be updated in update_hero_card_layout
        self.hero_card_layout.setContentsMargins(36, 40, 36, 40)
        self.hero_card_layout.setSpacing(24)

        # Title and subtitle
        self.title_label = QLabel("Discover New Packages")
        self.title_label.setObjectName("heroTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_card_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Search across pacman, AUR, Flatpak, and npm repositories")
        self.subtitle_label.setObjectName("heroSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_card_layout.addWidget(self.subtitle_label)

        # Search container
        self.create_search_container(self.hero_card_layout)
        
        # Highlights container
        self.create_highlights_container(self.hero_card_layout)

    def update_hero_card_layout(self):
        """Update hero card layout based on current mode"""
        if self.is_maximized_layout:
            # Much tighter spacing for maximized layout to fit 4 cards
            self.hero_card_layout.setContentsMargins(28, 24, 28, 24)
            self.hero_card_layout.setSpacing(14)
        else:
            # Normal spacing for compact layout
            self.hero_card_layout.setContentsMargins(36, 40, 36, 40)
            self.hero_card_layout.setSpacing(24)

    def create_search_container(self, parent_layout):
        """Create the search input container"""
        search_container = QWidget()
        search_container.setObjectName("largeSearchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(24, 18, 24, 18)
        search_layout.setSpacing(16)

        self.search_icon = QLabel()
        self.search_icon.setFixedSize(40, 40)
        self.search_icon.setObjectName("searchIconBubble")
        self.set_search_icon()
        search_layout.addWidget(self.search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Try \"system monitor\" or \"AUR helpers\"")
        self.search_input.setObjectName("largeSearchInput")
        self.search_input.setFixedHeight(48)
        self.search_input.returnPressed.connect(self.on_search_triggered)
        self.search_input.textChanged.connect(self.on_text_changed)
        search_layout.addWidget(self.search_input, 1)

        self.search_button = QPushButton("Search")
        self.search_button.setMinimumWidth(110)
        self.search_button.setFixedHeight(48)
        self.search_button.setObjectName("largeSearchButton")
        self.search_button.clicked.connect(self.on_search_triggered)
        self.set_button_icon()
        search_layout.addWidget(self.search_button)

        parent_layout.addWidget(search_container)

    def create_highlights_container(self, parent_layout):
        """Create highlights/feature cards container"""
        self.highlights_container = QWidget()
        self.highlights_container.setObjectName("highlightsContainer")
        
        # This will be dynamically set based on layout mode
        self.highlights_layout = QHBoxLayout(self.highlights_container)
        self.highlights_layout.setContentsMargins(0, 0, 0, 0)
        self.highlights_layout.setSpacing(18)

        parent_layout.addWidget(self.highlights_container)
        self.create_highlight_cards()

    def create_highlight_cards(self):
        """Create feature highlight cards"""
        # Clear existing widgets
        for widget in self.highlight_widgets:
            widget["card"].setParent(None)
        self.highlight_widgets.clear()

        # Define highlights based on layout mode
        if self.is_maximized_layout:
            highlights = [
                ("🚀", "Blazing Fast search", "Instant multi-repo search"),
                ("⭕", "Curated Collections", "Handpicked package sets"),
                ("⭐", "Curated results", "Trusted package picks"),
                ("⚙️", "Advanced User Tools", "Power user controls")
            ]
            # Adjust spacing for 4 cards
            self.highlights_layout.setSpacing(8)
        else:
            highlights = [
                ("🚀", "Instant multi repo search", "Instant unified search"),
                ("⭐", "Curated results", "Trusted package picks"),
                ("⚙️", "Power user ready", "Advanced user control")
            ]
            # Normal spacing for 3 cards
            self.highlights_layout.setSpacing(18)

        for highlight_data in highlights:
            emoji, title, description = highlight_data
            highlight_card = QFrame()
            highlight_card.setObjectName("highlightCard")
            
            # Set card height constraints based on layout mode
            if self.is_maximized_layout:
                highlight_card.setMinimumHeight(80)
                highlight_card.setMaximumHeight(100)
            else:
                highlight_card.setMinimumHeight(120)
                highlight_card.setMaximumHeight(150)
            
            # Adjust card margins for maximized layout
            if self.is_maximized_layout:
                card_layout_inner = QVBoxLayout(highlight_card)
                card_layout_inner.setContentsMargins(12, 10, 12, 10)
                card_layout_inner.setSpacing(3)
            else:
                card_layout_inner = QVBoxLayout(highlight_card)
                card_layout_inner.setContentsMargins(20, 20, 20, 20)
                card_layout_inner.setSpacing(8)

            icon_label = QLabel(emoji)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            icon_label.setObjectName("highlightIcon")
            
            # Set font sizes based on layout mode
            if self.is_maximized_layout:
                # Smaller fonts for 4-card layout
                icon_font = icon_label.font()
                icon_font.setPointSize(18)
                icon_label.setFont(icon_font)
            else:
                # Larger fonts for 3-card layout
                icon_font = icon_label.font()
                icon_font.setPointSize(24)
                icon_label.setFont(icon_font)
            
            card_layout_inner.addWidget(icon_label)

            title_label = QLabel(title)
            title_label.setObjectName("highlightTitle")
            title_label.setWordWrap(True)
            
            # Set title font size based on layout mode
            if self.is_maximized_layout:
                title_font = title_label.font()
                title_font.setPointSize(11)
                title_font.setBold(True)
                title_label.setFont(title_font)
            else:
                title_font = title_label.font()
                title_font.setPointSize(15)
                title_font.setBold(True)
                title_label.setFont(title_font)
            
            card_layout_inner.addWidget(title_label)

            description_label = QLabel(description)
            description_label.setObjectName("highlightDescription")
            description_label.setWordWrap(True)
            
            # Set description font size based on layout mode
            if self.is_maximized_layout:
                desc_font = description_label.font()
                desc_font.setPointSize(8)
                description_label.setFont(desc_font)
            else:
                desc_font = description_label.font()
                desc_font.setPointSize(11)
                description_label.setFont(desc_font)
            
            card_layout_inner.addWidget(description_label)

            # Add stretch to push content to top
            card_layout_inner.addStretch()

            self.highlight_widgets.append({
                "card": highlight_card,
                "icon": icon_label,
                "title": title_label,
                "desc": description_label,
            })

            self.highlights_layout.addWidget(highlight_card, 1)

    def create_expanded_sections(self):
        """Create additional sections for maximized layout"""
        self.expanded_sections = QWidget()
        self.expanded_sections.setObjectName("expandedSections")
        expanded_layout = QHBoxLayout(self.expanded_sections)
        expanded_layout.setContentsMargins(0, 20, 0, 0)
        expanded_layout.setSpacing(20)

        # Recent Updates section
        recent_updates = self.create_recent_updates_section()
        expanded_layout.addWidget(recent_updates, 1)

        # System Health section
        system_health = self.create_system_health_section()
        expanded_layout.addWidget(system_health, 1)

        self.expanded_sections.hide()  # Initially hidden
        
        # Initialize system health data
        self.update_system_health()
        
        # Set up timer to refresh updates periodically
        self.updates_timer = QTimer()
        self.updates_timer.setInterval(300000)  # Refresh every 5 minutes
        self.updates_timer.timeout.connect(self.refresh_updates)
        
    def refresh_updates(self):
        """Refresh the recent updates display"""
        if self.is_maximized_layout and self.recent_updates_container:
            self.load_recent_updates()

    def create_recent_updates_section(self):
        """Create enhanced Recent Updates section with real package data"""
        section = QFrame()
        section.setObjectName("recentUpdatesSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header with title and refresh button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = QLabel("Recent Updates")
        title.setObjectName("recentUpdatesTitle")
        header_layout.addWidget(title)

        # Last updated indicator
        last_updated = QLabel("Live")
        last_updated.setObjectName("lastUpdatedLabel")
        header_layout.addWidget(last_updated)
        
        header_layout.addStretch()
        layout.addWidget(header_container)

        # Updates container (will be populated dynamically)
        self.recent_updates_container = QWidget()
        self.recent_updates_layout = QVBoxLayout(self.recent_updates_container)
        self.recent_updates_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_updates_layout.setSpacing(12)
        
        layout.addWidget(self.recent_updates_container)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        section.setGraphicsEffect(shadow)

        # Load initial updates
        self.load_recent_updates()

        return section

    @staticmethod
    def get_package_icon(package_name):
        """Get appropriate icon for package type"""
        package_name = package_name.lower()
        
        # System packages
        if any(sys_pkg in package_name for sys_pkg in ['kernel', 'systemd', 'glibc', 'gcc']):
            return "⚙️"  # Gear for system packages
        # Development tools
        elif any(dev_pkg in package_name for dev_pkg in ['python', 'nodejs', 'git', 'vim', 'code', 'gcc', 'make']):
            return "🛠️"  # Hammer and wrench for dev tools
        # Media packages
        elif any(media_pkg in package_name for media_pkg in ['ffmpeg', 'vlc', 'gimp', 'blender']):
            return "🎨"  # Artist palette for media
        # Network/web packages
        elif any(net_pkg in package_name for net_pkg in ['firefox', 'chrome', 'wget', 'curl', 'nginx']):
            return "🌐"  # Globe for network
        # Gaming
        elif any(game_pkg in package_name for game_pkg in ['steam', 'wine', 'lutris']):
            return "🎮"  # Game controller
        # Security
        elif any(sec_pkg in package_name for sec_pkg in ['gpg', 'ssh', 'openssl']):
            return "🔒"  # Lock for security
        else:
            return "📦"  # Package for general packages

    @staticmethod
    def format_time_ago(timestamp):
        """Format timestamp to human-readable time ago"""
        try:
            now = datetime.datetime.now()
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
        except Exception:
            return "Unknown"

    def load_recent_updates(self):
        """Load recent package updates from system logs"""
        layout = self.recent_updates_layout
        if layout is None:
            return
        try:
            # Clear existing updates
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Get recent pacman updates from log
            updates = self.get_pacman_updates()
            
            if not updates:
                # Show system status instead of empty message
                self.show_system_status()
                return
            
            # Display up to 4 most recent updates
            for update in updates[:4]:
                self.create_update_item(update)
                
        except Exception:
            self.show_system_status()  # Show system status instead of error

    @staticmethod
    def get_pacman_updates():
        """Get recent pacman updates from system log"""
        updates = []
        try:
            # Try to read pacman log
            result = subprocess.run(
                ['/usr/bin/tail', '-n', '50', '/var/log/pacman.log'],
                capture_output=True, text=True, timeout=5, check=False
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '[ALPM] upgraded' in line or '[ALPM] installed' in line:
                        match = re.search(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*\] \[ALPM\] (upgraded|installed) ([^\s]+) \(([^)]+)\)', line)
                        if match:
                            timestamp_str, action, package, version = match.groups()
                            timestamp = datetime.datetime.fromisoformat(timestamp_str)
                            updates.append({
                                'package': package,
                                'version': version,
                                'action': action,
                                'timestamp': timestamp
                            })
            
            # Sort by timestamp (newest first)
            updates.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception:
            # Return empty list to show system status instead
            updates = []
        
        return updates

    def create_update_item(self, update_data):
        """Create a modern update item widget"""
        item = QFrame()
        item.setObjectName("modernUpdateItem")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(16, 12, 16, 12)
        item_layout.setSpacing(14)

        # Package icon with background
        icon_container = QFrame()
        icon_container.setObjectName("updateIconContainer")
        icon_container.setFixedSize(40, 40)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(self.get_package_icon(update_data['package']))
        icon_label.setObjectName("updatePackageIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        item_layout.addWidget(icon_container)

        # Package info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Package name and action
        name_action = QLabel(f"{update_data['package']} {update_data['action']}")
        name_action.setObjectName("updatePackageName")
        info_layout.addWidget(name_action)

        # Version info
        version_label = QLabel(f"Version {update_data['version']}")
        version_label.setObjectName("updateVersion")
        info_layout.addWidget(version_label)

        item_layout.addWidget(info_container, 1)

        # Time ago
        time_label = QLabel(self.format_time_ago(update_data['timestamp']))
        time_label.setObjectName("updateTime")
        item_layout.addWidget(time_label)

        if self.recent_updates_layout is not None:
            self.recent_updates_layout.addWidget(item)

    def show_system_status(self):
        """Show useful system information when no updates are available"""
        try:
            # Load basic info first (fast)
            uptime_info = self.get_system_uptime()
            self.create_status_item("⏱️", "System Uptime", uptime_info, "System running smoothly")
            
            boot_time = self.get_last_boot_time()
            self.create_status_item("🚀", "Last Boot", boot_time, "System startup")
            
            # Load heavier operations asynchronously
            QTimer.singleShot(100, self.load_package_info)
            QTimer.singleShot(300, self.load_update_info)
            
        except Exception:
            # Fallback to basic system info
            self.create_status_item("💻", "System Status", "Running", "All systems operational")
            self.create_status_item("📊", "Package Manager", "Ready", "Pacman available")
    
    def load_package_info(self):
        """Load package information asynchronously"""
        try:
            pkg_count = self.get_package_count()
            self.create_status_item("📦", "Installed Packages", f"{pkg_count} packages", "System packages")
        except Exception:
            self.create_status_item("📦", "Installed Packages", "Unknown", "System packages")
    
    def load_update_info(self):
        """Load update information asynchronously"""
        try:
            available_updates = self.check_available_updates()
            self.create_status_item("🔄", "Available Updates", available_updates, "Package manager")
        except Exception:
            self.create_status_item("🔄", "Available Updates", "Check manually", "Package manager")

    def get_cached_system_data(self, key, fetch_func):
        """Get cached system data or fetch if expired"""
        current_time = datetime.datetime.now().timestamp()
        
        # Check if cache is valid
        if (key in self.system_data_cache and 
            current_time - self.cache_timestamp < self.cache_duration):
            return self.system_data_cache[key]
        
        # Fetch new data
        try:
            data = fetch_func()
            self.system_data_cache[key] = data
            self.cache_timestamp = current_time
            return data
        except Exception:
            # Return cached data if available, otherwise default
            return self.system_data_cache.get(key, "Unknown")
    
    def get_system_uptime(self):
        """Get system uptime information with caching"""
        def fetch_uptime():
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.datetime.now().timestamp() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {int((uptime_seconds % 3600) // 60)}m"
            else:
                return f"{int(uptime_seconds // 60)}m"
        
        return self.get_cached_system_data('uptime', fetch_uptime)

    def get_package_count(self):
        """Get installed package count with caching"""
        def fetch_package_count():
            result = subprocess.run(
                ['/usr/bin/pacman', '-Q'], 
                capture_output=True, text=True, timeout=3, check=False
            )
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n'))
            return "Unknown"
        
        return self.get_cached_system_data('package_count', fetch_package_count)

    def get_last_boot_time(self):
        """Get last boot time with caching"""
        def fetch_boot_time():
            boot_time = psutil.boot_time()
            boot_datetime = datetime.datetime.fromtimestamp(boot_time)
            now = datetime.datetime.now()
            diff = now - boot_datetime
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            else:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
        
        return self.get_cached_system_data('boot_time', fetch_boot_time)

    def check_available_updates(self):
        """Check for available updates with caching and timeout optimization"""
        def fetch_updates():
            # Use faster timeout for better responsiveness
            result = subprocess.run(
                ['/usr/bin/checkupdates'], 
                capture_output=True, text=True, timeout=5, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                count = len(result.stdout.strip().split('\n'))
                return f"{count} available"
            else:
                return "Up to date"
        
        return self.get_cached_system_data('available_updates', fetch_updates)

    def create_status_item(self, icon, title, value, description):
        """Create a system status item"""
        item = QFrame()
        item.setObjectName("modernUpdateItem")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(16, 12, 16, 12)
        item_layout.setSpacing(14)

        # Icon with background
        icon_container = QFrame()
        icon_container.setObjectName("updateIconContainer")
        icon_container.setFixedSize(40, 40)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("updatePackageIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        item_layout.addWidget(icon_container)

        # Info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("updatePackageName")
        info_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("updateVersion")
        info_layout.addWidget(desc_label)

        item_layout.addWidget(info_container, 1)

        # Value
        value_label = QLabel(value)
        value_label.setObjectName("updateTime")
        item_layout.addWidget(value_label)

        self.recent_updates_layout.addWidget(item)

    def create_system_health_section(self):
        """Create enhanced System Health section with modern design"""
        section = QFrame()
        section.setObjectName("systemHealthSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header with title and status indicator
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = QLabel("System Health")
        title.setObjectName("systemHealthTitle")
        header_layout.addWidget(title)

        # Status indicator
        status_indicator = QLabel("●")
        status_indicator.setObjectName("systemHealthStatus")
        header_layout.addWidget(status_indicator)
        
        header_layout.addStretch()
        layout.addWidget(header_container)

        # Metrics grid container
        metrics_container = QWidget()
        metrics_layout = QVBoxLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(16)

        # CPU Usage Card
        cpu_card = self.create_metric_card("🖥️", "CPU Usage", "cpu")
        metrics_layout.addWidget(cpu_card)

        # Memory Usage Card
        memory_card = self.create_metric_card("💾", "Memory Usage", "memory")
        metrics_layout.addWidget(memory_card)

        # Disk Usage Card
        disk_card = self.create_metric_card("💿", "Disk Usage", "disk")
        metrics_layout.addWidget(disk_card)

        layout.addWidget(metrics_container)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        section.setGraphicsEffect(shadow)

        return section

    def create_metric_card(self, icon, label_text, metric_type):
        """Create a modern metric card with progress visualization"""
        card = QFrame()
        card.setObjectName("metricCard")
        card.setFixedHeight(70)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header row with icon, label, and value
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Icon with background
        icon_container = QFrame()
        icon_container.setObjectName("metricIconContainer")
        icon_container.setFixedSize(36, 36)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("metricIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        header_layout.addWidget(icon_container)

        # Label
        label = QLabel(label_text)
        label.setObjectName("metricLabel")
        header_layout.addWidget(label, 1)

        # Value label
        value_label = QLabel("Loading...")
        value_label.setObjectName("metricValue")
        header_layout.addWidget(value_label)

        layout.addLayout(header_layout)

        # Progress bar
        progress = QProgressBar()
        progress.setObjectName(f"{metric_type}Progress")
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        layout.addWidget(progress)

        # Store references for updates
        if metric_type == "cpu":
            self.cpu_value_label = value_label
            self.cpu_progress = progress
        elif metric_type == "memory":
            self.memory_percentage_label = value_label
            self.memory_progress = progress
        elif metric_type == "disk":
            self.disk_percentage_label = value_label
            self.disk_progress = progress

        return card

    def animate_progress_bar(self, progress_bar, target_value):
        """Animate progress bar to target value with smooth transition"""
        if not progress_bar:
            return
            
        animation = QPropertyAnimation(progress_bar, b"value")
        animation.setDuration(800)  # 800ms animation
        animation.setStartValue(progress_bar.value())
        animation.setEndValue(int(target_value))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Store animation reference to prevent garbage collection
        self.progress_animations.append(animation)
        animation.finished.connect(lambda: self.progress_animations.remove(animation))
        
        animation.start()

    def update_system_health(self):
        """Update system health metrics with real data"""
        try:
            # Get CPU usage (average over 1 second)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if self.cpu_value_label:
                self.cpu_value_label.setText(f"{cpu_percent:.1f}%")
            if self.cpu_progress:
                self.animate_progress_bar(self.cpu_progress, cpu_percent)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            if self.memory_progress:
                self.animate_progress_bar(self.memory_progress, memory_percent)
            if self.memory_percentage_label:
                self.memory_percentage_label.setText(f"{memory_percent:.1f}%")
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if self.disk_progress:
                self.animate_progress_bar(self.disk_progress, disk_percent)
            if self.disk_percentage_label:
                self.disk_percentage_label.setText(f"{disk_percent:.1f}%")
                
        except Exception:
            # Fallback to static data if psutil fails
            if self.cpu_value_label:
                self.cpu_value_label.setText("N/A")
            if self.cpu_progress:
                self.animate_progress_bar(self.cpu_progress, 0)
            if self.memory_percentage_label:
                self.memory_percentage_label.setText("N/A")
            if self.memory_progress:
                self.animate_progress_bar(self.memory_progress, 0)
            if self.disk_percentage_label:
                self.disk_percentage_label.setText("N/A")
            if self.disk_progress:
                self.animate_progress_bar(self.disk_progress, 0)

    def showEvent(self, event):
        """Handle widget show events"""
        super().showEvent(event)
        # Ensure layout is properly set when widget becomes visible
        if self.width() > 0:
            self.current_width = self.width()
            self.update_layout_for_size()

    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events"""
        super().resizeEvent(event)
        new_width = event.size().width()
        
        # Only update if width changed significantly (avoid excessive updates)
        if abs(new_width - self.current_width) > 50:
            self.current_width = new_width
            self.update_layout_for_size()

    def update_layout_for_size(self):
        """Update layout based on current window size with performance optimization"""
        if self.layout_switching:
            return  # Prevent recursive calls during layout switching
            
        # Get actual widget width if available, fallback to current_width
        actual_width = max(self.width(), self.current_width)
        
        # Determine if we should use maximized layout (wider than 1200px)
        should_be_maximized = actual_width > 1200
        
        if should_be_maximized != self.is_maximized_layout:
            self.layout_switching = True
            self.is_maximized_layout = should_be_maximized
            
            # Use QTimer.singleShot to defer heavy operations
            if should_be_maximized:
                self.rebuild_layout()
                # Defer data loading to avoid blocking UI
                QTimer.singleShot(100, self.load_maximized_data)
            else:
                self.rebuild_layout()
                self.system_update_timer.stop()
                if self.updates_timer is not None:
                    self.updates_timer.stop()
            
            self.layout_switching = False
        
        # Update margins based on width
        if actual_width > 1400:
            margins = (60, 40, 60, 40)
        elif actual_width > 1000:
            margins = (40, 30, 40, 30)
        else:
            margins = (20, 30, 20, 30)
        
        if self.main_layout is not None:
            self.main_layout.setContentsMargins(*margins)
    
    def load_maximized_data(self):
        """Load data for maximized layout with performance optimization"""
        if self.is_maximized_layout:
            # Start timers first for immediate feedback
            self.system_update_timer.start()
            if self.updates_timer is not None:
                self.updates_timer.start()
            
            # Load system health data (lightweight)
            QTimer.singleShot(50, self.update_system_health)
            
            # Load recent updates data (heavier operation)
            if self.recent_updates_container:
                QTimer.singleShot(200, self.load_recent_updates)

    def rebuild_layout(self):
        """Rebuild the layout when switching between modes"""
        main = self.main_layout
        hero = self.hero_card
        expanded = self.expanded_sections
        if main is None or hero is None or expanded is None:
            return
        # Clear current layout
        while main.count():
            child = main.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        if self.is_maximized_layout:
            # Maximized layout: hero card + expanded sections
            main.addWidget(hero)
            main.addWidget(expanded)
            expanded.show()
        else:
            # Compact layout: centered hero card
            main.addStretch()
            main.addWidget(hero, alignment=Qt.AlignmentFlag.AlignCenter)
            main.addStretch()
            expanded.hide()
        
        # Update hero card layout for new mode
        self.update_hero_card_layout()
        
        # Recreate highlight cards for new layout
        self.create_highlight_cards()

    def set_search_icon(self):
        """Set the search icon in the input area"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "search.svg")
            if os.path.exists(icon_path):
                svg_renderer = QSvgRenderer(icon_path)
                if svg_renderer.isValid():
                    pixmap = QPixmap(32, 32)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    with QPainter(pixmap) as painter:
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        svg_renderer.render(painter, QRectF(pixmap.rect()))
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter.fillRect(pixmap.rect(), QColor("#666666"))
                    self.search_icon.setPixmap(pixmap)
                else:
                    self.search_icon.setText("🔍")
            else:
                self.search_icon.setText("🔍")
        except Exception:
            self.search_icon.setText("🔍")

    def set_button_icon(self):
        """Set the search button icon"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "search.svg")
            if os.path.exists(icon_path):
                svg_renderer = QSvgRenderer(icon_path)
                if svg_renderer.isValid():
                    pixmap = QPixmap(24, 24)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    with QPainter(pixmap) as painter:
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        svg_renderer.render(painter, QRectF(pixmap.rect()))
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter.fillRect(pixmap.rect(), QColor("white"))
                    self.search_button.setIcon(QIcon(pixmap))
                    self.search_button.setIconSize(QSize(24, 24))
                else:
                    self.search_button.setText("🔍")
            else:
                self.search_button.setText("🔍")
        except Exception:
            self.search_button.setText("🔍")

    def on_text_changed(self):
        """Start auto-search timer when text changes"""
        self.search_timer.start()

    def on_auto_search(self):
        """Perform auto-search when timer times out"""
        query = self.search_input.text().strip()
        if len(query) >= 3:  # Only search if 3+ characters
            self.search_requested.emit(query)

    def on_search_triggered(self):
        """Handle search trigger (enter or button click)"""
        query = self.search_input.text().strip()
        if query:
            self.search_timer.stop()  # Stop any pending auto-search
            self.search_submitted.emit(query)

    def set_compact_mode(self, compact: bool):
        self.compact_mode = compact
        for w in self.highlight_widgets:
            try:
                w["icon"].setVisible(not compact)
                w["desc"].setVisible(not compact)
                w["title"].setVisible(True)
            except Exception:
                pass

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            LargeSearchBox {
                background-color: transparent;
            }

            QFrame#largeSearchCard {
                background-color: rgba(32, 34, 40, 0.95);
                border-radius: 28px;
                border: 1px solid rgba(0, 191, 174, 0.18);
            }

            QLabel#heroTitle {
                color: #F6F7FB;
                font-size: 28px;
                font-weight: 600;
                letter-spacing: 0.6px;
            }

            QLabel#heroSubtitle {
                color: #AEB4C2;
                font-size: 16px;
            }

            QWidget#largeSearchContainer {
                background-color: rgba(20, 22, 28, 0.9);
                border-radius: 28px;
                border: 1px solid rgba(0, 191, 174, 0.35);
            }

            QWidget#largeSearchContainer:hover {
                border-color: rgba(0, 230, 214, 0.65);
                background-color: rgba(22, 26, 34, 0.95);
            }

            QLabel#searchIconBubble {
                background-color: rgba(0, 191, 174, 0.12);
                border-radius: 20px;
                padding: 4px;
            }

            QLineEdit#largeSearchInput {
                background-color: transparent;
                border: none;
                color: #F0F3F5;
                font-size: 18px;
                font-weight: 400;
                padding: 8px 0px;
                selection-background-color: rgba(0, 191, 174, 0.3);
            }

            QLineEdit#largeSearchInput::placeholder {
                color: #8C94A4;
                font-size: 17px;
            }

            QLineEdit#largeSearchInput:focus {
                outline: none;
            }

            QPushButton#largeSearchButton {
                background-color: #00BFAE;
                border: none;
                border-radius: 24px;
                padding: 0 24px;
                color: #081017;
                font-size: 17px;
                font-weight: 600;
            }

            QPushButton#largeSearchButton:hover {
                background-color: #00D4C1;
            }

            QPushButton#largeSearchButton:pressed {
                background-color: #009688;
            }

            QWidget#highlightsContainer {
                background-color: transparent;
            }

            QFrame#highlightCard {
                background-color: rgba(18, 21, 27, 0.9);
                border-radius: 18px;
                border: 1px solid rgba(0, 191, 174, 0.14);
                min-height: 100px;
            }

            QFrame#highlightCard:hover {
                background-color: rgba(22, 26, 34, 0.95);
                border-color: rgba(0, 191, 174, 0.25);
            }

            QLabel#highlightIcon {
                font-size: 24px;
            }

            QLabel#highlightTitle {
                color: #EAF6F5;
                font-size: 15px;
                font-weight: 600;
                line-height: 1.2em;
            }

            QLabel#highlightDescription {
                color: #9CA6B4;
                font-size: 11px;
                line-height: 1.4em;
            }

            /* Expanded Sections Styles */
            QWidget#expandedSections {
                background-color: transparent;
            }

            QFrame#expandedSection {
                background-color: rgba(28, 30, 36, 0.95);
                border-radius: 20px;
                border: 1px solid rgba(0, 191, 174, 0.12);
            }

            QLabel#sectionTitle {
                color: #F6F7FB;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 8px;
            }

            /* Enhanced Recent Updates Styles */
            QFrame#recentUpdatesSection {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(32, 34, 40, 0.98),
                    stop:0.5 rgba(28, 30, 36, 0.95),
                    stop:1 rgba(24, 26, 32, 0.92));
                border-radius: 24px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            QLabel#recentUpdatesTitle {
                color: #F6F7FB;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            QLabel#lastUpdatedLabel {
                color: #00E6D6;
                font-size: 11px;
                font-weight: 600;
                background-color: rgba(0, 230, 214, 0.12);
                padding: 3px 8px;
                border-radius: 10px;
                border: 1px solid rgba(0, 230, 214, 0.2);
            }

            QFrame#modernUpdateItem {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 28, 0.9),
                    stop:1 rgba(16, 18, 24, 0.85));
                border-radius: 16px;
                border: 1px solid rgba(0, 191, 174, 0.08);
            }

            QFrame#modernUpdateItem:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 26, 32, 0.95),
                    stop:1 rgba(20, 22, 28, 0.9));
                border-color: rgba(0, 191, 174, 0.18);
            }

            QFrame#updateIconContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 150, 255, 0.15),
                    stop:1 rgba(0, 191, 174, 0.12));
                border-radius: 20px;
                border: 1px solid rgba(100, 150, 255, 0.2);
            }

            QLabel#updatePackageIcon {
                color: #6496FF;
                font-size: 18px;
                font-weight: 600;
            }

            QLabel#updatePackageName {
                color: #E8F4F3;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }

            QLabel#updateVersion {
                color: #9CA6B4;
                font-size: 12px;
                font-weight: 400;
            }

            QLabel#updateTime {
                color: #00BFAE;
                font-size: 12px;
                font-weight: 700;
                background-color: rgba(0, 191, 174, 0.08);
                padding: 4px 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 191, 174, 0.15);
                min-width: 50px;
            }

            QLabel#noUpdatesMessage {
                color: #9CA6B4;
                font-size: 14px;
                font-style: italic;
                padding: 20px;
            }

            QLabel#errorMessage {
                color: #FF6B6B;
                font-size: 12px;
                padding: 20px;
            }

            /* Enhanced System Health Styles */
            QFrame#systemHealthSection {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(32, 34, 40, 0.98),
                    stop:0.5 rgba(28, 30, 36, 0.95),
                    stop:1 rgba(24, 26, 32, 0.92));
                border-radius: 24px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            QLabel#systemHealthTitle {
                color: #F6F7FB;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            QLabel#systemHealthStatus {
                color: #00E6D6;
                font-size: 12px;
                margin-left: 8px;
            }

            QFrame#metricCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 28, 0.9),
                    stop:1 rgba(16, 18, 24, 0.85));
                border-radius: 16px;
                border: 1px solid rgba(0, 191, 174, 0.08);
            }

            QFrame#metricCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 26, 32, 0.95),
                    stop:1 rgba(20, 22, 28, 0.9));
                border-color: rgba(0, 191, 174, 0.18);
            }

            QFrame#metricIconContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 191, 174, 0.15),
                    stop:1 rgba(0, 230, 214, 0.12));
                border-radius: 18px;
                border: 1px solid rgba(0, 191, 174, 0.2);
            }

            QLabel#metricIcon {
                color: #00E6D6;
                font-size: 18px;
                font-weight: 600;
            }

            QLabel#metricLabel {
                color: #E8F4F3;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }

            QLabel#metricValue {
                color: #00BFAE;
                font-size: 14px;
                font-weight: 700;
                background-color: rgba(0, 191, 174, 0.08);
                padding: 4px 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            /* CPU Progress Bar */
            QProgressBar#cpuProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#cpuProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B6B, stop:0.3 #FF8E53, stop:0.7 #FF6B35, stop:1 #E74C3C);
                border-radius: 3px;
            }

            /* Memory Progress Bar */
            QProgressBar#memoryProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#memoryProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFAE, stop:0.3 #00D4C1, stop:0.7 #00E6D6, stop:1 #4ECDC4);
                border-radius: 3px;
            }

            /* Disk Progress Bar */
            QProgressBar#diskProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#diskProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:0.3 #8E44AD, stop:0.7 #A569BD, stop:1 #BB8FCE);
                border-radius: 3px;
            }
        """

# === components: loading_spinner.py ===
"""
LoadingSpinner Component - Reusable loading spinner widget
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QPen


class LoadingSpinner(QWidget):
    """Reusable loading spinner component"""

    def __init__(self, parent=None, message="Loading..."):
        super().__init__(parent)
        self.message = message
        self.spinner_angle = 0
        self.init_ui()

    def init_ui(self):
        """Initialize the loading spinner UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spinner label - will be replaced with custom drawing
        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(48, 48)
        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Set up timer for animation
        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.animate_spinner)

        # Loading text
        self.loading_label = QLabel(self.message)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)

        # Apply styling
        self.setStyleSheet("""
            LoadingSpinner {
                background-color: transparent;
                border: none;
            }

            LoadingSpinner QLabel {
                background-color: transparent;
                color: #00BFAE;
                font-size: 14px;
                font-weight: 500;
            }
        """)

    def animate_spinner(self):
        """Animate the spinner with a beautiful colorful cycling effect"""
        self.spinner_angle = (self.spinner_angle + 15) % 360
        
        pixmap = QPixmap(48, 48)
        if pixmap.isNull():
            return
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        if not painter.isActive():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Define rainbow colors for the segments
        rainbow_colors = [
            QColor("#FF6B6B"),  # Red
            QColor("#FFD93D"),  # Yellow
            QColor("#6BCF7F"),  # Green
            QColor("#4ECDC4"),  # Teal
            QColor("#45B7D1"),  # Blue
            QColor("#96CEB4"),  # Mint
            QColor("#FECA57"),  # Orange
            QColor("#FF9FF3"),  # Pink
        ]
        
        # Draw the cycling spinner with rainbow colors
        for i in range(8):  # 8 segments
            angle = (self.spinner_angle + i * 45) % 360
            # Calculate opacity based on position in cycle
            progress = (angle / 360.0)
            opacity = 0.2 + 0.8 * (1 - abs(progress - 0.5) * 2)  # Peak at 0.5, fade to 0.2
            
            # Get rainbow color for this segment
            color = rainbow_colors[i].lighter(120)  # Slightly brighter
            color.setAlphaF(opacity)
            
            painter.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw arc segment
            start_angle = angle * 16  # Qt uses 1/16th degrees
            span_angle = 35 * 16  # Slightly larger arc for better visibility
            
            # Rectangle for the arc (centered and sized for beautiful appearance)
            rect = QRectF(8, 8, 32, 32)  # 48-16=32 diameter, centered
            painter.drawArc(rect, start_angle, span_angle)
        
        painter.end()
        self.spinner_label.setPixmap(pixmap)

    def start_animation(self, message=None):
        """Start the spinner animation"""
        if message:
            self.loading_label.setText(message)
        self.spinner_timer.start(100)  # Update every 100ms

    def stop_animation(self):
        """Stop the spinner animation"""
        self.spinner_timer.stop()

    def set_message(self, message):
        """Set the loading message"""
        self.loading_label.setText(message)

    def is_animating(self):
        """Check if the spinner is currently animating"""
        return self.spinner_timer.isActive()

# === components: plugins_view.py ===
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy, QMenu
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QAction
from typing import Any
import os
import shutil
import re
import random


class CardState:
    """Encapsulates the state of a plugin card"""
    def __init__(self):
        self.is_installing = False
        self.is_installed_state = False
        self.matching_plugin = None
    
    def set_installing(self, installing):
        """Set the installing state"""
        self.is_installing = installing
    
    def get_installing(self):
        """Get the installing state"""
        return self.is_installing
    
    def set_installed_state(self, installed):
        """Set the installed state"""
        self.is_installed_state = installed
    
    def get_installed_state(self):
        """Get the installed state"""
        return self.is_installed_state
    
    def set_matching_plugin(self, plugin):
        """Set the matching plugin reference"""
        self.matching_plugin = plugin
    
    def get_matching_plugin(self):
        """Get the matching plugin reference"""
        return self.matching_plugin


class ElideLabel(QLabel):
    def __init__(self, text="", parent=None, max_lines=2):
        super().__init__(text, parent)
        self._full_text = text or ""
        self._max_lines = max(1, int(max_lines))
        try:
            self.setWordWrap(True)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        except Exception:
            pass

    def set_max_lines(self, n):
        try:
            self._max_lines = max(1, int(n))
        except Exception:
            self._max_lines = 1
        self._apply_elide()

    def setText(self, text):
        self._full_text = text or ""
        self._apply_elide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_elide()

    def _apply_elide(self):
        try:
            fm = self.fontMetrics()
            width = max(0, self.width())
            if width <= 0:
                QLabel.setText(self, self._full_text)
                return
            if self._max_lines <= 1:
                el = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, width)
                QLabel.setText(self, el)
                return
            words = (self._full_text or "").split()
            lines = []
            current = ""
            i = 0
            while i < len(words):
                w = words[i]
                trial = (current + " " + w).strip()
                if fm.horizontalAdvance(trial) <= width:
                    current = trial
                    i += 1
                else:
                    if current:
                        lines.append(current)
                    else:
                        lines.append(fm.elidedText(w, Qt.TextElideMode.ElideRight, width))
                        i += 1
                    current = ""
                if len(lines) == self._max_lines - 1:
                    remaining = " ".join(words[i:])
                    last = (current + (" " if current and remaining else "") + remaining).strip()
                    el = fm.elidedText(last, Qt.TextElideMode.ElideRight, width)
                    lines.append(el)
                    current = ""
                    break
            if current and len(lines) < self._max_lines:
                lines.append(current)
            QLabel.setText(self, "\n".join(lines[: self._max_lines]))
        except Exception:
            try:
                QLabel.setText(self, self._full_text)
            except Exception:
                pass

class PluginCard(QFrame):
    def __init__(self, spec: dict, icon: QIcon, installed: bool, on_install, on_open, on_uninstall, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.on_install = on_install
        self.on_open = on_open
        self.on_uninstall = on_uninstall
        self.setObjectName("pluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(self._style())
        # Fix height so all cards are uniform regardless of content/state
        self.setFixedHeight(148)
        # Prevent vertical stretch so grid vertical spacing is visible
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.icon_label = QLabel()
        try:
            if icon and not icon.isNull():
                self.icon_label.setPixmap(icon.pixmap(36, 36))
            else:
                self.icon_label.setText("🧩")
        except Exception:
            self.icon_label.setText("🧩")
        layout.addWidget(self.icon_label)

        text_col = QVBoxLayout()
        title_text = spec.get('name') or spec.get('id') or "Unknown"
        title = ElideLabel(title_text, self, max_lines=1)
        title.setObjectName("pluginTitle")
        try:
            title.setToolTip(title_text)
        except Exception:
            pass
        desc_text = spec.get('desc', "")
        desc = ElideLabel(desc_text, self, max_lines=2)
        desc.setObjectName("pluginDesc")
        try:
            desc.setToolTip(desc_text)
        except Exception:
            pass
        text_col.addWidget(title)
        text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.action_btn = QPushButton()
        self.status_label = QLabel()
        self.status_label.setObjectName("pluginStatus")
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setVisible(False)
        btn_col = QVBoxLayout()
        btn_col.addWidget(self.action_btn)
        btn_col.addWidget(self.uninstall_btn)
        btn_col.addWidget(self.status_label)
        btn_col.addStretch()
        layout.addLayout(btn_col)

        self.update_state(installed)

    def update_icon(self, icon: QIcon):
        try:
            if icon and not icon.isNull():
                self.icon_label.setPixmap(icon.pixmap(36, 36))
            else:
                self.icon_label.setText("🧩")
        except Exception:
            try:
                self.icon_label.setText("🧩")
            except Exception:
                pass

    def update_state(self, installed: bool):
        self.status_label.setText("Installed" if installed else "Not installed")
        if installed:
            self.action_btn.setText("Open")
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_open(self.spec))
            self.uninstall_btn.setVisible(True)
            self.uninstall_btn.clicked.disconnect() if self.uninstall_btn.receivers(self.uninstall_btn.clicked) else None
            self.uninstall_btn.clicked.connect(lambda: self.on_uninstall(self.spec))
        else:
            self.action_btn.setText("Install")
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_install(self.spec))
            self.uninstall_btn.setVisible(False)

    def set_installing(self, installing: bool):
        try:
            if installing:
                self.action_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)
                self.action_btn.setText("Installing…")
                self.status_label.setText("Installing…")
            else:
                self.action_btn.setEnabled(True)
                self.uninstall_btn.setEnabled(True)
                # Restore text based on state
                self.update_state(self.status_label.text().lower().startswith("installed"))
        except Exception:
            pass

    def _style(self):
        return """
        QFrame#pluginCard {
            background-color: #0f0f0f;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.06);
            margin: 10px;
        }
        QLabel#pluginTitle {
            color: #F0F0F0;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#pluginDesc {
            color: #A0A0A0;
            font-size: 11px;
        }
        QLabel#pluginStatus {
            color: #00BFAE;
            font-size: 10px;
        }
        """


class DraggableScrollArea(QScrollArea):
    """Custom scroll area that supports drag scrolling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos = None
        self._drag_start_value = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._drag_start_value = self.horizontalScrollBar().value()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            delta = event.pos().x() - self._drag_start_pos.x()
            new_value = self._drag_start_value - delta
            self.horizontalScrollBar().setValue(new_value)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._drag_start_value = None
        super().mouseReleaseEvent(event)


class PluginsView(QWidget):
    install_requested = pyqtSignal(str)   # plugin id
    launch_requested = pyqtSignal(str)    # plugin id
    uninstall_requested = pyqtSignal(str) # plugin id

    def __init__(self, main_app, get_icon_callback, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.get_icon_callback = get_icon_callback
        self._filter_text = ""
        self._installed_only = False
        self._categories = set()
        self._selected_category = None  # Track selected category
        self._current_cols = 2  # Track current column count
        self._all_cards = []  # Store all created cards for performance
        self._current_filter_states = {}  # Track current filter states
        self._current_source_states = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}  # Track source states
        
        # Pagination variables for infinite scrolling
        self._all_plugins = []  # All available plugins
        self._loaded_count = 0  # Number of plugins currently loaded
        self._batch_size = 4  # Load 4 plugins at a time for better performance
        self._is_loading = False  # Prevent multiple simultaneous loads
        self._loading_indicator = None  # Loading indicator widget
        self._load_timer = None  # Timer for deferred loading
        self._card_cache = {}
        self._category_filtered_plugins = []
        self._category_loaded_count = 0
        self._is_layouting = False  # Guard to avoid loading during relayout
        
        # Debounce timer for resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize)
        
        # UI components initialized in _init_ui
        self.slider_layout: Any = None
        self.grid_layout: Any = None
        self._loading_container: Any = None
        self._scroll_area: Any = None
        
        self._init_specs()
        self._init_ui()

    def _init_specs(self):
        """Initialize plugin specifications from external data file"""
        self.plugins = get_plugins_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Popular Apps Slider Section
        self.create_popular_slider(layout)
        
        # Filter Buttons Row
        self.create_filter_buttons(layout)
        
        # Apps Grid
        self.create_apps_grid(layout)
        QTimer.singleShot(100, self.populate_app_cards)

    def create_popular_slider(self, parent_layout):
        """Create the popular apps slider at the top"""
        slider_container = QWidget()
        slider_container.setFixedHeight(220)  # Increased height for larger cards
        slider_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(20, 25, 35, 0.9),
                    stop:1 rgba(25, 30, 40, 0.9));
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Create draggable scroll area for horizontal scrolling
        scroll_area = DraggableScrollArea()
        scroll_area.setFixedHeight(220)  # Increased height for larger cards
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Enable scroll bar interaction
        scroll_area.horizontalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea::corner {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(60, 60, 60, 0.7);
                border-radius: 6px;
                min-width: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(80, 80, 80, 0.9);
            }
            QScrollBar::handle:horizontal:pressed {
                background: rgba(100, 100, 100, 1);
            }
            QScrollBar::add-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                border: none;
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        
        # Create content widget for the scroll area
        scroll_content = QWidget()
        self.slider_layout = QHBoxLayout(scroll_content)
        self.slider_layout.setContentsMargins(20, 20, 20, 20)
        self.slider_layout.setSpacing(16)
        
        # Popular apps data - curated selection with image filenames
        popular_apps = [
            {"name": "Firefox", "desc": "Fast, private & safe web browser", "category": "Internet", "rating": 4.6, "image": "firefox.jpg"},
            {"name": "Visual Studio Code", "desc": "Powerful code editor", "category": "Development", "rating": 4.8, "image": "vscode.jpg"},
            {"name": "Timeshift", "desc": "System restore utility", "category": "System Tools", "rating": 4.5, "image": "timeshift.jpg"},
            {"name": "BleachBit", "desc": "System cleaner & privacy tool", "category": "System Tools", "rating": 4.3, "image": "bleachbit.jpg"},
            {"name": "GIMP", "desc": "GNU Image Manipulation Program", "category": "Graphics", "rating": 4.4, "image": "gimp.jpg"},
            {"name": "VLC Media Player", "desc": "Universal media player", "category": "Multimedia", "rating": 4.7, "image": "vlc.jpg"},
            {"name": "Discord", "desc": "Voice, video and text chat", "category": "Communication", "rating": 4.2, "image": "discode.jpg"},
            {"name": "Krita", "desc": "Digital painting application", "category": "Graphics", "rating": 4.6, "image": "krita.jpg"},
            {"name": "Spotify", "desc": "Music streaming service", "category": "Multimedia", "rating": 4.1, "image": "spotify.jpg"},
            {"name": "Telegram", "desc": "Fast and secure messaging", "category": "Communication", "rating": 4.4, "image": "telegram.jpg"},
            {"name": "Google Chrome", "desc": "Fast and secure web browser", "category": "Internet", "rating": 4.3, "image": "chrome.jpg"},
            {"name": "Kitty", "desc": "Fast, feature-rich terminal", "category": "System Tools", "rating": 4.5, "image": "kitty.jpg"}
        ]
        
        # Shuffle the apps list to randomize the order
        shuffled_apps = popular_apps.copy()
        random.shuffle(shuffled_apps)
        
        for app in shuffled_apps:
            card = self.create_slider_card(app)
            self.slider_layout.addWidget(card)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(scroll_content)
        scroll_content.setCursor(Qt.CursorShape.OpenHandCursor)
        
        # Add scroll area to the main container
        container_layout = QVBoxLayout(slider_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(slider_container)

    def create_slider_card(self, app_data):
        """Create a card for the popular apps slider with background image"""
        card = QFrame()
        card.setFixedSize(240, 180)  # Larger size for better visibility
        
        # Find matching plugin for this app
        matching_plugin = None
        app_name = app_data.get('name', '').lower()
        
        # Try exact name match first
        for plugin in self.plugins:
            if plugin.get('name', '').lower() == app_name:
                matching_plugin = plugin
                break
        
        # If no exact match, try partial/fuzzy matching
        if not matching_plugin:
            for plugin in self.plugins:
                plugin_name = plugin.get('name', '').lower()
                # Check if app_name is contained in plugin name or vice versa
                if app_name in plugin_name or plugin_name in app_name:
                    # Prefer exact word matches
                    if app_name.split()[0] in plugin_name.split():
                        matching_plugin = plugin
                        break
        
        # Last resort: try ID matching
        if not matching_plugin:
            app_id = app_data.get('name', '').lower().replace(' ', '-')
            for plugin in self.plugins:
                if plugin.get('id', '').lower() == app_id or app_id in plugin.get('id', '').lower():
                    matching_plugin = plugin
                    break
        
        # Check if app is installed
        is_installed = False
        if matching_plugin:
            is_installed = self.is_installed(matching_plugin)
        
        # Get background image path
        image_filename = app_data.get("image", "")
        background_image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "slidebar", image_filename)
        
        # Create background image label
        background_label = QLabel(card)
        background_label.setGeometry(0, 0, 240, 180)
        
        # Load and scale the background image
        if os.path.exists(background_image_path):
            pixmap = QPixmap(background_image_path)
            if not pixmap.isNull():
                # Scale the pixmap to cover the entire card while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                
                # If the scaled image is larger than the card, crop it to center
                if scaled_pixmap.width() > 240 or scaled_pixmap.height() > 180:
                    x_offset = max(0, (scaled_pixmap.width() - 240) // 2)
                    y_offset = max(0, (scaled_pixmap.height() - 180) // 2)
                    cropped_pixmap = scaled_pixmap.copy(x_offset, y_offset, 240, 180)
                    background_label.setPixmap(cropped_pixmap)
                else:
                    background_label.setPixmap(scaled_pixmap)
        
        # Style the card frame
        card.setStyleSheet("""
            QFrame {
                border-radius: 12px;
                border: none;
            }
        """)
        
        # Create overlay container for text content
        overlay = QWidget(card)
        overlay.setGeometry(0, 0, 240, 180)
        overlay.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0.1),
                    stop:0.6 rgba(0, 0, 0, 0.3),
                    stop:1 rgba(0, 0, 0, 0.8));
                border: none;
            }
        """)
        
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Add stretch to push content to bottom
        layout.addStretch()
        
        # App name
        name_label = QLabel(app_data["name"])
        name_label.setStyleSheet("""
            color: white;
            font-weight: 700;
            font-size: 16px;
            background: transparent;
        """)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        
        # App description
        desc_label = QLabel(app_data["desc"])
        desc_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 12px;
            font-weight: 400;
            background: transparent;
        """)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc_label.setMaximumHeight(32)
        layout.addWidget(desc_label)
        
        # Bottom row with rating and install button
        bottom_row = QWidget()
        bottom_row.setStyleSheet("background: transparent;")
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(8)
        
        # Rating
        rating_label = QLabel(f"⭐ {app_data['rating']}")
        rating_label.setStyleSheet("""
            color: #FFD700;
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        bottom_layout.addWidget(rating_label)
        
        bottom_layout.addStretch()
        
        # Install/Open button
        button_text = "Open" if is_installed else "Install"
        action_btn = QPushButton(button_text)
        action_btn.setFixedSize(80, 32)
        action_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 0.9);
                color: white;
                border: none;
                border-radius: 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(50, 50, 50, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(20, 20, 20, 0.9);
            }
        """)
        
        # Connect button to appropriate action
        if matching_plugin:
            if is_installed:
                action_btn.clicked.connect(lambda: self.launch_requested.emit(matching_plugin['id']))
            else:
                action_btn.clicked.connect(lambda: (card.set_installing(True), self.install_requested.emit(matching_plugin['id'])))
        
        bottom_layout.addWidget(action_btn)
        
        layout.addWidget(bottom_row)
        
        # Store state using CardState class for proper encapsulation
        card_state = CardState()
        card_state.set_installed_state(is_installed)
        card_state.set_matching_plugin(matching_plugin)
        card.card_state = card_state
        
        def set_card_installing(installing):
            card_state.set_installing(installing)
            if installing:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(False)
                    widget.setText("Installing…")
            else:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(True)
                    widget.setText("Open" if card_state.get_installed_state() else "Install")
        card.set_installing = set_card_installing
        
        return card

    def _get_or_create_card(self, plugin_spec):
        """Return cached card data for a plugin or create it."""
        try:
            pid = plugin_spec.get('id')
        except Exception:
            pid = None
        if pid and pid in getattr(self, '_card_cache', {}):
            return self._card_cache[pid]
        installed = self.is_installed(plugin_spec)
        icon = self._icon_for(plugin_spec)
        card = self.create_app_card(plugin_spec, icon, installed)
        data = {
            'plugin': plugin_spec,
            'widget': card,
            'installed': installed
        }
        try:
            if pid:
                self._card_cache[pid] = data
        except Exception:
            pass
        return data

    def create_filter_buttons(self, parent_layout):
        """Create the main filter buttons row"""
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(12)
        
        filters = ["All", "Popular", "Updated", "Categories"]
        
        for i, filter_name in enumerate(filters):
            btn = QPushButton(filter_name)
            btn.setFixedHeight(36)
            
            # Special handling for Categories button
            if filter_name == "Categories":
                # Create dropdown menu for categories
                categories_menu = QMenu(self)
                categories_menu.setStyleSheet("""
                    QMenu {
                        background-color: #1a1a1a;
                        color: #E0E0E0;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 8px;
                        padding: 4px;
                    }
                    QMenu::item {
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(0, 191, 174, 0.2);
                    }
                """)
                
                # Add "All Categories" option first
                all_action = QAction("All Categories", self)
                all_action.triggered.connect(self.show_all_apps)
                categories_menu.addAction(all_action)
                categories_menu.addSeparator()
                
                # Get unique categories from plugins using normalized mapping
                unique_categories = sorted({self._category_for(p) for p in self.plugins})
                
                for category in unique_categories:
                    action = QAction(category, self)
                    action.triggered.connect(lambda checked, cat=category: self.filter_by_category(cat))
                    categories_menu.addAction(action)
                
                btn.setMenu(categories_menu)
            
            if i == 0:  # "All" button selected by default
                btn.clicked.connect(self.show_all_apps)  # Connect All button to show all apps
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00BFAE;
                        color: white;
                        border: none;
                        border-radius: 18px;
                        padding: 0 20px;
                        font-weight: 600;
                        font-size: 13px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.1);
                        color: #E0E0E0;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 18px;
                        padding: 0 20px;
                        font-weight: 500;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 191, 174, 0.2);
                        border-color: rgba(0, 191, 174, 0.4);
                    }
                """)
            
            filter_layout.addWidget(btn)
        
        filter_layout.addStretch()
        parent_layout.addWidget(filter_container)


    @staticmethod
    def _get_scrollbar_stylesheet():
        """Return beautiful scrollbar stylesheet with dark rounded corners"""
        return """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea::corner {
                background: transparent;
                border: none;
            }
            /* Vertical Scrollbar */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(60, 60, 60, 0.7);
                border-radius: 6px;
                min-height: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(80, 80, 80, 0.9);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(100, 100, 100, 1);
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            
            /* Horizontal Scrollbar */
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(60, 60, 60, 0.7);
                border-radius: 6px;
                min-width: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(80, 80, 80, 0.9);
            }
            QScrollBar::handle:horizontal:pressed {
                background: rgba(100, 100, 100, 1);
            }
            QScrollBar::add-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                border: none;
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """

    def create_apps_grid(self, parent_layout):
        """Create the apps grid section"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Enable scroll bar interaction
        scroll.verticalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.horizontalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.setStyleSheet(self._get_scrollbar_stylesheet())
        
        # Connect scroll event to detect when user reaches bottom
        scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        
        # Create grid container
        grid_container = QWidget()
        # Use Minimum vertical policy so content grows naturally and scrollbars appear when needed
        grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Dynamic column stretching will be set in populate_app_cards
        
        # Add loading indicator container at the bottom
        self._loading_container = QWidget()
        self._loading_container.setVisible(False)
        loading_layout = QVBoxLayout(self._loading_container)
        loading_layout.setContentsMargins(20, 10, 20, 10)
        loading_layout.setSpacing(8)
        
        loading_text = QLabel("Loading more plugins...")
        loading_text.setStyleSheet("""
            QLabel {
                color: #00BFAE;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
            }
        """)
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(loading_text)
        
        # Add grid and loading indicator to scroll layout
        scroll_layout.addWidget(grid_container)
        scroll_layout.addWidget(self._loading_container)
        
        scroll.setWidget(scroll_widget)
        self._scroll_area = scroll  # Store reference for scroll handling
        parent_layout.addWidget(scroll)

    def populate_app_cards(self):
        """Populate the grid with real plugin cards filtered by category"""
        # For category filtering, show all cards that match the category
        if self._selected_category:
            if not self._all_cards:
                self._create_all_cards()
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            self._reset_row_stretches()
            for card_data in self._all_cards:
                card_data['widget'].hide()
            try:
                viewport_w = self._scroll_area.viewport().width()
                viewport_h = self._scroll_area.viewport().height()
            except Exception:
                viewport_w = self.width()
                viewport_h = self.height()
            cols = self._calc_cols(viewport_w)
            visible_rows = self._calc_visible_rows(viewport_h)
            initial_rows = visible_rows + 2
            self._current_cols = cols
            # Ensure full dataset is available for categories
            if not self._all_plugins:
                self._all_plugins = get_all_plugins_data()
            # Build filtered plugin list from the full dataset
            self._category_filtered_plugins = [p for p in self._all_plugins if self._category_for(p) == self._selected_category]
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
                try:
                    self.grid_layout.setColumnMinimumWidth(i, 340)
                except Exception:
                    pass
            initial_batch = min(len(self._category_filtered_plugins), cols * initial_rows)
            self._category_loaded_count = 0
            self._load_initial_category_batch(initial_batch)
            QTimer.singleShot(10, self._ensure_category_scrollbar_visible)
        else:
            # For "All" tab, use pagination system
            if not self._all_plugins:
                # Initialize pagination if not already done
                self.show_all_apps()
            else:
                # Just refresh the current view
                self._update_grid_layout()
    
    def _create_all_cards(self):
        """Create all plugin cards once for better performance"""
        self._all_cards = []
        for plugin in self.plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            self._all_cards.append({
                'plugin': plugin,
                'widget': card,
                'installed': installed
            })

    @staticmethod
    def _get_package_source(plugin_spec):
        """Determine package source from plugin spec"""
        pkg = plugin_spec.get('pkg', '').lower()
        if pkg.startswith('npm-') or 'npm' in pkg:
            return 'npm'
        elif pkg.startswith('aur/') or 'aur' in pkg:
            return 'aur'
        elif pkg.endswith('.flatpak') or 'flatpak' in pkg:
            return 'flatpak'
        elif pkg.startswith('brew-') or 'brew' in pkg:
            return 'brew'
        else:
            return 'pacman'
    
    @staticmethod
    def _category_for(plugin):
        cat = (plugin.get('category') or '').strip()
        if cat:
            c = cat.lower()
            synonyms = {
                'system': 'System Tools',
                'system tool': 'System Tools',
                'system tools': 'System Tools',
                'utility': 'Utility',
                'utilities': 'Utility',
                'dev': 'Development',
                'development': 'Development',
                'internet': 'Internet',
                'network': 'Internet',
                'graphics': 'Graphics',
                'multimedia': 'Multimedia',
                'audio': 'Multimedia',
                'video': 'Multimedia',
                'office': 'Office',
                'productivity': 'Office',
                'education': 'Education',
                'game': 'Games',
                'games': 'Games',
                'security': 'Security',
                'communication': 'Communication',
                'chat': 'Communication',
            }
            return synonyms.get(c, cat)
        tags = plugin.get('tags') or []
        tags_text = ' '.join(tags) if isinstance(tags, (list, tuple, set)) else str(tags)
        text = ' '.join([
            plugin.get('name', ''),
            plugin.get('desc', ''),
            plugin.get('id', ''),
            plugin.get('pkg', ''),
            tags_text,
        ]).lower()
        patterns = [
            (('vscode','visual studio','code','editor','ide','developer','dev','git','node','npm','python','qt','gcc','make','electron','android studio'), 'Development'),
            (('browser','firefox','chrome','web','network','mail','torrent','internet','ftp'), 'Internet'),
            (('image','photo','graphic','draw','paint','gimp','krita','inkscape','blender'), 'Graphics'),
            (('video','music','audio','player','vlc','mpv','spotify','media','ffmpeg'), 'Multimedia'),
            (('chat','telegram','discord','slack','message','voip','call','communication'), 'Communication'),
            (('system','monitor','btop','htop','terminal','shell','backup','timeshift','disk','partition','gparted','bleachbit'), 'System Tools'),
            (('game','steam','lutris','retroarch','games'), 'Games'),
            (('office','libreoffice','document','spreadsheet','writer','calc','pdf'), 'Office'),
            (('learn','education','anki','study'), 'Education'),
            (('password','privacy','guard','vpn','security','encrypt'), 'Security'),
        ]
        for kws, label in patterns:
            for kw in kws:
                if kw in text:
                    return label
        return 'Utility'
    
    @staticmethod
    def _get_source_icon(source):
        """Get icon path for package source"""
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover")
        icons = {
            'pacman': os.path.join(base_path, 'pacman.svg'),
            'aur': os.path.join(base_path, 'aur.svg'),
            'flatpak': os.path.join(base_path, 'flatpack.svg'),
            'npm': os.path.join(base_path, 'node.svg'),
            'brew': os.path.join(base_path, 'pacman.svg'),
            'pip': os.path.join(base_path, 'pacman.svg')
        }
        return icons.get(source, os.path.join(base_path, 'pacman.svg'))

    # --- Layout helpers to keep calculations consistent ---
    def _layout_spacing(self):
        try:
            return self.grid_layout.spacing() if self.grid_layout else 20
        except Exception:
            return 20

    def _calc_cols(self, viewport_width):
        spacing = self._layout_spacing()
        unit_w = 340 + spacing
        # Cap columns to 5 to avoid tight packing on very wide screens
        return max(1, min(5, (max(0, viewport_width) + spacing) // unit_w))

    def _calc_visible_rows(self, viewport_height):
        spacing = self._layout_spacing()
        row_h = 140 + spacing
        return max(1, (max(0, viewport_height) + spacing) // row_h)

    def _enforce_row_min_heights(self, upto_row):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            for r in range(0, max(0, int(upto_row)) + 1):
                self.grid_layout.setRowMinimumHeight(r, 140)
        except Exception:
            pass
    
    def _stop_deferred_loads(self):
        try:
            if self._load_timer is not None:
                self._load_timer.stop()
                self._load_timer = None
        except Exception:
            self._load_timer = None

    def _begin_layout_update(self):
        if self._is_layouting:
            return False
        self._is_layouting = True
        self._stop_deferred_loads()
        try:
            self.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.setUpdatesEnabled(False)
                self._scroll_area.viewport().setUpdatesEnabled(False)
        except Exception:
            pass
        return True

    def _finish_layout_update(self):
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.viewport().setUpdatesEnabled(True)
                self._scroll_area.setUpdatesEnabled(True)
                self._scroll_area.viewport().update()
        except Exception:
            pass
        try:
            self.setUpdatesEnabled(True)
        except Exception:
            pass
        self._is_layouting = False

    def create_app_card(self, plugin_spec, icon, installed):
        """Create a medium-sized app card with enhanced styling"""
        card = QFrame()
        card.setFixedSize(340, 140)
        # Ensure the widget paints its own background to avoid transparency/bleed issues
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setAutoFillBackground(True)
            card.setObjectName("appCard")
        except Exception:
            pass
        
        # Store state using CardState class for proper encapsulation
        card_state = CardState()
        card_state.set_installed_state(installed)
        card.card_state = card_state
        
        def set_card_installing(installing):
            card_state.set_installing(installing)
            if installing:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(False)
                    if widget.text() in ("Install", "Open"):
                        widget.setText("Installing…")
                    elif widget.text() == "Uninstall":
                        widget.setText("Uninstalling…")
            else:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(True)
                    if "Installing" in widget.text() or "Uninstalling" in widget.text():
                        if "Uninstalling" in widget.text():
                            widget.setText("Uninstall")
                        else:
                            widget.setText("Install" if not card_state.get_installed_state() else "Open")
        card.set_installing = set_card_installing
        bg_image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "cardbackground.jpg")
        bg_image_url = bg_image_path.replace("\\", "/")
        card.setStyleSheet(f"""
            QFrame#appCard {{
                background-image: url('{bg_image_url}');
                background-position: center;
                background-repeat: no-repeat;
                background-color: rgb(15, 20, 30);
                border-radius: 14px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }}
            QFrame#appCard:hover {{
                border: 1px solid rgba(0, 191, 174, 0.4);
                background-color: rgb(20, 25, 35);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Left side: Icon and text
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        # Icon and name row
        icon_name_layout = QHBoxLayout()
        icon_name_layout.setContentsMargins(0, 0, 0, 0)
        icon_name_layout.setSpacing(10)
        
        # Icon with shadow effect
        icon_label = QLabel()
        icon_label.setFixedSize(52, 52)
        icon_label.setStyleSheet("""
            QLabel {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 2px;
            }
        """)
        if icon and not icon.isNull():
            icon_label.setPixmap(icon.pixmap(48, 48))
        else:
            icon_label.setText("🧩")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 28px;
                    border: none;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                }
            """)
        icon_name_layout.addWidget(icon_label)
        
        # Name and source column
        name_source_layout = QVBoxLayout()
        name_source_layout.setContentsMargins(0, 0, 0, 0)
        name_source_layout.setSpacing(2)
        
        # Name
        name_label = QLabel(plugin_spec.get('name', plugin_spec.get('id')))
        name_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_source_layout.addWidget(name_label)
        
        # Source (package manager) with icon
        source = self._get_package_source(plugin_spec)
        source_icon_path = self._get_source_icon(source)
        
        # Create source layout with icon and text
        source_layout = QHBoxLayout()
        source_layout.setContentsMargins(6, 2, 6, 2)
        source_layout.setSpacing(4)
        
        # Source icon
        source_icon_label = QLabel()
        source_icon_label.setFixedSize(12, 12)
        try:
            source_pixmap = QPixmap(source_icon_path)
            if not source_pixmap.isNull():
                source_icon_label.setPixmap(source_pixmap.scaled(12, 12, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                source_icon_label.setText("📦")
                source_icon_label.setStyleSheet("font-size: 10px;")
        except Exception:
            source_icon_label.setText("📦")
            source_icon_label.setStyleSheet("font-size: 10px;")
        
        # Source text
        source_text_label = QLabel(source)
        source_text_label.setStyleSheet("""
            QLabel {
                color: #00BFAE;
                font-size: 9px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        source_layout.addWidget(source_icon_label)
        source_layout.addWidget(source_text_label)
        source_layout.addStretch()
        
        # Source container with background
        source_container = QWidget()
        source_container.setLayout(source_layout)
        source_container.setStyleSheet("""
            QWidget {
                background: rgba(0, 191, 174, 0.1);
                border-radius: 6px;
            }
        """)
        name_source_layout.addWidget(source_container)
        
        icon_name_layout.addLayout(name_source_layout, 1)
        left_layout.addLayout(icon_name_layout)
        
        # Description
        desc_label = QLabel(plugin_spec.get('desc', ''))
        desc_label.setStyleSheet("""
            QLabel {
                color: #B0B0B0;
                font-size: 10px;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(28)
        left_layout.addWidget(desc_label)
        
        left_layout.addStretch()
        layout.addLayout(left_layout, 1)
        
        # Right side: Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        
        if installed:
            # Open button (filled white)
            open_btn = QPushButton("Open")
            open_btn.setFixedHeight(34)
            open_btn.setMinimumWidth(85)
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #1a1a1a;
                    border: none;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 12px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                    color: #000000;
                }
                QPushButton:pressed {
                    background-color: #E8E8E8;
                }
            """)
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda: self.launch_requested.emit(plugin_spec['id']))
            btn_layout.addWidget(open_btn)
            
            # Uninstall button (outlined)
            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setFixedHeight(32)
            uninstall_btn.setMinimumWidth(85)
            uninstall_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E0E0E0;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 11px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    border: 1px solid rgba(0, 191, 174, 0.8);
                    color: #00BFAE;
                    background-color: rgba(0, 191, 174, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 191, 174, 0.2);
                    border: 1px solid rgba(0, 191, 174, 1.0);
                }
            """)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.clicked.connect(lambda: (card.set_installing(True), self.uninstall_requested.emit(plugin_spec['id'])))
            btn_layout.addWidget(uninstall_btn)
        else:
            # Install button (filled teal)
            install_btn = QPushButton("Install")
            install_btn.setFixedHeight(34)
            install_btn.setMinimumWidth(85)
            install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00BFAE;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 12px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: #00D4C4;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #009080;
                }
            """)
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.clicked.connect(lambda: (card.set_installing(True), self.install_requested.emit(plugin_spec['id'])))
            btn_layout.addWidget(install_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return card

    def _icon_for(self, spec):
        try:
            path = spec.get('icon')
            if path and os.path.exists(path):
                return self.get_icon_callback(os.path.normpath(path), 36)

            # Try to resolve using available files (supports svg/png/jpg/jpeg) with aliases
            resolved = self._find_plugin_icon_file(spec)
            if resolved and os.path.exists(resolved):
                return self.get_icon_callback(os.path.normpath(resolved), 36)

            # Fallback to default plugin icon
            fallback = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "plugins.svg")
            return self.get_icon_callback(os.path.normpath(fallback), 36)
        except Exception:
            return QIcon()

    def _normalize_name(self, s: str) -> str:
        try:
            return re.sub(r'[^a-z0-9]', '', (s or '').lower())
        except Exception:
            s = (s or '').lower()
            return s.replace('-', '').replace('_', '').replace(' ', '')

    def _candidate_aliases(self, spec) -> list:
        pid = (spec.get('id') or '')
        name = (spec.get('name') or '')
        aliases = []

        def add(x):
            if x and x not in aliases:
                aliases.append(x)

        # Base identifiers
        add(pid)
        add(name)
        add(pid.replace('-', ''))
        add(pid.replace('-', '_'))
        add(pid.replace('_', ''))
        add((name or '').replace(' ', ''))
        add((name or '').replace(' ', '-').lower())
        add((name or '').replace(' ', '').lower())

        # Explicit aliases for known mismatches and alt names
        alias_map = {
            'bleachbit': ['BleachBit', 'bleachbit'],
            'timeshift': ['timeshift'],
            'baobab': ['diskusageanalyzer', 'baobab'],
            'deja-dup': ['dejadup', 'DejaDup'],
            'gparted': ['gparted'],
            'gnome-disk-utility': ['gnome-disks', 'gnomedisks', 'gnomeDis'],
            'pavucontrol': ['pavucontrol', 'pulseaudio'],
            'system-config-printer': ['printer', 'printers'],
            'btop': ['btop'],
            'htop': ['htop'],
            'gnome-system-monitor': ['system-monitor', 'gnomesystemmonitor', 'gnomeSystemMonitor'],
            'simple-scan': ['simple-scan', 'documentscanner'],
            'file-roller': ['file-roller', 'archive', 'achive', 'archivemanager', 'archiver'],
            'nvidia-settings': ['nvidia-settings', 'nvidia', 'nvideasettings', 'nvidiasettings'],
            'nvtop': ['nvtop'],
        }
        for a in alias_map.get(pid, []):
            add(a)

        return aliases

    def _find_plugin_icon_file(self, spec):
        icons_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "plugins"))
        try:
            files = []
            try:
                files = os.listdir(icons_dir)
            except Exception:
                files = []
            if not files:
                return None

            # Build index by normalized stem per extension, prefer svg, then png, jpeg, jpg
            exts = ['.svg', '.png', '.jpeg', '.jpg']
            index = {e: {} for e in exts}
            for fname in files:
                path = os.path.join(icons_dir, fname)
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in index:
                    continue
                stem = os.path.splitext(fname)[0]
                key = self._normalize_name(stem)
                # Do not overwrite existing mapping for same key/ext to keep first-found
                index[ext].setdefault(key, path)

            candidates = [self._normalize_name(a) for a in self._candidate_aliases(spec) if a]

            # Exact match by preference order
            for ext in exts:
                for key in candidates:
                    if key in index[ext]:
                        return index[ext][key]

            # Fallback: partial contains match (still following ext preference)
            for ext in exts:
                for key in candidates:
                    for k2, p2 in index[ext].items():
                        if key and (k2.startswith(key) or key in k2):
                            return p2
            return None
        except Exception:
            return None

    def is_installed(self, spec):
        cmd = spec.get('cmd')
        pkg = spec.get('pkg')
        # Prefer which on the launch command; fallback to pacman -Qi
        try:
            if cmd and shutil.which(cmd):
                return True
        except Exception:
            pass
        try:
            import subprocess
            r = subprocess.run(["pacman", "-Qi", pkg], capture_output=True, text=True)
            return r.returncode == 0
        except Exception:
            return False

    def refresh_all(self):
        """Refresh all plugin cards to reflect current installation state"""
        try:
            # Refresh slider cards to update Open/Install buttons
            try:
                if hasattr(self, 'slider_layout'):
                    for i in range(self.slider_layout.count()):
                        card = self.slider_layout.itemAt(i).widget()
                        if card and hasattr(card, 'card_state'):
                            plugin = card.card_state.get_matching_plugin()
                            if plugin:
                                # Re-check if app is installed
                                is_now_installed = self.is_installed(plugin)
                                # Update button text
                                buttons = card.findChildren(QPushButton)
                                if buttons:
                                    btn = buttons[0]
                                    btn.setText("Open" if is_now_installed else "Install")
                                    # Update the stored state for animation
                                    card.card_state.set_installed_state(is_now_installed)
            except Exception:
                pass
            
            # Clear grid layout
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Clear and rebuild all cards with updated installation status
            self._all_cards = []
            for plugin in self.plugins:
                installed = self.is_installed(plugin)
                icon = self._icon_for(plugin)
                card = self.create_app_card(plugin, icon, installed)
                self._all_cards.append({
                    'plugin': plugin,
                    'widget': card,
                    'installed': installed
                })
            
            # Rebuild grid with updated cards
            cols = self._current_cols
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
            
            for i, card_data in enumerate(self._all_cards):
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card_data['widget'], row, col)
        except Exception:
            pass

    def get_plugin(self, plugin_id):
        for spec in self.plugins:
            if spec['id'] == plugin_id:
                return spec
        return None

    def set_filter(self, text: str, installed_only: bool, categories=None):
        self._filter_text = (text or "").strip().lower()
        self._installed_only = bool(installed_only)
        self._categories = set((categories or []))
        self.apply_filter()

    def apply_filter(self):
        """Apply text, installed, and category filters to the plugins view"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        # Clear the grid layout
        while self.grid_layout.count():
            _ = self.grid_layout.takeAt(0)
        
        # Reset row stretches before re-adding cards
        self._reset_row_stretches()
        
        # Hide all cards first
        for card_data in self._all_cards:
            card_data['widget'].hide()
        
        # Filter and display cards based on search text, installed status, and categories
        filtered_cards = []
        for card_data in self._all_cards:
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check installed filter
            if self._installed_only and not is_installed:
                continue
            
            # Check category filter
            if self._categories:
                plugin_category = plugin.get('category', '')
                if plugin_category not in self._categories:
                    continue
            
            # Check search text filter
            if self._filter_text:
                name = (plugin.get('name', '') or '').lower()
                desc = (plugin.get('desc', '') or '').lower()
                plugin_id = (plugin.get('id', '') or '').lower()
                
                # Match if search text is in name, description, or id
                if not (self._filter_text in name or self._filter_text in desc or self._filter_text in plugin_id):
                    continue
            
            filtered_cards.append(card_data)
        
        # Use tracked column count
        cols = self._current_cols
        
        # Set column stretching dynamically
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        
        # Add filtered cards to layout and show them
        for i, card_data in enumerate(filtered_cards):
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        # Ensure the layout can scroll and does not keep a big empty bottom gap
        max_row = ((len(filtered_cards) - 1) // cols) if filtered_cards else 0
        self.grid_layout.setRowStretch(max_row + 1, 1)
        if not self._selected_category:
            QTimer.singleShot(50, self._ensure_scrollbar_visible)
        QTimer.singleShot(10, self._adjust_bottom_stretch)

    def set_installing(self, plugin_id: str, installing: bool):
        """Update installing state for a plugin card"""
        try:
            # Find the card with this plugin_id
            for card_data in self._all_cards:
                if card_data['plugin'].get('id') == plugin_id:
                    card = card_data['widget']
                    if hasattr(card, 'set_installing'):
                        card.set_installing(installing)
                    break
        except Exception:
            pass
    
    def filter_by_category(self, category):
        """Handle category selection from dropdown menu"""
        self._selected_category = category
        self._category_filtered_plugins = []
        self._category_loaded_count = 0
        self.populate_app_cards()
    
    def show_all_apps(self):
        """Show all apps by clearing category filter and initializing pagination"""
        self._selected_category = None
        
        # Initialize pagination for "All" tab
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
            self._loaded_count = 0
            self._all_cards = []
            
            # Clear existing grid
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            
            # Load first batch sized to fill visible rows on current viewport
            try:
                viewport_w = self._scroll_area.viewport().width()
                viewport_h = self._scroll_area.viewport().height()
            except Exception:
                viewport_w = self.width()
                viewport_h = self.height()
            cols = self._calc_cols(viewport_w)
            visible_rows = self._calc_visible_rows(viewport_h)
            initial_rows = visible_rows + 2  # fill screen + buffer
            initial_batch = min(len(self._all_plugins), cols * initial_rows)
            self._load_initial_batch(initial_batch)
        else:
            # Just refresh the current view
            self._update_grid_layout()
    
    def _load_initial_batch(self, batch_size):
        """Load the initial batch of plugins for the All tab"""
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        
        # Get initial batch
        new_plugins = self._all_plugins[:batch_size]
        
        # Create cards for initial plugins
        new_cards = []
        for plugin in new_plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            card_data = {
                'plugin': plugin,
                'widget': card,
                'installed': installed
            }
            new_cards.append(card_data)
        
        # Reset any previous row stretch factors
        try:
            rc = max(0, self.grid_layout.rowCount())
            for r in range(rc + 4):
                self.grid_layout.setRowStretch(r, 0)
        except Exception:
            pass

        # Add cards to grid using optimized positioning
        cols = self._current_cols
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
            try:
                self.grid_layout.setColumnMinimumWidth(i, 340)
            except Exception:
                pass
        
        # Pre-calculate maximum row needed for initial batch
        max_position = len(new_cards) - 1
        max_row_needed = max_position // cols
        
        # Add cards to positions
        for i, card_data in enumerate(new_cards):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        self._enforce_row_min_heights(max_row_needed)
        
        self._all_cards.extend(new_cards)
        self._loaded_count = batch_size
        
        # Hide loading indicator
        QTimer.singleShot(300, self._hide_loading_indicator)
        QTimer.singleShot(20, self._ensure_scrollbar_visible)
        self._is_loading = False
        self._finish_layout_update()
    
    def _load_initial_category_batch(self, batch_size):
        if self._is_loading:
            return
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        cols = self._current_cols
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        max_position = batch_size - 1
        max_row_needed = max(0, max_position // max(1, cols))
        for i in range(batch_size):
            plugin = self._category_filtered_plugins[i]
            card_data = self._get_or_create_card(plugin)
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._category_loaded_count = batch_size
        self._enforce_row_min_heights(max_row_needed)
        QTimer.singleShot(300, self._hide_loading_indicator)
        self._is_loading = False
        self._finish_layout_update()
    
    def _hide_loading_indicator(self):
        """Hide the loading indicator widget"""
        if hasattr(self, '_loading_container'):
            self._loading_container.setVisible(False)
    
    def _reset_row_stretches(self):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            rc = max(0, self.grid_layout.rowCount())
            for r in range(rc + 4):
                self.grid_layout.setRowStretch(r, 0)
        except Exception:
            pass
    
    def _adjust_bottom_stretch(self):
        """Keep a stretch row only when no scrollbar; remove it when scrolling is available."""
        if not hasattr(self, 'grid_layout'):
            return
        try:
            last_row = max(0, self.grid_layout.rowCount() - 1)
            sb = None
            try:
                sb = self._scroll_area.verticalScrollBar() if hasattr(self, '_scroll_area') else None
            except Exception:
                sb = None
            if sb and sb.maximum() > 0:
                # Scrolling available, remove artificial stretch row
                self.grid_layout.setRowStretch(last_row, 0)
            else:
                # No scrolling; keep stretch so content fills viewport cleanly
                self.grid_layout.setRowStretch(last_row, 1)
        except Exception:
            pass
    
    def _ensure_scrollbar_visible(self):
        """Auto-load more batches until the scrollbar appears (or we run out of items)."""
        # Only applies for the infinite-scroll 'All' view
        if getattr(self, '_selected_category', None):
            return
        if not hasattr(self, '_scroll_area'):
            return
        
        state = {'attempts': 0}
        
        def _step():
            if state['attempts'] >= 10:
                self._adjust_bottom_stretch()
                return
            sb = self._scroll_area.verticalScrollBar()
            if (sb.maximum() > 0) or (self._loaded_count >= len(self._all_plugins)):
                # If last row is not full, top it off to avoid a one-time gap
                try:
                    viewport_w = self._scroll_area.viewport().width()
                    cols = self._calc_cols(viewport_w)
                except Exception:
                    cols = max(1, int(self._current_cols) if hasattr(self, '_current_cols') else 1)
                remaining = len(self._all_plugins) - self._loaded_count
                need = (cols - (self._loaded_count % cols)) % cols
                if need > 0 and remaining > 0:
                    if self._is_loading:
                        QTimer.singleShot(120, _step)
                        return
                    state['attempts'] += 1
                    self._load_more_plugins()
                    QTimer.singleShot(120, _step)
                    return
                self._adjust_bottom_stretch()
                return
            if self._is_loading:
                QTimer.singleShot(120, _step)
                return
            state['attempts'] += 1
            self._load_more_plugins()
            QTimer.singleShot(120, _step)
        
        QTimer.singleShot(50, _step)
    
    def _ensure_category_scrollbar_visible(self):
        if not hasattr(self, '_scroll_area'):
            return
        if not getattr(self, '_selected_category', None):
            return
        state = {'attempts': 0}
        def _step():
            if state['attempts'] >= 10:
                self._adjust_bottom_stretch()
                return
            sb = self._scroll_area.verticalScrollBar()
            if (sb.maximum() > 0) or (self._category_loaded_count >= len(self._category_filtered_plugins)):
                try:
                    viewport_w = self._scroll_area.viewport().width()
                    cols = self._calc_cols(viewport_w)
                except Exception:
                    cols = max(1, int(self._current_cols) if hasattr(self, '_current_cols') else 1)
                remaining = len(self._category_filtered_plugins) - self._category_loaded_count
                need = (cols - (self._category_loaded_count % cols)) % cols
                if need > 0 and remaining > 0:
                    if self._is_loading:
                        QTimer.singleShot(120, _step)
                        return
                    state['attempts'] += 1
                    self._load_more_category()
                    QTimer.singleShot(120, _step)
                    return
                self._adjust_bottom_stretch()
                return
            if self._is_loading:
                QTimer.singleShot(120, _step)
                return
            state['attempts'] += 1
            self._load_more_category()
            QTimer.singleShot(120, _step)
        QTimer.singleShot(50, _step)
    
    def resizeEvent(self, event):
        """Handle window resize to update grid layout"""
        super().resizeEvent(event)
        # Debounce resize events to prevent performance issues
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
            self._resize_timer.start(150)  # Wait 150ms after resize stops
    
    def _handle_resize(self):
        """Handle debounced resize event"""
        if not hasattr(self, 'grid_layout') or not self.plugins:
            return
            
        # Determine new column count using actual viewport width
        try:
            viewport_width = self._scroll_area.viewport().width() if self._scroll_area else self.width()
        except Exception:
            viewport_width = self.width()
        new_cols = self._calc_cols(viewport_width)
        
        # Only rebuild if column count changed
        if new_cols != self._current_cols:
            self._current_cols = new_cols
            self._stop_deferred_loads()
            # Use optimized layout update instead of full rebuild
            self._update_grid_layout()
    
    def _update_grid_layout(self):
        """Update grid layout without recreating cards"""
        if not self._all_cards:
            self.populate_app_cards()
            return
        if self._is_layouting:
            return
        self._begin_layout_update()
        
        try:
            # Clear layout items
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            
            # Reset row stretches before re-layout
            self._reset_row_stretches()
            
            # Get filtered cards
            filtered_cards = self._all_cards
            if self._selected_category:
                if hasattr(self, '_category_filtered_plugins') and self._category_loaded_count:
                    filtered_cards = [self._get_or_create_card(p) for p in self._category_filtered_plugins[:self._category_loaded_count]]
                else:
                    # Fallback build from full dataset
                    if not self._all_plugins:
                        self._all_plugins = get_all_plugins_data()
                    filtered_cards = [self._get_or_create_card(p) for p in self._all_plugins if self._category_for(p) == self._selected_category]
            
            # Re-layout with new column count
            cols = self._current_cols
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
                try:
                    self.grid_layout.setColumnMinimumWidth(i, 340)
                except Exception:
                    pass
            
            for i, card_data in enumerate(filtered_cards):
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card_data['widget'], row, col)
            max_row = ((len(filtered_cards) - 1) // cols) if filtered_cards else 0
            self.grid_layout.setRowStretch(max_row + 1, 1)
            self._enforce_row_min_heights(max_row)
            # Adjust the bottom stretch so we don't keep a big empty row once scrolling is available
            QTimer.singleShot(10, self._adjust_bottom_stretch)
            if self._selected_category:
                QTimer.singleShot(50, self._ensure_category_scrollbar_visible)
            else:
                QTimer.singleShot(50, self._ensure_scrollbar_visible)
        finally:
            self._finish_layout_update()
    
    def _on_scroll(self, value):
        """Handle scroll events to detect when user reaches bottom"""
        if self._is_loading or self._is_layouting or not hasattr(self, '_scroll_area'):
            return
            
        scrollbar = self._scroll_area.verticalScrollBar()
        max_value = scrollbar.maximum()
        
        if self._selected_category:
            if max_value - value <= 150 and self._category_loaded_count < len(self._category_filtered_plugins):
                if self._load_timer is not None:
                    self._load_timer.stop()
                self._load_timer = QTimer()
                self._load_timer.setSingleShot(True)
                self._load_timer.timeout.connect(self._load_more_category)
                self._load_timer.start(100)
        else:
            if max_value - value <= 150 and self._loaded_count < len(self._all_plugins):
                if self._load_timer is not None:
                    self._load_timer.stop()
                self._load_timer = QTimer()
                self._load_timer.setSingleShot(True)
                self._load_timer.timeout.connect(self._load_more_plugins)
                self._load_timer.start(100)
    
    def _load_more_plugins(self):
        """Load next batch of plugins with optimized performance"""
        if self._is_loading or self._loaded_count >= len(self._all_plugins):
            return
            
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        
        # Calculate how many more plugins to load; align with row boundaries
        remaining = len(self._all_plugins) - self._loaded_count
        try:
            viewport_w = self._scroll_area.viewport().width()
        except Exception:
            viewport_w = self.width()
        cols = self._calc_cols(viewport_w)
        target_total = ((self._loaded_count + self._batch_size + cols - 1) // cols) * cols
        min_needed = max(cols, target_total - self._loaded_count)
        batch_size = min(remaining, min_needed)
        
        # Get next batch of plugins
        start_idx = self._loaded_count
        end_idx = start_idx + batch_size
        new_plugins = self._all_plugins[start_idx:end_idx]
        
        # Create cards for new plugins
        new_cards = []
        for plugin in new_plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            card_data = {
                'plugin': plugin,
                'widget': card,
                'installed': installed
            }
            new_cards.append(card_data)
        
        # Add new cards to the grid - optimized positioning
        cols = self._current_cols
        
        # Pre-calculate maximum row needed
        max_position = self._loaded_count + len(new_cards) - 1
        max_row_needed = max_position // cols
        
        # Reset previous stretches so we don't leave a stretched empty row in the middle
        self._reset_row_stretches()
        
        # Add cards to grid positions
        for i, card_data in enumerate(new_cards):
            total_position = self._loaded_count + i
            row = total_position // cols
            col = total_position % cols
            self.grid_layout.addWidget(card_data['widget'], row, col)
        
        # Add a final stretch row to enable scrolling
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._enforce_row_min_heights(max_row_needed)
        
        # Add to all_cards list
        self._all_cards.extend(new_cards)
        self._loaded_count += batch_size
        
        # Hide loading indicator after a short delay
        QTimer.singleShot(100, self._hide_loading_indicator)
        self._is_loading = False
        self._finish_layout_update()
    
    def _load_more_category(self):
        if self._is_loading or self._category_loaded_count >= len(self._category_filtered_plugins):
            return
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        remaining = len(self._category_filtered_plugins) - self._category_loaded_count
        try:
            viewport_w = self._scroll_area.viewport().width()
        except Exception:
            viewport_w = self.width()
        cols = self._calc_cols(viewport_w)
        target_total = ((self._category_loaded_count + self._batch_size + cols - 1) // cols) * cols
        min_needed = max(cols, target_total - self._category_loaded_count)
        batch_size = min(remaining, min_needed)
        max_position = self._category_loaded_count + batch_size - 1
        max_row_needed = max_position // cols
        self._reset_row_stretches()
        for i in range(batch_size):
            total_position = self._category_loaded_count + i
            plugin = self._category_filtered_plugins[total_position]
            card_data = self._get_or_create_card(plugin)
            row = total_position // cols
            col = total_position % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._category_loaded_count += batch_size
        self._enforce_row_min_heights(max_row_needed)
        QTimer.singleShot(100, self._hide_loading_indicator)
        self._is_loading = False
    
    def apply_filters(self, filter_states):
        """Apply Available/Installed filters to the plugins view"""
        # Store current filter states
        self._current_filter_states = filter_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()
    
    def apply_source_filters(self, source_states):
        """Apply source filters (pacman, AUR, Flatpak, npm) to the plugins view"""
        # Store current source states
        self._current_source_states = source_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()
    
    def _apply_combined_filters(self):
        """Apply both status and source filters together"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        # Clear the grid layout
        while self.grid_layout.count():
            _ = self.grid_layout.takeAt(0)
        
        # Get filter states
        show_available = self._current_filter_states.get('Available', True)
        show_installed = self._current_filter_states.get('Installed', True)
        
        # Get source states
        show_pacman = self._current_source_states.get('pacman', True)
        show_aur = self._current_source_states.get('AUR', True)
        show_flatpak = self._current_source_states.get('Flatpak', True)
        show_npm = self._current_source_states.get('npm', True)
        
        # Filter cards based on both status and source
        filtered_cards = []
        for card_data in self._all_cards:
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check status filter
            status_match = (is_installed and show_installed) or (not is_installed and show_available)
            
            # Check source filter
            source = self._get_package_source(plugin).lower()
            source_match = False
            if source == 'pacman' and show_pacman:
                source_match = True
            elif source == 'aur' and show_aur:
                source_match = True
            elif source == 'flatpak' and show_flatpak:
                source_match = True
            elif source == 'npm' and show_npm:
                source_match = True
            
            # Include card only if both filters match
            if status_match and source_match:
                filtered_cards.append(card_data)
        
        # Use tracked column count
        cols = self._current_cols
        
        # Set column stretching dynamically
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        
        # Add filtered cards to layout and show them
        for i, card_data in enumerate(filtered_cards):
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)

# === components: plugins_sidebar.py ===
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QButtonGroup, QListWidget, QPushButton, QMenu
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction


class PluginsSidebar(QWidget):
    filter_changed = pyqtSignal(str, bool)  # search_text, installed_only
    install_requested = pyqtSignal(str)     # plugin_id
    uninstall_requested = pyqtSignal(str)   # plugin_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugins: list = []
        self._selected_cats: set = set()
        self.category_menu: Any = None
        self.category_btn: Any = None
        self._build()
        self._apply_style()

    def _build(self):
        self.setObjectName("pluginsSidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Extensions")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search extensions")
        self.search.textChanged.connect(lambda _text: self._emit())
        try:
            self.search.setClearButtonEnabled(True)
        except Exception:
            pass
        try:
            self.search.setFixedHeight(34)
        except Exception:
            pass
        self.search.setObjectName("searchBox")
        layout.addWidget(self.search)

        self.group = QButtonGroup(self)
        self.rb_all = QRadioButton("All")
        self.rb_installed = QRadioButton("Installed")
        self.group.addButton(self.rb_all, 0)
        self.group.addButton(self.rb_installed, 1)
        self.rb_all.setChecked(True)
        self.group.buttonClicked.connect(lambda _: self._emit())

        row = QHBoxLayout()
        row.addWidget(self.rb_all)
        row.addWidget(self.rb_installed)
        row.addStretch()
        layout.addLayout(row)
        
        # Categories dropdown (saves horizontal space)
        self.category_btn = QPushButton("Categories: All")
        self.category_menu = QMenu(self)
        self.category_btn.setMenu(self.category_menu)
        try:
            self.category_btn.setFixedHeight(34)
        except Exception:
            pass
        self.category_btn.setObjectName("categoryBtn")
        layout.addWidget(self.category_btn)

        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._on_select)
        try:
            self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        except Exception:
            pass
        try:
            self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        except Exception:
            pass
        try:
            self.list.setUniformItemSizes(True)
        except Exception:
            pass
        try:
            self.list.setSpacing(2)
        except Exception:
            pass
        self.list.setObjectName("pluginsList")
        layout.addWidget(self.list)
        
        self.install_btn = QPushButton("Install Selected")
        self.install_btn.clicked.connect(self._install_selected)
        try:
            self.install_btn.setFixedHeight(34)
        except Exception:
            pass
        self.install_btn.setObjectName("primaryBtn")
        layout.addWidget(self.install_btn)
        self.uninstall_btn = QPushButton("Uninstall Selected")
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        try:
            self.uninstall_btn.setFixedHeight(34)
        except Exception:
            pass
        self.uninstall_btn.setObjectName("dangerBtn")
        layout.addWidget(self.uninstall_btn)
        layout.addStretch()

    def _apply_style(self):
        try:
            self.setStyleSheet(self._style())
        except Exception:
            pass

    def _style(self):
        return (
            """
            QWidget#pluginsSidebar {
                background-color: transparent;
            }
            QLineEdit#searchBox {
                background-color: #151515;
                color: #F0F0F0;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                padding: 6px 10px;
            }
            QLineEdit#searchBox:focus {
                border: 1px solid #00BFAE;
                outline: none;
            }
            QPushButton#categoryBtn {
                background-color: #151515;
                color: #E0E0E0;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                padding: 6px 10px;
                text-align: left;
            }
            QPushButton#categoryBtn:hover {
                border-color: rgba(0,191,174,0.6);
            }
            QListWidget#pluginsList {
                background-color: #0f0f0f;
                color: #E0E0E0;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }
            QListWidget#pluginsList::item {
                padding: 6px 8px;
            }
            QListWidget#pluginsList::item:selected {
                background: rgba(0,191,174,0.15);
                color: #FFFFFF;
            }
            QPushButton#primaryBtn {
                background-color: #1a1a1a;
                color: #E0E0E0;
                border: 1px solid rgba(0,191,174,0.5);
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton#primaryBtn:hover {
                background-color: rgba(0,191,174,0.15);
                border-color: #00BFAE;
            }
            QPushButton#dangerBtn {
                background-color: #1a1a1a;
                color: #E0E0E0;
                border: 1px solid rgba(229,57,53,0.5);
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton#dangerBtn:hover {
                background-color: rgba(229,57,53,0.15);
                border-color: #E53935;
            }
            QRadioButton {
                color: #E0E0E0;
            }
            """
        )

    def set_plugins(self, plugins):
        self.plugins = plugins or []
        try:
            self.list.blockSignals(True)
            self.list.clear()
            for p in self.plugins:
                name = p.get('name') or p.get('id')
                self.list.addItem(name)
        finally:
            self.list.blockSignals(False)
    
    def set_categories(self, categories):
        # Build dropdown menu with checkable actions
        if self.category_menu is None:
            self.category_menu = QMenu(self)
            self.category_btn.setMenu(self.category_menu)
        self.category_menu.clear()
        self._selected_cats = set()
        if not categories:
            self._update_category_btn()
            return
        # Optional helper actions
        act_all = QAction("All Categories", self)
        act_all.triggered.connect(self._clear_categories)
        self.category_menu.addAction(act_all)
        self.category_menu.addSeparator()
        for cat in categories:
            action = QAction(cat, self)
            action.setCheckable(True)
            action.toggled.connect(lambda checked, c=cat: self._on_category_toggled(c, checked))
            self.category_menu.addAction(action)
        self._update_category_btn()
    
    def get_selected_categories(self):
        return list(self._selected_cats)

    def _on_category_toggled(self, cat, checked):
        if checked:
            self._selected_cats.add(cat)
        else:
            self._selected_cats.discard(cat)
        self._update_category_btn()
        self._emit()

    def _clear_categories(self):
        self._selected_cats.clear()
        # Uncheck all actions
        if self.category_menu:
            for act in self.category_menu.actions():
                if act.isCheckable():
                    act.setChecked(False)
        self._update_category_btn()
        self._emit()

    def _update_category_btn(self):
        if not self._selected_cats:
            self.category_btn.setText("Categories: All")
        else:
            # Show up to 2 names, then count
            cats = sorted(self._selected_cats)
            label = ", ".join(cats[:2]) + ("…" if len(cats) > 2 else "")
            self.category_btn.setText(f"Categories: {label}")

    def _emit(self):
        text = self.search.text().strip()
        installed_only = self.group.checkedId() == 1
        self.filter_changed.emit(text, installed_only)
    
    def _on_select(self, text):
        # Selecting an item narrows the filter to that name
        self.filter_changed.emit(text or "", self.group.checkedId() == 1)
    
    def _install_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        # Map back to id
        pid = None
        for p in self.plugins:
            n = p.get('name') or p.get('id')
            if n == name:
                pid = p.get('id')
                break
        if pid:
            self.install_requested.emit(pid)
    
    def _uninstall_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        pid = None
        for p in self.plugins:
            n = p.get('name') or p.get('id')
            if n == name:
                pid = p.get('id')
                break
        if pid:
            self.uninstall_requested.emit(pid)

# === components: settings_general.py ===
import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
                             QLabel, QCheckBox, QLineEdit, QPushButton, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt

class GeneralSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        # Add title with subtitle
        title = QLabel("General")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #ffffff; 
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)
        
        subtitle = QLabel("Configure basic application settings and preferences")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        """)
        self.layout.addWidget(subtitle)
        
        # Basic Settings
        basic_box = QGroupBox("Basic Settings")
        basic_box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #d0d0d0;
                font-size: 13px;
                spacing: 12px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 10px 14px;
                color: #e0e0e0;
                min-width: 150px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #0d7377;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QLabel {
                color: #a0a0a0;
            }
        """)
        grid = QGridLayout(basic_box)
        grid.setContentsMargins(16, 20, 16, 16)
        grid.setSpacing(12)

        # Auto check updates on launch
        self.cb_auto_check = QCheckBox("Auto check updates on launch")
        self.cb_auto_check.setChecked(bool(self.app.settings.get('auto_check_updates', True)))
        self.cb_auto_check.toggled.connect(lambda v: self.app.update_setting('auto_check_updates', v))
        grid.addWidget(self.cb_auto_check, 0, 0, 1, 2)

        # Include Local source
        self.cb_local = QCheckBox("Include Local source (custom scripts)")
        self.cb_local.setChecked(bool(self.app.settings.get('include_local_source', True)))
        self.cb_local.toggled.connect(lambda v: self.app.update_setting('include_local_source', v))
        grid.addWidget(self.cb_local, 1, 0, 1, 2)

        # Use npm user mode
        self.cb_npm = QCheckBox("Use npm user mode for global installs")
        self.cb_npm.setChecked(bool(self.app.settings.get('npm_user_mode', True)))
        self.cb_npm.toggled.connect(lambda v: self.app.update_setting('npm_user_mode', v))
        grid.addWidget(self.cb_npm, 2, 0, 1, 2)

        # AUR Helper selection
        grid.addWidget(QLabel("AUR Helper:"), 3, 0)
        self.aur_helper_combo = QComboBox()
        
        # Get available AUR helpers
        available_helpers = sys_utils.get_available_aur_helpers()
        
        # Add auto option first
        self.aur_helper_combo.addItem("Auto (detect available)", "auto")
        
        # Add all supported helpers (mark unavailable ones)
        for helper in ['yay', 'paru', 'trizen', 'pikaur']:
            if helper in available_helpers:
                self.aur_helper_combo.addItem(helper, helper)
            else:
                self.aur_helper_combo.addItem(f"{helper} (not installed)", helper)
        
        # Set current selection
        current_helper = self.app.settings.get('aur_helper', 'auto')
        index = self.aur_helper_combo.findData(current_helper)
        if index >= 0:
            self.aur_helper_combo.setCurrentIndex(index)
        
        self.aur_helper_combo.currentIndexChanged.connect(self.on_aur_helper_changed)
        grid.addWidget(self.aur_helper_combo, 3, 1)
        
        # Show currently detected helper
        detected_helper = sys_utils.get_aur_helper()
        if detected_helper:
            helper_status = QLabel(f"Currently using: {detected_helper}")
            helper_status.setStyleSheet("color: #888; font-size: 11px;")
            grid.addWidget(helper_status, 4, 1)
        else:
            helper_status = QLabel("No AUR helper detected")
            helper_status.setStyleSheet("color: #d9534f; font-size: 11px;")
            grid.addWidget(helper_status, 4, 1)

        self.layout.addWidget(basic_box)

        # Bundle Settings
        bundle_box = QGroupBox("Bundle Autosave")
        bundle_box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #d0d0d0;
                font-size: 13px;
                spacing: 12px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 12px 14px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0d7377;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0a5c5f;
            }
            QLabel {
                color: #a0a0a0;
            }
        """)
        pgrid = QGridLayout(bundle_box)
        pgrid.setContentsMargins(16, 20, 16, 16)
        pgrid.setSpacing(12)

        self.cb_bsave = QCheckBox("Autosave bundle to file")
        self.cb_bsave.setChecked(bool(self.app.settings.get('bundle_autosave', True)))
        self.cb_bsave.toggled.connect(lambda v: self.app.update_setting('bundle_autosave', v))
        pgrid.addWidget(self.cb_bsave, 0, 0, 1, 3)

        from_path = self.app.settings.get('bundle_autosave_path') or os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass

        self.path_edit = QLineEdit(from_path)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.on_browse_bundle_path)
        pgrid.addWidget(QLabel("Autosave path:"), 1, 0)
        pgrid.addWidget(self.path_edit, 1, 1)
        pgrid.addWidget(browse_btn, 1, 2)

        self.layout.addWidget(bundle_box)

        # Import/Export buttons
        btns = QHBoxLayout()
        btns.setSpacing(12)
        btn_export = QPushButton("Export Settings")
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_export.clicked.connect(self.app.export_settings)
        btn_import = QPushButton("Import Settings")
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_import.clicked.connect(self.app.import_settings)
        btns.addWidget(btn_export)
        btns.addWidget(btn_import)
        btns.addStretch()
        self.layout.addLayout(btns)

        self.layout.addStretch()

    def on_browse_bundle_path(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select Bundle Autosave Path",
                                           self.path_edit.text(), "Bundle JSON (*.json)")
        if path:
            self.path_edit.setText(path)
            self.app.update_setting('bundle_autosave_path', path)
    
    def on_aur_helper_changed(self, index):
        helper = self.aur_helper_combo.itemData(index)
        self.app.update_setting('aur_helper', helper)
        self.app.log(f"AUR helper preference set to: {helper}")

# === components: settings_auto_update.py ===
import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
                             QLabel, QCheckBox, QSpinBox, QPushButton)
from PyQt6.QtCore import Qt

class AutoUpdateSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        # Add title with subtitle
        title = QLabel("Auto Update")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #ffffff; 
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)
        
        subtitle = QLabel("Manage automatic updates and system snapshots")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        """)
        self.layout.addWidget(subtitle)
        
        # Auto Update Settings
        update_box = QGroupBox("Auto Update")
        update_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 12px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QSpinBox:focus {
                border-color: #0d7377;
            }
            QLabel {
                color: #b0b0b0;
            }
        """)
        auto_grid = QGridLayout(update_box)
        auto_grid.setContentsMargins(16, 20, 16, 16)
        auto_grid.setSpacing(12)

        self.cb_auto_update = QCheckBox("Enable automatic updates")
        self.cb_auto_update.setChecked(bool(self.app.settings.get('auto_update_enabled', False)))
        self.cb_auto_update.toggled.connect(lambda v: self.app.update_setting('auto_update_enabled', v))
        auto_grid.addWidget(self.cb_auto_update, 0, 0, 1, 2)

        auto_grid.addWidget(QLabel("Update interval (days):"), 1, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 30)  # 1 day to 30 days
        self.interval_spin.setValue(int(self.app.settings.get('auto_update_interval_days', 1)))
        self.interval_spin.valueChanged.connect(lambda v: self.app.update_setting('auto_update_interval_days', v))
        auto_grid.addWidget(self.interval_spin, 1, 1)

        self.layout.addWidget(update_box)

        # Snapshot Settings
        snapshot_box = QGroupBox("Snapshots")
        snapshot_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 600;
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: transparent;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(13, 115, 119, 0.6);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
            QPushButton {
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        snap_grid = QGridLayout(snapshot_box)
        snap_grid.setContentsMargins(16, 20, 16, 16)
        snap_grid.setSpacing(12)

        self.cb_snapshot = QCheckBox("Create snapshot before updates")
        self.cb_snapshot.setChecked(bool(self.app.settings.get('snapshot_before_update', False)))
        self.cb_snapshot.toggled.connect(lambda v: self.app.update_setting('snapshot_before_update', v))
        snap_grid.addWidget(self.cb_snapshot, 0, 0, 1, 2)

        snap_btns = QHBoxLayout()
        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.clicked.connect(self.app.create_snapshot)
        snap_btns.addWidget(create_snap_btn)

        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.clicked.connect(self.app.revert_to_snapshot)
        snap_btns.addWidget(revert_snap_btn)

        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.clicked.connect(self.app.delete_snapshots)
        snap_btns.addWidget(delete_snap_btn)

        snap_btns.addStretch()
        snap_grid.addLayout(snap_btns, 1, 0, 1, 2)

        self.layout.addWidget(snapshot_box)

        self.layout.addStretch()

# === components: settings_plugins.py ===
import os
from typing import Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QPushButton, QLabel, QTabWidget,
                             QMessageBox, QCheckBox, QDialog, QLineEdit, QTextEdit,
                             QComboBox, QFileDialog, QFormLayout)
from PyQt6.QtCore import Qt

class PluginsSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.setup_ui()

    def setup_ui(self):
        # Add title with subtitle
        title = QLabel("Plugins")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #ffffff; 
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        """)
        self.layout.addWidget(title)
        
        subtitle = QLabel("Manage installed plugins and extensions")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        """)
        self.layout.addWidget(subtitle)
        
        # Create tab widget for Core Plugins and Community Hub
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background-color: rgba(255, 255, 255, 0.03);
                margin-top: 12px;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #888;
                padding: 14px 28px;
                margin-right: 6px;
                border-radius: 8px 8px 0 0;
                font-weight: 500;
                font-size: 14px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
                color: #ffffff;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
        """)
        
        # Core Plugins Tab
        core_tab = QWidget()
        core_layout = QVBoxLayout(core_tab)
        core_layout.setContentsMargins(16, 16, 16, 16)
        core_layout.setSpacing(12)
        
        # Core plugins actions
        core_actions = QHBoxLayout()
        btn_reload = QPushButton("Reload Plugins")
        btn_reload.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_reload.clicked.connect(self.app.reload_plugins_and_notify)
        core_actions.addWidget(btn_reload)
        core_actions.addStretch()
        core_layout.addLayout(core_actions)
        
        # Core Plugins Table
        self.core_plugins_table = QTableWidget()
        self.core_plugins_table.setColumnCount(3)
        self.core_plugins_table.setHorizontalHeaderLabels(["Enabled", "Plugin", "Location"])
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.core_plugins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.core_plugins_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #e0e0e0;
                selection-background-color: rgba(13, 115, 119, 0.3);
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QTableWidget::item:selected {
                background-color: rgba(13, 115, 119, 0.25);
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
                font-size: 13px;
            }
        """)
        core_layout.addWidget(self.core_plugins_table)
        
        # Community Hub Tab
        community_tab = QWidget()
        community_layout = QVBoxLayout(community_tab)
        community_layout.setContentsMargins(16, 16, 16, 16)
        community_layout.setSpacing(12)
        
        # Community hub actions
        community_actions = QHBoxLayout()
        btn_add = QPushButton("Upload Plugin")
        btn_add.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0a5c5f;
            }
        """)
        btn_add.clicked.connect(self.show_upload_plugin_form)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #d9534f;
                border: 1px solid rgba(217, 83, 79, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(217, 83, 79, 0.15);
                border-color: #d9534f;
            }
        """)
        btn_remove.clicked.connect(self.app.remove_selected_plugins)
        btn_go_plugins = QPushButton("Browse Community")
        btn_go_plugins.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: transparent;
                color: #0d7377;
                border: 1px solid rgba(13, 115, 119, 0.4);
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(13, 115, 119, 0.15);
                border-color: #0d7377;
            }
        """)
        btn_go_plugins.clicked.connect(self.go_to_plugins_page)
        
        community_actions.addWidget(btn_add)
        community_actions.addWidget(btn_remove)
        community_actions.addWidget(btn_go_plugins)
        community_actions.addStretch()
        community_layout.addLayout(community_actions)
        
        # Community Packages Table (repurpose the existing table)
        self.community_plugins_table = QTableWidget()
        self.community_plugins_table.setColumnCount(3)
        self.community_plugins_table.setHorizontalHeaderLabels(["Select", "Package Name", "Source"])
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.community_plugins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.community_plugins_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #e0e0e0;
                selection-background-color: rgba(13, 115, 119, 0.3);
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QTableWidget::item:selected {
                background-color: rgba(13, 115, 119, 0.25);
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
                font-size: 13px;
            }
        """)
        
        community_layout.addWidget(self.community_plugins_table)
        
        # Add tabs to tab widget
        self.tabs.addTab(core_tab, "Core Plugins")
        self.tabs.addTab(community_tab, "Community Hub")
        
        self.layout.addWidget(self.tabs)
        
        # Initialize tables
        self.refresh_plugins_table()
        self.core_plugins_table.itemChanged.connect(self.on_plugin_item_changed)
        
        # Initialize community bundles
        self.refresh_community_bundles()

    def refresh_plugins_table(self):
        self._plugins_populating = True
        plugs = self.app.scan_plugins()
        enabled = set(self.app.settings.get('enabled_plugins') or [])
        self.core_plugins_table.setRowCount(0)

        for p in plugs:
            row = self.core_plugins_table.rowCount()
            self.core_plugins_table.insertRow(row)

            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            enabled_item.setCheckState(Qt.CheckState.Checked if p['name'] in enabled else Qt.CheckState.Unchecked)
            name_item = QTableWidgetItem(p['name'])
            loc_item = QTableWidgetItem(p.get('location', 'Core'))

            self.core_plugins_table.setItem(row, 0, enabled_item)
            self.core_plugins_table.setItem(row, 1, name_item)
            self.core_plugins_table.setItem(row, 2, loc_item)

        self._plugins_populating = False

    def on_plugin_item_changed(self, item):
        if getattr(self, '_plugins_populating', False):
            return
        if item.column() != 0:
            return

        row = item.row()
        name_item = self.core_plugins_table.item(row, 1)
        if not name_item:
            return

        name = name_item.text().strip()
        enabled = set(self.app.settings.get('enabled_plugins') or [])

        if item.checkState() == Qt.CheckState.Checked:
            enabled.add(name)
        else:
            enabled.discard(name)

        self.app.settings['enabled_plugins'] = sorted(enabled)
        self.app.save_settings()

    def remove_selected_plugins(self):
        """Remove selected plugins from the table and filesystem"""
        rows = self.plugins_table.selectionModel().selectedRows()
        if not rows:
            return
        
        removed = 0
        for mi in rows:
            r = mi.row()
            name_item = self.plugins_table.item(r, 1)
            if not name_item:
                continue
            name = name_item.text().strip()
            path = os.path.join(self.app.get_user_plugins_dir(), name + '.py')
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed += 1
                enabled = set(self.app.settings.get('enabled_plugins') or [])
                enabled.discard(name)
                self.app.settings['enabled_plugins'] = sorted(enabled)
            except Exception:
                pass
        
        self.app.save_settings()
        self.refresh_plugins_table()
        if removed > 0:
            self.app._show_message("Remove Plugins", f"Removed {removed} plugin(s)")

    def go_to_plugins_page(self):
        """Switch to the main plugins page"""
        try:
            self.app.switch_view("plugins")
        except Exception as e:
            print(f"Could not switch to plugins page: {e}")

    def refresh_community_bundles(self):
        """Refresh the community packages display"""
        try:
            pass  # inlined
            
            # Clear existing packages
            self.community_plugins_table.setRowCount(0)
            
            # Load community bundles and extract all packages
            bundles = list_community_bundles()
            all_packages = []
            
            # Extract all packages from all bundles
            for bundle_data in bundles:
                items = bundle_data.get('items', [])
                for item in items:
                    if isinstance(item, dict) and item.get('name') and item.get('source'):
                        all_packages.append(item)
            
            if not all_packages:
                # Add a single row with message
                self.community_plugins_table.setRowCount(1)
                message_item = QTableWidgetItem("No community packages found. Share bundles from the Bundle page to see them here!")
                message_item.setFlags(message_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(0, 1, message_item)
                self.community_plugins_table.setSpan(0, 1, 1, 2)  # Span across remaining columns
                return
            
            # Remove duplicates while preserving order
            seen = set()
            unique_packages = []
            for pkg in all_packages:
                key = (pkg.get('name'), pkg.get('source'))
                if key not in seen:
                    seen.add(key)
                    unique_packages.append(pkg)
            
            # Populate table with packages
            self.community_plugins_table.setRowCount(len(unique_packages))
            
            for row, package in enumerate(unique_packages):
                # Checkbox column
                checkbox = QCheckBox()
                checkbox.setObjectName("packageCheckbox")
                cb_container = QWidget()
                cb_container.setStyleSheet("background: transparent;")
                cb_layout = QHBoxLayout(cb_container)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                cb_layout.addStretch()
                cb_layout.addWidget(checkbox)
                cb_layout.addStretch()
                self.community_plugins_table.setCellWidget(row, 0, cb_container)
                
                # Package name
                name_item = QTableWidgetItem(package.get('name', 'Unknown Package'))
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(row, 1, name_item)
                
                # Source
                source_item = QTableWidgetItem(package.get('source', 'Unknown'))
                source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.community_plugins_table.setItem(row, 2, source_item)
                
        except Exception as e:
            # Show error in table
            self.community_plugins_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Error loading community packages: {str(e)}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.community_plugins_table.setItem(0, 1, error_item)
            self.community_plugins_table.setSpan(0, 1, 1, 2)

    def show_upload_plugin_form(self):
        """Show the upload plugin form dialog"""
        # Get selected packages from the community table
        selected_packages = self.get_selected_community_packages()
        if not selected_packages:
            QMessageBox.information(self, "No Selection", "Please select packages from the table first.")
            return
        
        dialog = UploadPluginDialog(self, selected_packages)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the form data
            plugin_data = dialog.get_plugin_data()
            if plugin_data:
                self.upload_plugin_to_community(plugin_data)

    def get_selected_community_packages(self):
        """Get selected packages from the community table"""
        selected_packages = []
        for row in range(self.community_plugins_table.rowCount()):
            checkbox_widget = self.community_plugins_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    name_item = self.community_plugins_table.item(row, 1)
                    source_item = self.community_plugins_table.item(row, 2)
                    if name_item and source_item:
                        selected_packages.append({
                            'name': name_item.text(),
                            'source': source_item.text()
                        })
        return selected_packages

    def upload_plugin_to_community(self, plugin_data):
        """Upload the plugin data to community"""
        try:
            # Here you would implement the actual upload logic
            # For now, just show a success message
            QMessageBox.information(self, "Upload Successful", 
                                  f"Plugin '{plugin_data['name']}' uploaded successfully!\n\n"
                                  f"Category: {plugin_data['category']}\n"
                                  f"Logo: {plugin_data['logo_path'] if plugin_data['logo_path'] else 'No logo'}")
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to upload plugin: {str(e)}")


class UploadPluginDialog(QDialog):
    """Dialog for uploading plugins to the community"""
    
    def __init__(self, parent=None, selected_packages=None):
        super().__init__(parent)
        self.selected_packages = selected_packages or []
        self.setWindowTitle("Upload Plugin to Community")
        self.setFixedSize(480, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
            }
            QLabel {
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                font-size: 13px;
                selection-background-color: #0d7377;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0d7377;
                background-color: #2f2f2f;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #777777;
            }
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #0d7377;
                background-color: #2f2f2f;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #444444;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #333333;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                border: 1px solid #0d7377;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: #0d7377;
                outline: none;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 500;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0a5c5f;
            }
            QPushButton:pressed {
                background-color: #085a5d;
            }
        """)
        
        self.logo_path = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Upload Plugin to Community")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #ffffff; 
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Selected packages info
        if self.selected_packages:
            packages_text = f"Selected {len(self.selected_packages)} package(s): {', '.join([pkg['name'] for pkg in self.selected_packages[:3]])}"
            if len(self.selected_packages) > 3:
                packages_text += f" and {len(self.selected_packages) - 3} more..."
            
            packages_info = QLabel(packages_text)
            packages_info.setStyleSheet("""
                color: #0d7377; 
                font-size: 12px; 
                font-weight: 500;
                background-color: rgba(13, 115, 119, 0.15);
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid rgba(13, 115, 119, 0.3);
            """)
            packages_info.setWordWrap(True)
            layout.addWidget(packages_info)
        
        # Form fields
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Plugin name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter plugin name...")
        form_layout.addRow("Plugin Name:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter plugin description...")
        self.description_input.setMaximumHeight(70)
        form_layout.addRow("Description:", self.description_input)
        
        # Category
        self.category_combo = QComboBox()
        categories = [
            "System", "Office", "Development", "Internet", "Multimedia",
            "Graphics", "Games", "Education", "Utilities", "Customization",
            "Security", "Lifestyle"
        ]
        self.category_combo.addItems(categories)
        form_layout.addRow("Category:", self.category_combo)
        
        # Version and Author
        version_author_layout = QHBoxLayout()
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("1.0.0")
        self.version_input.setText("1.0.0")
        
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Enter author name...")
        
        version_author_layout.addWidget(self.version_input)
        version_author_layout.addWidget(self.author_input)
        
        version_author_widget = QWidget()
        version_author_widget.setLayout(version_author_layout)
        form_layout.addRow("Version / Author:", version_author_widget)
        
        layout.addLayout(form_layout)
        
        # Logo section
        logo_layout = QHBoxLayout()
        logo_label = QLabel("Plugin Logo (Optional - Max 1MB):")
        logo_layout.addWidget(logo_label)
        
        self.logo_button = QPushButton("Choose Logo")
        self.logo_button.clicked.connect(self.choose_logo)
        logo_layout.addWidget(self.logo_button)
        
        self.logo_status = QLabel("No logo selected")
        self.logo_status.setStyleSheet("color: #777777; font-size: 12px;")
        logo_layout.addWidget(self.logo_status)
        logo_layout.addStretch()
        
        layout.addLayout(logo_layout)
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        upload_btn = QPushButton("Upload Plugin")
        upload_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(upload_btn)
        
        layout.addLayout(buttons_layout)
    
    def choose_logo(self):
        """Choose logo file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Choose Plugin Logo", 
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.svg *.gif);;All Files (*)"
        )
        
        if file_path:
            # Check file size (1MB = 1048576 bytes)
            file_size = os.path.getsize(file_path)
            if file_size > 1048576:  # 1MB
                QMessageBox.warning(self, "File Too Large", 
                                  f"Logo file is {file_size / 1048576:.1f}MB. Please choose a file smaller than 1MB.")
                return
            
            self.logo_path = file_path
            filename = os.path.basename(file_path)
            size_mb = file_size / 1048576
            self.logo_status.setText(f"✓ {filename} ({size_mb:.2f}MB)")
            self.logo_status.setStyleSheet("color: #0d7377; font-weight: normal;")
    
    def get_plugin_data(self):
        """Get the plugin data from the form"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Please enter a plugin name.")
            return None
        
        return {
            'name': name,
            'description': self.description_input.toPlainText().strip(),
            'category': self.category_combo.currentText(),
            'version': self.version_input.text().strip() or "1.0.0",
            'author': self.author_input.text().strip() or "Unknown",
            'logo_path': self.logo_path,
            'selected_packages': self.selected_packages
        }



# === components: about_dialog.py ===
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

# === components: community_plugins.py ===
"""
Community Plugins Browser
Allows users to discover, install, and share plugins from the community
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QLineEdit,
                             QMessageBox, QProgressBar, QGroupBox, QListWidget, QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QTimer
from PyQt6.QtGui import QGuiApplication
from typing import Any
import os

 
try:
    from supabase_store import SupabasePluginStore
except Exception:
    SupabasePluginStore = None  # type: ignore
try:
    pass  # inlined
except Exception:
    MongoPluginStore = None  # type: ignore

class CommunityPluginCard(QFrame):
    """Card displaying a community plugin"""

    def __init__(self, plugin_info: dict, on_install, on_view_details, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.on_install = on_install
        self.on_view_details = on_view_details

        self.setObjectName("communityPluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(self._style())
        self.setMinimumHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header with title, author, and version (no image)
        header = QHBoxLayout()
        title = QLabel(plugin_info.get('name', 'Unknown Plugin'))
        title.setObjectName("pluginTitle")
        header.addWidget(title)
        author = QLabel(f"by {plugin_info.get('author', 'Unknown')}")
        author.setObjectName("pluginAuthor")
        author.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(author)
        header.addStretch()
        ver = QLabel(f"v{plugin_info.get('version', '1.0.0')}")
        ver.setStyleSheet("color: #666; font-size: 10px;")
        header.addWidget(ver)
        layout.addLayout(header)

        # Description
        desc = QLabel(plugin_info.get('description', ''))
        desc.setObjectName("pluginDesc")
        desc.setWordWrap(True)
        desc.setMaximumHeight(32)
        layout.addWidget(desc)

        # Footer with actions
        footer = QHBoxLayout()
        footer.addStretch()

        # Buttons
        details_btn = QPushButton("Details")
        details_btn.setFixedWidth(54)
        details_btn.clicked.connect(lambda: self.on_view_details(self.plugin_info))
        footer.addWidget(details_btn)

        install_btn = QPushButton("Install")
        install_btn.setFixedWidth(54)
        install_btn.clicked.connect(lambda: self.on_install(self.plugin_info))
        footer.addWidget(install_btn)

        layout.addLayout(footer)

    def _style(self):
        return """
        QFrame#communityPluginCard {
            background-color: #1a1a1a;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        QLabel#pluginTitle {
            color: #F0F0F0;
            font-size: 10px;
            font-weight: 600;
        }
        QLabel#pluginDesc {
            color: #A0A0A0;
            font-size: 9px;
            line-height: 1.3;
        }
        QPushButton {
            background-color: transparent;
            color: #00BFAE;
            border: 1px solid #00BFAE;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 9px;
        }
        QPushButton:hover {
            background-color: rgba(0, 191, 174, 0.1);
        }
        """

class PluginDetailsDialog(QFrame):
    """Dialog showing detailed plugin information"""

    def __init__(self, plugin_info: dict, on_install, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.on_install = on_install

        self.setObjectName("pluginDetailsDialog")
        self.setStyleSheet(self._dialog_style())
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel(plugin_info.get('name', 'Plugin Details'))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Info grid
        info_layout = QGridLayout()
        info_layout.setSpacing(8)

        labels = ["Author:", "Version:", "Downloads:", "Last Updated:"]
        values = [
            plugin_info.get('author', 'Unknown'),
            plugin_info.get('version', '1.0.0'),
            str(plugin_info.get('downloads', 0)),
            plugin_info.get('last_updated', 'Unknown')
        ]

        for i, (label, value) in enumerate(zip(labels, values)):
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; color: #CCC;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #FFF;")

            info_layout.addWidget(label_widget, i, 0)
            info_layout.addWidget(value_widget, i, 1)

        layout.addLayout(info_layout)

        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        desc_text = QTextEdit()
        desc_text.setPlainText(plugin_info.get('description', 'No description available.'))
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(100)
        desc_layout.addWidget(desc_text)
        layout.addWidget(desc_group)

        # Features (if available)
        if plugin_info.get('features'):
            features_group = QGroupBox("Features")
            features_layout = QVBoxLayout(features_group)
            features_text = QLabel('\n'.join(f"• {f}" for f in plugin_info['features']))
            features_text.setWordWrap(True)
            features_layout.addWidget(features_text)
            layout.addWidget(features_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        install_btn = QPushButton("Install Plugin")
        install_btn.clicked.connect(lambda: self.on_install(self.plugin_info))
        button_layout.addWidget(install_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _dialog_style(self):
        return """
        QFrame#pluginDetailsDialog {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #444;
        }
        QLabel#dialogTitle {
            color: #FFF;
            font-size: 18px;
            font-weight: bold;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }
        QPushButton {
            background-color: #00BFAE;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #00A090;
        }
        """

class PluginCreatorDialog(QFrame):
    """Dialog for creating new plugins"""

    def __init__(self, plugin_store, on_plugin_created, parent=None):
        super().__init__(parent)
        self.plugin_store = plugin_store
        self.on_plugin_created = on_plugin_created

        self.setObjectName("pluginCreatorDialog")
        self.setStyleSheet(self._dialog_style())
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel("Create New Plugin")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel("Fill in the details below to create a plugin template")
        subtitle.setStyleSheet("color: #AAA;")
        layout.addWidget(subtitle)

        # Form
        form_layout = QGridLayout()
        form_layout.setSpacing(8)

        # Plugin name
        name_label = QLabel("Plugin Name:")
        name_label.setStyleSheet("font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Awesome Plugin")

        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setPlaceholderText("What does your plugin do?")

        form_layout.addWidget(name_label, 0, 0)
        form_layout.addWidget(self.name_input, 0, 1)
        form_layout.addWidget(desc_label, 1, 0)
        form_layout.addWidget(self.desc_input, 1, 1)

        layout.addLayout(form_layout)

        # Template preview
        template_group = QGroupBox("Generated Template")
        template_layout = QVBoxLayout(template_group)
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setFontFamily("Monospace")
        self.template_preview.setStyleSheet("font-size: 10px;")
        template_layout.addWidget(self.template_preview)
        layout.addWidget(template_group)

        # Update preview when inputs change
        self.name_input.textChanged.connect(self.update_preview)
        self.desc_input.textChanged.connect(self.update_preview)

        # Set initial preview
        self.update_preview()

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        create_btn = QPushButton("Create Plugin")
        create_btn.clicked.connect(self.create_plugin)
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.hide)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def update_preview(self):
        """Update the template preview"""
        name = self.name_input.text().strip() or "My Plugin"
        desc = self.desc_input.toPlainText().strip() or "A plugin that does amazing things"

        template = self.plugin_store.create_plugin_template(name, desc)
        self.template_preview.setPlainText(template)

    def create_plugin(self):
        """Create and save the plugin"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a plugin name.")
            return

        desc = self.desc_input.toPlainText().strip()
        template = self.plugin_store.create_plugin_template(name, desc)

        # Save to plugins directory
        filename = name.lower().replace(' ', '_').replace('-', '_') + '.py'
        plugin_path = self.plugin_store.plugins_dir / filename

        try:
            with open(plugin_path, 'w') as f:
                f.write(template)

            QMessageBox.information(self, "Success",
                                  f"Plugin template created!\n\nSaved to: {plugin_path}\n\n"
                                  "You can now edit the plugin and enable it in Settings → Plugins.")

            if self.on_plugin_created:
                self.on_plugin_created(plugin_path)

            self.hide()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create plugin: {e}")

    def _dialog_style(self):
        return """
        QFrame#pluginCreatorDialog {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #444;
        }
        QLabel#dialogTitle {
            color: #FFF;
            font-size: 18px;
            font-weight: bold;
        }
        QLineEdit, QTextEdit {
            background-color: #1a1a1a;
            border: 1px solid #555;
            border-radius: 4px;
            color: #FFF;
            padding: 4px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QPushButton {
            background-color: #00BFAE;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #00A090;
        }
        """

class CommunityPluginsTab(QWidget):
    """Community plugins discovery and sharing tab"""

    plugin_installed = pyqtSignal(str)  # plugin_id

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.plugin_store: Any = None
        self._is_supabase = False
        self._is_mongo = False
        try:
            if MongoPluginStore is not None:
                m = MongoPluginStore()
                if m.is_configured():
                    self.plugin_store = m
                    self._is_mongo = True
        except Exception:
            self.plugin_store = None
        if self.plugin_store is None:
            try:
                if SupabasePluginStore is not None:
                    s = SupabasePluginStore()
                    if s.is_configured():
                        self.plugin_store = s
                        self._is_supabase = True
            except Exception:
                self.plugin_store = None
        if self.plugin_store is None:
            self.plugin_store = PluginStore()
        self.community_plugins = []
        self.details_dialog = None
        self.creator_dialog = None
        self.my_plugins = []
        self._selected_my_id = None
        self._setup_status = None

        self._init_ui()
        self.refresh_plugins()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with title and refresh button
        header = QHBoxLayout()

        title = QLabel("Community Plugins")
        title.setObjectName("sectionLabel")
        header.addWidget(title)

        header.addStretch()

        # Action buttons
        create_btn = QPushButton("Create Plugin")
        create_btn.clicked.connect(self.show_plugin_creator)
        header.addWidget(create_btn)

        submit_btn = QPushButton("Submit Plugin")
        submit_btn.clicked.connect(self.submit_plugin)
        header.addWidget(submit_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_plugins)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        if self._is_supabase:
            self.onboarding_group = QGroupBox("Supabase Setup Required")
            ob_layout = QVBoxLayout(self.onboarding_group)
            self.ob_text = QLabel("Your Supabase project is missing required objects. Use the buttons below to copy SQL and run it in the Supabase SQL editor, and create two storage buckets: plugin-icons and plugin-files.")
            self.ob_text.setWordWrap(True)
            ob_layout.addWidget(self.ob_text)
            btns = QHBoxLayout()
            self.btn_copy_sql = QPushButton("Copy Table + RLS SQL")
            self.btn_copy_sql.clicked.connect(self._copy_sql_setup)
            self.btn_copy_storage = QPushButton("Copy Storage Policies SQL")
            self.btn_copy_storage.clicked.connect(self._copy_storage_policies)
            btns.addWidget(self.btn_copy_sql)
            btns.addWidget(self.btn_copy_storage)
            btns.addStretch()
            ob_layout.addLayout(btns)
            layout.addWidget(self.onboarding_group)
            self.onboarding_group.setVisible(False)
            auth_row = QHBoxLayout()
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText("Email")
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("Password")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_login = QPushButton("Login")
            self.btn_signup = QPushButton("Sign up")
            self.btn_logout = QPushButton("Logout")
            self.btn_login.clicked.connect(self.sign_in)
            self.btn_signup.clicked.connect(self.sign_up)
            self.btn_logout.clicked.connect(self.sign_out)
            auth_row.addWidget(self.email_input)
            auth_row.addWidget(self.password_input)
            auth_row.addWidget(self.btn_login)
            auth_row.addWidget(self.btn_signup)
            auth_row.addWidget(self.btn_logout)
            auth_row.addStretch()
            layout.addLayout(auth_row)

        # Progress bar for loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setSpacing(6)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)

        if self._is_supabase:
            self.my_group = QGroupBox("My Plugins")
            my_layout = QHBoxLayout(self.my_group)
            self.my_list = QListWidget()
            self.my_list.currentTextChanged.connect(self._on_my_select)
            my_layout.addWidget(self.my_list, 1)

            form_col = QVBoxLayout()
            form_grid = QGridLayout()
            form_grid.setSpacing(6)
            self.input_id = QLineEdit()
            self.input_name = QLineEdit()
            self.input_version = QLineEdit()
            self.input_author = QLineEdit()
            self.input_desc = QTextEdit()
            self.input_desc.setMaximumHeight(80)
            self.input_cats = QLineEdit()
            self.icon_path = QLineEdit()
            self.file_path = QLineEdit()
            btn_browse_icon = QPushButton("Browse Icon")
            btn_browse_icon.clicked.connect(self._browse_icon)
            btn_browse_file = QPushButton("Browse File")
            btn_browse_file.clicked.connect(self._browse_file)
            form_grid.addWidget(QLabel("ID"), 0, 0)
            form_grid.addWidget(self.input_id, 0, 1)
            form_grid.addWidget(QLabel("Name"), 1, 0)
            form_grid.addWidget(self.input_name, 1, 1)
            form_grid.addWidget(QLabel("Version"), 2, 0)
            form_grid.addWidget(self.input_version, 2, 1)
            form_grid.addWidget(QLabel("Author"), 3, 0)
            form_grid.addWidget(self.input_author, 3, 1)
            form_grid.addWidget(QLabel("Categories (comma)"), 4, 0)
            form_grid.addWidget(self.input_cats, 4, 1)
            form_grid.addWidget(QLabel("Description"), 5, 0)
            form_grid.addWidget(self.input_desc, 5, 1)
            form_grid.addWidget(QLabel("Icon"), 6, 0)
            row6 = QHBoxLayout()
            row6.addWidget(self.icon_path, 1)
            row6.addWidget(btn_browse_icon)
            form_col.addLayout(form_grid)
            form_col.addLayout(row6)
            form_grid2 = QGridLayout()
            form_grid2.addWidget(QLabel("Plugin File (.py)"), 0, 0)
            rowf = QHBoxLayout()
            rowf.addWidget(self.file_path, 1)
            rowf.addWidget(btn_browse_file)
            form_col.addLayout(form_grid2)
            form_col.addLayout(rowf)
            btn_row = QHBoxLayout()
            self.btn_new = QPushButton("New")
            self.btn_save = QPushButton("Save")
            self.btn_delete = QPushButton("Delete")
            self.btn_reload_my = QPushButton("Reload")
            self.btn_new.clicked.connect(self._reset_my_form)
            self.btn_save.clicked.connect(self._save_my_plugin)
            self.btn_delete.clicked.connect(self._delete_my_plugin)
            self.btn_reload_my.clicked.connect(self._load_my_plugins)
            btn_row.addWidget(self.btn_new)
            btn_row.addWidget(self.btn_save)
            btn_row.addWidget(self.btn_delete)
            btn_row.addWidget(self.btn_reload_my)
            btn_row.addStretch()
            form_col.addLayout(btn_row)
            my_layout.addLayout(form_col, 2)
            layout.addWidget(self.my_group)
            self._update_auth_ui()
            self._update_onboarding_panel()

    def refresh_plugins(self):
        """Refresh the list of community plugins"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Clear existing plugins
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add loading message
        loading_label = QLabel("Loading community plugins...")
        loading_label.setStyleSheet("color: #AAA; font-style: italic;")
        self.grid_layout.addWidget(loading_label, 0, 0, 1, 5, Qt.AlignmentFlag.AlignCenter)

        # Load plugins in background
        QTimer.singleShot(100, self._load_plugins_async)

        if self._is_supabase:
            QTimer.singleShot(150, self._load_my_plugins)
            QTimer.singleShot(50, self._update_onboarding_panel)

    def _load_plugins_async(self):
        """Load plugins asynchronously"""
        try:
            self.community_plugins = self.plugin_store.discover_plugins()
            self._display_plugins()
        except Exception as e:
            self._show_error(f"Failed to load community plugins: {e}")
            self.progress_bar.setVisible(False)

    def _update_auth_ui(self):
        if not self._is_supabase:
            return
        try:
            uid = self.plugin_store.current_user_id()
        except Exception:
            uid = None
        logged_in = bool(uid)
        self.btn_logout.setVisible(logged_in)
        self.btn_login.setVisible(not logged_in)
        self.btn_signup.setVisible(not logged_in)
        self.email_input.setVisible(not logged_in)
        self.password_input.setVisible(not logged_in)
        if hasattr(self, "my_group"):
            self.my_group.setVisible(logged_in)

    def _update_onboarding_panel(self):
        if not self._is_supabase:
            return
        try:
            status = self.plugin_store.get_setup_status()
        except Exception:
            status = None
        self._setup_status = status
        if not status:
            if hasattr(self, 'onboarding_group'):
                self.onboarding_group.setVisible(False)
            return
        missing = (not status.get('has_plugins_table')) or (not status.get('has_increment_fn'))
        if hasattr(self, 'onboarding_group'):
            self.onboarding_group.setVisible(bool(missing))
            if missing:
                parts = []
                if not status.get('has_plugins_table'):
                    parts.append("plugins table")
                if not status.get('has_increment_fn'):
                    parts.append("increment_downloads function")
                self.ob_text.setText("Missing: " + ", ".join(parts) + ". Copy SQL and run in Supabase SQL editor, and create buckets plugin-icons and plugin-files.")

    def _copy_sql_setup(self):
        try:
            QGuiApplication.clipboard().setText(self._get_sql_setup())
            QMessageBox.information(self, "Copied", "SQL copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _copy_storage_policies(self):
        try:
            QGuiApplication.clipboard().setText(self._get_sql_storage())
            QMessageBox.information(self, "Copied", "Storage SQL copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _get_sql_setup(self) -> str:
        return (
            "create table if not exists public.plugins (\n"
            "  id text primary key,\n"
            "  name text not null,\n"
            "  description text,\n"
            "  version text default '1.0.0' not null,\n"
            "  author text not null,\n"
            "  categories text[] default '{}',\n"
            "  icon_url text,\n"
            "  file_url text not null,\n"
            "  downloads bigint default 0 not null,\n"
            "  created_by uuid not null references auth.users(id) on delete cascade,\n"
            "  created_at timestamptz not null default now(),\n"
            "  updated_at timestamptz not null default now(),\n"
            "  constraint id_slug check (id ~ '^[a-z0-9_]+$')\n"
            ");\n\n"
            "create or replace function public.set_updated_at() returns trigger language plpgsql as $$\n"
            "begin new.updated_at = now(); return new; end; $$;\n"
            "drop trigger if exists trg_plugins_set_updated_at on public.plugins;\n"
            "create trigger trg_plugins_set_updated_at before update on public.plugins for each row execute function public.set_updated_at();\n\n"
            "alter table public.plugins enable row level security;\n"
            "drop policy if exists \"plugins_select_all\" on public.plugins;\n"
            "create policy \"plugins_select_all\" on public.plugins for select to public using (true);\n"
            "drop policy if exists \"plugins_insert_owner\" on public.plugins;\n"
            "create policy \"plugins_insert_owner\" on public.plugins for insert to authenticated with check (created_by = auth.uid());\n"
            "drop policy if exists \"plugins_update_owner\" on public.plugins;\n"
            "create policy \"plugins_update_owner\" on public.plugins for update to authenticated using (created_by = auth.uid()) with check (created_by = auth.uid());\n"
            "drop policy if exists \"plugins_delete_owner\" on public.plugins;\n"
            "create policy \"plugins_delete_owner\" on public.plugins for delete to authenticated using (created_by = auth.uid());\n\n"
            "create or replace function public.increment_downloads(p_id text) returns void language plpgsql security definer as $$\n"
            "begin update public.plugins set downloads = downloads + 1, updated_at = now() where id = p_id; end; $$;\n"
            "revoke all on function public.increment_downloads(text) from public;\n"
            "grant execute on function public.increment_downloads(text) to anon, authenticated;\n"
        )

    def _get_sql_storage(self) -> str:
        return (
            "create policy if not exists \"icons_read_public\" on storage.objects for select to public using (bucket_id = 'plugin-icons');\n"
            "create policy if not exists \"files_read_public\" on storage.objects for select to public using (bucket_id = 'plugin-files');\n"
            "create policy if not exists \"icons_insert_auth\" on storage.objects for insert to authenticated with check (bucket_id = 'plugin-icons');\n"
            "create policy if not exists \"files_insert_auth\" on storage.objects for insert to authenticated with check (bucket_id = 'plugin-files');\n"
            "create policy if not exists \"icons_update_owner\" on storage.objects for update to authenticated using (bucket_id = 'plugin-icons' and owner = auth.uid()) with check (bucket_id = 'plugin-icons' and owner = auth.uid());\n"
            "create policy if not exists \"icons_delete_owner\" on storage.objects for delete to authenticated using (bucket_id = 'plugin-icons' and owner = auth.uid());\n"
            "create policy if not exists \"files_update_owner\" on storage.objects for update to authenticated using (bucket_id = 'plugin-files' and owner = auth.uid()) with check (bucket_id = 'plugin-files' and owner = auth.uid());\n"
            "create policy if not exists \"files_delete_owner\" on storage.objects for delete to authenticated using (bucket_id = 'plugin-files' and owner = auth.uid());\n"
        )

    def _display_plugins(self):
        """Display the loaded plugins"""
        # Clear loading message
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.community_plugins:
            no_plugins_label = QLabel("No community plugins found.\n\nBe the first to share a plugin!")
            no_plugins_label.setStyleSheet("color: #AAA; text-align: center;")
            no_plugins_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(no_plugins_label, 0, 0, 1, 5, Qt.AlignmentFlag.AlignCenter)
            return

        # Display plugins in grid (three columns for readability)
        col_count = 3
        for idx, plugin_info in enumerate(self.community_plugins):
            card = CommunityPluginCard(
                plugin_info,
                on_install=self.install_plugin,
                on_view_details=self.show_plugin_details,
                parent=self
            )
            row = idx // col_count
            col = idx % col_count
            self.grid_layout.addWidget(card, row, col)

    def install_plugin(self, plugin_info):
        """Install a community plugin"""
        plugin_id = plugin_info.get('id')
        if not plugin_id:
            QMessageBox.warning(self, "Error", "Invalid plugin information.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        try:
            if self.plugin_store.install_community_plugin(plugin_id):
                QMessageBox.information(self, "Success",
                                      f"Plugin '{plugin_info.get('name')}' installed successfully!\n\n"
                                      "Go to Settings → Plugins to enable it.")
                self.plugin_installed.emit(plugin_id)
                self.main_app.reload_plugins_and_notify()
            else:
                QMessageBox.warning(self, "Installation Failed",
                                  f"Failed to install plugin '{plugin_info.get('name')}'.\n\n"
                                  "Please check your internet connection and try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Installation error: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def sign_in(self):
        if not self._is_supabase:
            return
        email = (self.email_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        if not email or not password:
            QMessageBox.warning(self, "Login", "Enter email and password")
            return
        res = self.plugin_store.sign_in(email, password)
        if not res.get("ok"):
            QMessageBox.critical(self, "Login", str(res.get("error")))
            return
        self._update_auth_ui()
        self._load_my_plugins()

    def sign_up(self):
        if not self._is_supabase:
            return
        email = (self.email_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        if not email or not password:
            QMessageBox.warning(self, "Sign up", "Enter email and password")
            return
        res = self.plugin_store.sign_up(email, password)
        if not res.get("ok"):
            QMessageBox.critical(self, "Sign up", str(res.get("error")))
            return
        QMessageBox.information(self, "Sign up", "Check your email to confirm (if required). Now login.")

    def sign_out(self):
        if not self._is_supabase:
            return
        self.plugin_store.sign_out()
        self._update_auth_ui()

    def _load_my_plugins(self):
        if not self._is_supabase:
            return
        try:
            self.my_plugins = self.plugin_store.list_my_plugins() or []
        except Exception:
            self.my_plugins = []
        try:
            self.my_list.blockSignals(True)
            self.my_list.clear()
            for p in self.my_plugins:
                name = p.get('name') or p.get('id')
                self.my_list.addItem(name)
        finally:
            self.my_list.blockSignals(False)

    def _find_my_by_name(self, name):
        for p in self.my_plugins:
            if (p.get('name') or p.get('id')) == name:
                return p
        return None

    def _on_my_select(self, text):
        p = self._find_my_by_name(text)
        if not p:
            return
        self._selected_my_id = p.get('id')
        self.input_id.setText(p.get('id') or "")
        self.input_id.setEnabled(False)
        self.input_name.setText(p.get('name') or "")
        self.input_version.setText(p.get('version') or "")
        self.input_author.setText(p.get('author') or "")
        self.input_desc.setPlainText(p.get('description') or "")
        cats = p.get('categories') or []
        self.input_cats.setText(','.join(cats))
        self.icon_path.setText("")
        self.file_path.setText("")

    def _reset_my_form(self):
        self._selected_my_id = None
        self.input_id.setEnabled(True)
        self.input_id.clear()
        self.input_name.clear()
        self.input_version.clear()
        self.input_author.clear()
        self.input_desc.clear()
        self.input_cats.clear()
        self.icon_path.clear()
        self.file_path.clear()

    def _save_my_plugin(self):
        if not self._is_supabase:
            return
        pid = (self.input_id.text() or "").strip()
        name = (self.input_name.text() or "").strip()
        version = (self.input_version.text() or "").strip() or "1.0.0"
        author = (self.input_author.text() or "").strip() or "Unknown"
        desc = self.input_desc.toPlainText().strip()
        cats = [c.strip() for c in (self.input_cats.text() or "").split(',') if c.strip()]
        iconp = (self.icon_path.text() or "").strip() or None
        filep = (self.file_path.text() or "").strip() or None
        if not pid or not name:
            QMessageBox.warning(self, "Save", "ID and Name are required")
            return
        if self._selected_my_id:
            res = self.plugin_store.update_plugin(self._selected_my_id, name=name, description=desc, version=version, author=author, categories=cats, icon_path=iconp, file_path=filep)
        else:
            res = self.plugin_store.create_plugin(pid, name, desc, version, author, cats, iconp, filep)
        if not res.get('ok'):
            QMessageBox.critical(self, "Save", str(res.get('error')))
            return
        QMessageBox.information(self, "Save", "Saved")
        self._reset_my_form()
        self._load_my_plugins()
        self.refresh_plugins()

    def _delete_my_plugin(self):
        if not self._is_supabase or not self._selected_my_id:
            return
        res = self.plugin_store.delete_plugin(self._selected_my_id)
        if not res.get('ok'):
            QMessageBox.critical(self, "Delete", str(res.get('error')))
            return
        QMessageBox.information(self, "Delete", "Deleted")
        self._reset_my_form()
        self._load_my_plugins()
        self.refresh_plugins()

    def _browse_icon(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Icon", os.path.expanduser('~'), "Images (*.png *.svg *.jpg *.jpeg)")
        if p:
            self.icon_path.setText(p)

    def _browse_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Plugin File", os.path.expanduser('~'), "Python (*.py)")
        if p:
            self.file_path.setText(p)

    def show_plugin_details(self, plugin_info):
        """Show detailed information about a plugin"""
        if self.details_dialog:
            self.details_dialog.close()

        self.details_dialog = PluginDetailsDialog(plugin_info, self.install_plugin, self)
        self.details_dialog.show()

    def show_plugin_creator(self):
        """Show the plugin creation dialog"""
        if self.creator_dialog:
            self.creator_dialog.close()

        self.creator_dialog = PluginCreatorDialog(
            self.plugin_store,
            self.on_plugin_created,
            self
        )
        self.creator_dialog.show()

    def on_plugin_created(self, plugin_path):
        """Called when a new plugin is created"""
        QMessageBox.information(self, "Plugin Created",
                              f"Your plugin template has been created!\n\n"
                              f"Location: {plugin_path}\n\n"
                              "You can now edit it and enable it in Settings → Plugins.")

    def submit_plugin(self):
        """Launch the plugin submission tool"""
        try:
            import subprocess
            import sys
            script_path = os.path.join(os.path.dirname(__file__), "..", "submit_plugin.py")
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch submission tool: {e}")

    def _show_error(self, message):
        """Show error message"""
        error_label = QLabel(f"Error: {message}")
        error_label.setStyleSheet("color: #F44336;")
        self.grid_layout.addWidget(error_label, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

def _qt_msg_handler(mode, context, message):
    s = str(message)
    if "QPainter::" in s:
        return
    if mode in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
        return
    try:
        sys.stderr.write(s + "\n")
    except Exception:
        pass

qInstallMessageHandler(_qt_msg_handler)

try:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
except Exception:
    pass
app = QApplication(sys.argv)

def _build_window_icon(icon_path: str) -> QIcon:
    try:
        icon = QIcon()
        if not os.path.exists(icon_path):
            return icon
        ext = os.path.splitext(icon_path)[1].lower()
        sizes = (16, 24, 32, 48, 64, 96, 128, 192, 256, 512)
        if ext == ".svg":
            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                for sz in sizes:
                    pm = QPixmap(sz, sz)
                    pm.fill(Qt.GlobalColor.transparent)
                    p = QPainter(pm)
                    renderer.render(p)
                    p.end()
                    icon.addPixmap(pm)
                return icon
            # Fallback to loading as regular icon
            return QIcon(icon_path)
        # Raster path
        base = QPixmap(icon_path)
        if base.isNull():
            return QIcon(icon_path)
        # Trim transparent padding so glyph fills the icon box better
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
        for sz in sizes:
            try:
                pm = base.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon.addPixmap(pm)
            except Exception:
                pass
        try:
            icon.addPixmap(base)
        except Exception:
            pass
        return icon
    except Exception:
        return QIcon(icon_path)

def _get_brand_icon_path():
    base_dir = os.path.dirname(__file__)
    candidates = [
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

icon_path = _get_brand_icon_path()
if os.path.exists(icon_path):
    app.setWindowIcon(_build_window_icon(icon_path))

class ArchPkgManagerUniGetUI(QMainWindow):
    packages_ready = pyqtSignal(list)
    discover_results_ready = pyqtSignal(list)
    show_message = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    load_error = pyqtSignal()
    search_timer = QTimer()
    installation_progress = pyqtSignal(str, bool)  # status, can_cancel
    ui_call = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeoArch - Package Manager")
        self.setGeometry(100, 100, 1600, 900)  # Increased width to accommodate sidebar
        self.setMinimumSize(1200, 800)  # Set minimum size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(Styles.get_dark_stylesheet())
        icon_path = _get_brand_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(_build_window_icon(icon_path))
        # self.set_minimal_icon()
        
        self.current_view = "discover"
        self.updating = False
        self.all_packages = []
        self.search_results = []
        self.packages_per_page = 10
        self.current_page = 0
        self.loader_thread: Any = None
        self.git_manager: Any = None
        self.docker_manager: Any = None
        self.current_search_mode = 'both'
        self.filtered_results = []
        self.installed_index: Any = None
        self._installed_index_building = False
        self._installed_index_last_built = 0
        self._installed_index_sources = set()
        # Working bundle state (list of {name,id,source,version?})
        self.bundle_items = []
        # Settings state
        self.settings = self.load_settings()
        # Plugins runtime
        self.plugins = []
        self.plugin_timer = QTimer()
        self.plugin_timer.setInterval(60000)
        self.plugin_timer.timeout.connect(self.run_plugin_tick)
        self._icon_cache = {}
        self._source_icon_cache = {}
        self._flathub_checked = False
        self.plugins_manager = PluginsManager(self)
        self.packages_ready.connect(self.on_packages_loaded)
        self.discover_results_ready.connect(self.display_discover_results)
        self.show_message.connect(self._show_message)
        self.log_signal.connect(self.log)
        self.load_error.connect(self.on_load_error)
        self.installation_progress.connect(self.on_installation_progress)
        self.ui_call.connect(self._on_ui_call)
        # Background loading coordination
        self.loading_context: Any = None
        self.cancel_update_load = False
        self.cancel_discover_search = False
        # Nav badges (e.g., updates count)
        self.nav_badges = {}
        # Attributes initialized in other methods
        self.settings_widgets = {}
        self.settings_content_layout: Any = None
        self.settings_nav_buttons = {}
        self.source_card: Any = None
        self.filters_panel: Any = None
        self.setup_ui()
        # Set initial nav button state
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == self.current_view)
        self.center_window()
        
        # Initialize the default view
        self.switch_view(self.current_view)
        
        # Show welcome animation in console on first launch
        QTimer.singleShot(500, self.show_welcome_animation)
        # Initialize plugins shortly after UI is ready
        QTimer.singleShot(1000, self.initialize_plugins)
        QTimer.singleShot(1200, self._prewarm_installed_index_async)
        
        # Debounce search input
        self.search_timer.setInterval(800)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        try:
            self.search_input.returnPressed.connect(self.perform_search)
        except Exception:
            pass
        QTimer.singleShot(1500, self.run_first_run_checks)

    def on_large_search_requested(self, query):
        """Handle search request from large search box"""
        try:
            self.search_input.blockSignals(True)
            self.search_input.setText(query)
        finally:
            try:
                self.search_input.blockSignals(False)
            except Exception:
                pass
        # Ensure user can continue typing seamlessly in the top search field
        try:
            self.search_input.setFocus()
            self.search_input.setCursorPosition(len(query))
        except Exception:
            pass
        self.perform_search()

    def on_large_search_submitted(self, query):
        """Handle explicit submit from large search box (enter/button)"""
        try:
            self.search_input.blockSignals(True)
            self.search_input.setText(query)
        finally:
            try:
                self.search_input.blockSignals(False)
            except Exception:
                pass
        self.perform_search()
        try:
            self.search_input.setFocus()
            self.search_input.setCursorPosition(len(query))
        except Exception:
            pass

    def on_search_text_changed(self):
        try:
            if getattr(self, 'current_view', '') == "plugins":
                # Immediate filtering for Plugins for a responsive feel
                self.perform_search()
                return
        except Exception:
            pass
        self.search_timer.start()

    def perform_search(self):
        query = self.search_input.text().strip()
        # Plugins view: always filter regardless of text length
        if getattr(self, 'current_view', '') == "plugins":
            try:
                installed_only = False
                cats = []
                if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                    try:
                        installed_only = (self.plugins_sidebar.group.checkedId() == 1)
                    except Exception:
                        installed_only = False
                    try:
                        cats = self.plugins_sidebar.get_selected_categories()
                    except Exception:
                        cats = []
                if hasattr(self, 'plugins_view') and self.plugins_view:
                    self.plugins_view.set_filter(query, installed_only, cats)
                # Keep sidebar search box in sync with the top search
                if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                    try:
                        self.plugins_sidebar.search.blockSignals(True)
                        self.plugins_sidebar.search.setText(query)
                    finally:
                        self.plugins_sidebar.search.blockSignals(False)
            except Exception:
                pass
            return

        if len(query) < 2:
            if self.current_view == "discover":
                self.large_search_box.setVisible(True)
                self.package_table.setVisible(False)
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                self.header_info.setText("Search and discover new packages to install")
            elif self.current_view == "installed":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self.apply_filters()
                self.package_table.setVisible(True)
            elif self.current_view == "updates":
                try:
                    if hasattr(self, 'no_results_widget'):
                        self.no_results_widget.setVisible(False)
                except Exception:
                    pass
                self.apply_update_filters()
                self.package_table.setVisible(True)
            return
        if self.current_view == "discover":
            self.large_search_box.setVisible(False)
            self.package_table.setVisible(True)
            self.search_discover_packages(query)
        else:
            self.filter_packages()

    def set_minimal_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        with QPainter(pixmap) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            painter.setBrush(QColor(0, 212, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)
            
            font = QFont("Segoe UI", 32, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(26, 26, 26))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
        
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)
    
    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Main Content Area
        content = self.create_content_area()
        main_layout.addWidget(content, 1)
        
        # Ensure proper sizing
        self.adjustSize()
    
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(180)  # Increased to accommodate larger logo and text
        sidebar.setMinimumHeight(650)
        sidebar.setObjectName("sidebar")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 0)
        layout.setSpacing(16)  # Increased spacing between cards
        
        # Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 8, 8, 8)  # Add padding for better spacing
        header_layout.setSpacing(8)  # Spacing between logo and text
        
        # Logo on the left - larger and more prominent
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "icons", "NeoarchLogo.svg")
        try:
            if logo_path.endswith('.svg'):
                # Handle SVG files
                renderer = QSvgRenderer(logo_path)
                if renderer.isValid():
                    pixmap = QPixmap(40, 40)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(painter, QRectF(0, 0, 40, 40))
                    painter.end()
                    logo_label.setPixmap(pixmap)
                else:
                    logo_label.setText("🖥️")
                    logo_label.setStyleSheet("font-size: 24px; color: white;")
            else:
                # Handle raster images
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    # Scale logo to 40px for better balance with text
                    scaled_pixmap = pixmap.scaledToWidth(40, Qt.TransformationMode.SmoothTransformation)
                    logo_label.setPixmap(scaled_pixmap)
                else:
                    logo_label.setText("🖥️")
                    logo_label.setStyleSheet("font-size: 24px; color: white;")
        except OSError:
            # Handle file loading or parsing errors
            self.log("Error loading logo")
            logo_label.setText("🖥️")
            logo_label.setStyleSheet("font-size: 24px; color: white;")
        
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedWidth(40)
        header_layout.addWidget(logo_label)
        
        # Text container on the right - expanded to take remaining space
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)  # Minimal left padding
        text_layout.setSpacing(2)  # Minimal spacing between title and subtitle
        
        # Title - larger and more prominent
        title_label = QLabel("NeoArch")
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: 700; 
            color: #FFFFFF; 
            background: transparent;
            letter-spacing: 0.2px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        text_layout.addWidget(title_label)
        
        # Subtitle - improved visibility and size
        subtitle_label = QLabel("Elevate Your Arch Experience")
        subtitle_label.setStyleSheet("""
            font-size: 9px; 
            color: #D5D5D5; 
            background: transparent; 
            line-height: 1.2;
            font-weight: 400;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        subtitle_label.setWordWrap(True)  # Allow wrapping for multi-line text
        text_layout.addWidget(subtitle_label)
        
        header_layout.addWidget(text_widget)  # Give it stretch factor of 1 to take remaining space
        
        layout.addWidget(header_widget)
        
        # Spacer
        layout.addSpacing(8)  # Adjusted spacing for horizontal header
        
        # Navigation buttons with icons
        nav_items = [
            (os.path.join(os.path.dirname(__file__), "assets", "icons", "discover.svg"), "Discover", "discover"),
            (os.path.join(os.path.dirname(__file__), "assets", "icons", "updates.svg"), "Updates", "updates"), 
            (os.path.join(os.path.dirname(__file__), "assets", "icons", "installed.svg"), "Installed", "installed"),
            (os.path.join(os.path.dirname(__file__), "assets", "icons", "plugins.svg"), "Plugins", "plugins"),
            (os.path.join(os.path.dirname(__file__), "assets", "icons", "local-builds.svg"), "Bundles", "bundles")
        ]
        
        self.nav_buttons = {}
        
        for icon_path, text, view_id in nav_items:
            btn = self.create_nav_button(icon_path, text, view_id)
            self.nav_buttons[view_id] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Bottom section with card-style buttons
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 20)
        bottom_layout.setSpacing(12)  # Consistent spacing
        
        # Settings button - card style
        settings_btn = self.create_bottom_card_button(os.path.join(os.path.dirname(__file__), "assets", "icons", "settings.svg"), "Settings", self.show_settings)
        bottom_layout.addWidget(settings_btn)
        
        # About button - card style
        about_btn = self.create_bottom_card_button(os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"), "About", self.show_about)
        bottom_layout.addWidget(about_btn)
        
        layout.addLayout(bottom_layout)
        
        return sidebar
    
    def create_nav_button(self, icon_path, text, view_id):
        btn = QPushButton()
        btn.setObjectName("navBtn")
        btn.setProperty("view_id", view_id)
        btn.setCheckable(True)
        
        # Create vertical layout for icon + text
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(12, 16, 12, 16)  # Balanced padding
        layout.setSpacing(6)  # Space between icon and text
        
        # Icon container to support badge overlay
        icon_container = QWidget()
        icon_container.setFixedSize(50, 50)
        icon_container.setObjectName("navIconContainer")
        try:
            icon_container.setStyleSheet("background-color: transparent;")
        except Exception:
            pass


        # Absolute children in container
        icon_label = QLabel(icon_container)
        icon_label.setObjectName("navIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setGeometry(0, 0, 50, 50)

        # Try to load and render SVG in white
        pixmap = self.get_svg_icon(icon_path, 50).pixmap(50, 50)
        if pixmap and not pixmap.isNull():
            icon_label.setPixmap(pixmap)
        else:
            # Fallback to black icon or emoji
            icon = QIcon(icon_path)
            if not icon.isNull():
                icon_label.setPixmap(icon.pixmap(50, 50))
            else:
                emoji = self.get_fallback_icon(icon_path)
                icon_label.setText(emoji)

        # Small badge for Updates
        if view_id == "updates":
            try:
                badge = QLabel("", icon_container)
                badge.setObjectName("navBadge")
                badge.setFixedSize(18, 18)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(
                    """
                    QLabel#navBadge {
                        background-color: #E53935;
                        color: white;
                        border-radius: 9px;
                        font-size: 10px;
                        font-weight: 700;
                    }
                    """
                )
                # Position top-right over the icon (container is 50x50, badge 18x18)
                badge.move(32, 0)
                badge.setVisible(False)
                self.nav_badges[view_id] = badge
            except Exception:
                pass

        layout.addWidget(icon_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Text label - below icon
        text_label = QLabel(text)
        text_label.setObjectName("navText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center align text
        layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        btn.clicked.connect(lambda checked, v=view_id: self.switch_view(v))
        
        return btn

    def set_updates_count(self, count):
        """Update the updates count in nav and header."""
        # Update badge on nav button
        badge = self.nav_badges.get("updates")
        if badge is not None:
            try:
                n = int(count) if count is not None else 0
                if n > 0:
                    text = str(n)
                    badge.setText(text)
                    # Dynamically size the badge to fit the text
                    fm = badge.fontMetrics()
                    w = max(18, fm.horizontalAdvance(text) + 8)
                    badge.setFixedSize(w, 18)
                    # Anchor to top-right of icon container
                    parent = badge.parentWidget()
                    if parent is not None:
                        badge.move(max(0, parent.width() - badge.width()), 0)
                    badge.setVisible(True)
                else:
                    badge.setVisible(False)
            except Exception:
                pass
        # Optionally reflect in label text
        btn = self.nav_buttons.get("updates") if hasattr(self, 'nav_buttons') else None
        if btn:
            label = btn.findChild(QLabel, "navText")
            if label:
                try:
                    n = int(count) if count is not None else 0
                    label.setText(f"Updates{f' ({n})' if n > 0 else ''}")
                except Exception:
                    label.setText("Updates")

    def update_updates_header_counts(self):
        """Update the header info subtitle for Updates with real counts."""
        if self.current_view != "updates":
            return
        total = len(getattr(self, 'updates_all', []) or [])
        matched = len(self.all_packages or [])
        try:
            self.header_info.setText(f"{total} packages were found, {matched} of which match the specified filters")
        except Exception:
            pass
    
    def update_installed_header_counts(self):
        """Update the header info subtitle for Installed with total installed count."""
        if self.current_view != "installed":
            return
        total = len(getattr(self, 'installed_all', []) or [])
        try:
            self.header_info.setText(f"{total} packages installed")
        except Exception:
            pass
    
    def create_bottom_card_button(self, icon_path, text, callback):
        btn = QPushButton()
        btn.setObjectName("bottomCardBtn")
        
        # Create horizontal layout for icon + text
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(12, 16, 12, 16)  # Balanced padding
        layout.setSpacing(8)  # Space between icon and text
        
        # Icon label - smaller for bottom cards
        icon_label = QLabel()
        icon_label.setObjectName("bottomCardIcon")
        icon_label.setFixedSize(28, 28)  # Smaller than main nav
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load and render SVG in white
        pixmap = self.get_svg_icon(icon_path, 28).pixmap(28, 28)
        if pixmap and not pixmap.isNull():
            icon_label.setPixmap(pixmap)
        else:
            # Fallback to black icon or emoji
            icon = QIcon(icon_path)
            if not icon.isNull():
                icon_label.setPixmap(icon.pixmap(28, 28))
            else:
                emoji = "⚙️" if "settings" in icon_path else "ℹ️"
                icon_label.setText(emoji)
        
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Text label - right of icon
        text_label = QLabel(text)
        text_label.setObjectName("bottomCardText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Left align text, vertically centered
        layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addStretch()
        
        btn.clicked.connect(callback)
        
        return btn
    
    def get_fallback_icon(self, icon_path):
        # Return emoji based on icon path
        if "discover" in icon_path:
            return "🔍"
        elif "updates" in icon_path:
            return "⬆️"
        elif "installed" in icon_path:
            return "📦"
        elif "local" in icon_path or "bundles" in icon_path:
            return "🎁"
        elif "settings" in icon_path:
            return "⚙️"
        elif "docker" in icon_path.lower():
            return "🐳"
        else:
            return "📦"
    
    def get_source_icon(self, source, size=18):
        icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
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

            painter = QPainter(pixmap)
            if not painter.isActive():
                return QIcon()

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                renderer.render(painter, QRectF(pixmap.rect()))
                painter.end()
                icon = QIcon(pixmap)
            else:
                # Fallback: try to load as regular icon
                painter.end()
                icon = QIcon(icon_path)

            try:
                if isinstance(getattr(self, "_source_icon_cache", None), dict):
                    self._source_icon_cache[(source, int(size))] = icon
            except Exception:
                pass
            return icon
        except Exception:
            return QIcon()
    
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
    
    def get_ignore_file_path(self):
        return config_utils.get_ignore_file_path()

    def load_ignored_updates(self):
        return config_utils.load_ignored_updates()

    def save_ignored_updates(self, items):
        return config_utils.save_ignored_updates(items)

    def get_local_updates_file_path(self):
        return config_utils.get_local_updates_file_path()

    def load_local_update_entries(self):
        return config_utils.load_local_update_entries()

    def cmd_exists(self, cmd):
        return sys_utils.cmd_exists(cmd)

    def get_missing_dependencies(self):
        return sys_utils.get_missing_dependencies()

    def run_first_run_checks(self):
        missing = self.get_missing_dependencies()
        if not missing:
            return
        text = "The following dependencies are missing and are required for best experience:\n\n" + "\n".join(f"• {m}" for m in missing) + "\n\nInstall now?"
        reply = QMessageBox.question(self, "Setup Environment", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            Thread(target=lambda: self.install_dependencies(missing), daemon=True).start()

    def install_dependencies(self, missing):
        try:
            # Filter out AUR helper from pacman packages
            pacman_pkgs = [p for p in missing if p not in ["yay", "yay or paru"]]
            if pacman_pkgs:
                cmd = ["pacman", "-S", "--needed", "--noconfirm"] + pacman_pkgs
                worker = CommandWorker(cmd, sudo=True)
                worker.output.connect(self.log)
                worker.error.connect(self.log)
                done_event = Event()
                worker.finished.connect(lambda: done_event.set())
                worker.run()
                done_event.wait(timeout=1)
            # Install an AUR helper if none are available
            if ("yay" in missing or "yay or paru" in missing) and self.cmd_exists("git"):
                self.install_aur_helper()
            self.show_message.emit("Environment", "Dependency setup completed")
        except Exception as e:
            self.show_message.emit("Environment", f"Setup failed: {str(e)}")

    def install_aur_helper(self):
        """Install yay as the default AUR helper if none are available."""
        tmpdir = tempfile.mkdtemp(prefix="neoarch-yay-")
        try:
            self.log("Installing yay AUR helper...")
            clone = subprocess.run(["git", "clone", "https://aur.archlinux.org/yay-bin.git", tmpdir], capture_output=True, text=True, timeout=120)
            if clone.returncode != 0:
                self.log(f"Error: {clone.stderr}")
                return
            env, cleanup = self.prepare_askpass_env()
            cmd = f"cd '{tmpdir}' && makepkg -si --noconfirm"
            process = subprocess.Popen(["bash", "-lc", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            while True:
                line = process.stdout.readline() if process.stdout else ""
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log(line.strip())
            _, stderr = process.communicate()
            if process.returncode != 0 and stderr:
                self.log(f"Error: {stderr}")
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def update_core_tools(self):
        return update_service.update_core_tools(self)
    
    def get_sudo_askpass(self):
        return askpass_service.get_sudo_askpass()

    def prepare_askpass_env(self):
        return askpass_service.prepare_askpass_env()
    
    def check_authentication_tools(self):
        """Check if authentication tools are available and warn user if not"""
        pass  # inlined
        is_supported, message = sys_utils.check_aur_authentication_support()
        if not is_supported:
            # Show warning after a short delay to ensure UI is ready
            QTimer.singleShot(2000, lambda: self.show_message.emit("AUR Authentication Warning", message))

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
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid rgba({r}, {g}, {b}, 0.4);
                background-color: transparent;
            }}
            QCheckBox#tableCheckbox::indicator:checked {{
                background-color: {hex_color};
                border: 2px solid {hex_color};
            }}
            QCheckBox#tableCheckbox::indicator:hover {{
                border-color: rgba({r}, {g}, {b}, 0.8);
            }}
            """
        )

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
                # Directly load raster images to avoid QSvgRenderer warnings
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
                    # Fallback: try to load as regular icon
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
    
    def create_toolbar_button(self, icon_path, tooltip, callback, icon_size=24):
        """Create a reusable toolbar button with icon and tooltip"""
        btn = QPushButton()
        btn.setFixedSize(40, 40)  # Slightly smaller for better fit
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                padding: 6px;
                margin: 2px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-radius: 6px;
            }
            QPushButton:pressed {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        
        # Try to load SVG icon, fallback to emoji
        icon = self.get_svg_icon(icon_path, icon_size)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))
        else:
            # Fallback to emoji based on icon path
            emoji = self.get_fallback_icon(icon_path)
            if "help" in icon_path.lower():
                emoji = "❓"
            elif "add" in icon_path.lower() or "sudo" in icon_path.lower():
                emoji = "➕"
            btn.setText(emoji)
        
        return btn
    
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

    def create_content_area(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main Content (Splitter)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        
        # Left panel: Filters/Sources
        left_panel = self.create_filters_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Packages table + Console
        right_panel = self.create_packages_panel()
        splitter.addWidget(right_panel)
        
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        splitter.setSizes([200, 950])
        
        layout.addWidget(splitter, 1)
        
        return content
    
    def create_header(self):
        header = QFrame()
        header.setStyleSheet(Styles.get_header_stylesheet())
        header.setFixedHeight(70)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Icon label (hidden by default)
        self.header_icon = QLabel()
        try:
            self.header_icon.setFixedSize(32, 32)
        except Exception:
            pass
        self.header_icon.setVisible(False)
        layout.addWidget(self.header_icon)
        
        self.header_label = QLabel("🔄 Software Updates")
        self.header_label.setObjectName("headerLabel")
        layout.addWidget(self.header_label)
        
        self.header_info = QLabel("24 packages were found, 24 of which match the specified filters")
        self.header_info.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        layout.addWidget(self.header_info)
        
        layout.addStretch()
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search for packages")
        search_input.setFixedWidth(250)
        search_input.setFixedHeight(36)
        self.search_input = search_input
        layout.addWidget(search_input)
        
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(36, 36)
        icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
        
        refresh_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "refresh.svg"), 20))
        refresh_btn.setToolTip("Refresh")
        refresh_btn.clicked.connect(self.refresh_packages)
        layout.addWidget(refresh_btn)
        
        return header
    
    def show_docker_install_dialog(self):
        """Show Docker container management dialog"""
        if not self.docker_manager:
            pass  # inlined
            self.docker_manager = DockerManager(self.log_signal, self.show_message, self.sources_layout, self)
        
        self.docker_manager.install_from_docker()
    
    def show_community_hub(self):
        """Show Community Hub for plugins and extensions"""
        try:
            # Switch to plugins view and show community tab
            self.switch_view("settings")
            # Wait a moment for the settings UI to load
            QTimer.singleShot(100, self.switch_to_community_tab)
        except Exception as e:
            self._show_message("Community Hub", f"Error opening community hub: {e}")
    
    def switch_to_community_tab(self):
        """Switch to the community tab in plugins settings"""
        try:
            if hasattr(self, 'settings_widgets') and 'plugins' in self.settings_widgets:
                # Switch to plugins category in settings
                self.switch_settings_category("plugins")
                # Switch to community tab in plugins widget
                plugins_widget = self.settings_widgets['plugins']
                if hasattr(plugins_widget, 'tabs'):
                    plugins_widget.tabs.setCurrentIndex(1)  # Community Hub is index 1
        except Exception as e:
            self._show_message("Community Hub", f"Error switching to community tab: {e}")
    
    def on_plugin_install_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.install_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Install error: {e}")
    
    def on_plugin_launch_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.launch_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Launch error: {e}")
    
    def on_plugin_uninstall_requested(self, plugin_id):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_manager.uninstall_by_id(self.plugins_view, plugin_id)
        except Exception as e:
            self._show_message("Plugins", f"Uninstall error: {e}")
    
    def open_plugins_folder(self):
        try:
            folder = self.get_user_plugins_dir()
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
            subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._show_message("Plugins", f"Cannot open folder: {e}")
    
    def show_git_install_dialog(self):
        """Show Git repository installation dialog"""
        if not self.git_manager:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
        
        self.git_manager.install_from_git()
    
    def show_help(self):
        """Show help dialog"""
        help_service.show_help(self, getattr(self, 'current_view', ''))
    
    def go_to_bundles(self):
        """Switch to bundles view"""
        self.switch_view("bundles")
    
    def show_settings(self):
        self.switch_view("settings")

    def on_plugins_filter_changed(self, text, installed_only):
        try:
            if hasattr(self, 'plugins_view') and self.plugins_view:
                cats = []
                try:
                    if hasattr(self, 'plugins_sidebar') and self.plugins_sidebar:
                        cats = self.plugins_sidebar.get_selected_categories()
                except Exception:
                    cats = []
                self.plugins_view.set_filter(text, installed_only, cats)
        except Exception:
            pass
    
    def sudo_install_selected(self):
        """Install selected packages with sudo privileges"""
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                id_item = self.package_table.item(row, 2)
                pkg_name = name_item.text().strip() if name_item else ''
                pkg_id = id_item.text().strip() if id_item else pkg_name
                if self.current_view == "discover":
                    source = ""
                    chip = self.package_table.cellWidget(row, 4)
                    if chip is not None:
                        labels = chip.findChildren(QLabel)
                        if labels:
                            source = labels[-1].text()
                else:
                    source_item = self.package_table.item(row, 5)
                    source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                install_token = pkg_id if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(install_token)
        
        if not packages_by_source:
            QMessageBox.information(self, "No Selection", "Please select packages to install.")
            return
        
        try:
            if self.current_view == "discover":
                sel_src = {s: True for s in packages_by_source.keys()}
            else:
                sel_src = None
            self.build_installed_index(sel_src)
        except Exception:
            pass
        to_install = {}
        idx = self.installed_index or {}
        for source, pkgs in packages_by_source.items():
            installed_set = idx.get(source) or set()
            remaining = [p for p in pkgs if p not in installed_set]
            if remaining:
                to_install[source] = remaining
        if not to_install:
            self.log_signal.emit("All selected packages are already installed")
            return
        package_list = "\n".join(f"• {pkg}" for src, pkgs in to_install.items() for pkg in pkgs)
        reply = QMessageBox.question(
            self, "Install Packages with Sudo",
            f"This will install the following packages with elevated privileges:\n\n{package_list}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.force_sudo_install = True
        except Exception:
            pass
        self.log_signal.emit(f"Installing with sudo: {', '.join([f'{pkg} ({source})' for source, pkgs in to_install.items() for pkg in pkgs])}")
        install_service.install_packages(self, to_install)
    
    def create_filters_panel(self):
        self.filters_panel = QFrame()
        self.filters_panel.setStyleSheet(Styles.get_filters_panel_stylesheet())
        
        layout = QVBoxLayout(self.filters_panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        self.sources_section = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_section)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setSpacing(8)
        
        self.sources_title_label = QLabel("Sources")
        self.sources_title_label.setObjectName("sectionLabel")
        self.sources_layout.addWidget(self.sources_title_label)
        
        sources = ["pacman", "AUR", "Flatpak"]
        self.source_checkboxes = {}
        for source in sources:
            checkbox = QCheckBox(source)
            checkbox.setChecked(True)
            self.source_checkboxes[source] = checkbox
            self.sources_layout.addWidget(checkbox)
        
        layout.addWidget(self.sources_section)
        
        layout.addSpacing(12)
        
        # Filters Section
        self.filters_section = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_section)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(8)
        
        layout.addWidget(self.filters_section)
        layout.addStretch()
        
        return self.filters_panel
    
    def create_packages_panel(self):
        panel = QWidget()
        self.packages_panel_layout = QVBoxLayout(panel)
        self.packages_panel_layout.setContentsMargins(12, 12, 12, 12)
        self.packages_panel_layout.setSpacing(12)
        
        # Toolbar
        self.toolbar_widget = QWidget()
        self.toolbar_layout = QVBoxLayout(self.toolbar_widget)
        self.toolbar_layout.setContentsMargins(0,0,0,0)
        # Keep toolbar fixed-height and top-aligned so it doesn't shift during loading
        try:
            self.toolbar_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.toolbar_widget, 0, Qt.AlignmentFlag.AlignTop)
        
        # Large search box for discover page
        self.large_search_box = LargeSearchBox()
        self.large_search_box.search_requested.connect(self.on_large_search_requested)
        # Explicit submit from large box (enter or button)
        try:
            self.large_search_box.search_submitted.connect(self.on_large_search_submitted)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.large_search_box)
        
        # Loading spinner widget
        self.loading_widget = LoadingSpinner(message="Checking for updates...")
        self.loading_widget.setVisible(False)  # Hidden by default
        
        # Cancel button for installation
        self.cancel_install_btn = QPushButton("Cancel Installation")
        self.cancel_install_btn.setMinimumHeight(36)
        self.cancel_install_btn.setVisible(False)  # Hidden by default
        self.cancel_install_btn.clicked.connect(self.cancel_installation)
        
        # Container for loading widget and cancel button (centered both axes)
        self.loading_container = QWidget()
        self.loading_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        loading_layout = QVBoxLayout(self.loading_container)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        loading_layout.setSpacing(12)
        loading_layout.addStretch()  # Top stretch for vertical centering
        loading_layout.addWidget(self.loading_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        loading_layout.addWidget(self.cancel_install_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        loading_layout.addStretch()  # Bottom stretch for vertical centering
        self.loading_container.setVisible(False)
        
        self.packages_panel_layout.addWidget(self.loading_container, 1)
        self.no_results_widget = QFrame()
        nr_layout = QVBoxLayout(self.no_results_widget)
        nr_layout.setContentsMargins(0, 40, 0, 40)
        nr_layout.setSpacing(8)
        self.no_results_title = QLabel("No results found")
        self.no_results_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_title.setStyleSheet("color: #c0c0c0; font-size: 18px; font-weight: 600;")
        self.no_results_desc = QLabel("")
        self.no_results_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_desc.setStyleSheet("color: #9aa0a6; font-size: 13px;")
        nr_layout.addWidget(self.no_results_title)
        nr_layout.addWidget(self.no_results_desc)
        self.no_results_widget.setVisible(False)
        self.packages_panel_layout.addWidget(self.no_results_widget)
        
        # Settings container (hidden by default)
        self.settings_container = QScrollArea()
        self.settings_container.setWidgetResizable(True)
        self.settings_container.setVisible(False)
        self.settings_root = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_root)
        self.settings_layout.setContentsMargins(12, 12, 12, 12)
        self.settings_layout.setSpacing(12)
        self.settings_container.setWidget(self.settings_root)
        self.packages_panel_layout.addWidget(self.settings_container)
        
        # Plugins view (hidden by default)
        self.plugins_view = PluginsView(self, self.get_svg_icon)
        self.plugins_view.install_requested.connect(self.on_plugin_install_requested)
        self.plugins_view.launch_requested.connect(self.on_plugin_launch_requested)
        try:
            self.plugins_view.uninstall_requested.connect(self.on_plugin_uninstall_requested)
        except Exception:
            pass
        self.plugins_view.setVisible(False)
        
        # Add plugins view directly (no tabs needed)
        self.plugins_view.setVisible(False)
        self.packages_panel_layout.addWidget(self.plugins_view)
        
        # Packages Table
        self.package_table = QTableWidget()
        self.package_table.setColumnCount(6)
        self.package_table.setHorizontalHeaderLabels(
            ["", "Package Name", "Package ID", "Version", "New Version", "Source"]
        )
        self.package_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.package_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.package_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.package_table.verticalHeader().setVisible(False)
        self.package_table.setAlternatingRowColors(True)
        self.package_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.package_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.package_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.packages_panel_layout.addWidget(self.package_table, 1)
        self.load_more_btn = QPushButton("Load More Packages")
        self.load_more_btn.setMinimumHeight(36)
        icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
        
        self.load_more_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "load-more.svg"), 20))
        self.load_more_btn.clicked.connect(self.load_more_packages)
        self.load_more_btn.setVisible(False)
        self.packages_panel_layout.addWidget(self.load_more_btn)

        # Console toggle button (bottom-right)
        self.console_toggle_btn = QPushButton()
        self.console_toggle_btn.setFixedSize(36, 36)
        self.console_toggle_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "terminal.svg"), 20))
        self.console_toggle_btn.setIconSize(QSize(20, 20))
        self.console_toggle_btn.setToolTip("Show Console")
        self.console_toggle_btn.clicked.connect(self.toggle_console)
        self.console_toggle_btn.setVisible(False)
        self.packages_panel_layout.addWidget(self.console_toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Console Output
        self.console_label = QLabel("Console Output")
        self.console_label.setObjectName("sectionLabel")
        self.packages_panel_layout.addWidget(self.console_label)
        # Hidden by default; shown via the bottom-right toggle
        try:
            self.console_label.setVisible(False)
        except Exception:
            pass
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        try:
            self.console.document().setMaximumBlockCount(500)
        except Exception:
            pass
        self.packages_panel_layout.addWidget(self.console)
        try:
            self.console.setVisible(False)
        except Exception:
            pass
        
        return panel
    
    def update_toolbar(self):
        # Clear existing toolbar
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            if item.layout():
                # Remove the layout
                layout = item.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
        
        if self.current_view == "updates":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            
            update_btn = QPushButton("Update Selected")
            update_btn.setMinimumHeight(36)
            update_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            update_btn.clicked.connect(self.update_selected)
            layout.addWidget(update_btn)
            
            ignore_btn = QPushButton("Ignore Selected")
            ignore_btn.setMinimumHeight(36)
            ignore_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            ignore_btn.clicked.connect(self.ignore_selected)
            layout.addWidget(ignore_btn)
            
            manage_btn = QPushButton("Manage Ignored")
            manage_btn.setMinimumHeight(36)
            manage_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            manage_btn.clicked.connect(self.manage_ignored)
            layout.addWidget(manage_btn)
            
            layout.addStretch()
            # Right-side action icons similar to Discover
            icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
            bundles_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "local-builds.svg"),
                "Add selected to Bundle",
                self.add_selected_to_bundle
            )
            layout.addWidget(bundles_btn)

            sudo_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "sudo.svg"),
                "Run Updates (sudo where needed)",
                lambda: self.update_selected()
            )
            layout.addWidget(sudo_btn)

            tools_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "download.svg"),
                "Update Tools",
                self.update_core_tools
            )
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            layout.addWidget(tools_btn)
            layout.addWidget(help_btn)

            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "installed":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            update_btn = QPushButton("Update Selected")
            update_btn.setMinimumHeight(36)
            update_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            update_btn.clicked.connect(self.update_selected)
            layout.addWidget(update_btn)

            uninstall_btn = QPushButton("Uninstall Selected")
            uninstall_btn.setMinimumHeight(36)
            uninstall_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            uninstall_btn.clicked.connect(self.uninstall_selected)
            layout.addWidget(uninstall_btn)

            layout.addStretch()
            icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
            bundles_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "local-builds.svg"),
                "Add selected to Bundle",
                self.add_selected_to_bundle
            )
            layout.addWidget(bundles_btn)
            tools_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "download.svg"),
                "Onclick Update",
                self.update_core_tools
            )
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            layout.addWidget(tools_btn)
            layout.addWidget(help_btn)
            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "discover":
            layout = QHBoxLayout()
            layout.setSpacing(8)  # Tighter spacing
            
            install_btn = QPushButton("Install selected packages")
            install_btn.setMinimumHeight(36)
            install_btn.clicked.connect(self.install_selected)
            icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
            
            install_btn.setIcon(self.get_svg_icon(os.path.join(icon_dir, "install-selected packge.svg"), 20))
            
            layout.addWidget(install_btn)

            # Git button on the left side
            git_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "git.svg"),
                "Install via GitHub",
                self.show_git_install_dialog
            )
            layout.addWidget(git_btn)
            
            # Docker button next to Git
            docker_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "docker.svg"),
                "Install via Docker",
                self.show_docker_install_dialog
            )
            layout.addWidget(docker_btn)
            
            layout.addStretch()  # Push remaining buttons to the right
            
            # Action buttons on the right side
            bundles_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "local-builds.svg"),
                "Add selected to Bundle",
                self.add_selected_to_bundle
            )
            layout.addWidget(bundles_btn)
            
            sudo_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "sudo.svg"),
                "Install with Sudo Privileges",
                self.sudo_install_selected
            )
            layout.addWidget(sudo_btn)
            
            # Help button on the far right
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            tools_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "download.svg"),
                "Onclick Update",
                self.update_core_tools
            )
            layout.addWidget(tools_btn)
            layout.addWidget(help_btn)
            
            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "plugins":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            
            # Add stretch to push icon buttons to the right
            layout.addStretch()
            
            icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
            bundles_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "local-builds.svg"),
                "Add selected to Bundle",
                lambda: None  # Empty handler for now
            )
            layout.addWidget(bundles_btn)
            tools_btn = self.create_toolbar_button(
                os.path.join(icon_dir, "download.svg"),
                "Onclick Update",
                lambda: None  # Empty handler for now
            )
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            layout.addWidget(tools_btn)
            layout.addWidget(help_btn)
            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "bundles":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            install_bundle_btn = QPushButton("Install Bundle")
            install_bundle_btn.setMinimumHeight(36)
            install_bundle_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #F0F0F0;
                    border: 1px solid rgba(0, 191, 174, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
                QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
                """
            )
            install_bundle_btn.clicked.connect(self.install_bundle)
            layout.addWidget(install_bundle_btn)

            export_btn = QPushButton("Export Bundle")
            export_btn.setMinimumHeight(36)
            export_btn.setStyleSheet(install_bundle_btn.styleSheet())
            export_btn.clicked.connect(self.export_bundle)
            layout.addWidget(export_btn)

            import_btn = QPushButton("Import Bundle")
            import_btn.setMinimumHeight(36)
            import_btn.setStyleSheet(install_bundle_btn.styleSheet())
            import_btn.clicked.connect(self.import_bundle)
            layout.addWidget(import_btn)

            remove_sel_btn = QPushButton("Remove Selected")
            remove_sel_btn.setMinimumHeight(36)
            remove_sel_btn.setStyleSheet(install_bundle_btn.styleSheet())
            remove_sel_btn.clicked.connect(self.remove_selected_from_bundle)
            layout.addWidget(remove_sel_btn)

            # Add to Community button
            add_to_community_btn = QPushButton("Add to Community")
            add_to_community_btn.setMinimumHeight(36)
            add_to_community_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #00BFAE;
                    border: 1px solid rgba(0, 191, 174, 0.4);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { 
                    background-color: rgba(0, 191, 174, 0.15); 
                    border-color: rgba(0, 191, 174, 0.6); 
                    color: #00D4C4;
                }
                QPushButton:pressed { 
                    background-color: rgba(0, 191, 174, 0.25); 
                }
                """)
            add_to_community_btn.clicked.connect(self.add_selected_to_community)
            add_to_community_btn.setToolTip("Share selected bundle items with the community")
            layout.addWidget(add_to_community_btn)

            clear_btn = QPushButton("Clear Bundle")
            clear_btn.setMinimumHeight(36)
            clear_btn.setStyleSheet(install_bundle_btn.styleSheet())
            clear_btn.clicked.connect(self.clear_bundle)
            layout.addWidget(clear_btn)

            layout.addStretch()
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            layout.addWidget(help_btn)
            self.toolbar_layout.addLayout(layout)
        elif self.current_view == "settings":
            layout = QHBoxLayout()
            layout.setSpacing(12)
            layout.addStretch()
            help_btn = self.create_toolbar_button(
                os.path.join(os.path.dirname(__file__), "assets", "icons", "about.svg"),
                "Help & Documentation",
                self.show_help
            )
            layout.addWidget(help_btn)
            self.toolbar_layout.addLayout(layout)
    
    def show_welcome_animation(self):
        """Display a welcome animation in the console when the app first opens"""
        welcome_messages = [
            "🌟 Welcome to NeoArch Package Manager!",
            "🚀 Ready to elevate your Arch experience",
            "📦 Search, install, and manage packages with ease",
            "⚡ Multi-repo support: pacman, AUR, Flatpak & npm",
            "🔍 Start by searching for packages above"
        ]
        
        self.welcome_index = 0
        
        def animate_next_message():
            if self.welcome_index < len(welcome_messages):
                self.log(welcome_messages[self.welcome_index])
                self.welcome_index += 1
                QTimer.singleShot(800, animate_next_message)  # 800ms delay between messages
            else:
                # Clear the console after the animation completes
                QTimer.singleShot(2000, lambda: self.console.clear())  # Wait 2 seconds then clear
        
        # Start the animation
        animate_next_message()
    
    def switch_view(self, view_id):
        self.current_view = view_id
        try:
            _installing = getattr(self, "_installing", False) or hasattr(self, 'install_cancel_event')
        except Exception:
            _installing = False
        if not _installing:
            self.console.clear()
        # Stop any spinners and cancel background loads when switching views
        try:
            self.loading_widget.stop_animation()
            self.loading_widget.setVisible(False)
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
            self.cancel_install_btn.setVisible(False)
            self.settings_container.setVisible(False)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.setVisible(False)
            # plugins_tab_widget removed - plugins_view is handled above
            if hasattr(self, 'no_results_widget'):
                self.no_results_widget.setVisible(False)
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(False)
        except Exception:
            pass
        # Cancel ongoing non-install tasks
        self.cancel_update_load = True
        self.cancel_discover_search = True
        # Tag the current view as the active loading context
        self.loading_context = view_id
        
        # Update button states
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == view_id)
        
        # Update header
        headers = {
            "updates": (os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "update12.svg"), "Software Updates", ""),
            "installed": (os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "installed.svg"), "Installed Packages", ""),
            "discover": (os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "search.svg"), "Discover Packages", "Search and discover new packages to install"),
            "bundles": (os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "bundle.svg"), "Package Bundles", "Manage package bundles"),
            "plugins": (os.path.join(os.path.dirname(__file__), "assets", "icons", "plugins.svg"), "Plugins", "Extensions and system tools"),
            "settings": (os.path.join(os.path.dirname(__file__), "assets", "icons", "settings.svg"), "Settings", "Configure NeoArch settings and plugins"),
        }
        
        header_data = headers.get(view_id, ("NeoArch", ""))
        if len(header_data) == 3:  # Icon, title, subtitle
            icon_path, title, subtitle = header_data
            self.header_icon.setPixmap(self.get_svg_icon(icon_path, 32).pixmap(32, 32))
            self.header_icon.setVisible(True)
            self.header_label.setText(title)
            self.header_info.setText(subtitle)
        else:  # Title, subtitle
            title, subtitle = header_data
            self.header_icon.setVisible(False)
            self.header_label.setText(title)
            self.header_info.setText(subtitle)
        # Update dynamic counts if on updates/installed
        if view_id == "updates":
            QTimer.singleShot(0, self.update_updates_header_counts)
        elif view_id == "installed":
            QTimer.singleShot(0, self.update_installed_header_counts)
        
        self.update_table_columns(view_id)
        self.update_filters_panel(view_id)
        self.update_toolbar()
        self.search_input.clear()
        if view_id != "discover":
            self.large_search_box.setVisible(False)
        
        # Show filters panel for all views except settings and bundles
        if hasattr(self, 'filters_panel'):
            self.filters_panel.setVisible(view_id not in ("settings", "bundles"))
        
        # Load data for view
        if view_id == "updates":
            # Prepare UI for loading updates
            try:
                self.large_search_box.setVisible(False)
            except Exception:
                pass
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            try:
                self.loading_widget.set_message("Checking for updates...")
                self.loading_widget.setVisible(True)
                self.loading_widget.start_animation()
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
            self.package_table.setVisible(False)
            self.load_updates()
        elif view_id == "installed":
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            try:
                self.loading_widget.set_message("Loading installed packages...")
                self.loading_widget.setVisible(True)
                self.loading_widget.start_animation()
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
            try:
                self.package_table.setVisible(False)
            except Exception:
                pass
            self.load_installed_packages()
        elif view_id == "discover":
            self.large_search_box.setVisible(True)
            self.package_table.setVisible(False)
            self.load_more_btn.setVisible(False)
            self.package_table.setRowCount(0)
            self.header_info.setText("Search and discover new packages to install")
            try:
                self.search_input.setPlaceholderText("Search for packages")
            except Exception:
                pass
            # Removed verbose log: self.log("Type a package name to search in AUR and official repositories")
            # Hide console in Discover view
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            try:
                _installing = getattr(self, "_installing", False) or hasattr(self, 'install_cancel_event')
            except Exception:
                _installing = False
            if _installing:
                try:
                    self.loading_widget.set_message("Installing packages...")
                    self.loading_widget.setVisible(True)
                    self.loading_widget.start_animation()
                    if hasattr(self, 'loading_container'):
                        self.loading_container.setVisible(True)
                except Exception:
                    pass
                try:
                    self.large_search_box.setVisible(False)
                    self.package_table.setVisible(False)
                except Exception:
                    pass
                try:
                    self.cancel_install_btn.setVisible(True)
                except Exception:
                    pass
        elif view_id == "bundles":
            self.package_table.setRowCount(0)
            self.header_info.setText("Create, import, export, and install bundles of packages across sources")
            self.package_table.setVisible(True)
            self.load_more_btn.setVisible(False)
            try:
                self.search_input.setPlaceholderText("Search for packages")
            except Exception:
                pass
            # Show console in non-settings views
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            try:
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
            QTimer.singleShot(0, self.refresh_bundles_table)
        elif view_id == "plugins":
            try:
                self.loading_widget.setVisible(False)
                self.loading_widget.stop_animation()
            except Exception:
                pass
            try:
                self.search_input.setPlaceholderText("Search extensions")
            except Exception:
                pass
            self.large_search_box.setVisible(False)
            self.settings_container.setVisible(False)
            self.package_table.setVisible(False)
            self.load_more_btn.setVisible(False)
            
            # Clear any existing source cards from sources_layout
            while self.sources_layout.count() > 1:
                item = self.sources_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()
            
            # Clear filters layout
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # For plugins view, create filter by plugin status (like installed view)
            self.filter_card = FilterCard(self)
            self.filter_card.filter_changed.connect(self.on_filter_selection_changed)
            
            # Add plugin status filters
            self.filter_card.add_filter("Available")
            self.filter_card.add_filter("Installed")
            
            self.filters_layout.addWidget(self.filter_card)
            
            # Update visibility like installed view
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            
            # Add source cards like installed section
            self.update_plugins_sources()
            
            # Show plugins view directly (no tab widget)
            try:
                self.plugins_view.setVisible(True)
            except Exception:
                pass
            self.plugins_view.refresh_all()

            self.header_info.setText("Install and launch extensions like BleachBit and Timeshift")
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
            except Exception:
                pass
        elif view_id == "settings":
            # Show settings panel, hide package table & search
            try:
                self.loading_widget.setVisible(False)
                self.loading_widget.stop_animation()
            except Exception:
                pass
            self.large_search_box.setVisible(False)
            self.package_table.setVisible(False)
            self.load_more_btn.setVisible(False)
            self.settings_container.setVisible(True)
            
            # Retain source checkboxes; no clearing needed
            
            # Clear filters layout
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Hide sources and filters sections in settings view
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
            
            # Hide console in Settings view
            try:
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            self.header_info.setText("Configure NeoArch settings and plugins")
            QTimer.singleShot(0, self.build_settings_ui)
        # Notify plugins about view change
        try:
            self.run_plugin_hook('on_view_changed', view_id)
        except Exception:
            pass
        # Other views: ensure console visible (not in settings/plugins/discover)
        if view_id in ("",):
            try:
                self.console_label.setVisible(True)
                self.console.setVisible(True)
            except Exception:
                pass
    
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
            # For installed view, filter by update status
            self.filter_card = FilterCard(self)
            self.filter_card.filter_changed.connect(self.on_filter_selection_changed)
            
            # Add status filters
            self.filter_card.add_filter("Updates available")
            self.filter_card.add_filter("Installed")
            
            self.filters_layout.addWidget(self.filter_card)
        else:
            filter_options = []
        
        # Update visibility
        if view_id == "installed":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            self.update_installed_sources()
        elif view_id == "updates":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        elif view_id == "discover":
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            self.update_discover_sources()
        elif view_id == "bundles":
            # No source or status filters for bundles
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        elif view_id == "plugins":
            # Show a VS Code-like extensions sidebar in filters_section
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
            # Clear and add PluginsSidebar
            while self.filters_layout.count():
                item = self.filters_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            try:
                self.plugins_sidebar = PluginsSidebar(self)
                self.plugins_sidebar.filter_changed.connect(self.on_plugins_filter_changed)
                # Populate sidebar with the same list as cards
                try:
                    if hasattr(self, 'plugins_view') and self.plugins_view:
                        self.plugins_sidebar.set_plugins(self.plugins_view.plugins)
                        cats = sorted({(p.get('category') or '') for p in self.plugins_view.plugins if p.get('category')})
                        try:
                            self.plugins_sidebar.set_categories(cats)
                        except Exception:
                            pass
                except Exception:
                    pass
                # Allow install from sidebar
                try:
                    self.plugins_sidebar.install_requested.connect(self.on_plugin_install_requested)
                    self.plugins_sidebar.uninstall_requested.connect(self.on_plugin_uninstall_requested)
                except Exception:
                    pass
                self.filters_layout.addWidget(self.plugins_sidebar)
            except Exception:
                pass
        elif view_id == "settings":
            self.sources_section.setVisible(False)
            self.filters_section.setVisible(False)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(False)
        else:
            self.sources_section.setVisible(True)
            self.filters_section.setVisible(True)
            if hasattr(self, 'sources_title_label'):
                self.sources_title_label.setVisible(True)
    
    def on_filter_selection_changed(self, filter_states):
        """Handle changes in filter selection"""
        # Apply filtering based on current view
        if self.current_view == "installed":
            self.apply_filters()
        elif self.current_view == "updates":
            self.apply_update_filters()
        elif self.current_view == "plugins":
            # Apply plugin status filters (Available/Installed)
            if hasattr(self, 'plugins_view') and self.plugins_view:
                self.plugins_view.apply_filters(filter_states)
    
    def update_discover_sources(self):
        """Update the discover sources using the new SourceCard component"""
        # Clear existing sources layout (except the title label)
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # Always create a new SourceCard component
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_source_selection_changed)
        self.source_card.search_mode_changed.connect(self.on_search_mode_changed)
        
        # Add the four main sources (exclude Local from Discover)
        sources = [
            ("pacman", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "node.svg")),
        ]
        
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        
        self.sources_layout.addWidget(self.source_card)
        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
        else:
            try:
                self.git_manager.create_git_section()
            except Exception:
                pass
        # Pin Docker containers card in Discover sidebar
        try:
            if not hasattr(self, 'docker_manager') or self.docker_manager is None:
                pass  # inlined
                self.docker_manager = DockerManager(self.log_signal, self.show_message, self.sources_layout, self)
            else:
                # Reattach/recreate the Docker section under the current sources layout
                try:
                    self.docker_manager.sources_layout = self.sources_layout
                except Exception:
                    pass
                try:
                    self.docker_manager.create_docker_section()
                except Exception:
                    pass
        except Exception:
            pass

    def update_updates_sources(self):
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        sources = [
            ("pacman", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "node.svg")),
            ("Local", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "local.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        self.sources_layout.addWidget(self.source_card)
        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
        else:
            try:
                # Recreate/Reattach the Git section under the current Sources card
                self.git_manager.create_git_section()
            except Exception:
                pass
        self.source_card.source_changed.connect(self.on_updates_source_changed)
        try:
            self.source_card.on_source_changed()
        except Exception:
            pass

    def update_installed_sources(self):
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_installed_source_changed)
        sources = [
            ("pacman", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        try:
            for obj_name in ("searchModeTitle",):
                w = self.source_card.findChild(QLabel, obj_name)
                if w:
                    w.setVisible(False)
            for rb in self.source_card.findChildren(QRadioButton, "searchModeRadio"):
                rb.setVisible(False)
        except Exception:
            pass
        self.sources_layout.addWidget(self.source_card)

    def update_plugins_sources(self):
        """Update plugins sources using the same SourceCard component as installed section"""
        # Clear existing sources layout (except the title label)
        while self.sources_layout.count() > 1:
            item = self.sources_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # Create source card for plugins (same as installed section)
        self.source_card = SourceCard(self)
        self.source_card.source_changed.connect(self.on_plugins_source_changed)
        sources = [
            ("pacman", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "pacman.svg")),
            ("AUR", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "aur.svg")),
            ("Flatpak", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "flatpack.svg")),
            ("npm", os.path.join(os.path.dirname(__file__), "assets", "icons", "discover", "node.svg"))
        ]
        for source_name, source_icon_path in sources:
            self.source_card.add_source(source_name, source_icon_path)
        try:
            for obj_name in ("searchModeTitle",):
                w = self.source_card.findChild(QLabel, obj_name)
                if w:
                    w.setVisible(False)
            for rb in self.source_card.findChildren(QRadioButton, "searchModeRadio"):
                rb.setVisible(False)
        except Exception:
            pass
        self.sources_layout.addWidget(self.source_card)

    def on_installed_source_changed(self, source_states):
        # Re-apply combined filters (source + status)
        self.apply_filters()

    def on_plugins_source_changed(self, source_states):
        # Apply source filters to plugins view
        if hasattr(self, 'plugins_view') and self.plugins_view:
            self.plugins_view.apply_source_filters(source_states)

    def on_updates_source_changed(self, source_states):
        base = getattr(self, 'updates_all', self.all_packages)
        show_pacman = source_states.get("pacman", True)
        show_aur = source_states.get("AUR", True)
        show_flatpak = source_states.get("Flatpak", True)
        show_npm = source_states.get("npm", True)
        show_local = source_states.get("Local", True)
        filtered = []
        for pkg in base:
            s = pkg.get('source')
            if s == 'pacman' and show_pacman:
                filtered.append(pkg)
            elif s == 'AUR' and show_aur:
                filtered.append(pkg)
            elif s == 'Flatpak' and show_flatpak:
                filtered.append(pkg)
            elif s == 'npm' and show_npm:
                filtered.append(pkg)
            elif s == 'Local' and show_local:
                filtered.append(pkg)
        self.all_packages = filtered
        self.current_page = 0
        self.package_table.setRowCount(0)
        self.display_page()
        self.update_load_more_visibility()
        # Refresh counts after filtering
        self.update_updates_header_counts()
        
        # Initialize Git Manager for sources panel
        if not hasattr(self, 'git_manager') or self.git_manager is None:
            pass  # inlined
            self.git_manager = GitManager(self.log_signal, self.show_message, self.sources_layout, self)
    
    def on_source_selection_changed(self, source_states):
        """Handle changes in source selection"""
        # Removed verbose log: self.log(f"Source selection changed: {source_states}")
        # Apply source filtering if we have search results
        if self.current_view == "discover" and hasattr(self, 'search_results') and self.search_results:
            self.display_discover_results(selected_sources=source_states)
    
    def on_search_mode_changed(self, search_mode):
        """Handle changes in search mode"""
        # Removed verbose log: self.log(f"Search mode changed to: {search_mode}")
        # Store the current search mode for future searches
        self.current_search_mode = search_mode
        # Re-run search if we have a current query
        current_query = self.search_input.text().strip()
        if current_query and self.current_view == "discover":
            self.search_discover_packages(current_query)
    
    def update_table_columns(self, view_id):
        if view_id == "installed":
            self.package_table.setColumnCount(6)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Package ID", "Version", "Source", "Status"])
            self.package_table.setObjectName("")  # Reset object name
            self.package_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.package_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.package_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        elif view_id == "bundles":
            self.package_table.setColumnCount(5)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Package ID", "Version", "Source"])
            self.package_table.setObjectName("bundlesTable")
            header = self.package_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 220)
            self.package_table.setColumnWidth(3, 140)
            self.package_table.setColumnWidth(4, 120)
            self.package_table.setShowGrid(False)
            self.package_table.setIconSize(QSize(20, 20))
            self.package_table.setWordWrap(True)
            self.package_table.verticalHeader().setDefaultSectionSize(56)
        elif view_id == "discover":
            self.package_table.setColumnCount(5)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Package ID", "Version", "Source"])
            self.package_table.setObjectName("discoverTable")  # Apply special styling
            header = self.package_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.package_table.setColumnWidth(0, 48)
            self.package_table.setColumnWidth(2, 220)
            self.package_table.setColumnWidth(3, 140)
            self.package_table.setColumnWidth(4, 120)
            self.package_table.setShowGrid(False)
            self.package_table.setIconSize(QSize(20, 20))
            self.package_table.setWordWrap(True)
            self.package_table.verticalHeader().setDefaultSectionSize(56)
        else:
            self.package_table.setColumnCount(6)
            self.package_table.setHorizontalHeaderLabels(["", "Package Name", "Package ID", "Version", "New Version", "Source"])
            self.package_table.setObjectName("")  # Reset object name
            self.package_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.package_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.package_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self.package_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    
    def load_updates(self):
        return packages_service.load_updates(self)
    
    def load_installed_packages(self):
        return packages_service.load_installed_packages(self)
    
    def on_packages_loaded(self, packages):
        # Ignore results if user has navigated away from the originating view
        if self.loading_context != self.current_view or self.current_view not in ("updates", "installed"):
            return
        self.all_packages = packages
        if self.current_view == "updates":
            self.updates_all = packages
        elif self.current_view == "installed":
            self.installed_all = packages
        self.current_page = 0
        self.packages_per_page = 10
        self.package_table.setRowCount(0)
        self.display_page()
        if self.current_view == "updates" and hasattr(self, 'source_card') and self.source_card:
            try:
                states = self.source_card.get_selected_sources()
                self.on_updates_source_changed(states)
            except Exception:
                pass
        elif self.current_view == "installed" and hasattr(self, 'source_card') and self.source_card:
            try:
                states = self.source_card.get_selected_sources()
                self.on_installed_source_changed(states)
            except Exception:
                pass
        
        
        # Hide loading spinner, stop animation, and show packages table
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        self.package_table.setVisible(True)
        # Show console toggle button for updates view like Discover
        try:
            if self.current_view in ("updates", "installed") and hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
                self.console_toggle_btn.setToolTip("Show Console")
        except Exception:
            pass
        # Update counts and nav badge
        if self.current_view == "updates":
            try:
                self.set_updates_count(len(self.updates_all or []))
            except Exception:
                pass
            self.update_updates_header_counts()
        elif self.current_view == "installed":
            self.update_installed_header_counts()
    
    def on_load_error(self):
        # Hide loading spinner, stop animation, and show packages table (empty)
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        self.package_table.setVisible(True)
        try:
            if self.current_view in ("updates", "installed") and hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
                self.console_toggle_btn.setToolTip("Show Console")
        except Exception:
            pass
        self.log("Failed to load packages. Please check the logs for details.")
    
    def cancel_installation(self):
        """Cancel the ongoing installation process"""
        if hasattr(self, 'install_cancel_event'):
            self.install_cancel_event.set()
            self.log("Installation cancellation requested...")
    
    def on_installation_progress(self, status, can_cancel):
        if status == "start":
            try:
                self._installing = True
            except Exception:
                pass
            self.load_more_btn.setVisible(False)
            self.loading_widget.set_message("Installing packages...")
            self.loading_widget.setVisible(True)
            self.loading_widget.start_animation()
            try:
                if hasattr(self, 'loading_container'):
                    self.loading_container.setVisible(True)
            except Exception:
                pass
            try:
                if hasattr(self, 'large_search_box'):
                    self.large_search_box.setVisible(False)
            except Exception:
                pass
            try:
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
            except Exception:
                pass
            try:
                self.package_table.setVisible(False)
            except Exception:
                pass
            # Keep console accessible via toggle, but hide the panel by default
            try:
                if hasattr(self, 'console_toggle_btn'):
                    self.console_toggle_btn.setVisible(True)
                    self.console_toggle_btn.setToolTip("Show Console")
                self.console_label.setVisible(False)
                self.console.setVisible(False)
            except Exception:
                pass
            self.cancel_install_btn.setVisible(can_cancel)
        elif status == "success":
            try:
                self._installing = False
            except Exception:
                pass
            self.loading_widget.set_message("Success")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly to show success, then hide
            QTimer.singleShot(1500, lambda: self.finish_installation_progress())
        elif status == "failed":
            try:
                self._installing = False
            except Exception:
                pass
            self.loading_widget.set_message("Install failed")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly to show failure, then hide
            QTimer.singleShot(2000, lambda: self.finish_installation_progress())
        elif status == "cancelled":
            try:
                self._installing = False
            except Exception:
                pass
            self.loading_widget.set_message("Installation cancelled")
            self.cancel_install_btn.setVisible(False)
            # Keep spinner visible briefly to show cancellation, then hide
            QTimer.singleShot(1500, lambda: self.finish_installation_progress())
    
    def finish_installation_progress(self):
        try:
            self._installing = False
        except Exception:
            pass
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        try:
            self.package_table.setVisible(True)
        except Exception:
            pass
        self.update_load_more_visibility()
    
    def update_load_more_visibility(self):
        if self.current_view == "discover":
            if hasattr(self, 'filtered_results') and self.filtered_results:
                total = len(self.filtered_results)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)
        elif self.current_view == "installed":
            if self.all_packages:
                total = len(self.all_packages)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)
        elif self.current_view == "updates":
            if self.all_packages:
                total = len(self.all_packages)
                displayed = (self.current_page + 1) * self.packages_per_page
                has_more = displayed < total
                self.load_more_btn.setVisible(has_more)
            else:
                self.load_more_btn.setVisible(False)
    
    def display_page(self):
        self.package_table.setUpdatesEnabled(False)
        start = self.current_page * self.packages_per_page
        end = start + self.packages_per_page
        page_packages = self.all_packages[start:end]
        
        for pkg in page_packages:
            if self.current_view == "installed":
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
            elif self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))
        
        self.package_table.setUpdatesEnabled(True)
        # Make sure nothing is selected by default
        try:
            self.package_table.clearSelection()
        except Exception:
            pass
        
        has_more = end < len(self.all_packages)
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = len(self.all_packages) - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        # Keep header subtitle accurate for Updates
        if self.current_view == "updates":
            self.update_updates_header_counts()
    
    def load_more_packages(self):
        self.current_page += 1
        start = self.current_page * self.packages_per_page
        end = start + self.packages_per_page
        
        if self.current_view == "discover":
            dataset = self.get_filtered_discover_results()
            if self.installed_index is None:
                try:
                    ss = self.source_card.get_selected_sources() if hasattr(self, 'source_card') and self.source_card else None
                except Exception:
                    ss = None
                self._ensure_installed_index_async(ss)
        else:
            dataset = self.search_results if self.search_results else self.all_packages
        
        page_packages = dataset[start:end]
        total = len(dataset)
        
        self.package_table.setUpdatesEnabled(False)
        for pkg in page_packages:
            if self.current_view == "installed":
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
            elif self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))
        self.package_table.setUpdatesEnabled(True)
        
        has_more = end < total
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = total - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        else:
            self.log("All results loaded")
        
        # Uncheck the newly loaded items
        old_count = self.package_table.rowCount() - len(page_packages)
        for i in range(old_count, self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(i)
            if checkbox is not None:
                checkbox.setChecked(False)
    
    def add_discover_row(self, pkg):
        row = self.package_table.rowCount()
        self.package_table.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setObjectName("tableCheckbox")
        checkbox.setChecked(False)
        self.apply_checkbox_accent(checkbox, pkg.get('source', ''))
        cb_container = QWidget()
        cb_container.setStyleSheet("background: transparent;")
        cb_layout = QHBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.addStretch()
        cb_layout.addWidget(checkbox)
        cb_layout.addStretch()
        self.package_table.setCellWidget(row, 0, cb_container)
        checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))
        
        name_item = QTableWidgetItem(pkg['name'])
        name_item.setToolTip(pkg['name'])
        font = QFont()
        font.setBold(True)
        name_item.setFont(font)
        icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
        name_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "packagename.svg"), 20))
        self.package_table.setItem(row, 1, name_item)
        id_item = QTableWidgetItem(pkg['id'])
        id_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "pacakgeid.svg"), 18))
        self.package_table.setItem(row, 2, id_item)
        ver_item = QTableWidgetItem(pkg['version'])
        ver_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "version.svg"), 18))
        self.package_table.setItem(row, 3, ver_item)
        source_chip = QWidget()
        source_chip.setObjectName("sourceChip")
        chip_layout = QHBoxLayout(source_chip)
        chip_layout.setContentsMargins(6, 2, 6, 2)
        chip_layout.setSpacing(6)
        chip_icon = QLabel()
        source_icon = self.get_source_icon(pkg.get('source', ''), 16)
        if not source_icon.isNull():
            chip_icon.setPixmap(source_icon.pixmap(16, 16))
        chip_layout.addWidget(chip_icon)
        chip_text = QLabel(pkg.get('source', ''))
        chip_layout.addWidget(chip_text)
        self.package_table.setCellWidget(row, 4, source_chip)
        try:
            installed = self.is_package_installed(pkg)
        except Exception:
            installed = False
        if installed:
            green = QColor(16, 185, 129)
            name_item.setForeground(green)
            id_item.setForeground(green)
            ver_item.setForeground(green)
            tip = "Already installed"
            name_item.setToolTip(tip)
            id_item.setToolTip(tip)
            ver_item.setToolTip(tip)
            try:
                chip_text.setStyleSheet("color: rgb(16,185,129);")
                source_chip.setToolTip(tip)
            except Exception:
                pass
            try:
                checkbox.setEnabled(False)
                checkbox.setToolTip(tip)
            except Exception:
                pass
    
    def add_package_row(self, name, pkg_id, version, new_version, source, pkg_data=None):
        row = self.package_table.rowCount()
        self.package_table.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setObjectName("tableCheckbox")
        # Always start unchecked in all views
        checkbox.setChecked(False)
        self.apply_checkbox_accent(checkbox, source if source else "")
        cb_container = QWidget()
        cb_container.setStyleSheet("background: transparent;")
        cb_layout = QHBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.addStretch()
        cb_layout.addWidget(checkbox)
        cb_layout.addStretch()
        self.package_table.setCellWidget(row, 0, cb_container)
        checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))
        
        name_item = QTableWidgetItem(name)
        font = QFont()
        font.setBold(True)
        name_item.setFont(font)
        icon_dir = os.path.join(os.path.dirname(__file__), "assets", "icons", "discover")
        name_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "packagename.svg"), 20))
        self.package_table.setItem(row, 1, name_item)
        id_item = QTableWidgetItem(pkg_id)
        id_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "pacakgeid.svg"), 18))
        self.package_table.setItem(row, 2, id_item)
        ver_item = QTableWidgetItem(version)
        ver_item.setIcon(self.get_svg_icon(os.path.join(icon_dir, "version.svg"), 18))
        self.package_table.setItem(row, 3, ver_item)
        
        if self.current_view == "installed" and pkg_data:
            self.package_table.setItem(row, 4, QTableWidgetItem(pkg_data.get('source', 'pacman')))
            status = "⬆️ Update available" if pkg_data.get('has_update') else "✓ Up to date"
            status_item = QTableWidgetItem(status)
            if pkg_data.get('has_update'):
                status_item.setForeground(QColor(255, 165, 0))
            else:
                status_item.setForeground(QColor(16, 185, 129))
            self.package_table.setItem(row, 5, status_item)
        elif self.package_table.columnCount() > 4:
            new_version_item = QTableWidgetItem(new_version)
            if self.current_view == "updates":
                # Make new version green to indicate available update
                new_version_item.setForeground(QColor(16, 185, 129))  # Green color
            self.package_table.setItem(row, 4, new_version_item)
            self.package_table.setItem(row, 5, QTableWidgetItem(source))
    
    def filter_packages(self):
        query = self.search_input.text().lower()
        
        if not query:
            if self.current_view == "discover":
                self.large_search_box.setVisible(True)
                self.package_table.setVisible(False)
                self.load_more_btn.setVisible(False)
                if hasattr(self, 'no_results_widget'):
                    self.no_results_widget.setVisible(False)
                self.package_table.setRowCount(0)
                self.header_info.setText("Search and discover new packages to install")
            elif self.current_view == "installed":
                self.apply_filters()
                return
            elif self.current_view == "updates":
                self.apply_update_filters()
                return
            else:
                return
        
        if self.current_view == "discover":
            self.search_discover_packages(query)
        else:
            self.search_results = [pkg for pkg in self.all_packages if query in pkg['name'].lower()]
            self.current_page = 0
            
            self.package_table.setUpdatesEnabled(False)
            self.package_table.setRowCount(0)
            
            start = 0
            end = min(10, len(self.search_results))
            for pkg in self.search_results[start:end]:
                if self.current_view == "installed":
                    self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'), pkg)
                else:
                    self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg.get('new_version', pkg['version']), pkg.get('source', 'pacman'))
            
            self.package_table.setUpdatesEnabled(True)
            
            has_more = end < len(self.search_results)
            self.load_more_btn.setVisible(has_more)
            if has_more:
                remaining = len(self.search_results) - end
                self.load_more_btn.setText(f"📥 Load More ({remaining} remaining)")
            if self.current_view == "updates":
                # Use search result count for matched in header
                try:
                    total = len(getattr(self, 'updates_all', []) or [])
                    matched = len(self.search_results or [])
                    self.header_info.setText(f"{total} packages were found, {matched} of which match the specified filters")
                except Exception:
                    pass
    
    def search_discover_packages(self, query):
        # Removed verbose search message: self.log(f"Searching for '{query}' in AUR, official repositories, and Flatpak...")
        self.package_table.setRowCount(0)
        self.search_results = []
        # Prepare discover loading context
        self.cancel_discover_search = False
        self.loading_context = "discover"

        try:
            if hasattr(self, 'source_card') and self.source_card:
                _src = self.source_card.get_selected_sources()
            else:
                _src = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        except Exception:
            _src = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        show_pacman = bool(_src.get("pacman", True))
        show_aur = bool(_src.get("AUR", True))
        show_flatpak = bool(_src.get("Flatpak", True))
        show_npm = bool(_src.get("npm", True))
        
        # Show loading spinner
        self.loading_widget.setVisible(True)
        self.loading_widget.set_message("Searching packages...")
        self.loading_widget.start_animation()
        self.package_table.setVisible(False)
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(True)
        except Exception:
            pass
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(False)
        except Exception:
            pass
        if hasattr(self, 'no_results_widget'):
            self.no_results_widget.setVisible(False)
        
        def search_in_thread():
            try:
                packages = []
                
                tokens = [t for t in query.split() if t]
                if show_pacman:
                    pacman_seen = set()
                    if len(tokens) > 1:
                        for tok in tokens:
                            try:
                                result = subprocess.run(["pacman", "-Ss", tok], capture_output=True, text=True, timeout=30)
                            except Exception:
                                result = None
                            if result and result.returncode == 0 and result.stdout:
                                lines = result.stdout.strip().split('\n')
                                i = 0
                                while i < len(lines):
                                    if lines[i].strip() and '/' in lines[i]:
                                        parts = lines[i].split()
                                        if len(parts) >= 2:
                                            name = parts[0].split('/')[-1]
                                            version = parts[1]
                                            description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                            key = ('pacman', name)
                                            if key not in pacman_seen:
                                                pacman_seen.add(key)
                                                packages.append({
                                                    'name': name,
                                                    'version': version,
                                                    'id': name,
                                                    'source': 'pacman',
                                                    'description': description,
                                                    'has_update': False
                                                })
                                    i += 1
                    else:
                        result = subprocess.run(["pacman", "-Ss", query], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0 and result.stdout:
                            lines = result.stdout.strip().split('\n')
                            i = 0
                            while i < len(lines):
                                if lines[i].strip() and '/' in lines[i]:
                                    parts = lines[i].split()
                                    if len(parts) >= 2:
                                        name = parts[0].split('/')[-1]
                                        version = parts[1]
                                        description = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                        packages.append({
                                            'name': name,
                                            'version': version,
                                            'id': name,
                                            'source': 'pacman',
                                            'description': description,
                                            'has_update': False
                                        })
                                i += 1

                if show_aur:
                    result_aur = subprocess.run(["curl", "-s", f"https://aur.archlinux.org/rpc/?v=5&type=search&by=name&arg={query}"], capture_output=True, text=True, timeout=10)
                    if result_aur.returncode == 0:
                        try:
                            data = json.loads(result_aur.stdout)
                            if data.get('results'):
                                for pkg in data['results']:
                                    packages.append({
                                        'name': pkg.get('Name', ''),
                                        'version': pkg.get('Version', ''),
                                        'id': pkg.get('Name', ''),
                                        'source': 'AUR',
                                        'description': pkg.get('Description', ''),
                                        'tags': ', '.join(pkg.get('Keywords', []))
                                    })
                        except Exception:
                            pass

                if show_flatpak:
                    try:
                        if not getattr(self, "_flathub_checked", False):
                            try:
                                self.ensure_flathub_user_remote()
                            except Exception:
                                pass
                            try:
                                self._flathub_checked = True
                            except Exception:
                                pass
                    except Exception:
                        pass
                    result_flatpak = subprocess.run([
                        "flatpak", "search", "--columns=application,name,description,version", query
                    ], capture_output=True, text=True, timeout=30)
                    if result_flatpak.returncode == 0 and result_flatpak.stdout:
                        lines = [l for l in result_flatpak.stdout.strip().split('\n') if l.strip()]
                        for line in lines:
                            ls = line.strip()
                            low = ls.lower()
                            if ('no match' in low) or ('no results' in low) or ('not found' in low):
                                continue
                            cols = line.split('\t')
                            if len(cols) < 2:
                                continue
                            app_id = cols[0].strip()
                            app_name = cols[1].strip() if cols[1].strip() else app_id
                            description = cols[2].strip() if len(cols) > 2 else ''
                            version = cols[3].strip() if len(cols) > 3 else ''
                            if app_id and ('no match' not in app_id.lower()) and ('not found' not in app_id.lower()):
                                packages.append({
                                    'name': app_name,
                                    'version': version,
                                    'id': app_id,
                                    'source': 'Flatpak',
                                    'description': description,
                                    'has_update': False
                                })

                if show_npm:
                    # Search npm packages
                    try:
                        result_npm = subprocess.run(["npm", "search", "--json", query], capture_output=True, text=True, timeout=30)
                        if result_npm.returncode == 0 and result_npm.stdout:
                            npm_data = json.loads(result_npm.stdout)
                            for pkg in npm_data:
                                packages.append({
                                    'name': pkg.get('name', ''),
                                    'version': pkg.get('version', ''),
                                    'id': pkg.get('name', ''),
                                    'source': 'npm',
                                    'description': pkg.get('description', ''),
                                    'has_update': False
                                })
                    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
                        # npm not available, try alternative method
                        pass
                
                # Only deliver results if still on Discover and not cancelled
                if not self.cancel_discover_search and self.loading_context == 'discover' and self.current_view == 'discover':
                    self.discover_results_ready.emit(packages)
            except Exception as e:
                self.log(f"Search error: {str(e)}")
        
        Thread(target=search_in_thread, daemon=True).start()

    def get_filtered_discover_results(self, selected_sources=None):
        if selected_sources is None:
            if hasattr(self, 'source_card') and self.source_card:
                selected_sources = self.source_card.get_selected_sources()
            else:
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        show_pacman = selected_sources.get("pacman", True)
        show_aur = selected_sources.get("AUR", True)
        show_flatpak = selected_sources.get("Flatpak", True)
        show_npm = selected_sources.get("npm", True)
        filtered = []
        for pkg in self.search_results:
            if pkg['source'] == 'pacman' and show_pacman:
                filtered.append(pkg)
            elif pkg['source'] == 'AUR' and show_aur:
                filtered.append(pkg)
            elif pkg['source'] == 'Flatpak' and show_flatpak:
                filtered.append(pkg)
            elif pkg['source'] == 'npm' and show_npm:
                filtered.append(pkg)
        query = self.search_input.text().strip().lower()
        search_mode = self.current_search_mode
        def get_sort_key(pkg):
            name_lower = pkg['name'].lower()
            id_lower = pkg['id'].lower()
            desc_lower = (pkg.get('description') or '').lower()
            exact = (name_lower == query) or (id_lower == query)
            starts = name_lower.startswith(query) or id_lower.startswith(query)
            contains = (query in name_lower) or (query in id_lower)
            desc_contains = (query in desc_lower)
            source_priority = {'pacman': 3, 'AUR': 2, 'Flatpak': 1, 'npm': 0}.get(pkg.get('source'), 0)
            if search_mode == 'name':
                exact_flag = (name_lower == query)
                starts_flag = name_lower.startswith(query)
                contains_flag = (query in name_lower)
                return (exact_flag, starts_flag, contains_flag, source_priority, desc_contains)
            elif search_mode == 'id':
                exact_flag = (id_lower == query)
                starts_flag = id_lower.startswith(query)
                contains_flag = (query in id_lower)
                return (exact_flag, starts_flag, contains_flag, source_priority, desc_contains)
            else:
                return (exact, starts, contains, source_priority, desc_contains)
        filtered.sort(key=get_sort_key, reverse=True)
        return filtered

    def display_discover_results(self, packages=None, selected_sources=None):
        # Safety: do nothing if the user is no longer on Discover
        if self.current_view != "discover" or self.loading_context != "discover":
            return
        if packages is not None:
            self.search_results = packages
        
        # Hide loading spinner and show package table
        self.loading_widget.setVisible(False)
        self.loading_widget.stop_animation()
        try:
            if hasattr(self, 'loading_container'):
                self.loading_container.setVisible(False)
        except Exception:
            pass
        self.package_table.setVisible(True)
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setVisible(True)
        except Exception:
            pass
        
        if selected_sources is None:
            # Get selected sources from the SourceCard component
            selected_sources = {}
            if hasattr(self, 'source_card') and self.source_card:
                selected_sources = self.source_card.get_selected_sources()
            else:
                # Fallback to showing all sources if component not initialized
                selected_sources = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}
        
        filtered = self.get_filtered_discover_results(selected_sources)
        self.filtered_results = filtered
        self.current_page = 0
        query = self.search_input.text().strip()
        
        self.package_table.setUpdatesEnabled(False)
        self.package_table.setRowCount(0)
        self._ensure_installed_index_async(selected_sources)
        
        start = 0
        end = min(self.packages_per_page, len(filtered))
        for pkg in filtered[start:end]:
            if self.current_view == "discover":
                self.add_discover_row(pkg)
            else:
                self.add_package_row(pkg['name'], pkg['id'], pkg['version'], pkg['version'], pkg['source'])
        
        self.package_table.setUpdatesEnabled(True)
        
        has_more = end < len(filtered)
        self.load_more_btn.setVisible(has_more)
        if has_more:
            remaining = len(filtered) - end
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        
        # Provide feedback if no results match
        if not filtered:
            self.header_info.setText(f"No packages found matching '{query}'.")
            self.package_table.setVisible(False)
            if hasattr(self, 'no_results_widget'):
                self.no_results_desc.setText(f"No packages found matching '{query}'.")
                self.no_results_widget.setVisible(True)
        else:
            count = len(filtered)
            self.header_info.setText(f"{count} packages were found, {count} of which match the specified filters")
            if hasattr(self, 'no_results_widget'):
                self.no_results_widget.setVisible(False)
            self.package_table.setVisible(True)

    def refresh_packages(self):
        if self.current_view == "updates":
            self.load_updates()
        elif self.current_view == "installed":
            self.load_installed_packages()
        elif self.current_view == "discover":
            query = self.search_input.text().strip()
            if query:
                self.search_discover_packages(query)
            else:
                self.package_table.setRowCount(0)
                # Removed verbose log: self.log("Type a package name to search in AUR and official repositories")
    
    def update_selected(self):
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                id_item = self.package_table.item(row, 2)
                # Source column differs by view: Updates has Source at col 5; Installed at col 4
                source_col = 5 if self.current_view == "updates" else 4
                source_item = self.package_table.item(row, source_col)
                # On Installed view, only update rows that actually have an update available
                if self.current_view == "installed":
                    status_item = self.package_table.item(row, 5)
                    if not status_item or "Update" not in (status_item.text() or ""):
                        continue
                if not name_item:
                    continue
                pkg_name = name_item.text().strip()
                pkg_id = id_item.text().strip() if id_item else pkg_name
                source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                token = pkg_id if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(token)
        if not packages_by_source:
            self.log("No packages selected for update")
            return
        self.log(f"Selected packages for update: {', '.join([f'{pkg} ({source})' for source, pkgs in packages_by_source.items() for pkg in pkgs])}")
        update_service.update_packages(self, packages_by_source)
    
    def ignore_selected(self):
        return ignore_service.ignore_selected(self)
    
    def manage_ignored(self):
        return ignore_service.manage_ignored(self)

    def get_source_text(self, row, view_id=None):
        vid = view_id or self.current_view
        try:
            if vid in ("discover", "bundles"):
                cell = self.package_table.cellWidget(row, 4)
                if cell:
                    labels = cell.findChildren(QLabel)
                    if labels:
                        return labels[-1].text()
                return ""
            elif vid == "updates":
                itm = self.package_table.item(row, 5)
                return itm.text() if itm else ""
            elif vid == "installed":
                itm = self.package_table.item(row, 4)
                return itm.text() if itm else ""
        except Exception:
            return ""
        return ""

    def get_row_info(self, row, view_id=None):
        vid = view_id or self.current_view
        name_item = self.package_table.item(row, 1)
        id_item = self.package_table.item(row, 2)
        version_item = self.package_table.item(row, 3)
        name = name_item.text().strip() if name_item else ""
        pkg_id = id_item.text().strip() if id_item else name
        version = version_item.text().strip() if version_item else ""
        source = self.get_source_text(row, vid)
        return {"name": name, "id": pkg_id, "version": version, "source": source}
    
    def build_installed_index(self, selected_sources=None, force=False):
        idx = self.installed_index if (self.installed_index is not None and not force) else {'pacman': set(), 'AUR': set(), 'Flatpak': set(), 'npm': set()}
        show_pacman = show_aur = show_flatpak = show_npm = True
        if selected_sources is not None:
            try:
                show_pacman = bool(selected_sources.get("pacman", True))
                show_aur = bool(selected_sources.get("AUR", True))
                show_flatpak = bool(selected_sources.get("Flatpak", True))
                show_npm = bool(selected_sources.get("npm", True))
            except Exception:
                pass
        needed = set()
        if show_pacman or show_aur:
            needed.update(["pacman", "AUR"])
        if show_flatpak:
            needed.add("Flatpak")
        if show_npm:
            needed.add("npm")
        now = time.time()
        if (not force) and self.installed_index is not None:
            if (now - (self._installed_index_last_built or 0) < 10) and needed.issubset(self._installed_index_sources or set()):
                return
        built_any = False
        try:
            if (force or (('pacman' not in self._installed_index_sources) or ('AUR' not in self._installed_index_sources))) and (show_pacman or show_aur):
                r = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout:
                    names = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
                    idx['pacman'].update(names)
                    idx['AUR'].update(names)
                    self._installed_index_sources.update(["pacman", "AUR"])
                    built_any = True
        except Exception:
            pass
        try:
            import shutil as _sh
            if (force or ('Flatpak' not in self._installed_index_sources)) and show_flatpak and _sh.which('flatpak'):
                installed_flatpak = set()
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application"]
                        fp = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if fp.returncode == 0 and fp.stdout:
                            for ln in [x for x in fp.stdout.strip().split('\n') if x.strip()]:
                                app_id = ln.split('\t')[0].strip()
                                if app_id:
                                    installed_flatpak.add(app_id)
                    except Exception:
                        continue
                idx['Flatpak'].update(installed_flatpak)
                self._installed_index_sources.add("Flatpak")
                built_any = True
        except Exception:
            pass
        try:
            import shutil as _sh
            if (force or ('npm' not in self._installed_index_sources)) and show_npm and _sh.which('npm'):
                results = []
                np_def = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, timeout=30)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=30)
                results.append((np_user.returncode, np_user.stdout))
                for code, out in results:
                    if code == 0 and out and out.strip():
                        try:
                            data = json.loads(out)
                            deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                            for name in deps.keys():
                                idx['npm'].add(name)
                        except Exception:
                            pass
                self._installed_index_sources.add("npm")
                built_any = True
        except Exception:
            pass
        self.installed_index = idx
        if built_any:
            self._installed_index_last_built = now

    def is_package_installed(self, pkg):
        try:
            src = pkg.get('source', '')
            name = (pkg.get('id') or '').strip() if src == 'Flatpak' else (pkg.get('name') or '').strip()
            index = self.installed_index or {}
            return bool(name) and (name in (index.get(src) or set()))
        except Exception:
            return False
    
    def add_selected_to_bundle(self):
        return bundle_service.add_selected_to_bundle(self)

    def refresh_bundles_table(self):
        return bundle_service.refresh_bundles_table(self)

    def export_bundle(self):
        return bundle_service.export_bundle(self)

    def import_bundle(self):
        return bundle_service.import_bundle(self)

    def remove_selected_from_bundle(self):
        return bundle_service.remove_selected_from_bundle(self)

    def clear_bundle(self):
        return bundle_service.clear_bundle(self)

    def install_bundle(self):
        return bundle_service.install_bundle(self)

    def add_selected_to_community(self):
        return bundle_service.add_selected_to_community(self)
    
    def install_selected(self):
        packages_by_source = {}
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None and checkbox.isChecked():
                name_item = self.package_table.item(row, 1)
                id_item = self.package_table.item(row, 2)
                pkg_name = name_item.text().strip() if name_item else ''
                pkg_id = id_item.text().strip() if id_item else pkg_name
                if self.current_view == "discover":
                    source = ""
                    chip = self.package_table.cellWidget(row, 4)
                    if chip is not None:
                        labels = chip.findChildren(QLabel)
                        if labels:
                            source = labels[-1].text()
                else:
                    source_item = self.package_table.item(row, 5)
                    source = source_item.text() if source_item else "pacman"
                if source not in packages_by_source:
                    packages_by_source[source] = []
                install_token = pkg_id if source == 'Flatpak' else pkg_name
                packages_by_source[source].append(install_token)
        
        if not packages_by_source:
            self.log_signal.emit("No packages selected for installation")
            return
        # Filter out already installed packages
        try:
            if self.current_view == "discover":
                sel_src = {s: True for s in packages_by_source.keys()}
            else:
                sel_src = None
            self.build_installed_index(sel_src)
        except Exception:
            pass
        to_install = {}
        idx = self.installed_index or {}
        for source, pkgs in packages_by_source.items():
            installed_set = idx.get(source) or set()
            remaining = [p for p in pkgs if p not in installed_set]
            if remaining:
                to_install[source] = remaining
        if not to_install:
            self.log_signal.emit("All selected packages are already installed")
            return
        self.log_signal.emit(f"Selected packages: {', '.join([f'{pkg} ({source})' for source, pkgs in to_install.items() for pkg in pkgs])}")
        self.log_signal.emit(f"Proceeding with installation...")
        install_service.install_packages(self, to_install)

    def _prewarm_installed_index_async(self):
        try:
            def _run():
                try:
                    sel = {"pacman": True, "AUR": True, "Flatpak": False, "npm": False}
                    self.build_installed_index(sel)
                except Exception:
                    pass
            Thread(target=_run, daemon=True).start()
        except Exception:
            pass
    
    def _ensure_installed_index_async(self, selected_sources=None):
        try:
            if self._installed_index_building:
                return
            self._installed_index_building = True
            def _run():
                try:
                    self.build_installed_index(selected_sources)
                finally:
                    self._installed_index_building = False
                    QTimer.singleShot(0, self._mark_installed_in_visible_rows)
            Thread(target=_run, daemon=True).start()
        except Exception:
            self._installed_index_building = False
    
    def _mark_installed_in_visible_rows(self):
        try:
            if self.current_view != "discover" or not self.installed_index:
                return
            green = QColor(16, 185, 129)
            for row in range(self.package_table.rowCount()):
                name_item = self.package_table.item(row, 1)
                id_item = self.package_table.item(row, 2)
                ver_item = self.package_table.item(row, 3)
                if not name_item or not id_item or not ver_item:
                    continue
                chip = self.package_table.cellWidget(row, 4)
                src = self.get_source_text(row, "discover")
                pkg = {"name": name_item.text().strip(), "id": id_item.text().strip(), "source": src}
                if self.is_package_installed(pkg):
                    name_item.setForeground(green)
                    id_item.setForeground(green)
                    ver_item.setForeground(green)
                    tip = "Already installed"
                    name_item.setToolTip(tip)
                    id_item.setToolTip(tip)
                    ver_item.setToolTip(tip)
                    if chip is not None:
                        try:
                            labels = chip.findChildren(QLabel)
                            if labels:
                                labels[-1].setStyleSheet("color: rgb(16,185,129);")
                            chip.setToolTip(tip)
                        except Exception:
                            pass
                    try:
                        checkbox = self.get_row_checkbox(row)
                        if checkbox is not None:
                            checkbox.setEnabled(False)
                            checkbox.setToolTip(tip)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def uninstall_selected(self):
        selected_rows = self.package_table.selectionModel().selectedRows()
        if not selected_rows:
            self.log("No packages selected for uninstallation")
            return
        
        # Group selections by source
        packages_by_source = {}
        for model_index in selected_rows:
            row = model_index.row()
            name_item = self.package_table.item(row, 1)
            id_item = self.package_table.item(row, 2)
            source_item = self.package_table.item(row, 4)
            if not name_item or not source_item:
                continue
            name = (name_item.text() or "").strip()
            pkg_id = (id_item.text() or name).strip() if id_item else name
            source = (source_item.text() or "pacman").strip()
            if source not in packages_by_source:
                packages_by_source[source] = []
            token = pkg_id if source == 'Flatpak' else name
            packages_by_source[source].append(token)
        
        flat_summary = ', '.join([f"{pkg} ({src})" for src, pkgs in packages_by_source.items() for pkg in pkgs])
        self.log(f"Selected for uninstallation: {flat_summary}")
        uninstall_service.uninstall_packages(self, packages_by_source)
    
    def apply_filters(self):
        return filters_service.apply_filters(self)

    def apply_update_filters(self):
        return filters_service.apply_update_filters(self)

    def on_selection_changed(self):
        selected_rows = set(index.row() for index in self.package_table.selectionModel().selectedRows())
        for row in range(self.package_table.rowCount()):
            checkbox = self.get_row_checkbox(row)
            if checkbox is not None:
                checkbox.setChecked(row in selected_rows)
    
    def on_checkbox_changed(self, row, state):
        model = self.package_table.selectionModel()
        if state == Qt.CheckState.Checked.value:
            model.select(self.package_table.model().index(row, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        else:
            model.select(self.package_table.model().index(row, 0), QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows)
    
    def select_all_sources(self):
        for checkbox in self.source_checkboxes.values():
            checkbox.setChecked(True)
    
    def clear_sources(self):
        for checkbox in self.source_checkboxes.values():
            checkbox.setChecked(False)
    
    def load_settings(self):
        return settings_service.load_settings()
    
    def save_settings(self):
        return settings_service.save_settings(self.settings, self.log)
    
    def get_user_plugins_dir(self):
        p = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'plugins')
        try:
            os.makedirs(p, exist_ok=True)
        except Exception:
            pass
        return p
    
    def scan_plugins(self):
        plugs = []
        try:
            user_dir = self.get_user_plugins_dir()
            for fn in sorted(os.listdir(user_dir)):
                if fn.endswith('.py'):
                    plugs.append({'name': os.path.splitext(fn)[0], 'path': os.path.join(user_dir, fn), 'location': 'User'})
        except Exception:
            pass
        return plugs
    
    def build_settings_ui(self):
        # Clear existing layout
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create main horizontal layout for sidebar + content
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create left sidebar for navigation
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("""
            QFrame#settingsSidebar {
                background-color: #1a1a1a;
                border: none;
            }
            QPushButton {
                text-align: left;
                padding: 18px 24px;
                border: none;
                background-color: transparent;
                color: #a0a0a0;
                font-size: 15px;
                font-weight: 500;
                border-radius: 8px;
                margin: 3px 20px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: rgba(13, 115, 119, 0.2);
                color: #0d7377;
                font-weight: 600;
                border: 1px solid rgba(13, 115, 119, 0.3);
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(6)
        
        # Create navigation buttons
        self.settings_nav_buttons = {}
        
        # Add a header label
        header_label = QLabel("SETTINGS")
        header_label.setStyleSheet("""
            color: #777;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.2px;
            padding: 12px 24px;
            margin-top: 12px;
            margin-bottom: 8px;
        """)
        sidebar_layout.addWidget(header_label)
        
        btn_general = QPushButton("General")
        btn_general.setCheckable(True)
        btn_general.setChecked(True)
        btn_general.clicked.connect(lambda: self.switch_settings_category("general"))
        self.settings_nav_buttons["general"] = btn_general
        sidebar_layout.addWidget(btn_general)
        
        btn_auto_update = QPushButton("Auto Update")
        btn_auto_update.setCheckable(True)
        btn_auto_update.clicked.connect(lambda: self.switch_settings_category("auto_update"))
        self.settings_nav_buttons["auto_update"] = btn_auto_update
        sidebar_layout.addWidget(btn_auto_update)
        
        btn_plugins = QPushButton("Plugins")
        btn_plugins.setCheckable(True)
        btn_plugins.clicked.connect(lambda: self.switch_settings_category("plugins"))
        self.settings_nav_buttons["plugins"] = btn_plugins
        sidebar_layout.addWidget(btn_plugins)
        
        sidebar_layout.addStretch()
        
        # Add version info at bottom
        version_label = QLabel("NeoArch v1.0")
        version_label.setStyleSheet("""
            color: #555;
            font-size: 11px;
            padding: 12px 20px;
        """)
        sidebar_layout.addWidget(version_label)
        
        # Create right content area
        content_area = QFrame()
        content_area.setObjectName("settingsContent")
        content_area.setStyleSheet("""
            QFrame#settingsContent {
                background-color: #1e1e1e;
                border-radius: 12px;
                margin: 24px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        
        self.settings_content_layout = QVBoxLayout(content_area)
        self.settings_content_layout.setContentsMargins(24, 24, 24, 24)
        self.settings_content_layout.setSpacing(16)
        
        # Create and store settings widgets
        self.settings_widgets = {
            "general": GeneralSettingsWidget(self),
            "auto_update": AutoUpdateSettingsWidget(self),
            "plugins": PluginsSettingsWidget(self)
        }
        
        # Add widgets to content area (initially show general)
        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == "general")
            self.settings_content_layout.addWidget(widget)
        
        self.settings_content_layout.addStretch()
        
        # Add sidebar and content to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, 1)
        
        # Add main layout to settings layout
        container_widget = QWidget()
        container_widget.setLayout(main_layout)
        self.settings_layout.addWidget(container_widget)
    
    def switch_settings_category(self, category):
        """Switch between settings categories"""
        # Update button states
        for key, btn in self.settings_nav_buttons.items():
            btn.setChecked(key == category)
        
        # Show/hide appropriate widget
        for key, widget in self.settings_widgets.items():
            widget.setVisible(key == category)
    
    def build_general_settings(self, layout):
        box = QGroupBox("General Settings")
        grid = QGridLayout(box)
        cb_auto = QCheckBox("Auto check updates on launch")
        cb_auto.setChecked(bool(self.settings.get('auto_check_updates')))
        cb_auto.toggled.connect(lambda v: self.update_setting('auto_check_updates', v))
        grid.addWidget(cb_auto, 0, 0, 1, 2)
        cb_local = QCheckBox("Include Local source (custom scripts)")
        cb_local.setChecked(bool(self.settings.get('include_local_source')))
        cb_local.toggled.connect(lambda v: self.update_setting('include_local_source', v))
        grid.addWidget(cb_local, 1, 0, 1, 2)
        cb_npm = QCheckBox("Use npm user mode for global installs")
        cb_npm.setChecked(bool(self.settings.get('npm_user_mode')))
        cb_npm.toggled.connect(lambda v: self.update_setting('npm_user_mode', v))
        grid.addWidget(cb_npm, 2, 0, 1, 2)
        layout.addWidget(box)
        
        path_box = QGroupBox("Bundle Autosave")
        pgrid = QGridLayout(path_box)
        cb_bsave = QCheckBox("Autosave bundle to file")
        cb_bsave.setChecked(bool(self.settings.get('bundle_autosave', True)))
        cb_bsave.toggled.connect(lambda v: self.update_setting('bundle_autosave', v))
        pgrid.addWidget(cb_bsave, 0, 0, 1, 3)
        from_path = self.settings.get('bundle_autosave_path') or os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass
        path_edit = QLineEdit(from_path)
        browse_btn = QPushButton("Browse…")
        def on_browse():
            path, _ = QFileDialog.getSaveFileName(self, "Select Bundle Autosave Path", from_path, "Bundle JSON (*.json)")
            if path:
                path_edit.setText(path)
                self.update_setting('bundle_autosave_path', path)
        browse_btn.clicked.connect(on_browse)
        pgrid.addWidget(QLabel("Autosave path:"), 1, 0)
        pgrid.addWidget(path_edit, 1, 1)
        pgrid.addWidget(browse_btn, 1, 2)
        layout.addWidget(path_box)
        
        # Auto Update Settings
        auto_update_box = QGroupBox("Auto Update")
        auto_grid = QGridLayout(auto_update_box)
        cb_auto_update = QCheckBox("Enable automatic updates")
        cb_auto_update.setChecked(bool(self.settings.get('auto_update_enabled')))
        cb_auto_update.toggled.connect(lambda v: self.update_setting('auto_update_enabled', v))
        auto_grid.addWidget(cb_auto_update, 0, 0, 1, 2)
        
        auto_grid.addWidget(QLabel("Update interval (hours):"), 1, 0)
        interval_spin = QSpinBox()
        interval_spin.setRange(1, 168)  # 1 hour to 1 week
        interval_spin.setValue(int(self.settings.get('auto_update_interval_hours', 24)))
        interval_spin.valueChanged.connect(lambda v: self.update_setting('auto_update_interval_hours', v))
        auto_grid.addWidget(interval_spin, 1, 1)
        
        layout.addWidget(auto_update_box)
        
        # Snapshot Settings
        snapshot_box = QGroupBox("Snapshots")
        snap_grid = QGridLayout(snapshot_box)
        cb_snapshot = QCheckBox("Create snapshot before updates")
        cb_snapshot.setChecked(bool(self.settings.get('snapshot_before_update')))
        cb_snapshot.toggled.connect(lambda v: self.update_setting('snapshot_before_update', v))
        snap_grid.addWidget(cb_snapshot, 0, 0, 1, 2)
        
        snap_btns = QHBoxLayout()
        create_snap_btn = QPushButton("Create Snapshot")
        create_snap_btn.clicked.connect(self.create_snapshot)
        snap_btns.addWidget(create_snap_btn)
        
        revert_snap_btn = QPushButton("Revert to Snapshot")
        revert_snap_btn.clicked.connect(self.revert_to_snapshot)
        snap_btns.addWidget(revert_snap_btn)
        
        delete_snap_btn = QPushButton("Delete Snapshots")
        delete_snap_btn.clicked.connect(self.delete_snapshots)
        snap_btns.addWidget(delete_snap_btn)
        
        snap_btns.addStretch()
        snap_grid.addLayout(snap_btns, 1, 0, 1, 2)
        
        layout.addWidget(snapshot_box)
        
        btns = QHBoxLayout()
        btn_export = QPushButton("Export Settings")
        btn_export.clicked.connect(self.export_settings)
        btn_import = QPushButton("Import Settings")
        btn_import.clicked.connect(self.import_settings)
        btns.addWidget(btn_export)
        btns.addWidget(btn_import)
        btns.addStretch()
    
    def update_setting(self, key, value):
        """Public method for updating a setting value."""
        self.settings[key] = value
        self.save_settings()
    
    def export_settings(self):
        return settings_service.export_settings(self)
    
    def import_settings(self):
        return settings_service.import_settings(self)
    
    # -------------------- Plugin runtime --------------------
    def initialize_plugins(self):
        try:
            self.ensure_default_plugins(force_enable=True)
            self.reload_plugins()
            self.run_plugin_hook('on_startup')
            try:
                self.plugin_timer.start()
            except Exception:
                pass
        except Exception as e:
            self.log(f"Plugin init error: {e}")
    
    def ensure_default_plugins(self, force_enable=False):
        user_dir = self.get_user_plugins_dir()
        defaults = {
            'auto_check_updates.py': (
                """
def on_startup(app):
    try:
        if app.settings.get('auto_check_updates', True):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(800, lambda: app.switch_view("updates"))
    except Exception as e:
        try:
            app.log(f"auto_check_updates plugin: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'flathub_remote.py': (
                """
def on_startup(app):
    try:
        app.ensure_flathub_user_remote()
    except Exception as e:
        try:
            app.log(f"flathub_remote plugin: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'bundle_autoload.py': (
                """
from PyQt6.QtCore import QTimer
import os, json

def on_view_changed(app, view_id):
    if view_id != "bundles":
        return
    try:
        base = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'bundles')
        path = os.path.join(base, 'default.json')
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list):
            return
        existing = {(i.get('source'), (i.get('id') or i.get('name'))) for i in app.bundle_items}
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            src = (it.get('source') or '').strip()
            nm = (it.get('name') or '').strip()
            pid = (it.get('id') or nm).strip()
            if not src or not nm:
                continue
            key = (src, pid or nm)
            if key not in existing:
                app.bundle_items.append({'name': nm, 'id': pid or nm, 'version': (it.get('version') or '').strip(), 'source': src})
                existing.add(key)
                added += 1
        if added:
            try:
                app.refresh_bundles_table()
            except Exception:
                pass
            try:
                app._show_message("Bundle", f"Loaded {added} items from default bundle")
            except Exception:
                pass
    except Exception as e:
        try:
            app.log(f"bundle_autoload plugin: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'notify_install.py': (
                """
from PyQt6.QtWidgets import QMessageBox

def on_startup(app):
    try:
        app.installation_progress.connect(lambda status, can_cancel: _on_status(app, status))
    except Exception:
        pass

def _on_status(app, status):
    try:
        if status == "success":
            QMessageBox.information(app, "Install", "Installation complete.")
        elif status == "failed":
            QMessageBox.warning(app, "Install", "Installation failed. See console for details.")
        elif status == "cancelled":
            QMessageBox.information(app, "Install", "Installation cancelled.")
    except Exception:
        try:
            app._show_message("Install", status)
        except Exception:
            pass
                """.strip()
            ),
            'bundle_autosave.py': (
                """
import os, json, hashlib

_last_hash = None

def _hash_items(items):
    try:
        s = json.dumps(items or [], sort_keys=True)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()
    except Exception:
        return None

def _save(app):
    try:
        if not app.settings.get('bundle_autosave', True):
            return
        path = app.settings.get('bundle_autosave_path')
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        items = list(app.bundle_items)
        global _last_hash
        h = _hash_items(items)
        if h and h == _last_hash:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'app': 'NeoArch', 'items': items}, f, indent=2)
        _last_hash = h
        try:
            app._show_message('Bundle', f'Autosaved bundle to {path}')
        except Exception:
            pass
    except Exception as e:
        try:
            app.log(f"bundle_autosave plugin: {e}")
        except Exception:
            pass

def on_view_changed(app, view_id):
    if view_id == 'bundles':
        _save(app)

def on_tick(app):
    _save(app)
                """.strip()
            ),
            'auto_refresh_updates.py': (
                """
import time

_last = 0

def on_tick(app):
    global _last
    try:
        minutes = int(app.settings.get('auto_refresh_updates_minutes') or 0)
    except Exception:
        minutes = 0
    if minutes <= 0:
        return
    now = time.time()
    if _last and now - _last < minutes * 60:
        return
    _last = now
    try:
        if app.current_view == 'updates':
            app.load_updates()
    except Exception as e:
        try:
            app.log(f"auto_refresh_updates: {e}")
        except Exception:
            pass
                """.strip()
            ),
            'auto_update.py': (
                """
import time
import subprocess
import os
import json

_last_update = 0
_last_check = 0
_state_file = os.path.join(os.path.expanduser('~'), '.config', 'aurora', 'last_update.json')

def _load_state():
    try:
        with open(_state_file, 'r') as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _save_state(data):
    try:
        os.makedirs(os.path.dirname(_state_file), exist_ok=True)
        with open(_state_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

_state = _load_state()
_last_update = float(_state.get('last_update', 0) or 0)
_last_check = float(_state.get('last_check', 0) or 0)

def on_tick(app):
    global _last_update, _last_check, _state
    try:
        if not app.settings.get('auto_update_enabled', False):
            return
        days = int(app.settings.get('auto_update_interval_days', 7))
        interval_seconds = days * 24 * 3600
        now = time.time()
        if _last_check and now - _last_check < 3600:
            return
        _last_check = now
        _state['last_check'] = _last_check
        _save_state(_state)
        if _last_update and now - _last_update < interval_seconds:
            return
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(app, "Scheduled Update",
            f"It's been {days} days since the last update.\n\n"
            "Would you like to update your system now?\n\n"
            "This will update packages and create snapshots if enabled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if reply != QMessageBox.StandardButton.Yes:
            return
        _last_update = now
        _state['last_update'] = _last_update
        _save_state(_state)
        if app.settings.get('snapshot_before_update', False):
            try:
                if app.cmd_exists("timeshift"):
                    try:
                        result = subprocess.run(["timeshift", "--list"], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            snapshot_count = sum(1 for line in lines if line.strip() and not line.startswith('Num') and not line.startswith('---'))
                            if snapshot_count > 2:
                                delete_result = subprocess.run(["pkexec", "timeshift", "--delete-all", "--skip", "2"], capture_output=True, text=True, timeout=300)
                                if delete_result.returncode == 0:
                                    app.log("Auto-update: Cleaned up old snapshots (kept latest 2)")
                                else:
                                    app.log(f"Auto-update: Failed to clean up snapshots: {delete_result.stderr}")
                    except Exception as e:
                        app.log(f"Auto-update: Error checking snapshots: {e}")
                    timestamp = subprocess.run(["date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True).stdout.strip()
                    comment = f"NeoArch pre-update snapshot {timestamp}"
                    result = subprocess.run(["pkexec", "timeshift", "--create", "--comments", comment], capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        app.log(f"Auto-update: Pre-update snapshot created: {comment}")
                        app.show_message.emit("Snapshot", f"Pre-update snapshot created: {comment}")
                    else:
                        app.log(f"Auto-update: Failed to create pre-update snapshot: {result.stderr}")
            except Exception as e:
                app.log(f"Auto-update: Pre-update snapshot creation failed: {e}")
        update_success = False
        try:
            app.log("Auto-update: Starting scheduled system updates...")
            if app.cmd_exists("pacman"):
                pass  # inlined
                env, _ = app.prepare_askpass_env()
                auth_cmd = get_auth_command(env)
                cmd = auth_cmd + ["pacman", "-Syu", "--noconfirm"]
                app.log(f"Auto-update: Using {auth_cmd[0]} for pacman")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
                if result.returncode == 0:
                    app.log("Auto-update: Pacman updates completed successfully")
                    update_success = True
                    app.show_message.emit("Auto Update", "System packages updated successfully")
                else:
                    app.log(f"Auto-update: Pacman update failed: {result.stderr}")
                    app.show_message.emit("Auto Update", f"Pacman update failed: {result.stderr}")
            # Update AUR packages using any available AUR helper
            aur_helper = sys_utils.get_aur_helper(app.settings.get('aur_helper', 'auto') if app.settings.get('aur_helper', 'auto') != 'auto' else None)
            if aur_helper:
                try:
                    env, _ = app.prepare_askpass_env()
                    result = subprocess.run([aur_helper, "-Syu", "--noconfirm", "--sudoflags", "-A"], capture_output=True, text=True, timeout=1800, env=env)
                    if result.returncode == 0:
                        app.log(f"Auto-update: AUR updates completed successfully using {aur_helper}")
                        update_success = True
                    else:
                        app.log(f"Auto-update: AUR update failed: {result.stderr}")
                except Exception as e:
                    app.log(f"Auto-update: AUR update error: {e}")
            if app.cmd_exists("flatpak"):
                scopes = [["--user"], ["--system"]] if app.cmd_exists("sudo") else [["--user"]]
                for scope in scopes:
                    try:
                        result = subprocess.run(["flatpak"] + scope + ["update", "-y"], capture_output=True, text=True, timeout=900)
                        if result.returncode == 0:
                            app.log(f"Auto-update: Flatpak {scope[0]} updates completed")
                            update_success = True
                        else:
                            app.log(f"Auto-update: Flatpak {scope[0]} update failed: {result.stderr}")
                    except Exception as e:
                        app.log(f"Auto-update: Flatpak {scope[0]} update error: {e}")
            if app.cmd_exists("npm"):
                try:
                    env = os.environ.copy()
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env['npm_config_prefix'] = npm_prefix
                    env['NPM_CONFIG_PREFIX'] = npm_prefix
                    env['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env.get('PATH', '')
                    result = subprocess.run(["npm", "update", "-g"], capture_output=True, text=True, timeout=600, env=env)
                    if result.returncode == 0:
                        app.log("Auto-update: NPM global packages updated")
                        update_success = True
                    else:
                        app.log(f"Auto-update: NPM update failed: {result.stderr}")
                except Exception as e:
                    app.log(f"Auto-update: NPM update error: {e}")
        except Exception as e:
            app.log(f"Auto-update: General error: {e}")
        if update_success:
            app.show_message.emit("Auto Update", f"System update completed successfully! Next check in {days} days.")
        else:
            app.show_message.emit("Auto Update", "Some updates failed. Check the console for details.")
    except Exception:
        pass
                """.strip()
            ),
        }
        for fname, code in defaults.items():
            fpath = os.path.join(user_dir, fname)
            write_needed = True
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        existing = f.read()
                    write_needed = existing.strip() != (code + "\n").strip()
                except Exception:
                    write_needed = True
            if write_needed:
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(code + "\n")
                except Exception as e:
                    self.log(f"Default plugin write failed {fname}: {e}")
            if force_enable:
                name = os.path.splitext(fname)[0]
                enabled = set(self.settings.get('enabled_plugins') or [])
                if name not in enabled:
                    enabled.add(name)
                    self.settings['enabled_plugins'] = sorted(enabled)
        if force_enable:
            self.save_settings()
    
    def load_enabled_plugins(self):
        loaded = []
        plugs = {p['name']: p for p in self.scan_plugins()}
        enabled = self.settings.get('enabled_plugins') or []
        for name in enabled:
            p = plugs.get(name)
            if not p:
                continue
            path = p.get('path')
            try:
                spec = importlib.util.spec_from_file_location(name, path)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                loaded.append(mod)
            except Exception as e:
                self.log(f"Failed to load plugin {name}: {e}\n{traceback.format_exc()}")
        return loaded
    
    def reload_plugins(self):
        self.plugins = self.load_enabled_plugins()
    
    def reload_plugins_and_notify(self):
        self.reload_plugins()
        self._show_message("Plugins", f"Reloaded {len(self.plugins)} plugin(s)")
    
    def install_default_plugins(self):
        self.ensure_default_plugins(force_enable=True)
        self.refresh_plugins_table()
        self.reload_plugins()
        self._show_message("Plugins", "Default plugins installed and enabled")
    
    def run_plugin_hook(self, hook_name, *args, **kwargs):
        for mod in self.plugins:
            try:
                func = getattr(mod, hook_name, None)
                if callable(func):
                    func(self, *args, **kwargs)
            except Exception as e:
                self.log(f"Plugin hook {hook_name} error: {e}\n{traceback.format_exc()}")
    
    def run_plugin_tick(self):
        try:
            self.run_plugin_hook('on_tick')
        except Exception:
            pass
    
    def _show_message(self, title, text):
        self.log(f"{title}: {text}")
    
    def display_message(self, title, text):
        """Public method to show a message in the console"""
        self.log(f"{title}: {text}")
    
    def show_busy_pm_warning(self, details: str = "", retry_action=None):
        try:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Package Manager Busy")
            dlg.setText("Another package manager is running")
            dlg.setInformativeText("The package database is locked. Close other package tools (pacman, pamac, yay/paru) and retry.")
            if details:
                dlg.setDetailedText(details)
            if callable(retry_action):
                retry_btn = dlg.addButton("Retry", QMessageBox.ButtonRole.AcceptRole)
                dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                dlg.setDefaultButton(retry_btn)
                dlg.exec()
                if dlg.clickedButton() == retry_btn:
                    try:
                        retry_action()
                    except Exception:
                        pass
            else:
                dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
                dlg.exec()
        except Exception:
            pass
    
    def log(self, message):
        try:
            self.ui_call.emit(lambda: self.console.append(message))
        except Exception:
            pass
    
    def _on_ui_call(self, fn):
        try:
            if callable(fn):
                fn()
        except Exception:
            pass
    
    def toggle_console(self):
        try:
            showing = self.console.isVisible()
        except Exception:
            showing = False
        new_state = not showing
        try:
            self.console.setVisible(new_state)
            self.console_label.setVisible(new_state)
        except Exception:
            pass
        try:
            if getattr(self, 'current_view', None) == "discover" and hasattr(self, 'large_search_box'):
                self.large_search_box.set_compact_mode(new_state)
        except Exception:
            pass
        try:
            if hasattr(self, 'console_toggle_btn'):
                self.console_toggle_btn.setToolTip("Hide Console" if new_state else "Show Console")
        except Exception:
            pass
    
    def show_about(self):
        help_service.show_about(self)

    def create_snapshot(self):
        return snapshot_service.create_snapshot(self)

    def revert_to_snapshot(self):
        return snapshot_service.revert_to_snapshot(self)

    def _restore_snapshot(self, snapshot_num):
        return snapshot_service.restore_snapshot(self, snapshot_num)

    def delete_snapshots(self):
        return snapshot_service.delete_snapshots(self)

    def install_plugin(self):
        path, _ = QFileDialog.getOpenFileName(self, "Install Plugin", os.path.expanduser('~'), "Python Plugin (*.py)")
        if not path:
            return
        try:
            dst = os.path.join(self.get_user_plugins_dir(), os.path.basename(path))
            shutil.copy2(path, dst)
            self._show_message("Install Plugin", f"Installed: {os.path.basename(path)}")
            # Refresh plugins table if it exists
            try:
                # Find the plugins widget and refresh it
                if hasattr(self, 'settings_container'):
                    tabs = self.settings_container.widget().findChild(QTabWidget)
                    if tabs:
                        for i in range(tabs.count()):
                            widget = tabs.widget(i)
                            if hasattr(widget, 'refresh_plugins_table'):
                                widget.refresh_plugins_table()
                                break
            except Exception:
                # Handle UI widget access errors gracefully
                pass
        except Exception as e:
            self._show_message("Install Plugin", f"Failed: {e}")
    
    def remove_selected_plugins(self):
        # This method needs to be called from the plugins settings widget
        # We'll implement it to work with the current table selection
        try:
            # Find the plugins widget and call its remove method
            if hasattr(self, 'settings_container'):
                tabs = self.settings_container.widget().findChild(QTabWidget)
                if tabs:
                    for i in range(tabs.count()):
                        widget = tabs.widget(i)
                        if hasattr(widget, 'remove_selected_plugins'):
                            widget.remove_selected_plugins()
                            break
        except Exception as e:
            self._show_message("Remove Plugins", f"Error: {e}")
    
    def refresh_plugins_table(self):
        # This method is used internally by the main class
        # The component will call this if needed
        pass

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print("NeoArch - Elevate Your Arch Experience")
            print("Usage: python aurora_home.py")
            print("A graphical package manager for Arch Linux with AUR support.")
            sys.exit(0)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information.")
            sys.exit(1)
    
    if os.geteuid() == 0:
        print("Do not run this application as root.")
        sys.exit(1)
    
    window = ArchPkgManagerUniGetUI()
    window.show()
    
    # Check for authentication tools after UI is shown
    window.check_authentication_tools()
    
    sys.exit(app.exec())


# === Module aliases for backward compatibility ===
import types

config_utils = types.SimpleNamespace()
config_utils.get_ignore_file_path = get_ignore_file_path
config_utils.get_local_updates_file_path = get_local_updates_file_path
config_utils.load_ignored_updates = load_ignored_updates
config_utils.load_local_update_entries = load_local_update_entries
config_utils.save_ignored_updates = save_ignored_updates

sys_utils = types.SimpleNamespace()
sys_utils.check_aur_authentication_support = check_aur_authentication_support
sys_utils.cmd_exists = cmd_exists
sys_utils.get_aur_helper = get_aur_helper
sys_utils.get_available_aur_helpers = get_available_aur_helpers
sys_utils.get_missing_auth_tools = get_missing_auth_tools
sys_utils.get_missing_dependencies = get_missing_dependencies

install_service = types.SimpleNamespace()
install_service.install_packages = install_packages

bundle_service = types.SimpleNamespace()
bundle_service.add_selected_to_bundle = add_selected_to_bundle
bundle_service.add_selected_to_community = add_selected_to_community
bundle_service.clear_bundle = clear_bundle
bundle_service.export_bundle = export_bundle
bundle_service.import_bundle = import_bundle
bundle_service.import_community_bundle = import_community_bundle
bundle_service.install_bundle = install_bundle
bundle_service.list_community_bundles = list_community_bundles
bundle_service.refresh_bundles_table = refresh_bundles_table
bundle_service.remove_selected_from_bundle = remove_selected_from_bundle

filters_service = types.SimpleNamespace()
filters_service.apply_filters = apply_filters
filters_service.apply_update_filters = apply_update_filters

help_service = types.SimpleNamespace()
help_service._make_text_tab = _make_text_tab
help_service.show_about = show_about
help_service.show_help = show_help

ignore_service = types.SimpleNamespace()
ignore_service.ignore_selected = ignore_selected
ignore_service.manage_ignored = manage_ignored

packages_service = types.SimpleNamespace()
packages_service.load_installed_packages = load_installed_packages
packages_service.load_updates = load_updates

settings_service = types.SimpleNamespace()
settings_service.export_settings = export_settings
settings_service.import_settings = import_settings
settings_service.load_settings = load_settings
settings_service.save_settings = save_settings

snapshot_service = types.SimpleNamespace()
snapshot_service.create_snapshot = create_snapshot
snapshot_service.delete_snapshots = delete_snapshots
snapshot_service.restore_snapshot = restore_snapshot
snapshot_service.revert_to_snapshot = revert_to_snapshot

uninstall_service = types.SimpleNamespace()
uninstall_service.uninstall_packages = uninstall_packages

update_service = types.SimpleNamespace()
update_service._update_aur = _update_aur
update_service._update_flatpak = _update_flatpak
update_service._update_npm = _update_npm
update_service._update_system_packages = _update_system_packages
update_service.update_core_tools = update_core_tools
update_service.update_packages = update_packages

askpass_service = types.SimpleNamespace()
askpass_service.get_sudo_askpass = get_sudo_askpass
askpass_service.prepare_askpass_env = prepare_askpass_env

if __name__ == "__main__":
    main()

