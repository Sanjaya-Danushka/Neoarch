"""Tests for the gettext-style i18n service (Phase 5 roadmap)."""

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.i18n as i18n


def _wrapped_msgids():
    """Every `_("...")` literal used across the frontend."""
    root = Path(__file__).resolve().parent.parent / "neoarch" / "frontend"
    msgids = set()
    for path in root.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "_" and node.args):
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    msgids.add(arg.value)
    return msgids


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
    (tmp_path / "en").mkdir(parents=True)
    (tmp_path / "si" / "LC_MESSAGES").mkdir(parents=True)
    (tmp_path / "si" / "LC_MESSAGES" / "neoarch.po").write_text("msgid ''\nmsgstr ''\n")
    (tmp_path / "es" / "LC_MESSAGES").mkdir(parents=True)
    (tmp_path / "es" / "LC_MESSAGES" / "neoarch.po").write_text("msgid ''\nmsgstr ''\n")
    # Stray folder with no catalog must not appear.
    (tmp_path / "notes").mkdir(parents=True)
    monkeypatch.setattr(i18n, "LOCALE_DIR", str(tmp_path))
    langs = i18n.available_languages()
    assert "si" in langs and "es" in langs
    assert "en" not in langs and "notes" not in langs


def test_language_label():
    assert i18n.language_label("es") == "Español (Spanish)"
    assert i18n.language_label("fr") == "Français (French)"
    assert i18n.language_label("qq") == "qq"
    assert i18n.LANGUAGE_NAMES["en"] == "English"


def test_bundled_catalogs_load():
    # The shipped si/es stubs must parse without errors.
    for lang in ("si", "es"):
        cat = i18n.load_catalog(lang)
        assert "Install" in cat
        assert cat["Install"]
        assert "General" in cat
        assert cat["General"]


def test_bundled_catalogs_cover_wrapped_strings():
    # Every msgid used by the wired UI must have an es translation so the
    # live language switch actually shows something.
    wrapped = _wrapped_msgids()
    assert len(wrapped) >= 350, len(wrapped)
    es = i18n.load_catalog("es")
    missing = wrapped - set(es)
    assert not missing, f"missing Spanish translations: {sorted(missing)[:20]}"
    si = i18n.load_catalog("si")
    assert {"General", "SETTINGS", "Maintenance"} <= set(si)
