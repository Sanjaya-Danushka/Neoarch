import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from neoarch.frontend.views.settings_general import GeneralSettingsWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeApp(QWidget):
    """Minimal app the General settings page talks to."""

    def __init__(self):
        super().__init__()
        self.settings = {
            "include_firmware_updates": True,
            "check_pipx_updates": True,
            "npm_user_mode": True,
            "bundle_autosave": True,
            "aur_helper": "auto",
            "culture": "en",
        }

    def update_setting(self, key, value):
        self.settings[key] = value

    def export_settings(self):
        pass

    def import_settings(self):
        pass

    def rebuild_ui(self):
        pass


def _build(monkeypatch, cmd_exists):
    monkeypatch.setattr(
        "neoarch.frontend.views.settings_general.sys_utils.cmd_exists",
        lambda name: cmd_exists)
    widget = GeneralSettingsWidget(_FakeApp())
    return widget


def test_missing_tools_disable_toggles(qapp, monkeypatch):
    widget = _build(monkeypatch, cmd_exists=False)

    for toggle in (widget.sw_firmware, widget.sw_pipx, widget.sw_npm):
        assert not toggle.isEnabled()
        assert "sudo pacman -S" in toggle.toolTip()


def test_installed_tools_enable_toggles(qapp, monkeypatch):
    widget = _build(monkeypatch, cmd_exists=True)

    for toggle in (widget.sw_firmware, widget.sw_pipx, widget.sw_npm):
        assert toggle.isEnabled()
        assert toggle.toolTip() == ""


def test_disabled_toggles_keep_values(qapp, monkeypatch):
    widget = _build(monkeypatch, cmd_exists=False)

    assert widget.sw_firmware.isChecked()
    assert widget.sw_pipx.isChecked()
    assert widget.sw_npm.isChecked()


def test_refresh_source_states_reenables_after_install(qapp, monkeypatch):
    widget = _build(monkeypatch, cmd_exists=False)
    assert not widget.sw_pipx.isEnabled()
    assert "sudo pacman -S pipx" in widget.sw_pipx.toolTip()

    monkeypatch.setattr(
        "neoarch.frontend.views.settings_general.sys_utils.cmd_exists",
        lambda name: True)
    widget.refresh_source_states()

    assert widget.sw_pipx.isEnabled()
    assert widget.sw_pipx.toolTip() == ""
    for toggle in (widget.sw_firmware, widget.sw_pipx, widget.sw_npm):
        assert toggle.isEnabled()


def test_refresh_source_states_disables_after_removal(qapp, monkeypatch):
    widget = _build(monkeypatch, cmd_exists=True)
    assert widget.sw_firmware.isEnabled()

    monkeypatch.setattr(
        "neoarch.frontend.views.settings_general.sys_utils.cmd_exists",
        lambda name: False)
    widget.refresh_source_states()

    assert not widget.sw_firmware.isEnabled()
    assert "sudo pacman -S fwupd" in widget.sw_firmware.toolTip()

    subtitle = widget._source_rows[0]["subtitle"]
    assert subtitle is not None
    assert "sudo pacman -S fwupd" in subtitle.text()