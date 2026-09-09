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
    "set_language", "get_language", "available_languages", "language_label",
    "translate", "load_catalog", "LOCALE_DIR", "LANGUAGE_NAMES",
]

# Native display names for common locales. Only strings whose code has a
# bundled catalog are shown in the UI; unknown codes fall back to the raw
# language code.
LANGUAGE_NAMES = {
    "en": "English",
    "si": "සිංහල (Sinhala)",
    "es": "Español (Spanish)",
    "fr": "Français (French)",
    "de": "Deutsch (German)",
    "it": "Italiano (Italian)",
    "pt": "Português (Portuguese)",
    "nl": "Nederlands (Dutch)",
    "ru": "Русский (Russian)",
    "uk": "Українська (Ukrainian)",
    "pl": "Polski (Polish)",
    "tr": "Türkçe (Turkish)",
    "ar": "العربية (Arabic)",
    "fa": "فارسی (Persian)",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "bn": "বাংলা (Bengali)",
    "te": "తెలుగు (Telugu)",
    "mr": "मराठी (Marathi)",
    "gu": "ગુજરાતી (Gujarati)",
    "zh": "中文 (Chinese)",
    "ja": "日本語 (Japanese)",
    "ko": "한국어 (Korean)",
    "vi": "Tiếng Việt (Vietnamese)",
    "id": "Bahasa Indonesia (Indonesian)",
    "ms": "Bahasa Melayu (Malay)",
    "th": "ไทย (Thai)",
}

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
    """Language codes with a bundled catalog (e.g. ['en', 'si', 'es']).

    Only directories that actually contain a `LC_MESSAGES/neoarch.po` are
    listed, so stray folders in the locale tree never surface in the UI.
    """
    try:
        codes = []
        for name in os.listdir(LOCALE_DIR):
            if os.path.isfile(os.path.join(
                    LOCALE_DIR, name, "LC_MESSAGES", "neoarch.po")):
                codes.append(name)
        return sorted(codes)
    except Exception:
        return []


def detect_system_language() -> str:
    """Return the best bundled language for the OS locale, else 'en'."""
    available = set(available_languages())
    env_names = [
        os.environ.get("LC_ALL"),
        os.environ.get("LC_MESSAGES"),
        os.environ.get("LANG"),
    ]
    try:
        import locale as _locale
        env_names.append(_locale.getdefaultlocale()[0])
    except Exception:
        pass
    candidates = []
    for name in env_names:
        if not name:
            continue
        lang = name.split("_")[0].split("-")[0].lower()
        candidates.append(lang)
        full = name.replace("_", "-").lower()
        candidates.append(full)
        if "-" in full:
            candidates.append(full.rsplit("-")[0])
    for c in candidates:
        if c in available:
            return c
    return "en"


def language_label(code: str) -> str:
    """Native display name for a language code, falling back to the code."""
    return LANGUAGE_NAMES.get(code, code)


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
