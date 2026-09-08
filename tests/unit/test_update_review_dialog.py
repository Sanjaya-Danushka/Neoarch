import pytest
from PyQt6.QtWidgets import QApplication, QDialog

from neoarch.frontend.components.update_review_dialog import UpdateReviewDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _sample_packages():
    return [
        {"name": "firefox", "version": "128.0", "new_version": "129.0",
         "source": "pacman"},
        {"name": "yay", "version": "12.4.0", "new_version": "12.4.1",
         "source": "AUR"},
        {"name": "org.chromium.Chromium", "version": "10.0", "new_version": "10.1",
         "source": "Flatpak"},
    ]


def test_update_review_dialog_layout(qapp):
    dlg = UpdateReviewDialog(_sample_packages())
    dlg.show()

    assert dlg.header_label.text() == "Packages to update: 3"
    assert dlg.table.rowCount() == 3
    assert dlg.confirm_btn.text() == "Update All"

    assert dlg.table.item(0, 0).text() == "firefox"
    assert dlg.table.item(0, 1).text() == "Pacman"
    assert dlg.table.item(0, 2).text() == "128.0"
    assert dlg.table.item(0, 3).text() == "129.0"
    assert dlg.table.item(1, 0).text() == "yay"
    assert dlg.table.item(2, 3).text() == "10.1"


def test_update_review_dialog_singular(qapp):
    dlg = UpdateReviewDialog([
        {"name": "kernel", "version": "6.10.1", "new_version": "6.11.0",
         "source": "pacman"},
    ])
    assert dlg.header_label.text() == "Packages to update: 1"


def test_update_review_dialog_accept_reject(qapp):
    dlg = UpdateReviewDialog(_sample_packages())
    dlg.accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    dlg.reject()
    assert dlg.result() == QDialog.DialogCode.Rejected