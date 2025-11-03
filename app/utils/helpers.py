import base64
import hmac
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional
from app.utils.colors import color_text
from app.utils.locale import t
from app.utils.params import STATUS_MODE
from app.config import cfg as Config


def exit_with_status(msg: str) -> None:
    """In STATUS_MODE print '-1', otherwise print message and exit."""
    if STATUS_MODE:
        print("-1")
    else:
        print(f"\n{color_text(msg, '91')}")
    sys.exit(1)


def decode_option_codes(option_string: str):
    """Return a list of tuples with (code, description)."""
    if not isinstance(option_string, str) or not option_string:
        return []

    excluded_codes = {'MDL3', 'MDLY', 'MDLX', 'MDLS'}
    codes = sorted({
        c.strip().upper() for c in option_string.split(',')
        if c.strip() and c.strip().upper() not in excluded_codes
    })

    from app.utils.option_codes import get_option_codes
    option_codes = get_option_codes()
    decoded = []
    for code in codes:
        entry = option_codes.get(code)
        label = None
        if isinstance(entry, dict):
            label = entry.get("label")
        elif isinstance(entry, str):
            # Backwards compatibility for legacy caches
            label = entry
        decoded.append(
            (code, label if label else t("Unknown option code"))
        )
    return decoded


def get_date_from_timestamp(timestamp):
    """Truncates an ISO-8601 timestamp to its date component.

    Older versions only handled timestamps without timezone information and
    would return the original value for inputs such as
    ``"2024-07-25T12:34:56Z"``. By leveraging ``datetime.fromisoformat`` the
    function now supports fractional seconds and timezone offsets. If parsing
    fails, the original value is returned unchanged.
    """

    if not isinstance(timestamp, str):
        return timestamp

    if not timestamp or timestamp.upper() == "N/A":
        return timestamp

    ts = timestamp.strip()
    if ts.endswith("Z") or ts.endswith("z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return timestamp
    return dt.date().isoformat()

def normalize_str(key: str) -> str:
    """
    Normalizes keys for robust comparisons:
    - trims spaces
    - converts to lowercase
    - collapses multiple spaces
    """

    if not isinstance(key, str):
        return ""
    collapsed = " ".join(key.strip().split())
    return collapsed.lower()


def clean_str(value):
    return value.strip() if isinstance(value, str) else value


def pretty_print(data: Any) -> str:
    """Return a pretty-printed string for lists or dictionaries.

    If *data* is a list or dict, it is converted to a JSON-formatted string
    with indentation for improved readability. Otherwise, the value is
    converted to ``str`` and returned unchanged.
    """

    if isinstance(data, (list, dict)):
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    return str(data)


def compare_dicts(old_dict, new_dict, path=""):
    differences = []
    for key in old_dict:
        if key not in new_dict:
            differences.append(
                {
                    "operation": "removed",
                    "key": path + key,
                    "old_value": clean_str(old_dict[key])
                }
            )
        elif isinstance(old_dict[key], dict) and isinstance(new_dict[key], dict):
            differences.extend(
                compare_dicts(old_dict[key], new_dict[key], path + key + ".")
            )
        else:
            old_value = clean_str(old_dict[key])
            new_value = clean_str(new_dict[key])
            if old_value != new_value:
                differences.append(
                {
                    "operation": "changed",
                    "key": path + key,
                    "old_value": old_value,
                    "value": new_value,
                }
            )

    for key in new_dict:
        if key not in old_dict:
            differences.append(
                {
                    "operation": "added",
                    "key": path + key,
                    "value": clean_str(new_dict[key]),
                }
            )

    return differences


def _b32(data: bytes, length: Optional[int] = None) -> str:
    s = base64.b32encode(data).decode("ascii").rstrip("=")
    return s if length is None else s[:length]

def _b32decode_nopad(s: str) -> bytes:
    pad = "=" * ((8 - (len(s) % 8)) % 8)
    return base64.b32decode(s + pad)

def generate_token(bytes_len: int, token_length: Optional[int] = None) -> str:
    if token_length is not None:
        min_bytes = (token_length * 5 + 7) // 8  # ceil division
        bytes_len = max(bytes_len, min_bytes)
    return _b32(os.urandom(bytes_len), token_length)

def pseudonymize_data(data: str, length: int) -> str:
    secret_b32 = Config.get("secret")
    if not secret_b32:
        secret_b32 = generate_token(32)
        Config.set("secret", secret_b32)
    secret = _b32decode_nopad(secret_b32)
    digest = hmac.new(secret, data.encode("utf-8"), hashlib.sha256).digest()
    return _b32(digest, length)
