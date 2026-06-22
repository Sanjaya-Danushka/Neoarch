"""Session credential caching for passwordless sudo operations.

On first authentication, stores the password in a secure temp file and
creates a persistent SUDO_ASKPASS script. All subsequent sudo commands
use this cached credential without prompting.
"""

import os
import signal
import stat
import subprocess
import atexit
import ctypes
import keyring
import shutil
from pathlib import Path
from neoarch.resources.paths import APP_NAME, CONFIG_DIR, PROJECT_ROOT

_session_askpass_script: str | None = None
_session_active: bool = False
_atexit_registered: bool = False

# pylint: disable=global-statement
def setup_session_auth(parent_widget=None) -> bool:
    """Show password dialog, validate credentials, create persistent askpass.

    Args:
        parent_widget: QWidget parent for the password dialog.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    global _session_active, _session_askpass_script, _atexit_registered

    from PyQt6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QMessageBox,
    )
    from PyQt6.QtCore import Qt, QEventLoop
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

    # Error label (hidden by default, shown inline on wrong password)
    error_label = QLabel("")
    error_label.setStyleSheet("""
        QLabel {
            color: #EF4444;
            font-size: 12px;
            font-weight: 500;
            padding: 6px 0 2px 0;
        }
    """)
    error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    error_label.setWordWrap(True)
    error_label.hide()
    root.addWidget(error_label)

    root.addSpacing(14)

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

    # Use a local event loop so the dialog can be reused across attempts
    loop = QEventLoop()
    dlg.finished.connect(loop.quit)

    confirmed = [False]
    def on_confirm():
        confirmed[0] = True
        dlg.accept()
    confirm_btn.clicked.connect(on_confirm)
    pw_input.returnPressed.connect(on_confirm)

    max_attempts = 3

    pw_text = None
    for attempt in range(max_attempts):
        error_label.hide()
        pw_input.clear()
        confirmed[0] = False
        dlg.setResult(QDialog.DialogCode.Rejected)
        dlg.show()
        loop.exec()

        if not confirmed[0]:
            return False

        raw = pw_input.text()
        pw_input.clear()
        if not raw:
            continue
        pw_text = secure_string(raw)
        store_sudo_password(pw_text)
        QApplication.processEvents()

        try:
            result = run_sudo_command(['-v'])

            if result.returncode == 0:
                break

            remaining = max_attempts - attempt - 1
            if remaining > 0:
                error_label.setText(
                    f"Incorrect password. {remaining} more attempt{'s' if remaining != 1 else ''} remaining."
                )
            else:
                QMessageBox.warning(
                    parent_widget, "Authentication Failed",
                    "Too many failed attempts."
                )
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

    helper_dir = CONFIG_DIR
    helper_dir.mkdir(parents=True, exist_ok=True)

    # Copy helper from resources if not already present
    source_helper = PROJECT_ROOT / "neoarch" / "resources" / "askpass_helper.py"
    target_helper = helper_dir / "askpass_helper.py"
    if not target_helper.exists():
        shutil.copy2(source_helper, target_helper)
    os.chmod(str(target_helper), stat.S_IRWXU)  # 700

    cache_dir = Path.home() / ".cache" / "neoarch"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create session lock (marker only)
    lock_path = cache_dir / "session.lock"
    lock_path.touch(mode=stat.S_IRUSR | stat.S_IWUSR)  # 600


    _session_askpass_script = str(target_helper)

    # Set environment so all child processes inherit the askpass
    os.environ["SUDO_ASKPASS"] = _session_askpass_script
    os.environ["SSH_ASKPASS"] = _session_askpass_script

    _session_active = True

    if not _atexit_registered:
        atexit.register(cleanup_session)
        signal.signal(signal.SIGTERM, lambda *_: cleanup_session())
        signal.signal(signal.SIGINT, lambda *_: cleanup_session())
        signal.signal(signal.SIGHUP, lambda *_: cleanup_session())
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

    If the session askpass is active, the returned env will include it;
    Otherwise returns a copy of the current os.environ.
    """
    env = os.environ.copy()
    if _session_active and _session_askpass_script:
        env["SUDO_ASKPASS"] = _session_askpass_script
        env["SSH_ASKPASS"] = _session_askpass_script
    return env

# pylint: disable=global-statement
def cleanup_session():
    """Remove credential files and environment variables."""
    global _session_active
    # Remove session lock file
    lock_path = Path.home() / ".cache" / "neoarch" / "session.lock"
    if lock_path.exists():
        try:
            lock_path.unlink()
        except Exception:
            pass

    helper_path = CONFIG_DIR / "askpass_helper.py"
    if helper_path.exists(): helper_path.unlink()
    os.environ.pop("SUDO_ASKPASS", None)
    os.environ.pop("SSH_ASKPASS", None)
    _session_active = False

def get_sudo_password() -> 'SecureBytes | None':
    """Retrieve cached sudo password from keyring"""
    pw = keyring.get_password(APP_NAME, "sudo_credential")
    if pw is None:
        return None
    return secure_string(pw)


def store_sudo_password(pw_text: 'SecureBytes') -> bool:
    """Store sudo password in keyring"""
    try:
        keyring.set_password(APP_NAME, "sudo_credential", pw_text.get_bytes().decode('utf-8'))
        pw_text.zero()
        return True
    except Exception:
        return False


def delete_sudo_password() -> None:
    """Remove stored password"""
    try:
        keyring.delete_password(APP_NAME, "sudo_credential")
    except Exception:
        pass



def secure_string(data: str) -> 'SecureBytes':
    """Store secret data in a mutable buffer that can be zeroed"""
    return SecureBytes(data.encode('utf-8'))


class SecureBytes:
    def __init__(self, data: bytes):
        self._buffer = ctypes.create_string_buffer(data)

    def zero(self):
        """"Overwrite with zeros in-place"""
        ctypes.memset(ctypes.addressof(self._buffer), 0, len(self._buffer))

    def get_bytes(self) -> bytes:
        return bytes(self._buffer.value)


    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.zero()


def run_sudo_command(command: list[str]) -> subprocess.CompletedProcess:
    """
    Runs a sudo command by retrieving the credential from Keyring,
    feeding it to stdin, and immediately zeroing the buffer.
    """

    # Retrieve from Keyring
    secure_pw = get_sudo_password()
    if not secure_pw:
        raise RuntimeError("No cached credential found. Please authenticate first.")

    try:
        proc = subprocess.run(
            ["sudo", "-S"] + command,
            input=secure_pw.get_bytes() + b"\n",
            capture_output=True,
            text=False,
            timeout=30,
            check=False
        )

        # Check result
        if proc.returncode != 0:

            delete_sudo_password()
            raise RuntimeError(f"Sudo failed: {proc.stderr.decode()}")

        return proc

    finally:
        # Zero the buffer immediately after use
        secure_pw.zero()

