"""PackageDetailCard — side-panel detail card with rich package info."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QWidget, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush

from neoarch.frontend.tokens import Colors, Fonts, SourceColors
from neoarch.backend.services.i18n import _


def _shadow(widget: QWidget, blur=24, offset=(4, 6), alpha=150):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(*offset)
    widget.setGraphicsEffect(s)


class _Avatar(QLabel):
    def __init__(self, letter: str, color: str):
        super().__init__()
        self._letter = letter[0].upper() if letter else "?"
        self._color = color
        self.setFixedSize(42, 42)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QColor(Colors.TEXT))
        f = QFont()
        f.setPointSize(17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._letter)
        p.end()


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_3}; font-size: {Fonts.TINY}; font-weight: 700; "
        f"letter-spacing: 0.8px; background: transparent; padding: 0;"
    )
    return lbl


def _detail_row(label: str, value: str) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    l = QHBoxLayout(row)
    l.setContentsMargins(0, 2, 0, 2)
    l.setSpacing(8)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {Colors.TEXT_3}; font-size: {Fonts.MD}; background: transparent;")
    lbl.setFixedWidth(56)
    l.addWidget(lbl)
    val = QLabel(value)
    val.setStyleSheet(f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; background: transparent;")
    val.setWordWrap(True)
    l.addWidget(val, 1)
    return row


def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"background: {Colors.BORDER}; max-height: 1px; border: none;")
    return sep


def _close_btn_stylesheet() -> str:
    return """
        QPushButton {
            background-color: #FF5F57;
            color: transparent;
            border: none;
            border-radius: 9px;
            font-size: {Fonts.SM};
            font-weight: 700;
        }
        QPushButton:hover {
            background-color: #FF5F57;
            color: rgba(80, 20, 20, 0.7);
        }
        QPushButton:pressed {
            background-color: #E0554E;
        }
    """


def _nav_btn_stylesheet(color: str = Colors.TEXT_2) -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {color};
            padding: 0 20px;
            text-align: center;
            font-size: {Fonts.BASE};
            font-weight: 500;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {Colors.TEXT};
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.08);
        }}
    """


SOURCE_COLORS = SourceColors


def _fmt_size(b):
    try:
        mb = float(b) / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GiB"
        return f"{mb:.1f} MiB"
    except Exception:
        return "—"


