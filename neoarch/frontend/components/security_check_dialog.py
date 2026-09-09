"""Pre-install AUR security scan results dialog.

Shown when AUR packages are about to be installed. Lists static-scan
findings per package so the user can review before the build starts.
Warning-level findings just require a Continue; if any critical finding
exists the Continue button stays disabled until the risk is explicitly
accepted — a soft gate, never a silent approval.
"""

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from neoarch.backend.services.i18n import _
from neoarch.frontend.tokens import Colors, Fonts

_SEVERITY_COLOR = {
    "critical": Colors.RED,
    "warning": Colors.ORANGE,
    "info": Colors.TEXT_3,
}


class SecurityScanDialog(QDialog):
    """Modal review of pre-install security findings for AUR packages."""

    def __init__(self, findings_by_pkg: Dict[str, List[Dict]], parent=None):
        super().__init__(parent)
        self._findings_by_pkg = findings_by_pkg or {}
        all_findings = [f for fs in self._findings_by_pkg.values() for f in fs]
        self._has_critical = any(
            f.get("severity") == "critical" for f in all_findings)
        pkg_list = ", ".join(self._findings_by_pkg.keys())
        self.setWindowTitle(_("AUR Security Notice"))
        self.resize(680, 480)
        self.setMinimumWidth(580)
        self.setStyleSheet(
            f"QDialog {{ background-color: {Colors.SURFACE}; }}")
        self._build(all_findings, pkg_list)

    def _build(self, all_findings, pkg_list):
        v = QVBoxLayout(self)
        v.setSpacing(12)

        count = len(all_findings)
        if count:
            header = _(
                "Security scan found {count} issue(s) in {pkgs}").format(
                count=count, pkgs=pkg_list)
        else:
            header = _(
                "No security issues found for any scanned AUR package.")
        header_label = QLabel(header)
        header_label.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.XL};"
            f" font-weight: 600;")
        header_label.setWordWrap(True)
        v.addWidget(header_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea {{ background: transparent; }}")
        body = QWidget()
        body.setStyleSheet("QWidget {{ background: transparent; }}")
        bv = QVBoxLayout(body)
        bv.setSpacing(10)
        bv.setContentsMargins(0, 0, 0, 0)

        if self._findings_by_pkg:
            for pkg, findings in self._findings_by_pkg.items():
                bv.addWidget(self._package_card(pkg, findings))

        scroll.setWidget(body)
        v.addWidget(scroll, 1)

        if self._has_critical:
            self.risk_check = QCheckBox(
                _("I understand the risk — continue anyway"))
            self.risk_check.setCursor(Qt.CursorShape.PointingHandCursor)
            self.risk_check.setStyleSheet(
                f"QCheckBox {{ color: {Colors.RED}; font-size: {Fonts.BASE};"
                f" font-weight: 600; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px; }}")
            self.risk_check.toggled.connect(self._on_risk_toggled)
            v.addWidget(self.risk_check)

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        self.cancel_btn = QPushButton(_("Cancel"))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.CARD};"
            f" color: {Colors.TEXT}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: {Fonts.BASE}; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {Colors.CARD_HOVER};"
            f" border-color: {Colors.BORDER_HOVER}; }}")
        self.cancel_btn.clicked.connect(self.reject)
        h.addWidget(self.cancel_btn)
        h.addStretch(1)

        label = (_("I understand, continue") if self._has_critical
                 else _("Continue"))
        self.continue_btn = QPushButton(label)
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.setMinimumHeight(36)
        self.continue_btn.setDefault(True)
        self.continue_btn.setMinimumWidth(150)
        self.continue_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.WHITE};"
            f" color: {Colors.TEXT_ON_ACCENT};"
            f" border: 1px solid rgba(255, 255, 255, 0.9);"
            f" border-radius: 10px; padding: 8px 18px;"
            f" font-size: {Fonts.BASE}; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.WHITE_HOVER}; }}"
            f"QPushButton:disabled {{ background-color: {Colors.SURFACE_3};"
            f" color: {Colors.TEXT_3}; border-color: {Colors.BORDER}; }}")
        self.continue_btn.clicked.connect(self.accept)
        if self._has_critical:
            self.continue_btn.setEnabled(False)
        h.addWidget(self.continue_btn)

        v.addWidget(row)

    def _on_risk_toggled(self, checked):
        self.continue_btn.setEnabled(checked)

    def _package_card(self, pkg, findings):
        card = QWidget()
        card.setStyleSheet(
            f"QWidget {{ background-color: {Colors.CARD};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(6)

        name = QLabel(pkg)
        name.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: {Fonts.CARD_TITLE};"
            f" font-weight: 700;")
        cv.addWidget(name)

        for f in findings:
            sev = f.get("severity", "info")
            color = _SEVERITY_COLOR.get(sev, Colors.TEXT_3)
            rule = QLabel(f"{sev.upper()}  ·  {f.get('rule', '')}")
            rule.setStyleSheet(
                f"color: {color}; font-size: {Fonts.BASE};"
                f" font-weight: 700;")
            rule.setWordWrap(True)
            cv.addWidget(rule)

            detail = QLabel(f.get("detail", ""))
            detail.setStyleSheet(
                f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};")
            detail.setWordWrap(True)
            cv.addWidget(detail)

            matched = f.get("matched")
            if matched:
                loc = f.get("file") or f.get("context") or ""
                if f.get("line"):
                    loc = f"{loc}:{f['line']}" if loc else str(f["line"])
                snippet = QLabel(f"[{loc}]  {matched}")
                snippet.setStyleSheet(
                    f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
                    f" font-family: {Fonts.MONO};")
                snippet.setWordWrap(True)
                cv.addWidget(snippet)

        return card
