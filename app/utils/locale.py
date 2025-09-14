import json
import re
from typing import Optional

import locale
import os
import sys
from app.config import PUBLIC_DIR, SETTINGS_FILE, cfg as Config
from app.utils.colors import color_text

LANG_DIR = PUBLIC_DIR / "lang"
DEFAULT_LANG = "en"

# Determine if we're running in status mode early to avoid banner prints (can't just import params.py cause of looping)
STATUS_MODE = "--status" in sys.argv

def _load_translations(lang: str) -> dict:
    """Load translation mappings for *lang* with English fallback."""
    translations = {}
    default_path = LANG_DIR / f"{DEFAULT_LANG}.json"
    if default_path.exists():
        try:
            translations.update(json.loads(default_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    lang_code = (lang or "").split("_")[0].lower()
    if lang_code and lang_code != DEFAULT_LANG:
        lang_path = LANG_DIR / f"{lang_code}.json"
        if lang_path.exists():
            try:
                translations.update(json.loads(lang_path.read_text(encoding="utf-8")))
            except Exception:
                pass
    return translations


def t(text: str) -> str:
    """Translate *text* using loaded translations."""
    return TRANSLATIONS.get(text, text)


# --- Mapping dictionaries (extend as needed) ---
WINDOWS_LANG_MAP = {
    # seen in the wild
    "english": "en",
    "german": "de",
    "finnish": "fi",
    "greek": "el",
    "polish": "pl",
    "spanish": "es",
    "swedish": "sv",
    # common extras
    "french": "fr",
    "italian": "it",
    "portuguese": "pt",
    "dutch": "nl",
}

WINDOWS_REGION_MAP = {
    # seen in the wild
    "germany": "DE",
    "austria": "AT",
    "switzerland": "CH",
    "sweden": "SE",
    "belgium": "BE",
    "finland": "FI",
    "greece": "GR",
    "united states": "US",
    "poland": "PL",
    "spain": "ES",
    # common extras
    "united kingdom": "GB",
    "france": "FR",
    "italy": "IT",
    "portugal": "PT",
    "netherlands": "NL",
}

# If region missing, optional defaults (only used if we got a known language)
LANG_DEFAULT_REGION = {
    "en": "US",
    "de": "DE",
    "es": "ES",
    "fi": "FI",
    "el": "GR",
    "sv": "SE",
    "pl": "PL",
}

_BCP47_RE = re.compile(r"^([a-zA-Z]{2,3})(?:[_-]([A-Za-z]{2}))?(?:\..*)?$")


def _strip_encoding(tag: str) -> str:
    # 'de_AT.ISO8859-1' -> 'de_AT'
    return tag.split(".")[0].strip()


def _to_bcp47(lang: Optional[str], region: Optional[str]) -> Optional[str]:
    if not lang:
        return None
    l = lang.lower()
    if region:
        r = region.upper()
        return f"{l}_{r}"
    return l


def _try_fast_bcp47(tag: str) -> Optional[str]:
    m = _BCP47_RE.match(tag)
    if not m:
        return None
    lang = m.group(1)
    region = m.group(2)
    return _to_bcp47(lang, region)


def _try_locale_normalize(tag: str) -> Optional[str]:
    try:
        norm = locale.normalize(tag)
        if norm and norm not in ("C", "POSIX"):
            norm = _strip_encoding(norm)  # de_AT.ISO8859-1 → de_AT
            # Re-check with regex to enforce ll[_]RR casing
            return _try_fast_bcp47(norm)
    except Exception:
        pass
    return None


def _try_windows_mapping(tag: str) -> Optional[str]:
    # Accept forms like 'English_United States', 'English_Germany', 'German_Austria'
    # Also be forgiving with spaces/dashes/parentheses
    s = tag.strip()
    # Replace dash with underscore to unify splitting
    s = s.replace('-', '_')

    # Try patterns like 'Language (Region)'
    m = re.match(r"^([A-Za-z ]+)\s*\(([^)]*)\)$", s)
    if m:
        lang_name = m.group(1).strip().lower()
        region_name = m.group(2).strip().lower()
        l = WINDOWS_LANG_MAP.get(lang_name)
        r = WINDOWS_REGION_MAP.get(region_name)
        if l and r:
            return _to_bcp47(l, r)
        if l:
            return _to_bcp47(l, LANG_DEFAULT_REGION.get(l))
        return None

    # Split on underscore first (Windows classic), else last run of spaces
    parts = s.split('_') if '_' in s else re.split(r"\s+", s, maxsplit=1)

    if len(parts) == 1:
        lang_name = parts[0].strip().lower()
        l = WINDOWS_LANG_MAP.get(lang_name)
        return _to_bcp47(l, LANG_DEFAULT_REGION.get(l)) if l else None

    lang_name = parts[0].strip().lower()
    region_name = parts[1].strip().lower()

    # Some inputs put extra spaces in region
    region_name = re.sub(r"\s+", " ", region_name)

    l = WINDOWS_LANG_MAP.get(lang_name)
    r = WINDOWS_REGION_MAP.get(region_name)

    if l and r:
        return _to_bcp47(l, r)
    if l:
        return _to_bcp47(l, LANG_DEFAULT_REGION.get(l))
    return None


def normalize_locale(code: str) -> Optional[str]:
    """Best-effort conversion to 'll' or 'll_RR'.

    Handles:
      - Already-normalized tags like 'de_DE' or 'de_DE.UTF-8'
      - Dash vs underscore variants 'en-US'
      - Windows names like 'English_United States', 'German_Austria', 'English_Germany'
    Returns None if unrecognized.
    """
    if not code:
        return None

    # 1) Fast path for already-good tags
    normalized = _try_fast_bcp47(code)
    if normalized:
        return normalized

    # 2) locale.normalize()
    normalized = _try_locale_normalize(code)
    if normalized:
        return normalized

    # 3) Windows mapping
    normalized = _try_windows_mapping(code)
    if normalized:
        return normalized

    return None


def get_os_locale() -> Optional[str]:
    """Return the system locale as 'll' or 'll_RR' where possible."""
    # 1) locale.getlocale()
    try:
        lang, _ = locale.getlocale()
        if lang and lang not in ("C", "POSIX"):
            res = normalize_locale(lang)
            if res:
                return res
    except Exception:
        pass

    # 2) locale.getdefaultlocale()
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang not in ("C", "POSIX"):
            res = normalize_locale(lang)
            if res:
                return res
    except Exception:
        pass

    # 3) Env vars
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        try:
            lang = os.environ.get(var)
        except Exception:
            lang = None
        if lang and lang not in ("C", "POSIX"):
            res = normalize_locale(lang)
            if res:
                return res

    return None

if STATUS_MODE:
    LANGUAGE = DEFAULT_LANG
else:
    LANGUAGE = Config.get("language")
    if not LANGUAGE:
        os_lang = get_os_locale()
        if os_lang:
            lang_code = os_lang.split("_")[0].lower()
            if (LANG_DIR / f"{lang_code}.json").exists():
                LANGUAGE = lang_code
                message = (
                    f'System language detected. Using "{lang_code}" '
                    f'instead of "{DEFAULT_LANG}"'
                )
                print(f"\n{color_text(message, '93')}")
                print(f"{color_text(f'You can change it in your {SETTINGS_FILE}', '93')}")
                print()
                Config.set("language", LANGUAGE)
            else:
                LANGUAGE = DEFAULT_LANG
        else:
            LANGUAGE = DEFAULT_LANG

TRANSLATIONS = _load_translations(LANGUAGE)

def set_language(lang: str) -> None:
    """Set active *lang* and reload translations."""
    global LANGUAGE, TRANSLATIONS
    LANGUAGE = lang
    TRANSLATIONS = _load_translations(lang)


class use_default_language:
    """Context manager to temporarily force DEFAULT_LANG translations."""

    def __enter__(self):
        self._previous = LANGUAGE
        set_language(DEFAULT_LANG)

    def __exit__(self, exc_type, exc, tb):
        set_language(self._previous)