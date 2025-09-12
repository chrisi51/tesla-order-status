import locale
import os

def get_os_locale() -> str:
    """Return the system's locale/language code."""
    try:
        lang, _ = locale.getlocale()
        if lang and lang not in ("C", "POSIX"):
            return normalize_locale(lang)
    except Exception:
        pass

    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang not in ("C", "POSIX"):
            return normalize_locale(lang)
    except Exception:
        pass

    try:
        for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            lang = os.environ.get(var)
            if lang and lang not in ("C", "POSIX"):
                return normalize_locale(lang)
    except Exception:
        pass

    return None


def normalize_locale(code: str) -> str:
    """Convert Windows-style locale like 'German_Austria' to ISO style 'de_AT'."""
    try:
        norm = locale.normalize(code)
        if norm and norm not in ("C", "POSIX"):
            return norm.split('.')[0]  # 'de_AT.ISO8859-1' → 'de_AT'
    except Exception:
        pass
    return code  # fallback

