import pytest
from neoarch.backend.package.updater import parse_aur_failures, _classify_aur_hint


def test_parse_yay_error_making_lines():
    msg = (
        "==> ERROR: A failure occurred in build().\n"
        " -> error making: docker-desktop: exit status 1\n"
        " -> error making: cursor-bin: exit status 1\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert set(failed) == {'docker-desktop', 'cursor-bin'}
    assert failed['docker-desktop'] == 'exit status 1'
    assert hint == 'a package failed to build'


def test_parse_paru_manual_intervention_section():
    msg = (
        "Failed to install the following packages. Manual intervention is required:\n"
        "cursor-bin - fork/exec /usr/bin/makepkg: no such file or directory\n"
        "nvidia-580xx-dkms - could not satisfy dependencies\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert set(failed) == {'cursor-bin', 'nvidia-580xx-dkms'}
    assert hint == 'a build tool is missing (install base-devel)'


def test_parse_colon_separated_paru_entries():
    msg = (
        "Failed to install the following packages. Manual intervention is required:\n"
        "foo: error making: exit status 1\n"
    )
    failed, _ = parse_aur_failures(msg)
    assert failed.get('foo') == 'error making: exit status 1'


def test_parse_empty_or_none():
    assert parse_aur_failures('') == ({}, None)
    assert parse_aur_failures(None) == ({}, None)


def test_parse_ignores_noise():
    msg = (
        "warning: w3m-0.5.6-1 is up to date -- reinstalling\n"
        "some unrelated progress line\n"
    )
    failed, hint = parse_aur_failures(msg)
    assert failed == {}
    assert hint is None


def test_classify_hints():
    assert _classify_aur_hint('fork/exec /usr/bin/makepkg: no such file or directory') == 'a build tool is missing (install base-devel)'
    assert _classify_aur_hint('error: failed to prepare transaction (could not satisfy dependencies)') == 'there is a dependency conflict'
    assert _classify_aur_hint('==> ERROR: A failure occurred in build()') == 'a package failed to build'
    assert _classify_aur_hint('nothing wrong here') is None
