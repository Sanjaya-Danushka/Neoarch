"""Tests for the gettext-style i18n service (Phase 5 roadmap)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.i18n as i18n


def _stub_locale(monkeypatch, tmp_path, language, pairs):
    d = tmp_path / language / "LC_MESSAGES"
    d.mkdir(parents=True)
    lines = ['msgid ""\n', 'msgstr ""\n']
    for key, val in pairs.items():
        lines.append(f'\nmsgid "{key}"\nmsgstr "{val}"\n')
    (d / "neoarch.po").write_text("".join(lines))
    monkeypatch.setattr(i18n, "LOCALE_DIR", str(tmp_path))


def test_load_catalog(monkeypatch, tmp_path):
    _stub_locale(monkeypatch, tmp_path, "xx", {"Install": "Xstalar"})
    cat = i18n.load_catalog("xx")
    assert cat == {"Install": "Xstalar"}


def test_load_catalog_missing():
    assert i18n.load_catalog("zz-missing") == {}


def test_english_is_noop():
    i18n.set_language("en")
    assert i18n.translate("Install") == "Install"
    assert i18n.get_language() == "en"


def test_set_language_activates_catalog(monkeypatch, tmp_path):
    _stub_locale(monkeypatch, tmp_path, "xx", {"Install": "Xstalar", "Search": "Xbucar"})
    i18n.set_language("xx")
    assert i18n.get_language() == "xx"
    assert i18n._("Install") == "Xstalar"
    assert i18n.translate("Search") == "Xbucar"
    assert i18n.translate("No translation for this") == "No translation for this"


def test_set_language_falls_back(monkeypatch, tmp_path):
    _stub_locale(monkeypatch, tmp_path, "xx", {})
    i18n.set_language("xx")  # empty catalog -> fallback to en
    assert i18n.get_language() == "en"
    assert i18n.translate("Install") == "Install"


def test_set_language_invalid():
    i18n.set_language(None)
    assert i18n.get_language() == "en"
    i18n.set_language("")
    assert i18n.get_language() == "en"


def test_available_languages(monkeypatch, tmp_path):
    (tmp_path / "en").mkdir()
    (tmp_path / "si").mkdir()
    (tmp_path / "es").mkdir()
    monkeypatch.setattr(i18n, "LOCALE_DIR", str(tmp_path))
    langs = i18n.available_languages()
    assert "en" in langs and "si" in langs and "es" in langs


def test_bundled_catalogs_load():
    # The shipped si/es stubs must parse without errors.
    for lang in ("si", "es"):
        cat = i18n.load_catalog(lang)
        assert "Install" in cat
        assert cat["Install"]
