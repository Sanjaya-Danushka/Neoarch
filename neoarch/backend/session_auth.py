"""Session credential caching for passwordless sudo operations.

On first authentication, stores the password in a secure temp file and
creates a persistent SUDO_ASKPASS script. All subsequent sudo commands
use this cached credential without prompting.
"""

import os
import stat
import subprocess
import tempfile
import atexit

_session_password_file: str | None = None
_session_askpass_script: str | None = None
_session_active: bool = False
_atexit_registered: bool = False


def setup_session_auth(parent_widget=None) -> bool:
    """Show password dialog, validate credentials, create persistent askpass.

    Args:
        parent_widget: QWidget parent for the password dialog.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    global _session_password_file, _session_askpass_script, _session_active, _atexit_registered

    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QMessageBox,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap

    dlg = QDialog(parent_widget)
    dlg.setWindowTitle("NeoArch - Authentication")
    dlg.setFixedSize(440, 420)
    dlg.setModal(True)
    dlg.setStyleSheet("""
        QDialog {
            background-color: #121316;
            border: 1px solid #2A2D35;
            border-radius: 12px;
        }
    """)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(32, 28, 32, 24)
    root.setSpacing(0)

    # Logo
    logo = QLabel()
    logo_path = _find_logo()
    if logo_path:
        pm = QPixmap(logo_path)
        if not pm.isNull():
            logo.setPixmap(pm.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    logo.setFixedHeight(64)
    root.addWidget(logo)

    root.addSpacing(12)

    # Title
    title = QLabel("Authentication Required")
    title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root.addWidget(title)

    root.addSpacing(6)

    # Subtitle
    subtitle = QLabel(
        "Enter your sudo password once.\n"
        "NeoArch will cache it securely for this session."
    )
    subtitle.setStyleSheet("font-size: 13px; color: #9CA3AF; line-height: 1.4;")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle.setWordWrap(True)
    root.addWidget(subtitle)

    root.addSpacing(20)

    # Benefits box
    benefits = QLabel(
        "✓  Sync package databases on startup\n"
        "✓  Install, update & uninstall without re-prompting\n"
        "✓  Password cached only for this session"
    )
    benefits.setStyleSheet("""
        QLabel {
            font-size: 12px;
            color: #D1D5DB;
            background-color: rgba(0, 191, 174, 0.08);
            border: 1px solid rgba(0, 191, 174, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            line-height: 1.6;
        }
    """)
    root.addWidget(benefits)

    root.addSpacing(20)

    # Password field
    pw_label = QLabel("Password")
    pw_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #D1D5DB; margin-bottom: 4px;")
    root.addWidget(pw_label)

    pw_input = QLineEdit()
    pw_input.setEchoMode(QLineEdit.EchoMode.Password)
    pw_input.setPlaceholderText("Enter your sudo password...")
    pw_input.setStyleSheet("""
        QLineEdit {
            background-color: #1C1E24;
            border: 1px solid #373A43;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            color: #F3F4F6;
            selection-background-color: #00BFAE;
        }
        QLineEdit:focus {
            border: 1px solid #00BFAE;
        }
    """)
    pw_input.setFixedHeight(40)
    root.addWidget(pw_input)

    root.addSpacing(20)

    # Buttons
    btn_row = QHBoxLayout()
    btn_row.setSpacing(12)

    cancel_btn = QPushButton("Cancel")
    cancel_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            border: 1px solid #373A43;
            border-radius: 8px;
            padding: 10px 0;
            font-size: 14px;
            font-weight: 500;
            color: #D1D5DB;
        }
        QPushButton:hover {
            background-color: #1C1E24;
            border: 1px solid #4B5563;
        }
        QPushButton:pressed {
            background-color: #2A2D35;
        }
    """)
    cancel_btn.setFixedHeight(40)
    cancel_btn.clicked.connect(dlg.reject)

    confirm_btn = QPushButton("Authenticate")
    confirm_btn.setStyleSheet("""
        QPushButton {
            background-color: #00BFAE;
            border: none;
            border-radius: 8px;
            padding: 10px 0;
            font-size: 14px;
            font-weight: 600;
            color: #FFFFFF;
        }
        QPushButton:hover {
            background-color: #00D4C1;
        }
        QPushButton:pressed {
            background-color: #009688;
        }
        QPushButton:disabled {
            background-color: #374151;
            color: #6B7280;
        }
    """)
    confirm_btn.setFixedHeight(40)
    confirm_btn.setDefault(True)

    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(confirm_btn)
    root.addLayout(btn_row)

    # Connect confirm after setup
    password = [""]
    def on_confirm():
        password[0] = pw_input.text()
        dlg.accept()
    confirm_btn.clicked.connect(on_confirm)
    pw_input.returnPressed.connect(on_confirm)

    dlg.exec()
    pw_text = password[0]

    if not pw_text:
        return False

    # Validate password via sudo -v (also extends sudo credential cache)
    try:
        result = subprocess.run(
            ["sudo", "-S", "-v"],
            input=pw_text + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            msg = result.stderr.strip() or "Authentication failed."
            QMessageBox.warning(parent_widget, "Authentication Failed", msg)
            return False
    except FileNotFoundError:
        QMessageBox.warning(
            parent_widget,
            "sudo Not Found",
            "The sudo command is required but was not found on your system.",
        )
        return False
    except subprocess.TimeoutExpired:
        QMessageBox.warning(
            parent_widget,
            "Timeout",
            "sudo did not respond in time. Check your system configuration.",
        )
        return False
    except Exception as e:
        QMessageBox.warning(parent_widget, "Authentication Error", str(e))
        return False

    # Write password to a secure temp file (only readable by user)
    fd, pw_path = tempfile.mkstemp(prefix="neoarch-pw-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(pw_text)
        os.chmod(pw_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        os.unlink(pw_path)
        return False
    _session_password_file = pw_path

    # Create persistent askpass script that reads from the password file
    fd2, script_path = tempfile.mkstemp(prefix="neoarch-askpass-", suffix=".sh")
    with os.fdopen(fd2, "w") as f:
        f.write("#!/bin/sh\n")
        f.write(f'cat "{pw_path}"\n')
    os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    _session_askpass_script = script_path

    # Set environment so all child processes inherit the askpass
    os.environ["SUDO_ASKPASS"] = script_path
    os.environ["SSH_ASKPASS"] = script_path

    _session_active = True

    if not _atexit_registered:
        atexit.register(cleanup_session)
        _atexit_registered = True

    return True


def _find_logo() -> str | None:
    """Find an app logo icon file."""
    from neoarch.resources.paths import ASSETS_DIR
    candidates = [
        ASSETS_DIR / "icons" / "logo.png",
        ASSETS_DIR / "icons" / "NeoarchLogo.svg",
        ASSETS_DIR / "icons" / "icon.png",
        ASSETS_DIR / "icons" / "app.png",
        ASSETS_DIR / "icons" / "brand" / "neoarch.svg",
        ASSETS_DIR / "icons" / "brand" / "neoarch.png",
        ASSETS_DIR / "icons" / "discover" / "logo.svg",
        ASSETS_DIR / "icons" / "discover" / "logo1.svg",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def is_session_active() -> bool:
    """Return True if a session credential cache is active."""
    return _session_active


def get_askpass_env() -> dict:
    """Return a copy of the current environment with SUDO_ASKPASS set.

    If the session askpass is active, the returned env will include it.
    Otherwise returns a copy of the current os.environ.
    """
    env = os.environ.copy()
    if _session_active and _session_askpass_script:
        env["SUDO_ASKPASS"] = _session_askpass_script
        env["SSH_ASKPASS"] = _session_askpass_script
    return env


def cleanup_session():
    """Remove credential files and environment variables."""
    global _session_active, _session_password_file, _session_askpass_script

    pw_path = _session_password_file
    if pw_path and os.path.exists(pw_path):
        try:
            os.remove(pw_path)
        except Exception:
            pass
    _session_password_file = None

    script_path = _session_askpass_script
    if script_path and os.path.exists(script_path):
        try:
            os.remove(script_path)
        except Exception:
            pass
    _session_askpass_script = None

    for var in ("SUDO_ASKPASS", "SSH_ASKPASS"):
        if var in os.environ:
            try:
                del os.environ[var]
            except Exception:
                pass

    _session_active = False
