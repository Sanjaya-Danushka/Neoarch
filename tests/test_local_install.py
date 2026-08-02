import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neoarch.frontend.mixins.views import _ViewsMixin


def test_is_arch_package_file_recognizes_pacman():
    assert _ViewsMixin._is_arch_package_file("waveterm-linux-x64-0.14.5.pacman") is True


def test_is_arch_package_file_recognizes_pkg_tar():
    for ext in (".pkg.tar.zst", ".pkg.tar.xz", ".pkg.tar.gz"):
        assert _ViewsMixin._is_arch_package_file(f"foo{ext}") is True


def test_is_arch_package_file_rejects_other_formats():
    for name in ("foo.AppImage", "foo.flatpakref", "foo.flatpak", "foo.tar.zst", "foo.zip"):
        assert _ViewsMixin._is_arch_package_file(name) is False


def test_is_arch_package_file_case_insensitive():
    assert _ViewsMixin._is_arch_package_file("FOO.PACMAN") is True
    assert _ViewsMixin._is_arch_package_file("foo.PKG.TAR.ZST") is True
