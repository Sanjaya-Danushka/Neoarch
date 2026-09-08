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