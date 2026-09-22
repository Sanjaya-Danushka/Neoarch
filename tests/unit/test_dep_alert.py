"""Dependency-alert behavior: only required deps flag the About icon red.

Optional components (flatpak, npm, docker, fwupd, pipx, ...) degrade
gracefully; their absence is still shown on the Diagnostics page (orange
warn + Install) but must not turn the main panel icon red.
"""

import pytest

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.mixins.views import _ViewsMixin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _catalog(pacman=True, fwupdmgr=False, pipx=False):
    return [
        {"name": "pacman", "pkg": "pacman", "required": True,
         "feature": "core", "present": pacman},
        {"name": "fwupdmgr", "pkg": "fwupd", "required": False,
         "feature": "firmware", "present": fwupdmgr},
        {"name": "pipx", "pkg": "pipx", "required": False,
         "feature": "pipx apps", "present": pipx},
    ]


def _set_catalog(monkeypatch, **kw):
    monkeypatch.setattr(
        "neoarch.backend.sys_utils.get_dependency_catalog",
        lambda: _catalog(**kw))


class _NavBtn:
    def setToolTip(self, text):
        self.tip = text


class _AboutView:
    def __init__(self):
        self.required = []
        self.optional = []

    def set_dep_alert(self, required, optional=()):
        self.required = list(required)
        self.optional = list(optional)


class _Badge:
    def __init__(self):
        self.visible = False
        self.text = None
        self.stylesheet = ""

    def setText(self, text):
        self.text = text

    def setStyleSheet(self, css):
        self.stylesheet = css

    def adjustSize(self):
        self.adjust_count = getattr(self, "adjust_count", 0) + 1

    def setFixedSize(self, w, h):
        self.fixed_size = (w, h)

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False


class _Label:
    def __init__(self):
        self.pixmaps = []

    def setPixmap(self, pixmap):
        self.pixmaps.append(pixmap)


class _IconRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, path, size=18, tint=None):
        self.calls.append((path, size, tint))
        return QIcon()


def _make_app():
    app = object.__new__(_ViewsMixin)
    app._about_icon_label = _Label()
    app.nav_buttons = {"about": _NavBtn()}
    app.about_view = _AboutView()
    app._about_dep_badge = _Badge()
    app.get_svg_icon = _IconRecorder()
    return app


def test_optional_missing_shows_green_icon_and_badge(monkeypatch):
    from neoarch.frontend.tokens import Colors

    _set_catalog(monkeypatch, pacman=True, fwupdmgr=False, pipx=False)
    app = _make_app()
    app._update_dep_alert(["fwupdmgr", "pipx"])
    assert app._dep_missing == []
    assert app._dep_optional_missing == ["fwupdmgr", "pipx"]
    assert app._about_dep_badge.visible is True
    assert app._about_dep_badge.text == "2"
    assert "background-color: " + str(Colors.GREEN) in app._about_dep_badge.stylesheet
    icon_call = app.get_svg_icon.calls[-1]
    assert icon_call[2] == Colors.GREEN
    assert app.nav_buttons["about"].tip == "About \u2014 optional components missing"
    assert app.about_view.required == []
    assert app.about_view.optional == ["fwupdmgr", "pipx"]

    path = str(icon_call[0]).replace("\\", "/")
    assert path.endswith("about.svg")


def test_required_missing_alerts(monkeypatch):
    from neoarch.frontend.tokens import Colors

    _set_catalog(monkeypatch, pacman=False, fwupdmgr=False)
    app = _make_app()
    app._update_dep_alert(["pacman", "fwupdmgr"])
    assert app._dep_missing == ["pacman"]
    assert app._dep_optional_missing == ["fwupdmgr"]
    assert app._about_dep_badge.visible is True
    assert app._about_dep_badge.text == "1"
    assert "background-color: " + str(Colors.RED) in app._about_dep_badge.stylesheet
    assert app.get_svg_icon.calls[-1][2] == Colors.RED
    assert app.about_view.required == ["pacman"]
    assert app.about_view.optional == ["fwupdmgr"]


def test_required_plus_optional_alerts_only_required(monkeypatch):
    _set_catalog(monkeypatch, pacman=False, pipx=False)
    app = _make_app()
    app._update_dep_alert(["pipx", "pacman", "fwupdmgr"])
    assert app._dep_missing == ["pacman"]
    assert app._dep_optional_missing == ["pipx", "fwupdmgr"]
    assert app._about_dep_badge.text == "1"


def test_no_missing_no_alert(monkeypatch):
    _set_catalog(monkeypatch, pacman=True)
    app = _make_app()
    app._update_dep_alert([])
    assert app._dep_missing == []
    assert app._dep_optional_missing == []
    assert app._about_dep_badge.visible is False
    assert app.get_svg_icon.calls[-1][2] is None


def test_catalog_failure_falls_back_to_all_missing(monkeypatch):
    from neoarch.frontend.tokens import Colors

    def boom():
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr("neoarch.backend.sys_utils.get_dependency_catalog", boom)
    app = _make_app()
    app._update_dep_alert(["fwupdmgr", "pipx"])
    assert app._dep_missing == ["fwupdmgr", "pipx"]
    assert app._dep_optional_missing == []
    assert app._about_dep_badge.visible is True
    assert app.get_svg_icon.calls[-1][2] == Colors.RED


def test_pipx_and_fwupd_are_optional_in_catalog():
    from neoarch.backend.sys_utils import get_dependency_catalog
    catalog = {d["name"]: d for d in get_dependency_catalog()}
    assert catalog["pipx"]["required"] is False
    assert catalog["fwupdmgr"]["required"] is False
    assert catalog["npm"]["required"] is False


def test_alert_nav_button_dot_states(qapp):
    from neoarch.frontend.tokens import Colors
    from neoarch.frontend.components.about_tab import _AlertNavButton

    btn = _AlertNavButton("Diagnostics")
    assert btn._dot.isHidden()

    btn.set_alert("error")
    assert not btn._dot.isHidden()
    assert str(Colors.RED) in btn._dot.styleSheet()

    btn.set_alert("warn")
    assert not btn._dot.isHidden()
    assert str(Colors.GREEN) in btn._dot.styleSheet()

    btn.set_alert(None)
    assert btn._dot.isHidden()

    btn.set_alert(True)
    assert not btn._dot.isHidden()
    assert str(Colors.RED) in btn._dot.styleSheet()