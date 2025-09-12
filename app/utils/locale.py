import locale
import os

def get_os_locale() -> str:
    """Return the system's locale/language code."""
    try:
        lang, _ = locale.getlocale()
        if lang:
            return lang
    except Exception:
        pass

    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            return lang
    except Exception:
        pass

    try:
        for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            value = os.environ.get(var)
            if value and value not in ("C", "POSIX"):
                return value.split(".")[0]  # trennt z.B. "de_DE.UTF-8" ab
    except Exception:
        pass

    return None

