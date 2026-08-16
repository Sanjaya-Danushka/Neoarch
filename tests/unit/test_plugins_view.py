"""Unit tests for the Plugins page: new-style plugin cards and row mapping."""

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QPushButton

from neoarch.frontend.components.packages_grid_view import PackageCard
from neoarch.frontend.components.plugins_view import PluginsView, _PluginPackageCard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _spec(pid="alacritty", pkg="alacritty", **extra):
    spec = {"id": pid, "name": pid.capitalize(), "pkg": pkg, "desc": "A thing"}
    spec.update(extra)
    return spec


def test_plugin_card_uses_new_design_language(qapp):
    card = _PluginPackageCard(_spec(), False, None)
    assert isinstance(card, PackageCard)
    assert card.objectName() == "packageCard"
    assert card.width() == 280
    assert card.height() == 150
    assert hasattr(card, "logo")
    assert hasattr(card, "status_chip")
    assert hasattr(card, "checkbox")


def test_plugin_card_actions_reflect_installed_state(qapp):
    avail = _PluginPackageCard(_spec(), False, None)
    assert [b.text() for b in avail._action_buttons] == ["Install"]
    assert avail.status_chip._text == "Available"

    inst = _PluginPackageCard(_spec(), True, None)
    assert [b.text() for b in inst._action_buttons] == ["Open", "Uninstall"]
    assert inst.status_chip._text == "Installed"


def test_plugin_card_set_installing_swaps_text(qapp):
    inst = _PluginPackageCard(_spec(), True, None)
    inst.set_installing(True)
    assert [b.text() for b in inst._action_buttons] == ["Installing\u2026", "Uninstalling\u2026"]
    assert all(not b.isEnabled() for b in inst._action_buttons)
    inst.set_installing(False)
    assert [b.text() for b in inst._action_buttons] == ["Open", "Uninstall"]

    avail = _PluginPackageCard(_spec(), False, None)
    avail.set_installing(True)
    assert avail._action_buttons[0].text() == "Installing\u2026"
    avail.set_installing(False)
    assert avail._action_buttons[0].text() == "Install"


def test_plugin_card_button_signals_emit_plugin_id(qapp):
    emitted = []

    avail = _PluginPackageCard(_spec(pid="bob"), False, None)
    avail.install_clicked.connect(lambda pid: emitted.append(("install", pid)))
    avail._action_buttons[0].click()

    inst = _PluginPackageCard(_spec(pid="htop"), True, None)
    inst.launch_clicked.connect(lambda pid: emitted.append(("launch", pid)))
    inst.uninstall_clicked.connect(lambda pid: emitted.append(("uninstall", pid)))
    inst._action_buttons[0].click()
    inst._action_buttons[1].click()

    assert emitted == [("install", "bob"), ("launch", "htop"), ("uninstall", "htop")]


class _StubView(QObject):
    install_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)
    uninstall_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.main_app = None


def test_create_app_card_wires_view_signals(qapp):
    view = _StubView()
    emitted = []
    view.install_requested.connect(lambda pid: emitted.append(("install", pid)))
    view.launch_requested.connect(lambda pid: emitted.append(("launch", pid)))
    view.uninstall_requested.connect(lambda pid: emitted.append(("uninstall", pid)))

    avail = PluginsView.create_app_card(view, _spec(pid="bob"), None, False)
    assert isinstance(avail, _PluginPackageCard)
    avail._action_buttons[0].click()

    inst = PluginsView.create_app_card(view, _spec(pid="htop"), None, True)
    inst._action_buttons[0].click()
    inst._action_buttons[1].click()

    assert emitted == [("install", "bob"), ("launch", "htop"), ("uninstall", "htop")]


def test_map_plugin_row_uses_canonical_source(qapp):
    aur = PluginsView._map_plugin_row(_spec(pid="zsh-syntax", pkg="aur/zsh-syntax"))
    assert aur["source"] == "AUR"
    flat = PluginsView._map_plugin_row(_spec(pid="spot", pkg="spot.flatpak"))
    assert flat["source"] == "Flatpak"
    pac = PluginsView._map_plugin_row(_spec(pid="vim", pkg="vim"))
    assert pac["source"] == "pacman"
    assert aur["status"] == "Available"
    assert aur["_installed"] is False


def _card_spec(pid, installed=False, category="", source="pacman"):
    return {"plugin": {"id": pid, "name": pid.capitalize(), "category": category, "pkg": source},
            "installed": installed, "widget": None}


def test_plugins_view_sort_cards_orders_by_mode(qapp):
    cards = [
        _card_spec("b", installed=False, category="System"),
        _card_spec("a", installed=True, category="Games"),
        _card_spec("c", installed=False, category="System"),
    ]
    view = PluginsView.__new__(PluginsView)
    view._sort_mode = "name_asc"
    view._get_package_source = PluginsView._get_package_source
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]
    view._sort_mode = "name_desc"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["c", "b", "a"]
    view._sort_mode = "installed"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]
    view._sort_mode = "category"
    assert [c["plugin"]["id"] for c in PluginsView._sort_cards(view, cards)] == ["a", "b", "c"]
