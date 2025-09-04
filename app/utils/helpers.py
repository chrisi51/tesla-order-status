import re
import sys
from datetime import datetime
from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE
from app.utils.colors import color_text, strip_color
from app.config import OPTION_CODES


def exit_with_status(msg: str) -> None:
    """In STATUS_MODE print '-1', otherwise print message and exit."""
    if STATUS_MODE:
        print("-1")
        sys.exit(0)

    print(f"\n{color_text(msg, '91')}")
    sys.exit(0)


def decode_option_codes(option_string: str):
    """Return a list of tuples with (code, description)."""
    codes = sorted(c.strip() for c in option_string.split(',') if c.strip())
    return [(code, OPTION_CODES.get(code, "Unknown option code")) for code in codes]


def get_date_from_timestamp(timestamp):
    """Truncates an ISO-8601 timestamp to its date component.

    Older versions only handled timestamps without timezone information and
    would return the original value for inputs such as
    ``"2024-07-25T12:34:56Z"``. By leveraging ``datetime.fromisoformat`` the
    function now supports fractional seconds and timezone offsets. If parsing
    fails, the original value is returned unchanged.
    """

    if not timestamp or timestamp == "N/A":
        return timestamp

    ts = timestamp.strip()
    if ts.endswith("Z"):
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


def compare_dicts(old_dict, new_dict, path=""):
    differences = []
    for key in old_dict:
        if key not in new_dict:
            differences.append(
                {
                    "operation": "removed",
                    "key": path + key,
                    "old_value": old_dict[key],
                }
            )
        elif isinstance(old_dict[key], dict) and isinstance(new_dict[key], dict):
            differences.extend(
                compare_dicts(old_dict[key], new_dict[key], path + key + ".")
            )
        elif old_dict[key] != new_dict[key]:
            differences.append(
                {
                    'operation': 'changed',
                    'key': path + key,
                    'old_value': old_dict[key],
                    'value': new_dict[key]
                }
            )

    for key in new_dict:
        if key not in old_dict:
            differences.append(
                {
                    'operation': 'added',
                    'key': path + key,
                    'value': new_dict[key]
                }
            )

    return differences