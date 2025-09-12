import base64
import os
import json
import hashlib
import webbrowser
import urllib.parse
import re
import sys
import shutil
from typing import Dict, Any, Optional, List


from app.update_check import main as run_update_check
from app.utils.migration import main as run_all_migrations


def main():
    # Run all migrations at startup
    run_all_migrations()
    run_update_check()

    from app.config import APP_VERSION, OPTION_CODES, ORDERS_FILE, TESLA_STORES, cfg as Config
    from app.utils.auth import main as run_tesla_auth
    from app.utils.colors import color_text, strip_color
    from app.utils.connection import request_with_retry
    from app.utils.helpers import exit_with_status, decode_option_codes, get_date_from_timestamp, compare_dicts, generate_token
    from app.utils.history import print_history, load_history_from_file, save_history_to_file
    from app.utils.orders import main as run_orders
    from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE
    from app.utils.telemetry import ensure_telemetry_consent

    if not Config.has("secret"):
        Config.set("secret", generate_token(32,None))

    if not Config.has("fingerprint"):
        Config.set("fingerprint", generate_token(16,32))

    ensure_telemetry_consent()
    access_token = run_tesla_auth()
    run_orders(access_token)


if __name__ == "__main__":
    main()

