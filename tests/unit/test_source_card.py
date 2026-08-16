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

    card.set_summary(5, "120 MB", noun="updates available", size_label="to download")
    assert card.summary_count_label.text() == "5"
    assert "UPDATES AVAILABLE" == card.summary_count_caption.text()
    assert "120 MB" == card.summary_size_label.text()
    assert "TO DOWNLOAD" == card.summary_size_caption.text()
    card.set_summary(None)
    assert card.summary_widget.isHidden() is True

    card.set_sort("size", False)
    assert card.get_sort() == "size"
    assert card.get_sort_asc() is False


def test_source_card_health_section(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    card = SourceCard()
    card.add_source("pacman", "/path/to/pacman.svg")
    card.add_source("AUR", "/path/to/aur.svg")
    card.show()
    card.configure_sections(show_health=True, show_counts=True)
    assert card.health_widget.isHidden() is False

    card.set_health(orphans=3, pacnew=1, outdated=7)
    assert card._health_rows["orphans"]._count == 3
    assert card._health_rows["pacnew"]._count == 1
    assert card._health_rows["outdated"]._count == 7

    card.set_distribution({"pacman": 5, "AUR": 3})
    assert card.distribution_bar.isVisible()


def test_source_card_health_signal(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    card = SourceCard()
    captured = []
    card.health_action.connect(lambda a: captured.append(a))
    card._health_rows["orphans"].clicked.emit()
    card._health_rows["pacnew"].clicked.emit()
    card._health_rows["outdated"].clicked.emit()
    assert captured == ["orphans", "pacnew", "outdated"]


def test_set_categories_builds_list_with_counts(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    sc = SourceCard()
    sc.set_categories(["Dev", "System"], {"Dev": 50, "System": 5})
    rows = [cat for cat, _ in sc._category_rows]
    assert rows == ["", "Dev", "System"]
    counts = [row.count for _, row in sc._category_rows]
    assert counts == [55, 50, 5]
    assert sc._current_category == ""


def test_category_selection_emits_and_checks_row(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    sc = SourceCard()
    emitted = []
    sc.category_changed.connect(emitted.append)
    sc.set_categories(["Dev", "System"])
    sc._on_category_selected("Dev")
    assert emitted == ["Dev"]
    state = {cat: row.isChecked() for cat, row in sc._category_rows}
    assert state == {"": False, "Dev": True, "System": False}


def test_status_mode_click_emits(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    sc = SourceCard()
    emitted = []
    sc.status_mode_changed.connect(emitted.append)
    sc._on_status_mode_clicked("installed")
    assert emitted == ["installed"]


def test_configure_stats_and_set_stats(qapp):
    from neoarch.frontend.components.source_card import SourceCard

    sc = SourceCard()
    sc.configure_stats("Extension Stats", [("total", "Total"), ("installed", "Installed")])
    sc.set_stats(total=183, installed=28)
    assert sc._stat_labels["total"].text() == "183"
    assert sc._stat_labels["installed"].text() == "28"
