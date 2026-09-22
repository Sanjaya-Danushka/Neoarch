import pytest

from neoarch.resources.changelog_map import CHANGELOG_MAP, get_changelog_url


def test_known_package_returns_url():
    url = get_changelog_url("firefox")
    assert url is not None
    assert url.startswith("http")


@pytest.mark.parametrize("name", ["FireFox", "  firefox  ", "FIREFOX"])
def test_lookup_is_case_insensitive(name):
    assert get_changelog_url(name) == get_changelog_url("firefox")


def test_unknown_package_returns_none():
    assert get_changelog_url("no-such-package-xyz") is None
    assert get_changelog_url("") is None
    assert get_changelog_url(None) is None


@pytest.mark.parametrize("name", ["org.mozilla.firefox", "org.videolan.VLC",
                                  "org.gimp.GIMP", "org.chromium.Chromium"])
def test_flatpak_app_id_resolves_via_alias(name):
    url = get_changelog_url(name, source="flatpak")
    assert url is not None
    assert url.startswith(("http://", "https://"))


def test_flatpak_id_without_source_still_resolves():
    url = get_changelog_url("org.mozilla.firefox")
    assert url is not None and url.startswith("http")


def test_unknown_flatpak_id_returns_none():
    assert get_changelog_url("org.acme.unknown-thing", source="flatpak") is None


def test_map_values_are_valid_urls():
    for name, url in CHANGELOG_MAP.items():
        assert url.startswith(("http://", "https://")), (name, url)


def test_map_is_read_only():
    with pytest.raises(Exception):
        CHANGELOG_MAP["firefox"] = "https://example.com"