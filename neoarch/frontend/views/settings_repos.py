"""Settings page: manage pacman repositories (add/remove/enable).

Third-party repos such as Chaotic AUR are added here instead of
hand-editing /etc/pacman.conf. Reads are root-free; every write goes
through the app's session auth, backs the config up, and restores it on
failure (see services/repo_manager). Repos NeoArch didn't add can't be
removed from the GUI, and built-in repos (core/extra/...) stay read-only.
"""

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from neoarch.backend.services.i18n import _
from neoarch.frontend.tokens import Colors, Fonts, QSS

from neoarch.frontend.views import _settings_kit as kit
from neoarch.frontend.components.source_item import ToggleSwitch

_ICON_REPO = (
    '<circle cx="5" cy="6" r="3"/>'
    '<path d="M12 6h8"/>'
    '<path d="M5 9v9"/>'
    '<path d="M19 9v6"/>'
    '<circle cx="5" cy="18" r="3"/>'
    '<circle cx="19" cy="18" r="3"/>'
    '<path d="M12 15h7"/>'
)

_ICON_PLUS_STROKE = (
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
)


class _AddRepoDialog(QDialog):
    """Three-field dark dialog: repo name, optional Include, optional Server."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Add Repository"))
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_QSS)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(12)

        title = QLabel(_("Add Repository"))
        title.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        root.addWidget(title)

        hint = QLabel(_("The section is appended to /etc/pacman.conf under a"
                        " NeoArch marker, so it can be removed again here later."))
        hint.setWordWrap(True)
        hint.setStyleSheet(QSS.HINT)
        root.addWidget(hint)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_("Repository name, e.g. archlinuxcn"))
        root.addWidget(self.name_edit)

        self.include_edit = QLineEdit()
        self.include_edit.setPlaceholderText(_("Include path under /etc/ (optional)"))
        root.addWidget(self.include_edit)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText(_("Server URL, e.g. https://mirror.example (optional)"))
        root.addWidget(self.server_edit)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(_("Cancel"))
        cancel.setStyleSheet(QSS.BTN_OUTLINE)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        ok = QPushButton(_("Add"))
        ok.setStyleSheet(QSS.BTN_OUTLINE)
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.setDefault(True)
        ok.clicked.connect(self._accept_values)
        buttons.addWidget(ok)
        root.addLayout(buttons)

        self.name_edit.setFocus()

    def _accept_values(self):
        if not (self.name_edit.text() or "").strip():
            return
        self.accept()

    def values(self):
        return {
            "name": (self.name_edit.text() or "").strip(),
            "include": (self.include_edit.text() or "").strip(),
            "server": (self.server_edit.text() or "").strip(),
        }


class RepositoriesSettingsWidget(QWidget):
    _repos_ready = pyqtSignal(dict)
    _op_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self._building = False
        self._pin_status = False
        self._repos = []
        self._chaotic_btn = None
        self._generic_btn = None
        self._repos_ready.connect(self._on_repos_ready)
        self._op_finished.connect(self._on_op_finished)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.setup_ui()
        self._reload()

    # ── UI ────────────────────────────────────────────────────────────
    def setup_ui(self):
        title = QLabel(_("Repositories"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("View and manage pacman repositories like Chaotic"
                            " AUR \u2014 no more hand-editing /etc/pacman.conf."))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        subtitle.setWordWrap(True)
        self.layout.addWidget(subtitle)

        # ── Configured repositories ──
        card, card_layout = kit.make_card(_("Configured Repositories"),
                                          svg_body=_ICON_REPO)
        hint = QLabel(_("Repositories NeoArch added carry a marker and can be"
                        " removed here; system and hand-written sections are"
                        " protected."))
        hint.setStyleSheet(QSS.HINT)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)
        self._rows_host = QVBoxLayout()
        self._rows_host.setSpacing(0)
        card_layout.addLayout(self._rows_host)
        self.layout.addWidget(card)

        # ── Add / remove ──
        add_card, add_card_layout = kit.make_card(_("Add a Repository"),
                                                  svg_body=_ICON_PLUS_STROKE)
        add_hint = QLabel(_("Quick-add Chaotic AUR (signs the maintainer key,"
                            " fetches the mirror list, appends [chaotic-aur]"
                            " and runs pacman -Syy), or add any repo by name."))
        add_hint.setStyleSheet(QSS.HINT)
        add_hint.setWordWrap(True)
        add_card_layout.addWidget(add_hint)

        self._status = QLabel("")
        self._status.setStyleSheet(QSS.HINT)
        self._status.setWordWrap(True)
        add_card_layout.addWidget(self._status)

        b_chaotic = kit.btn(_("Quick-add Chaotic AUR"), on_click=self._add_chaotic)
        b_generic = kit.btn(_("Add a Repository\u2026"), on_click=self._add_generic)
        add_card_layout.addWidget(kit.actions_row([b_chaotic, b_generic]))
        self._chaotic_btn = b_chaotic
        self._generic_btn = b_generic
        self.layout.addWidget(add_card)

        self.layout.addStretch()

    def _row_for(self, repo):
        if not repo["enabled"]:
            subtitle = _("Disabled")
        elif repo["include"]:
            subtitle = repo["include"]
        elif repo["servers"]:
            subtitle = repo["servers"][0]
        else:
            subtitle = _("Enabled")

        control = None
        if not repo["system"]:
            control = self._build_repo_control(repo)
        return kit.row(repo["name"], subtitle, control=control)

    def _build_repo_control(self, repo):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        toggle = ToggleSwitch(accent_color=Colors.ACCENT)
        toggle.setChecked(bool(repo["enabled"]))
        if self._building:
            toggle.toggled.connect(
                lambda checked, n=repo["name"]: self._toggle(n, checked))
        h.addWidget(toggle)

        if repo["managed"]:
            rem_btn = kit.btn(_("Remove"))
            rem_btn.clicked.connect(
                lambda checked=False, n=repo["name"]: self._remove(n))
            h.addWidget(rem_btn)

        h.addStretch()
        return container

    def _rebuild_rows(self):
        self._building = True
        while self._rows_host.count():
            item = self._rows_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for repo in self._repos:
            self._rows_host.addWidget(self._row_for(repo))
            self._rows_host.addWidget(kit.sep())
        self._building = False

    # ── actions ───────────────────────────────────────────────────────
    def _auth(self):
        if self.app is not None and hasattr(self.app, "ensure_session_auth"):
            try:
                return bool(self.app.ensure_session_auth())
            except Exception:
                return True
        return True

    def _run_op(self, kind, **kwargs):
        from threading import Thread
        from neoarch.backend.services import repo_manager

        if not self._auth():
            return
        self._set_busy(True)

        def task():
            try:
                ok, message = getattr(repo_manager, kind)(**kwargs)
            except Exception as e:
                ok, message = False, str(e)
            try:
                self._op_finished.emit(bool(ok), message)
            except RuntimeError:
                pass  # widget destroyed while the op ran

        Thread(target=task, daemon=True).start()

    def _set_busy(self, busy):
        for btn in (self._chaotic_btn, self._generic_btn):
            if btn is not None:
                btn.setEnabled(not busy)
        if busy:
            self._set_status(_("Working\u2026"), Colors.TEXT_2)

    def _set_status(self, text, color=None):
        self._status.setText(text)
        if color is None:
            self._status.setStyleSheet(QSS.HINT)
        else:
            self._status.setStyleSheet(
                f"color: {color}; font-size: {Fonts.MD}; border: none;")

    def _toggle(self, name, enabled):
        if self._building:
            return
        self._run_op("set_repo_enabled", name=name, enabled=enabled)

    def _remove(self, name):
        from neoarch.frontend.components.dark_dialogs import dark_confirm
        if not dark_confirm(self, _("Remove Repository"),
                            _("Remove '[{name}]' from /etc/pacman.conf?")
                            .format(name=name), danger=True):
            return
        self._run_op("remove_repo", name=name)

    def _add_generic(self):
        dlg = _AddRepoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        values = dlg.values()
        self._run_op(
            "add_repo",
            name=values["name"],
            include=values["include"] or None,
            servers=[values["server"]] if values["server"] else None,
        )

    def _add_chaotic(self):
        from neoarch.frontend.components.dark_dialogs import dark_confirm
        from neoarch.backend.services import repo_manager

        warning = ""
        try:
            warning = repo_manager.chaotic_preflight()
        except Exception:
            warning = ""
        message = warning + "\n\n" if warning else ""
        message += _("This signs the Chaotic AUR maintainer key, downloads the"
                     " mirror list over HTTPS, appends [chaotic-aur] to"
                     " /etc/pacman.conf and runs 'pacman -Syy'. Continue?")
        if not dark_confirm(self, _("Add Chaotic AUR"), message,
                            danger=bool(warning)):
            return
        self._run_op("add_chaotic_aur")

    def _reload(self):
        from threading import Thread
        from neoarch.backend.services import repo_manager

        if not self._pin_status:
            self._set_status(_("Reading /etc/pacman.conf\u2026"))

        def task():
            try:
                repos = repo_manager.list_repos()
            except Exception as e:
                repos, err = None, str(e)
            else:
                err = ""
            try:
                if err:
                    self._repos_ready.emit({"ok": False, "repos": [], "error": err})
                else:
                    self._repos_ready.emit({"ok": True, "repos": repos or []})
            except RuntimeError:
                pass  # widget destroyed during the read

        Thread(target=task, daemon=True).start()

    def _on_repos_ready(self, msg):
        if not msg.get("ok"):
            self._pin_status = False
            self._set_status(msg.get("error") or _("Failed to read repositories."),
                             Colors.RED)
            return
        self._repos = msg.get("repos") or []
        self._rebuild_rows()
        if not self._pin_status:
            self._set_status("")

    def _on_op_finished(self, ok, message):
        self._set_busy(False)
        self._pin_status = True
        self._set_status(message or _("Done."),
                         Colors.GREEN if ok else Colors.RED)
        try:
            if self.app is not None and hasattr(self.app, "show_message"):
                self.app.show_message.emit(_("Repositories"), message or _("Done."))
        except Exception:
            pass
        self._reload()


# ── small repro of the dark-dialog look for the add form ────────────
_DIALOG_QSS = f"""
QDialog {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER_STRONG};
    border-radius: 14px;
}}
QLineEdit {{
    background: {Colors.INPUT_BG};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER_INPUT};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: {Fonts.BASE};
}}
QLineEdit:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}
"""