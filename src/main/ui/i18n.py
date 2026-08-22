from __future__ import annotations

import json
import os
from pathlib import Path


I18N_DIR = Path(__file__).with_name("i18n")
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"zh_CN", "zh_TW", "ja", "en", "fr", "de", "pt", "ru"}
LANGUAGE_ALIASES = {
    "zh": "zh_CN",
    "zh_cn": "zh_CN",
    "zh_sg": "zh_CN",
    "zh_hans": "zh_CN",
    "zh_tw": "zh_TW",
    "zh_hk": "zh_TW",
    "zh_mo": "zh_TW",
    "zh_hant": "zh_TW",
    "jp": "ja",
}
LANGUAGE_NAMES = {
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "ja": "日本語",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
}


def resolve_language(language: str | None) -> str | None:
    if not language:
        return None
    code = language.split(":", 1)[0].split(".", 1)[0].replace("-", "_")
    lowered = code.lower()
    if lowered in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lowered]
    base = lowered.split("_", 1)[0]
    return base if base in SUPPORTED_LANGUAGES else None


def normalize_language(language: str | None) -> str:
    return resolve_language(language) or DEFAULT_LANGUAGE


def detect_language() -> str:
    for variable in ("NEURO_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if value:
            return normalize_language(value)
    return DEFAULT_LANGUAGE


def _load_catalog(language: str) -> dict[str, str]:
    try:
        with (I18N_DIR / f"{language}.json").open(encoding="utf-8") as catalog_file:
            catalog = json.load(catalog_file)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(catalog, dict):
        return {}
    return {
        key: value
        for key, value in catalog.items()
        if isinstance(key, str) and isinstance(value, str)
    }


_english_catalog = _load_catalog(DEFAULT_LANGUAGE)
_language = detect_language()
_catalog = _load_catalog(_language)


def set_language(language: str) -> str:
    global _catalog, _language
    resolved = resolve_language(language)
    if resolved is None:
        raise ValueError(f"Unsupported language: {language}")
    _language = resolved
    _catalog = _load_catalog(_language)
    return _language


def get_language() -> str:
    return _language


def tr(key: str, **values: object) -> str:
    template = _catalog.get(key, _english_catalog.get(key, key))
    try:
        return template.format(**values)
    except (AttributeError, KeyError, ValueError):
        fallback = _english_catalog.get(key, key)
        try:
            return fallback.format(**values)
        except (AttributeError, KeyError, ValueError):
            return key
