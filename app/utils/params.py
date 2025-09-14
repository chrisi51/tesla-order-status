import argparse
import os
import time

from app.config import ORDERS_FILE
from app.utils.locale import t

parser = argparse.ArgumentParser(description="Retrieve Tesla order status.")
group = parser.add_mutually_exclusive_group()
group.add_argument("--status", action="store_true", help=t("HELP PARAM STATUS"))
group.add_argument("--share", action="store_true", help=t("HELP PARAM SHARE"))
group.add_argument("--details", action="store_true", help=t("HELP PARAM DETAILS"))
group.add_argument("--all", action="store_true", help=t("HELP PARAM ALL"))
parser.add_argument("--cached", action="store_true", help=t("HELP PARAM CACHED"))

_args, _ = parser.parse_known_args()

if not _args.cached and os.path.exists(ORDERS_FILE):
    last_api_call = os.path.getmtime(ORDERS_FILE)
    if time.time() - last_api_call < 60:
        _args.cached = True

DETAILS_MODE = _args.details
SHARE_MODE = _args.share
STATUS_MODE = _args.status
CACHED_MODE = _args.cached
ALL_KEYS_MODE = _args.all