import locale

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
    return "unknown"
