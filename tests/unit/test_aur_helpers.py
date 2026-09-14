# Unit tests for AUR helper functionality
# Tests the multi-AUR helper support implementation

import pytest
from unittest.mock import patch

from neoarch.backend import sys_utils


class TestAURHelperDetection:
    """Test AUR helper detection and selection"""

    @pytest.mark.unit
    def test_cmd_exists_with_available_command(self):
        """Test cmd_exists returns True for available commands"""
        # Test with a command that should exist on most systems
        assert sys_utils.cmd_exists('ls') is True

    @pytest.mark.unit
    def test_cmd_exists_with_unavailable_command(self):
        """Test cmd_exists returns False for unavailable commands"""
        assert sys_utils.cmd_exists('nonexistent_command_xyz123') is False

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_available_aur_helpers_all_available(self, mock_cmd_exists):
        """Test get_available_aur_helpers when all helpers are available"""
        mock_cmd_exists.return_value = True
        helpers = sys_utils.get_available_aur_helpers()
        assert helpers == ['yay', 'paru', 'trizen', 'pikaur']

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_available_aur_helpers_none_available(self, mock_cmd_exists):
        """Test get_available_aur_helpers when no helpers are available"""
        mock_cmd_exists.return_value = False
        helpers = sys_utils.get_available_aur_helpers()
        assert helpers == []

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_available_aur_helpers_partial(self, mock_cmd_exists):
        """Test get_available_aur_helpers with only some helpers available"""
        # Only paru and trizen are available
        def cmd_exists_side_effect(cmd):
            return cmd in ['paru', 'trizen']
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        helpers = sys_utils.get_available_aur_helpers()
        assert 'paru' in helpers
        assert 'trizen' in helpers
        assert 'yay' not in helpers
        assert 'pikaur' not in helpers

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_aur_helper_auto_mode(self, mock_cmd_exists):
        """Test get_aur_helper in auto mode returns first available"""
        # Only paru is available
        def cmd_exists_side_effect(cmd):
            return cmd == 'paru'
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        helper = sys_utils.get_aur_helper(None)
        assert helper == 'paru'

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_aur_helper_preferred_available(self, mock_cmd_exists):
        """Test get_aur_helper returns preferred helper when available"""
        # Both yay and paru are available
        def cmd_exists_side_effect(cmd):
            return cmd in ['yay', 'paru']
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        helper = sys_utils.get_aur_helper('paru')
        assert helper == 'paru'

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_aur_helper_preferred_unavailable(self, mock_cmd_exists):
        """Test get_aur_helper falls back when preferred is unavailable"""
        # Only yay is available, but user prefers paru
        def cmd_exists_side_effect(cmd):
            return cmd == 'yay'
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        helper = sys_utils.get_aur_helper('paru')
        assert helper == 'yay'  # Falls back to available helper

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_aur_helper_none_available(self, mock_cmd_exists):
        """Test get_aur_helper returns None when no helpers available"""
        mock_cmd_exists.return_value = False
        helper = sys_utils.get_aur_helper()
        assert helper is None

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_missing_dependencies_no_aur_helper(self, mock_cmd_exists):
        """Test get_missing_dependencies includes AUR helper when none available"""
        # No AUR helpers available, but other tools are
        def cmd_exists_side_effect(cmd):
            return cmd in ['flatpak', 'git', 'node', 'npm', 'docker']
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        missing = sys_utils.get_missing_dependencies()
        assert 'yay or paru' in missing

    @pytest.mark.unit
    @patch('neoarch.backend.sys_utils.cmd_exists')
    def test_get_missing_dependencies_with_aur_helper(self, mock_cmd_exists):
        """Test get_missing_dependencies excludes AUR helper when available"""
        # Paru is available along with other tools
        def cmd_exists_side_effect(cmd):
            return cmd in ['flatpak', 'git', 'node', 'npm', 'docker', 'paru']
        
        mock_cmd_exists.side_effect = cmd_exists_side_effect
        missing = sys_utils.get_missing_dependencies()
        assert 'yay or paru' not in missing
        assert 'yay' not in missing


class TestAURHelperIntegration:
    """Integration tests for AUR helper functionality"""

    @pytest.mark.integration
    def test_real_aur_helper_detection(self):
        """Test actual AUR helper detection on the system"""
        helpers = sys_utils.get_available_aur_helpers()
        # Should return a list (may be empty if no helpers installed)
        assert isinstance(helpers, list)
        # All items should be valid helper names
        valid_helpers = ['yay', 'paru', 'trizen', 'pikaur']
        for helper in helpers:
            assert helper in valid_helpers

    @pytest.mark.integration
    def test_real_get_aur_helper(self):
        """Test actual AUR helper retrieval"""
        helper = sys_utils.get_aur_helper()
        # Should return a string or None
        assert helper is None or isinstance(helper, str)
        if helper:
            assert helper in ['yay', 'paru', 'trizen', 'pikaur']


class TestCloudVenv:
    """Test app-owned virtualenv for cloud sync dependencies."""

    @pytest.mark.unit
    def test_is_cloud_venv_ready_returns_false_without_venv(self, tmp_path, monkeypatch):
        """Returns False when no venv exists."""
        monkeypatch.setattr(sys_utils, "CLOUD_VENV_DIR", tmp_path / "no_venv")
        assert sys_utils.is_cloud_venv_ready() is False

    @pytest.mark.unit
    def test_ensure_cloud_venv_skips_when_ready(self, monkeypatch):
        """ensure_cloud_venv does nothing if already ready."""
        called = False

        def fake_ready():
            return True

        def fake_run(*a, **kw):
            nonlocal called
            called = True
            raise AssertionError("subprocess should not be called")

        monkeypatch.setattr(sys_utils, "is_cloud_venv_ready", fake_ready)
        monkeypatch.setattr(sys_utils.subprocess, "run", fake_run)
        sys_utils.ensure_cloud_venv()
        assert called is False

    @pytest.mark.unit
    def test_add_cloud_venv_to_path_with_venv(self, tmp_path, monkeypatch):
        """add_cloud_venv_to_path inserts venv site-packages."""
        venv_sp = tmp_path / "lib" / "python3.11" / "site-packages"
        venv_sp.mkdir(parents=True)
        monkeypatch.setattr(sys_utils, "CLOUD_VENV_DIR", tmp_path)
        import sys
        before = len(sys.path)
        sys_utils.add_cloud_venv_to_path()
        assert len(sys.path) == before + 1
        assert str(venv_sp) in sys.path
        sys.path.remove(str(venv_sp))

    @pytest.mark.unit
    def test_add_cloud_venv_to_path_no_venv(self, tmp_path, monkeypatch):
        """add_cloud_venv_to_path is a no-op when venv dir is missing."""
        monkeypatch.setattr(sys_utils, "CLOUD_VENV_DIR", tmp_path / "no_venv")
        import sys
        before = list(sys.path)
        sys_utils.add_cloud_venv_to_path()
        assert sys.path == before