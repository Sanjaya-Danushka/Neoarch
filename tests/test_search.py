import pytest
from neoarch.backend.services.search import _parse_pacman_ss, merge_results


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
