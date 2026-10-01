import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.components.package_detail_card import PackageDetailCard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_aur_actions_visible_only_for_aur(qapp):
    card = PackageDetailCard()
    card.show()
    pkg = {"name": "yay", "version": "12.4.1", "source": "AUR",
           "installed": False, "has_update": False,
           "description": "AUR helper written in Go.", "_view": ""}
    card.show_package(pkg)

    assert card.aur_sep.isVisible() is True
    assert card.aur_actions.isVisible() is True
    assert card.aur_pkgbuild_btn.text() == "View PKGBUILD"

    card.show_package({"name": "bash", "version": "5.2", "source": "pacman",
                       "installed": True, "has_update": False,
                       "description": "GNU Bourne Again SHell", "_view": ""})
    assert card.aur_sep.isVisible() is False
    assert card.aur_actions.isVisible() is False

    card.clear()
    assert card.aur_sep.isVisible() is False
    assert card.aur_actions.isVisible() is False


def test_update_button_reads_update_for_every_source(qapp):
    card = PackageDetailCard()
    card.show()

    card.show_package({"name": "yay", "version": "12.4.1", "source": "AUR",
                       "installed": True, "has_update": True,
                       "description": "AUR helper", "_view": ""})
    assert card.update_btn.text() == "Update"

    card.show_package({"name": "bash", "version": "5.2", "source": "pacman",
                       "installed": True, "has_update": True,
                       "description": "GNU shell", "_view": ""})
    assert card.update_btn.text() == "Update"


@pytest.mark.parametrize("view", ["updates", "installed", "discover"])
def test_installed_aur_package_always_offers_the_rebuild(qapp, view):
    # The three AUR actions show next to the rebuild, and a rebuild stays
    # meaningful with no newer version: the PKGBUILD, base or a dep changed.
    card = PackageDetailCard()
    card.show()
    card.show_package({"name": "yay", "version": "12.4.1", "source": "AUR",
                       "installed": True, "has_update": False,
                       "description": "AUR helper", "_view": view})

    assert card.aur_actions.isVisible() is True
    assert card.update_btn.isVisible() is True
    assert card.update_btn.text() == "Update"
    assert card.install_btn.isVisible() is False


def test_up_to_date_pacman_package_still_has_no_update_button(qapp):
    card = PackageDetailCard()
    card.show()
    card.show_package({"name": "bash", "version": "5.2", "source": "pacman",
                       "installed": True, "has_update": False,
                       "description": "GNU shell", "_view": "installed"})

    assert card.aur_actions.isVisible() is False
    assert card.update_btn.isVisible() is False
    assert card.uninstall_btn.isVisible() is True


def test_aur_package_that_is_not_installed_offers_install_not_rebuild(qapp):
    card = PackageDetailCard()
    card.show()
    card.show_package({"name": "yay", "version": "12.4.1", "source": "AUR",
                       "installed": False, "has_update": False,
                       "description": "AUR helper", "_view": "installed"})

    assert card.install_btn.isVisible() is True
    assert card.update_btn.isVisible() is False


def test_plugins_page_keeps_its_own_actions_for_aur(qapp):
    # Plugins are updated by reinstalling them there, so the plugins view
    # keeps uninstall/launch instead of a rebuild button.
    card = PackageDetailCard()
    card.show()
    card.show_package({"name": "some-plugin", "version": "1.0", "source": "AUR",
                       "installed": True, "has_update": False,
                       "description": "plugin", "_view": "plugins"})

    assert card.update_btn.isVisible() is False
    assert card.uninstall_btn.isVisible() is True
    assert card.launch_btn.isVisible() is True


def test_show_selection_replaces_single_package_fields(qapp):
    card = PackageDetailCard()
    card.show()
    card.show_package({"name": "bash", "version": "5.2", "source": "pacman",
                       "installed": True, "has_update": True,
                       "description": "GNU shell", "_view": ""})

    card.show_selection([
        {"name": "bash", "source": "pacman"},
        {"name": "curl", "source": "pacman"},
        {"name": "yay", "source": "AUR"},
    ], download_size=1024 * 1024)

    assert card.name_label.text() == "3 packages selected"
    assert card.details_section.isVisible() is False
    assert card.revdeps_section.isVisible() is False
    assert card.desc_section.isVisible() is False
    assert card.selection_section.isVisible() is True
    # Per-package actions describe one package, so they are hidden.
    assert card.update_btn.isVisible() is False
    assert card.install_btn.isVisible() is False
    assert card.uninstall_btn.isVisible() is False
    assert card.aur_actions.isVisible() is False
    assert card.selection_update_btn.isVisible() is True
    assert card.selection_clear_btn.isVisible() is True
    assert card.selection_update_btn.text() == "Update Selected (3)"
    assert card._pkg_data is None


def test_show_selection_breaks_down_sources_and_size(qapp):
    card = PackageDetailCard()
    card.show()

    card.show_selection([
        {"name": "a", "source": "pacman"},
        {"name": "b", "source": "AUR"},
        {"name": "c", "source": "AUR"},
        {"name": "d", "source": "Flatpak"},
    ], download_size=1024 * 1024 * 2)

    breakdown = card.selection_sources_label.text()
    assert "2 AUR" in breakdown
    assert "1 pacman" in breakdown
    assert "1 Flatpak" in breakdown
    assert card.selection_size_label.text() == "2.0 MiB to download"


def test_show_selection_without_empty_list_clears_card(qapp):
    card = PackageDetailCard()
    card.show()
    card.show_selection([{"name": "a", "source": "pacman"}])
    assert card.selection_section.isVisible() is True

    card.show_selection([])
    assert card.isVisible() is False
    assert card._pkg_data is None


def test_show_package_restores_single_package_layout(qapp):
    card = PackageDetailCard()
    card.show()
    card.show_selection([{"name": "a", "source": "pacman"},
                         {"name": "b", "source": "AUR"}])
    card.show_package({"name": "yay", "version": "12.4.1", "source": "AUR",
                       "installed": True, "has_update": True,
                       "description": "AUR helper", "_view": ""})

    assert card._multi_mode is False
    assert card.selection_section.isVisible() is False
    assert card.selection_update_btn.isVisible() is False
    assert card.selection_clear_btn.isVisible() is False
    assert card.details_section.isVisible() is True
    assert card.desc_section.isVisible() is True
    assert card.aur_actions.isVisible() is True
    assert card.update_btn.isVisible() is True


def test_selection_signals_emit_without_touching_package_data(qapp):
    card = PackageDetailCard()
    card.show_selection([{"name": "a", "source": "pacman"},
                         {"name": "b", "source": "AUR"}])
    seen = []
    card.selection_update_requested.connect(lambda: seen.append("update"))
    card.selection_clear_requested.connect(lambda: seen.append("clear"))

    card.selection_update_btn.click()
    card.selection_clear_btn.click()

    assert seen == ["update", "clear"]