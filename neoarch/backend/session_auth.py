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
import importlib.util
import shutil
from functools import lru_cache
from pathlib import Path
from neoarch.resources.paths import APP_NAME, CONFIG_DIR, PROJECT_ROOT

_session_askpass_script: str | None = None
_session_active: bool = False
_atexit_registered: bool = False
_CRED_FILE = Path.home() / ".cache" / "neoarch" / "sudo_credential"


@lru_cache(maxsize=1)
def _load_keyring():
    """Lazily import and cache the keyring module if available.

    Returns the keyring module, or None if it is not installed.
    """
    if importlib.util.find_spec("keyring") is None:
        return None
    import keyring
    return keyring


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
        QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QVBoxLayout, QWidget,
    )
    from PyQt6.QtCore import QEvent, QEventLoop, QObject, QRectF, Qt
    from PyQt6.QtGui import (
        QBrush, QColor, QIcon, QPainter, QPen, QPixmap,
    )

    def _paint_lock_pixmap(color="#9CA3AF"):
        pm = QPixmap(20, 22)
        pm.fill(QColor(Qt.GlobalColor.transparent))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawArc(QRectF(4.5, 1.5, 11, 11), 90 * 16, 180 * 16)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(QRectF(2, 8, 16, 12), 3, 3)
        painter.end()
        return pm

    def _paint_eye_pixmap(open_eye=True, color="#8B8D97"):
        pm = QPixmap(20, 14)
        pm.fill(QColor(Qt.GlobalColor.transparent))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        if open_eye:
            painter.drawEllipse(QRectF(1.5, 2.5, 17, 9))
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(QRectF(8.6, 5.2, 2.8, 2.8))
        else:
            painter.drawLine(1, 11, 19, 3)
        painter.end()
        return pm

    class _DragHandler(QObject):
        """Enables dragging the frameless dialog from its background."""

        def __init__(self, window):
            super().__init__(window)
            self._window = window

        def eventFilter(self, watched, event):
            if (event.type() == QEvent.Type.MouseButtonPress
                    and event.button() == Qt.MouseButton.LeftButton):
                handle = self._window.windowHandle()
                if handle is not None:
                    handle.startSystemMove()
                return True
            return super().eventFilter(watched, event)

    class _DialogTitleBar(QWidget):
        """macOS-style traffic light title bar matching the main window."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("authTitleBar")
            self.setFixedHeight(40)
            self.setStyleSheet("""
                QWidget#authTitleBar {
                    background-color: transparent;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                    border-top-left-radius: 14px;
                    border-top-right-radius: 14px;
                }
            """)

            layout = QHBoxLayout(self)
            layout.setContentsMargins(14, 0, 12, 0)
            layout.setSpacing(6)

            icon_label = QLabel(self)
            icon_label.setFixedSize(16, 16)
            icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            logo_path = _find_logo()
            if logo_path:
                pm = QPixmap(logo_path)
                if not pm.isNull():
                    icon_label.setPixmap(pm.scaled(
                        16, 16, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(icon_label)

            title = QLabel("NeoArch", self)
            title.setStyleSheet(
                "color: #8B8D97; font-size: 13px; font-weight: 500;"
                "background: transparent; border: none;"
            )
            title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(title)

            layout.addStretch()

            self.min_btn = self._traffic("\u2500", "#FEBC2E", "rgba(120, 80, 10, 0.7)")
            self.max_btn = self._traffic("\u25a1", "#29C840", "rgba(10, 70, 20, 0.7)")
            self.close_btn = self._traffic("\u2715", "#FF5F57", "rgba(80, 20, 20, 0.7)")

            self.min_btn.clicked.connect(lambda: self.window().showMinimized())
            self.max_btn.clicked.connect(self._toggle_maximize)
            self.close_btn.clicked.connect(self._close)

            layout.addWidget(self.min_btn)
            layout.addWidget(self.max_btn)
            layout.addWidget(self.close_btn)

        def _traffic(self, glyph, color, glyph_color):
            btn = QPushButton(glyph, self)
            btn.setFixedSize(14, 14)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: transparent;
                    border: none;
                    border-radius: 7px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 0;
                }}
                QPushButton:hover {{
                    color: {glyph_color};
                }}
            """)
            return btn

        def _toggle_maximize(self):
            w = self.window()
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()

        def _close(self):
            self.window().close()

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self.window().windowHandle()
                if handle is not None:
                    handle.startSystemMove()
                event.accept()
            else:
                super().mousePressEvent(event)

    dlg = QDialog(parent_widget)
    dlg.setWindowTitle("NeoArch - Authentication")
    dlg.setFixedSize(360, 404)
    dlg.setModal(True)
    dlg.setWindowFlags(
        Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
    )
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.installEventFilter(_DragHandler(dlg))

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(0, 0, 0, 0)

    shell = QFrame(dlg)
    shell.setObjectName("authShell")
    shell.setStyleSheet("""
        QFrame#authShell {
            background-color: rgba(12, 12, 14, 0.78);
            border: 1px solid rgba(0, 191, 174, 0.2);
            border-radius: 14px;
        }
    """)
    outer.addWidget(shell)

    root = QVBoxLayout(shell)
    root.setContentsMargins(0, 0, 0, 24)
    root.setSpacing(0)

    title_bar = _DialogTitleBar(shell)
    root.addWidget(title_bar)

    content = QWidget(shell)
    root.addWidget(content)

    root = QVBoxLayout(content)
    root.setContentsMargins(26, 16, 26, 0)
    root.setSpacing(0)

    # Accent bar
    accent = QFrame(shell)
    accent.setFixedSize(54, 5)
    accent.setStyleSheet("""
        QFrame {
            background-color: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 rgba(59, 130, 246, 0.0),
                stop: 0.5 #3B82F6,
                stop: 1 rgba(59, 130, 246, 0.0)
            );
            border: none;
            border-radius: 2.5px;
        }
    """)
    root.addWidget(accent, alignment=Qt.AlignmentFlag.AlignHCenter)

    root.addSpacing(10)

    # Brand badge
    badge = QFrame(shell)
    badge.setFixedSize(48, 48)
    badge.setObjectName("authBadge")
    badge.setStyleSheet("""
        QFrame#authBadge {
            background-color: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 14px;
        }
    """)
    badge_v = QVBoxLayout(badge)
    badge_v.setContentsMargins(0, 0, 0, 0)

    badge_icon = QLabel(badge)
    badge_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    logo_path = _find_logo()
    placed = False
    if logo_path:
        pm = QPixmap(logo_path)
        if not pm.isNull():
            badge_icon.setPixmap(pm.scaled(
                26, 26, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            placed = True
    if not placed:
        badge_icon.setPixmap(_paint_lock_pixmap(color="#60A5FA"))
    badge_v.addWidget(badge_icon, alignment=Qt.AlignmentFlag.AlignCenter)
    root.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

    root.addSpacing(10)

    # Title
    title = QLabel("Authentication Required")
    title.setStyleSheet("font-size: 17px; font-weight: 700; color: #FFFFFF;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root.addWidget(title)

    root.addSpacing(6)

    # Subtitle
    subtitle = QLabel(
        "Sign in once - NeoArch caches your password\n"
        "securely for this session."
    )
    subtitle.setStyleSheet("font-size: 12.5px; color: #9CA3AF;")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle.setWordWrap(True)
    root.addWidget(subtitle)

    root.addSpacing(16)

    # Password field with lock icon and show/hide toggle
    pw_input = QLineEdit(shell)
    pw_input.setObjectName("authPassInput")
    pw_input.setEchoMode(QLineEdit.EchoMode.Password)
    pw_input.setPlaceholderText("Enter your sudo password")
    pw_input.setFixedHeight(36)
    pw_input.setStyleSheet("""
        QLineEdit#authPassInput {
            background-color: rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 12px;
            padding: 0 14px;
            font-size: 14px;
            color: #F3F4F6;
            selection-background-color: #3B82F6;
        }
        QLineEdit#authPassInput:focus {
            border: 1px solid rgba(59, 130, 246, 0.85);
            background-color: rgba(255, 255, 255, 0.075);
        }
    """)
    pw_input.addAction(QIcon(_paint_lock_pixmap()),
                       QLineEdit.ActionPosition.LeadingPosition)
    eye_state = [True]
    eye_action = pw_input.addAction(QIcon(_paint_eye_pixmap(True)),
                                    QLineEdit.ActionPosition.TrailingPosition)

    def _toggle_eye():
        eye_state[0] = not eye_state[0]
        if eye_state[0]:
            pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            pw_input.setEchoMode(QLineEdit.EchoMode.Normal)
        eye_action.setIcon(QIcon(_paint_eye_pixmap(eye_state[0])))

    eye_action.triggered.connect(_toggle_eye)
    root.addWidget(pw_input)

    root.addSpacing(10)

    # Status banner (hint or inline error)
    status_label = QLabel("Password is cached only for this session.")
    status_label.setObjectName("authStatus")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status_label.setWordWrap(True)
    status_label.setFixedHeight(34)
    status_label.setStyleSheet("""
        QLabel#authStatus {
            color: #9CA3AF;
            font-size: 11.5px;
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 0 10px;
        }
    """)
    root.addWidget(status_label)

    root.addSpacing(14)

    # macOS-style action row (compact, right-aligned)
    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)

    btn_row.addStretch()

    cancel_btn = QPushButton("Cancel")
    cancel_btn.setObjectName("authSecondary")
    cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    cancel_btn.setFixedHeight(30)
    cancel_btn.setStyleSheet("""
        QPushButton#authSecondary {
            background-color: transparent;
            color: #9CA3AF;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            padding: 0 14px;
        }
        QPushButton#authSecondary:hover {
            background-color: rgba(255, 255, 255, 0.06);
            color: #EDEDEF;
        }
        QPushButton#authSecondary:pressed {
            background-color: rgba(255, 255, 255, 0.1);
        }
    """)

    confirm_btn = QPushButton("Authenticate")
    confirm_btn.setObjectName("authPrimary")
    confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    confirm_btn.setFixedHeight(30)
    confirm_btn.setDefault(True)
    confirm_btn.setStyleSheet("""
        QPushButton#authPrimary {
            background-color: #F4F4F6;
            color: #111114;
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            padding: 0 22px;
        }
        QPushButton#authPrimary:hover {
            background-color: #FFFFFF;
        }
        QPushButton#authPrimary:pressed {
            background-color: #E4E4E8;
        }
        QPushButton#authPrimary:disabled {
            background-color: #2A2E3A;
            color: #6B7280;
            border: none;
        }
    """)

    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(confirm_btn)
    root.addLayout(btn_row)

    root.addSpacing(8)

    # Footer hint
    footer = QLabel("Press Esc to skip authentication for now")
    footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
    footer.setStyleSheet("font-size: 11px; color: #6B7280;")
    root.addWidget(footer)

    # Use a local event loop so the dialog stays open while validating.
    # Wrong passwords re-prompt in place; Cancel re-asks instead of quitting.
    loop = QEventLoop()
    dlg.finished.connect(loop.quit)

    confirmed = [False]

    _STATUS_HINT = """
        QLabel#authStatus {
            color: #9CA3AF;
            font-size: 11.5px;
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 0 10px;
        }
    """
    _STATUS_ERROR = """
        QLabel#authStatus {
            color: #FCA5A5;
            font-size: 11.5px;
            background-color: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.30);
            border-radius: 10px;
            padding: 0 10px;
        }
    """

    def _set_status(text, is_error=False):
        status_label.setStyleSheet(_STATUS_ERROR if is_error else _STATUS_HINT)
        status_label.setText(text)

    def _validate():
        raw = pw_input.text()
        if not raw.strip():
            _set_status("Please enter your sudo password.", is_error=True)
            pw_input.setFocus()
            return

        pw_text = secure_string(raw)
        if not store_sudo_password(pw_text):
            _set_status("Credential storage unavailable (system keyring not found).",
                        is_error=True)
            pw_input.setFocus()
            return
        QApplication.processEvents()

        try:
            run_sudo_command(['-v'])
        except FileNotFoundError:
            QMessageBox.warning(
                parent_widget,
                "sudo Not Found",
                "The sudo command is required but was not found on your system.",
            )
            dlg.reject()
            return
        except subprocess.TimeoutExpired:
            QMessageBox.warning(
                parent_widget,
                "Timeout",
                "sudo did not respond in time. Check your system configuration.",
            )
            dlg.reject()
            return
        except RuntimeError as exc:
            msg = str(exc)
            if "password" in msg.lower() or "sorry" in msg.lower():
                _set_status("Incorrect password. Please try again.", is_error=True)
            else:
                _set_status(msg, is_error=True)
            pw_input.clear()
            pw_input.setFocus()
            return
        except Exception as exc:
            delete_sudo_password()
            _set_status(f"Authentication error: {exc}", is_error=True)
            pw_input.clear()
            pw_input.setFocus()
            return

        confirmed[0] = True
        dlg.accept()

    def on_confirm():
        _validate()

    def on_cancel():
        # Cancel aborts the dialog; the caller decides how to proceed
        # (operations log "authentication declined" and stop gracefully).
        dlg.reject()

    confirm_btn.clicked.connect(on_confirm)
    pw_input.returnPressed.connect(on_confirm)
    cancel_btn.clicked.connect(on_cancel)

    pw_input.clear()
    _set_status("Password is cached only for this session.")
    dlg.show()
    dlg.activateWindow()
    pw_input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
    loop.exec()

    if not confirmed[0]:
        return False

    helper_dir = CONFIG_DIR
    helper_dir.mkdir(parents=True, exist_ok=True)

    # Copy helper from resources so it always matches the current version
    source_helper = PROJECT_ROOT / "neoarch" / "resources" / "askpass_helper.py"
    target_helper = helper_dir / "askpass_helper.py"
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
        ASSETS_DIR / "icons" / "app" / "logo.png",
        ASSETS_DIR / "icons" / "app" / "icon.png",
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

    _delete_cred_file()

    helper_path = CONFIG_DIR / "askpass_helper.py"
    if helper_path.exists(): helper_path.unlink()
    os.environ.pop("SUDO_ASKPASS", None)
    os.environ.pop("SSH_ASKPASS", None)
    _session_active = False

def get_sudo_password() -> 'SecureBytes | None':
    """Retrieve cached sudo password from keyring, falling back to the session file."""
    pw = None
    try:
        kr = _load_keyring()
        if kr is not None:
            pw = kr.get_password(APP_NAME, "sudo_credential")
    except Exception:
        pw = None
    if not pw:
        pw = _read_cred_file()
    if pw is None:
        return None
    return secure_string(pw)


def store_sudo_password(pw_text: 'SecureBytes') -> bool:
    """Store sudo password in keyring, falling back to a 0600 session file.

    Returns True if the credential could be persisted through at least one
    backend, so the session cache always works even without a keyring daemon.
    """
    stored = False
    try:
        kr = _load_keyring()
        if kr is not None:
            kr.set_password(APP_NAME, "sudo_credential", pw_text.get_bytes().decode('utf-8'))
            stored = True
    except Exception:
        pass
    if not _write_cred_file(pw_text.get_bytes()):
        if not stored:
            return False
    else:
        stored = True
    pw_text.zero()
    return stored


def delete_sudo_password() -> None:
    """Remove stored password from keyring and the session file."""
    try:
        kr = _load_keyring()
        if kr is not None:
            kr.delete_password(APP_NAME, "sudo_credential")
    except Exception:
        pass
    _delete_cred_file()


def _read_cred_file():
    try:
        if not _CRED_FILE.exists():
            return None
        with open(_CRED_FILE, 'rb') as f:
            return f.read().decode('utf-8')
    except Exception:
        return None


def _write_cred_file(data: bytes) -> bool:
    try:
        _CRED_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(_CRED_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.chmod(str(_CRED_FILE), 0o600)
        return True
    except Exception:
        return False


def _delete_cred_file() -> None:
    try:
        if _CRED_FILE.exists():
            _CRED_FILE.unlink()
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
        env = os.environ.copy()
        env.pop("SUDO_ASKPASS", None)
        env.pop("SSH_ASKPASS", None)

        proc = subprocess.run(
            ["sudo", "-S"] + command,
            input=secure_pw.get_bytes() + b"\n",
            capture_output=True,
            text=False,
            timeout=60,
            check=False,
            env=env,
        )

        # Check result
        if proc.returncode != 0:

            delete_sudo_password()
            raise RuntimeError(f"Sudo failed: {proc.stderr.decode()}")

        return proc

    finally:
        # Zero the buffer immediately after use
        secure_pw.zero()

