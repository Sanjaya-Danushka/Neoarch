"""Tests for the release-notes service (CHANGELOG parsing / version gates).

Network-dependent GitHub lookups are exercised only through the
NEOARCH_CHECK_RELEASES toggle, which short-circuits to None so tests are
deterministic and offline-safe.
"""

import os

from neoarch.backend.services import release_notes as rn


def test_version_key_ordering():
    assert rn.version_key("") == (0,)
    assert rn.version_key("3") < rn.version_key("3.1.2") < rn.version_key("3.1.3")
    assert rn.version_key("v3.1.3") == rn.version_key("3.1.3")
    assert rn.version_key("Unreleased") > rn.version_key("99.0")
    assert rn.version_key("garbage") == (0,)


def test_parse_changelog_shapes():
    blocks = rn.parse_changelog()
    assert blocks, "CHANGELOG.md should parse to at least one block"
    for block in blocks:
        assert block["version"]
        assert isinstance(block["sections"], dict)
        assert "New Features" in block["sections"]
        assert all(isinstance(v, list) and v for v in block["sections"].values())
    # File order is newest-first: Unreleased sits right after the intro header.
    assert blocks[0]["version"].lower() == "unreleased"


def test_whats_new_only_returns_newer_blocks():
    blocks = rn.parse_changelog()
    seen = "3.1.2"
    out = rn.whats_new(blocks, seen)
    assert out, "should return newer blocks"
    versions = [b["version"] for b in out]
    assert all(rn.version_key(v) > rn.version_key(seen) for v in versions)
    assert versions == list(
        dict.fromkeys(versions)), "no duplicates, newest first"


def test_whats_new_respects_limit():
    blocks = rn.parse_changelog()
    assert len(rn.whats_new(blocks, "", limit=2)) <= 2


def test_latest_release_respects_toggle():
    os.environ["NEOARCH_CHECK_RELEASES"] = "0"
    try:
        assert rn.latest_release() is None
    finally:
        os.environ.pop("NEOARCH_CHECK_RELEASES", None)