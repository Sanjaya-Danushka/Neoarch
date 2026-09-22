from neoarch.backend.services.search import _parse_pacman_ss, merge_results
from neoarch.frontend.mixins.search import _parse_pacman_sync


SAMPLE = """extra/firefox 138.0-1 (firefox) [extra]
    Standalone web browser from mozilla.org
extra/firefox-developer-edition 138.0b3-1 [extra]
    Developer build of the Firefox web browser
aur/firefox-git 138.0.r-1 [installed]
    Standalone web browser from mozilla.org (git version)
"""


def test_parse_pacman_ss_extracts_repo_name_pkg():
    pkgs = _parse_pacman_ss(SAMPLE)
    assert len(pkgs) == 3
    assert pkgs[0]['source'] == 'pacman'
    assert pkgs[0]['id'] == 'pacman-firefox'
    assert pkgs[0]['pkg'] == 'firefox'
    assert pkgs[0]['name'] == 'firefox'
    assert 'web browser' in pkgs[0]['desc'].lower()


def test_parse_pacman_ss_handles_aur_repo():
    pkgs = _parse_pacman_ss(SAMPLE)
    assert pkgs[2]['repo'] == 'aur'
    assert pkgs[2]['installed'] is True


def test_parse_pacman_ss_empty():
    assert _parse_pacman_ss("") == []


def test_parse_pacman_sync_uses_indented_line_as_description():
    """pacman -Ss puts '[installed]' and group markers on the header line; the
    discover table must not leak them into the description (issue #62)."""
    out = """extra/optipng 0.7.8-2 (extra)
    Optimized PNG encoder
extra/pandoc 3.6.4-1 [installed]
    General markup converter
aur/pandoc-bin 3.6.4-1 [installed]
    Pandoc binary (Linux)
"""
    pkgs = _parse_pacman_sync(out)
    assert len(pkgs) == 3
    assert pkgs[0]["description"] == "Optimized PNG encoder"
    assert pkgs[1]["description"] == "General markup converter"
    assert pkgs[2]["description"] == "Pandoc binary (Linux)"
    assert not any("installed" in p["description"] for p in pkgs)
    assert pkgs[0]["id"] == "optipng"
    assert pkgs[1]["version"] == "3.6.4-1"


def test_parse_pacman_sync_skips_garbage_lines():
    assert _parse_pacman_sync("") == []
    assert _parse_pacman_sync("   \nblah\ncore/zlib 1.3.1-1\n    A compression library\n")[0]["description"] == "A compression library"


def test_merge_results_dedupes_by_id_prefer_pacman():
    pacman = [{'id': 'pacman-firefox', 'source': 'pacman', 'pkg': 'firefox', 'name': 'firefox'}]
    aur = [{'id': 'aur-firefox-git', 'source': 'aur', 'pkg': 'firefox-git', 'name': 'firefox-git'},
           {'id': 'pacman-firefox', 'source': 'aur', 'pkg': 'firefox', 'name': 'firefox'}]
    merged = merge_results(pacman, aur)
    ids = [r['id'] for r in merged]
    assert ids == ['pacman-firefox', 'aur-firefox-git']
    assert merged[0]['source'] == 'pacman'


def test_merge_results_no_dups_both_empty():
    assert merge_results([], []) == []