class PackageDetailCard(QFrame):
    install_requested = pyqtSignal()
    update_requested = pyqtSignal()
    uninstall_requested = pyqtSignal()
    launch_requested = pyqtSignal()
    selection_update_requested = pyqtSignal()
    selection_uninstall_requested = pyqtSignal()
    selection_clear_requested = pyqtSignal()
    updates_check_completed = pyqtSignal(str, str, bool, bool)  # name, new_version, has_updates, check_ok

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pkg_data = None
        self._multi_mode = False
        self.setObjectName("packageDetailCard")
        self.setFixedWidth(320)
        self.setVisible(False)
        self._build()

    def close_card(self):
        self.clear()

    @property
    def pkg_data(self):
        return self._pkg_data

    def _build(self):
        self.setStyleSheet(f"""
            QFrame#packageDetailCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(28, 30, 36, 0.55),
                    stop:1 rgba(20, 22, 26, 0.40));
                border: 1px solid {Colors.BORDER_INPUT};
                border-top: 1px solid {Colors.BORDER_HOVER};
                border-radius: 16px;
            }}
        """)
        _shadow(self, blur=40, offset=(8, 12), alpha=180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)

        content = QVBoxLayout(inner)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)

        self.avatar = _Avatar("?", Colors.ACCENT)
        hl.addWidget(self.avatar)

        nc = QVBoxLayout()
        nc.setSpacing(1)
        self.name_label = QLabel()
        f = QFont()
        f.setBold(True)
        f.setPointSize(14)
        self.name_label.setFont(f)
        self.name_label.setStyleSheet(f"color: {Colors.TEXT}; background: transparent;")
        self.name_label.setWordWrap(True)
        nc.addWidget(self.name_label)
        self.version_label = QLabel()
        self.version_label.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; background: transparent;"
        )
        nc.addWidget(self.version_label)
        hl.addLayout(nc, 1)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(_close_btn_stylesheet())
        self.close_btn.clicked.connect(self.close_card)
        self.close_btn.setVisible(True)
        hl.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)

        content.addWidget(header)

        # ── Status badge ──
        self.status_badge = QLabel()
        self.status_badge.setVisible(False)
        content.addSpacing(10)
        content.addWidget(self.status_badge)

        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)

        def _section_block(title: str):
            """Separator + title + rows, grouped so a block hides as one."""
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            v.addSpacing(12)
            v.addWidget(_make_sep())
            v.addSpacing(10)
            v.addWidget(_section_title(title))
            v.addSpacing(6)
            return w, v

        # ── Multi-selection summary (shown instead of the sections below) ──
        self.selection_section, sel = _section_block(_("Selection"))
        self.selection_sources_label = QLabel()
        self.selection_sources_label.setTextFormat(Qt.TextFormat.RichText)
        self.selection_sources_label.setWordWrap(True)
        self.selection_sources_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; background: transparent;"
        )
        sel.addWidget(self.selection_sources_label)
        sel.addSpacing(6)
        self.selection_size_label = QLabel()
        self.selection_size_label.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; background: transparent;"
        )
        sel.addWidget(self.selection_size_label)
        content.addWidget(self.selection_section)
        self.selection_section.setVisible(False)

        # ── Details ──
        self.details_section, dl = _section_block(_("Details"))
        self.version_row = QLabel()
        self.version_row.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; background: transparent;"
        )
        dl.addWidget(self.version_row)

        self.source_row = _detail_row(_("Source"), "")
        dl.addWidget(self.source_row)
        self.id_row = _detail_row(_("ID"), "")
        dl.addWidget(self.id_row)

        self.reason_row = _detail_row(_("Reason"), "")
        self.reason_row.setVisible(False)
        dl.addWidget(self.reason_row)

        self.size_row = _detail_row(_("Size"), "")
        self.size_row.setVisible(False)
        dl.addWidget(self.size_row)
        content.addWidget(self.details_section)

        # ── Reverse dependencies ──
        self.revdeps_widget = QWidget()
        self.revdeps_widget.setStyleSheet("background: transparent;")
        self.revdeps_layout = QVBoxLayout(self.revdeps_widget)
        self.revdeps_layout.setContentsMargins(0, 0, 0, 0)
        self.revdeps_layout.setSpacing(0)

        self.revdeps_label = QLabel()
        self.revdeps_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; background: transparent;"
        )
        self.revdeps_label.setWordWrap(True)
        self.revdeps_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.revdeps_layout.addWidget(self.revdeps_label)

        self.revdeps_section, rl = _section_block(_("Required By"))
        rl.addWidget(self.revdeps_widget)
        content.addWidget(self.revdeps_section)

        # ── Description ──
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; background: transparent;"
        )
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.desc_section, sl = _section_block(_("Description"))
        sl.addWidget(self.desc_label)
        content.addWidget(self.desc_section)

        content.addStretch(1)

        # ── Actions ──
        content.addSpacing(12)
        content.addWidget(_make_sep())
        content.addSpacing(10)

        self.action_container = QWidget()
        self.action_container.setStyleSheet("background: transparent;")
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(6)

        self.install_btn = QPushButton(_("Install Package"))
        self.install_btn.setMinimumHeight(40)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.ACCENT)
        )
        self.install_btn.clicked.connect(self.install_requested.emit)
        self.action_layout.addWidget(self.install_btn)

        self.update_btn = QPushButton(_("Update"))
        self.update_btn.setMinimumHeight(40)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(
            _nav_btn_stylesheet("#FF8A65")
        )
        self.update_btn.clicked.connect(self.update_requested.emit)
        self.action_layout.addWidget(self.update_btn)

        self.uninstall_btn = QPushButton(_("Uninstall Package"))
        self.uninstall_btn.setMinimumHeight(40)
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.RED)
        )
        self.uninstall_btn.clicked.connect(self.uninstall_requested.emit)
        self.action_layout.addWidget(self.uninstall_btn)

        self.launch_btn = QPushButton(_("Launch"))
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.launch_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.ACCENT)
        )
        self.launch_btn.clicked.connect(self.launch_requested.emit)
        self.action_layout.addWidget(self.launch_btn)

        self.check_updates_btn = QPushButton(_("Check for Updates"))
        self.check_updates_btn.setMinimumHeight(40)
        self.check_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_updates_btn.setStyleSheet(
            _nav_btn_stylesheet("#FF8A65")
        )
        self.action_layout.addWidget(self.check_updates_btn)

        self.up_to_date_label = QLabel(_("✓  Up to date"))
        self.up_to_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.up_to_date_label.setStyleSheet(
            f"color: #10B981; font-size: {Fonts.MD}; font-weight: 600; "
            "background: rgba(16,185,129,0.08); border-radius: 8px; padding: 8px;"
        )
        self.action_layout.addWidget(self.up_to_date_label)

        self.aur_sep = _make_sep()
        self.action_layout.addWidget(self.aur_sep)

        self.aur_actions = QWidget()
        self.aur_actions.setStyleSheet("background: transparent;")
        aur_row = QHBoxLayout(self.aur_actions)
        aur_row.setContentsMargins(0, 0, 0, 0)
        aur_row.setSpacing(6)

        self.aur_pkgbuild_btn = QPushButton(_("View PKGBUILD"))
        self.aur_pkgbuild_btn.setMinimumHeight(36)
        self.aur_pkgbuild_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aur_pkgbuild_btn.setToolTip(
            _("Open the PKGBUILD recipe this package builds from"))
        self.aur_pkgbuild_btn.setStyleSheet(_nav_btn_stylesheet(Colors.ORANGE))
        self.aur_pkgbuild_btn.clicked.connect(lambda: self._open_aur("pkgbuild"))
        aur_row.addWidget(self.aur_pkgbuild_btn, 1)

        self.aur_changes_btn = QPushButton(_("View Changes"))
        self.aur_changes_btn.setMinimumHeight(36)
        self.aur_changes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aur_changes_btn.setToolTip(_("Open the commit history for this package"))
        self.aur_changes_btn.setStyleSheet(_nav_btn_stylesheet(Colors.TEXT_2))
        self.aur_changes_btn.clicked.connect(lambda: self._open_aur("changes"))
        aur_row.addWidget(self.aur_changes_btn, 1)

        self.aur_snapshot_btn = QPushButton(_("Download snapshot"))
        self.aur_snapshot_btn.setMinimumHeight(36)
        self.aur_snapshot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aur_snapshot_btn.setToolTip(_("Download the current source tarball"))
        self.aur_snapshot_btn.setStyleSheet(_nav_btn_stylesheet(Colors.TEXT_2))
        self.aur_snapshot_btn.clicked.connect(lambda: self._open_aur("snapshot"))
        aur_row.addWidget(self.aur_snapshot_btn, 1)

        self.action_layout.addWidget(self.aur_actions)

        # ── Multi-selection actions ──
        self.selection_update_btn = QPushButton(_("Update Selected"))
        self.selection_update_btn.setMinimumHeight(40)
        self.selection_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.selection_update_btn.setStyleSheet(
            _nav_btn_stylesheet("#FF8A65")
        )
        self.selection_update_btn.clicked.connect(self.selection_update_requested.emit)
        self.action_layout.addWidget(self.selection_update_btn)

        self.selection_uninstall_btn = QPushButton(_("Uninstall Selected"))
        self.selection_uninstall_btn.setMinimumHeight(40)
        self.selection_uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.selection_uninstall_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.RED)
        )
        self.selection_uninstall_btn.clicked.connect(self.selection_uninstall_requested.emit)
        self.action_layout.addWidget(self.selection_uninstall_btn)

        self.selection_clear_btn = QPushButton(_("Clear Selection"))
        self.selection_clear_btn.setMinimumHeight(36)
        self.selection_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.selection_clear_btn.setStyleSheet(
            _nav_btn_stylesheet(Colors.TEXT_2)
        )
        self.selection_clear_btn.clicked.connect(self.selection_clear_requested.emit)
        self.action_layout.addWidget(self.selection_clear_btn)

        self.selection_update_btn.setVisible(False)
        self.selection_uninstall_btn.setVisible(False)
        self.selection_clear_btn.setVisible(False)

        content.addWidget(self.action_container)
        layout.addWidget(scroll)

    def _source_color(self, source: str) -> str:
        return SOURCE_COLORS.get(source.lower(), Colors.ACCENT)

    def show_package(self, pkg_data: dict):
        self._set_single_mode()
        self._pkg_data = pkg_data
        name = pkg_data.get("name", "")
        version = pkg_data.get("version", "")
        new_version = pkg_data.get("new_version", "")
        source = pkg_data.get("source", "")
        installed = pkg_data.get("installed", False)
        has_update = pkg_data.get("has_update", False)
        description = pkg_data.get("description", "")
        pkg_id = pkg_data.get("id", name)
        view = pkg_data.get("_view", "")
        is_aur = source.upper() == "AUR"

        sc = self._source_color(source)

        self.avatar._letter = name[0].upper() if name else "?"
        self.avatar._color = sc
        self.avatar.update()
        self.name_label.setText(name)

        vt = f"v{version}"
        if new_version and new_version != version:
            vt += f"  →  {new_version}"
        self.version_label.setText(vt)

        # status badge
        if installed:
            if has_update:
                self.status_badge.setText(_("◉  Update Available"))
                self.status_badge.setStyleSheet(
                    f"background: rgba(255,138,101,0.12); color: #FF8A65;"
                    f" font-size: {Fonts.SM}; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
            else:
                self.status_badge.setText(_("◉  Installed"))
                self.status_badge.setStyleSheet(
                    f"background: rgba(16,185,129,0.12); color: #10B981;"
                    f" font-size: {Fonts.SM}; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
                )
        else:
            self.status_badge.setText(_("○  Not Installed"))
            self.status_badge.setStyleSheet(
                f"background: rgba(92,94,102,0.12); color: {Colors.TEXT_3};"
                f" font-size: {Fonts.SM}; font-weight: 600; border-radius: 6px; padding: 3px 10px;"
            )
        self.status_badge.setVisible(True)

        vd = f"v{version}"
        if new_version and new_version != version:
            vd = f"v{version}  →  v{new_version}"
        self.version_row.setText(vd)

        self._set_row_text(self.source_row, source.capitalize() if source else "—")
        self._set_row_text(self.id_row, pkg_id)

        if description:
            self.desc_label.setText(description)
        else:
            self.desc_label.setText(_("No description available."))

        # Installed-only extras: install reason, size, reverse dependencies
        install_reason = pkg_data.get("install_reason", "")
        installed_size = pkg_data.get("installed_size")
        required_by = pkg_data.get("required_by") or []
        is_pacman_managed = source in ("pacman", "AUR", "")
        show_installed_extra = installed and is_pacman_managed

        self.reason_row.setVisible(show_installed_extra)
        self.size_row.setVisible(show_installed_extra)
        self.revdeps_widget.setVisible(show_installed_extra)

        if show_installed_extra:
            self._set_row_text(self.reason_row, install_reason or "—")
            if installed_size:
                self._set_row_text(self.size_row, _fmt_size(installed_size))
            else:
                self._set_row_text(self.size_row, "—")
            if required_by:
                self.revdeps_label.setText(", ".join(required_by))
            else:
                self.revdeps_label.setText(_("Nothing depends on this package (it is not needed by anything installed)."))

        self.launch_btn.setVisible(False)
        if view == "plugins":
            self.install_btn.setVisible(not installed)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(installed)
            self.launch_btn.setVisible(installed)
            self.check_updates_btn.setVisible(False)
            self.up_to_date_label.setVisible(False)
        elif view == "updates":
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(True)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(False)
            self.up_to_date_label.setVisible(False)
        elif view == "discover" and installed:
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(True)
            self.check_updates_btn.setText(_("Check for Updates"))
            self.check_updates_btn.setEnabled(True)
            self.up_to_date_label.setVisible(False)
        elif installed:
            if has_update:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(True)
                self.uninstall_btn.setVisible(True)
                self.check_updates_btn.setVisible(False)
                self.up_to_date_label.setVisible(False)
            else:
                self.install_btn.setVisible(False)
                self.update_btn.setVisible(False)
                self.uninstall_btn.setVisible(True)
                self.check_updates_btn.setVisible(False)
                self.up_to_date_label.setVisible(False)
        else:
            self.install_btn.setVisible(True)
            self.update_btn.setVisible(False)
            self.uninstall_btn.setVisible(False)
            self.check_updates_btn.setVisible(False)
            self.up_to_date_label.setVisible(False)

        self.aur_sep.setVisible(is_aur)
        self.aur_actions.setVisible(is_aur)

        # An AUR "update" rebuilds from the PKGBUILD, so it stays worth
        # offering when no newer version was detected - the recipe, the base or
        # a dependency may have changed. Every installed AUR package therefore
        # keeps the rebuild next to its three AUR actions. The plugins page is
        # the exception: plugins are updated by reinstalling them there.
        if is_aur and installed and view != "plugins" \
                and not self.update_btn.isVisible():
            self.install_btn.setVisible(False)
            self.update_btn.setVisible(True)

        # One label for every source: an AUR "update" rebuilds from the
        # PKGBUILD, but the button reads the same everywhere and the AUR
        # actions above it already show what the rebuild reads.
        self.update_btn.setText(_("Update"))

        self.setVisible(True)

    def _set_single_mode(self):
        """Leave the multi-selection summary and restore the per-package layout."""
        self._multi_mode = False
        self.selection_section.setVisible(False)
        self.selection_update_btn.setVisible(False)
        self.selection_uninstall_btn.setVisible(False)
        self.selection_clear_btn.setVisible(False)
        self.details_section.setVisible(True)
        self.revdeps_section.setVisible(True)
        self.desc_section.setVisible(True)

    def show_selection(self, pkgs, download_size=0, action="update",
                       updatable=True, allow_uninstall=False):
        """Show the aggregate panel for a multi-row selection.

        Per-package rows and the AUR-only actions describe exactly one
        package, so they are replaced by a count, a per-source breakdown and
        the actions that apply to the whole selection.

        ``updatable`` says whether any marked package actually has a pending
        update. On Installed most packages are up to date, and offering
        "Update Selected" for a selection that cannot change anything would
        push the user towards a no-op; there, the summary offers uninstall
        instead. ``allow_uninstall`` adds removal to a selection that also
        has something to update.
        """
        pkgs = [p for p in (pkgs or []) if isinstance(p, dict)]
        count = len(pkgs)
        if not count:
            self.clear()
            return

        self._pkg_data = None
        self._multi_mode = True

        counts = {}
        for pkg in pkgs:
            src = pkg.get("source") or "pacman"
            counts[src] = counts.get(src, 0) + 1
        # Busiest source first, then alphabetical, so the list stays stable.
        order = sorted(counts, key=lambda s: (-counts[s], s.lower()))

        self.avatar._letter = "N"
        self.avatar._color = Colors.ACCENT
        self.avatar.update()
        self.name_label.setText(
            _("{count} package{s} selected").format(
                count=count, s="" if count == 1 else "s"))
        labels = {
            "update": (_("Update Selected ({count})"),
                       _("Checked for update — actions apply to all of them")),
            "install": (_("Install Selected ({count})"),
                        _("Checked to install — actions apply to all of them")),
            "uninstall": (_("Uninstall Selected ({count})"),
                          _("Marked — actions apply to all of them")),
        }
        # An update page whose selection holds nothing to update would offer
        # a button that cannot change anything, so the primary action becomes
        # the removal. That also means the separate Uninstall button would be
        # a second, identical control - one removal action is enough.
        if action == "update" and not updatable:
            action = "uninstall"
            allow_uninstall = False
        primary_text, sub_text = labels.get(action, labels["uninstall"])
        self.version_label.setText(sub_text)

        self.status_badge.setVisible(False)
        chips = " &nbsp;·&nbsp; ".join(
            '<span style="color:{c}; font-weight:600;">{n} {s}</span>'.format(
                c=self._source_color(src), n=counts[src], s=src)
            for src in order)
        self.selection_sources_label.setText(chips)
        if download_size:
            self.selection_size_label.setText(
                _("{size} to download").format(size=_fmt_size(download_size)))
        else:
            self.selection_size_label.setText("")

        self.details_section.setVisible(False)
        self.revdeps_section.setVisible(False)
        self.desc_section.setVisible(False)
        self.selection_section.setVisible(True)

        self.install_btn.setVisible(False)
        self.update_btn.setVisible(False)
        self.uninstall_btn.setVisible(False)
        self.launch_btn.setVisible(False)
        self.check_updates_btn.setVisible(False)
        self.up_to_date_label.setVisible(False)
        self.aur_sep.setVisible(False)
        self.aur_actions.setVisible(False)
        self.selection_update_btn.setText(primary_text.format(count=count))
        self.selection_update_btn.setVisible(True)
        # Every marked package on Updates and Installed is removable, so
        # removal rides alongside the primary action - unless the primary
        # already is the removal, which would show it twice.
        if allow_uninstall:
            self.selection_uninstall_btn.setText(
                _("Uninstall Selected ({count})").format(count=count))
            self.selection_uninstall_btn.setVisible(True)
        else:
            self.selection_uninstall_btn.setVisible(False)
        self.selection_clear_btn.setVisible(True)

        self.setVisible(True)

    @staticmethod
    def _set_row_text(row: QWidget, value: str):
        for i in range(row.layout().count()):
            w = row.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and i == 1:
                w.setText(value)
                break

    def _open_aur(self, kind):
        name = (self._pkg_data or {}).get("name", "").strip()
        if not name:
            return
        urls = {
            "pkgbuild": f"https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h={name}",
            "changes": f"https://aur.archlinux.org/cgit/aur.git/log/?h={name}",
            "snapshot": f"https://aur.archlinux.org/cgit/aur.git/snapshot/{name}.tar.gz",
        }
        url = urls.get(kind)
        if not url:
            return
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def set_extra_info(self, info: dict):
        """Populate async-loaded installed-only extras (reason, size, reverse deps)."""
        if not self._pkg_data:
            return
        source = (self._pkg_data.get("source") or "").lower()
        if source not in ("pacman", "aur"):
            return
        install_reason = info.get("install_reason") or ""
        installed_size = info.get("installed_size")
        required_by = info.get("required_by") or []

        self.reason_row.setVisible(True)
        self._set_row_text(self.reason_row, install_reason or "—")

        if installed_size:
            self.size_row.setVisible(True)
            self._set_row_text(self.size_row, _fmt_size(installed_size))

        if required_by:
            self.revdeps_widget.setVisible(True)
            self.revdeps_label.setText(", ".join(required_by))

    def clear(self):
        self._set_single_mode()
        self._pkg_data = None
        self.name_label.clear()
        self.version_label.clear()
        self.version_row.clear()
        self.desc_label.clear()
        self.selection_sources_label.clear()
        self.selection_size_label.clear()
        self.status_badge.setVisible(False)
        self.aur_sep.setVisible(False)
        self.aur_actions.setVisible(False)
        self.setVisible(False)
