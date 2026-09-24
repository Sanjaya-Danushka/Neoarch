import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.mixins.filters import _FiltersMixin

_ALL_SOURCES = ["pacman", "AUR", "Flatpak", "npm", "Firmware", "pipx"]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeSourceItem:
    def __init__(self):
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, value):
        self.enabled = bool(value)

    def setToolTip(self, text):
        self.tooltip = text


class _FakeSourceCard:
    def __init__(self, names):
        self.sources = {name: _FakeSourceItem() for name in names}


class _FakeCtx:
    def __init__(self, card, present):
        self.source_card = card
        self._present = set(present)

    def cmd_exists(self, binary):
        return binary in self._present


def _build(present):
    card = _FakeSourceCard(_ALL_SOURCES)
    ctx = _FakeCtx(card, present)
    _FiltersMixin._disable_unavailable_sources(ctx)
    return card


def test_no_tools_installed_disables_everything():
    card = _build(present=[])
    assert card.sources["pacman"].enabled
    assert not card.sources["Flatpak"].enabled
    assert not card.sources["npm"].enabled
    assert not card.sources["Firmware"].enabled
    assert not card.sources["pipx"].enabled


def test_disabled_rows_show_install_path():
    card = _build(present=[])
    assert "sudo pacman -S python-pipx" in card.sources["pipx"].tooltip
    assert "sudo pacman -S fwupd" in card.sources["Firmware"].tooltip
    assert "sudo pacman -S flatpak" in card.sources["Flatpak"].tooltip
    assert "sudo pacman -S npm" in card.sources["npm"].tooltip


def test_installed_tools_stay_enabled():
    card = _build(present=["flatpak", "npm", "fwupdmgr", "pipx"])
    for name in ("Flatpak", "npm", "Firmware", "pipx"):
        assert card.sources[name].enabled
        assert card.sources[name].tooltip == ""


def test_pacman_aur_always_enabled():
    card = _build(present=[])
    assert card.sources["pacman"].enabled
    assert card.sources["AUR"].enabled


def _real_item(name):
    from neoarch.frontend.components.source_item import SourceItem
    return SourceItem(name, "")


def test_disabled_real_toggle_is_inert(qapp):
    item = _real_item("pipx")
    assert item.toggle.isEnabled()
    item.setEnabled(False)
    assert not item.toggle.isEnabled()
    item.toggle.toggle()
    assert item.toggle.isChecked() is True
    item.setEnabled(True)
    item.toggle.toggle()
    assert item.toggle.isChecked() is False