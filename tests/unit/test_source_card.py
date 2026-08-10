"""Unit tests for SourceCard and SourceItem macOS dark glass UI components."""

import os
import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_source_item_creation(qapp):
    from neoarch.frontend.components.source_item import SourceItem

    item = SourceItem("Pacman", "/path/to/pacman.svg", count=5, size="12.5 MB")
    assert item.source_name == "Pacman"
    assert item.is_checked() is True

    item.set_checked(False)
    assert item.is_checked() is False
    assert item.toggle.isChecked() is False

    item.set_count(10, "25.0 MB")
    assert item.count_label.text() == "10"


def test_source_card_initialization(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    card = SourceCard()
    card.show()
    assert card.get_search_mode() == "both"

    card.add_source("pacman", "/path/to/pacman.svg")
    card.add_source("AUR", "/path/to/aur.svg")

    sources = card.get_selected_sources()
    assert "pacman" in sources
    assert "AUR" in sources
    assert sources["pacman"] is True

    card.configure_sections(
        show_status=True,
        show_sort=True,
        show_actions=True,
        show_summary=True,
        show_search=True,
        show_counts=True,
    )
    assert card.status_widget.isHidden() is False
    assert card.sort_widget.isHidden() is False
    assert card.actions_widget.isHidden() is False

    card.set_summary(5, "120 MB")
    assert "5 updates" in card.summary_label.text()

    card.set_sort("size", False)
    assert card.get_sort() == "size"
    assert card.get_sort_asc() is False
