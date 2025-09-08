"""Utility functions for colored terminal output."""

import os
import sys
import re

def _supports_color():
    """Return True if ANSI colors are supported on this output."""
    if os.getenv("NO_COLOR"):
        return False
    if sys.platform == "win32":
        try:
            import colorama

            colorama.init()  # type: ignore
            return True
        except Exception:
            return False
    return sys.stdout.isatty()


_USE_COLOR = _supports_color()


def color_text(text, color_code):
    if _USE_COLOR:
        return f"\033[{color_code}m{text}\033[0m"
    return text


def strip_color(text):
    return re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)
