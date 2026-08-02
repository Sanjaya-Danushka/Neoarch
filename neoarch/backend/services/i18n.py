"""Lightweight gettext-style translation service.

Loads .po message catalogs directly (no msgfmt/compilation step) from
the bundled `neoarch/locale/<lang>/LC_MESSAGES/neoarch.po` directory or
an optional user override. `translate()` falls back to the source string
when no catalog or entry exists, so the app stays fully functional with
a single bundled language.
"""

import os
import re
from typing import Dict, Optional

__all__ = [
    "set_language", "get_language", "available_languages",
    "translate", "load_catalog", "LOCALE_DIR",
]

LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "locale")

_MSGID_RE = re.compile(r'^msgid\s+"((?:[^"\\]|\\.)*)"')
_MSGSTR_RE = re.compile(r'^msgstr\s+"((?:[^"\\]|\\.)*)"')

_language = "en"
_catalog: Dict[str, str] = {}
_catalog_loaded = False


def _unescape(text: str) -> str:
    return (text.replace(r"\"", '"').replace(r"\\", "\\")
                .replace(r"\n", "\n").replace(r"\t", "\t"))


def load_catalog(language: str) -> Dict[str, str]:
    """Parse the .po catalog for `language` into a msgid->msgstr map."""
    path = os.path.join(LOCALE_DIR, language, "LC_MESSAGES", "neoarch.po")
    if not os.path.exists(path):
        return {}
    catalog: Dict[str, str] = {}
    msgid: Optional[str] = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                m = _MSGID_RE.match(line)
                if m:
                    msgid = _unescape(m.group(1))
                    continue
                m = _MSGSTR_RE.match(line)
                if m and msgid is not None:
                    translated = _unescape(m.group(1))
                    if translated:
                        catalog[msgid] = translated
                    msgid = None
    except Exception:
        return {}
    return catalog


def available_languages() -> list:
    """Language codes with a bundled catalog (e.g. ['en', 'si', 'es'])."""
    try:
        return sorted(os.listdir(LOCALE_DIR))
    except Exception:
        return ["en"]


def set_language(language: str) -> None:
    """Activate a language catalog. Falls back to English on errors."""
    global _language, _catalog, _catalog_loaded
    if not language or not isinstance(language, str):
        language = "en"
    if language == "en":
        _catalog = {}
        _catalog_loaded = True
        _language = "en"
        return
    _catalog = load_catalog(language)
    _catalog_loaded = True
    _language = language if _catalog else "en"
    if _language != language:
        _catalog = {}


def get_language() -> str:
    return _language


def translate(text: str) -> str:
    """Return the translated string for `text`, or `text` unchanged."""
    if _language == "en" or not _catalog:
        return text
    return _catalog.get(text, text)


def _(text: str) -> str:
    """Convenience alias matching the standard gettext idiom."""
    return translate(text)
