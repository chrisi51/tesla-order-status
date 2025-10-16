import json
import textwrap
import webbrowser
from typing import Any, List

from app.config import PRIVATE_DIR
from app.utils.connection import request_with_retry
from app.utils.colors import color_text

BANNER_GET_URL = "https://www.tesla-order-status-tracker.de/get/banner.php"
BANNER_PUSH_CLICK_URL = "https://www.tesla-order-status-tracker.de/push/banner_clicked.php"
BANNER_FILE = PRIVATE_DIR / "banner_seen.json"
_DISPLAYED = False
_PLATFORM = "script"


def _load_seen() -> List[int]:
    if BANNER_FILE.exists():
        try:
            data = json.loads(BANNER_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [int(x) for x in data]
        except Exception:
            pass
    return []


def _save_seen(seen: List[int]) -> None:
    unique_seen = sorted(set(seen))
    BANNER_FILE.parent.mkdir(parents=True, exist_ok=True)
    BANNER_FILE.write_text(json.dumps(unique_seen), encoding="utf-8")


def _fetch_banner(seen: List[int]) -> dict[str, Any]:
    try:
        data = {
            "seen": seen,
            "platform": _PLATFORM,
        }
        response = request_with_retry(BANNER_GET_URL, json=data, max_retries=3, exit_on_error=False)
        return response.json()
    except Exception:
        return {}


def _send_banner_clicked(uid) -> Any:
    try:
        data = {
            "uid": uid,
            "platform": _PLATFORM,
        }
        response = request_with_retry(BANNER_PUSH_CLICK_URL, json=data, max_retries=3, exit_on_error=False)
        return response.json()
    except Exception:
        return {}


def wrap_with_linebreaks(text, width=60):
    lines = text.splitlines()  # Original-Umbrüche respektieren
    wrapped_lines = []
    for line in lines:
        if line.strip():  # normale Zeilen umbrechen
            wrapped_lines.extend(textwrap.wrap(line, width=width))
        else:  # leere Zeilen übernehmen
            wrapped_lines.append("")
    return "\n".join(wrapped_lines)


def _banner_targets_script(banner: dict[str, Any]) -> bool:
    """Return True when the banner is allowed to be shown in the Python script."""
    if not banner:
        return False
    flag_value = banner.get(_PLATFORM)
    if flag_value is None:
        return True
    if isinstance(flag_value, bool):
        return flag_value
    try:
        return int(flag_value) == 1
    except (TypeError, ValueError):
        return False


def display_banner() -> None:
    """Fetch and display a banner if available."""
    global _DISPLAYED
    if _DISPLAYED:
        return
    _DISPLAYED = True

    seen = _load_seen()
    banner = _fetch_banner(seen)
    uid = banner.get("id") if banner else None
    if not banner or uid is None:
        return
    if not _banner_targets_script(banner):
        return

    title = banner.get("title", "")
    text = banner.get("text", "")
    url = banner.get("url")

    msg_width = 90

    border = color_text("=" * msg_width, "33")
    print(border)
    if title:
        title_center = (msg_width - len(title) - 2) // 2
        left = title_center
        right = msg_width - len(title) - 2 - left
        print(color_text("=" * left + ' ' + title.upper() + ' ' + "=" * right, "33"))
        print(border)
    if text:
        print(color_text(wrap_with_linebreaks(text, msg_width), "33"))
    if url:
        print(border)
        print(color_text(f"==> {url}", "33"))
    print(border)

    if url:
        answer = input("Open link? [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            _send_banner_clicked(uid)
            try:
                webbrowser.open(url)
            except Exception:
                pass


    if uid not in seen:
        seen.append(uid)
        _save_seen(seen)
