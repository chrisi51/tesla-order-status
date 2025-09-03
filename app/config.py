from glob import glob
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# -------------------------
# Constants
# -------------------------
APP_VERSION = '9.99.9-9999' # we can use a dummy version here, as the API does not check it strictly
TODAY = time.strftime('%Y-%m-%d')

# -------------------------
# Directory structure (new)
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = DATA_DIR / "public"
PRIVATE_DIR = DATA_DIR / "private"

TOKEN_FILE = PRIVATE_DIR / 'tesla_tokens.json'
ORDERS_FILE = PRIVATE_DIR / 'tesla_orders.json'
HISTORY_FILE = PRIVATE_DIR / 'tesla_order_history.json'
OPTION_CODES_FOLDER = PUBLIC_DIR / 'option-codes'
TESLA_STORES_FILE = PUBLIC_DIR / 'tesla_locations.json'


# -------------------------
# Dataobjects
# -------------------------
TESLA_STORES = json.load(open(TESLA_STORES_FILE, encoding="utf-8" ))
# Load option codes (last wins)
OPTION_CODES: Dict[str, str] = {}
for p in sorted(glob(f"{OPTION_CODES_FOLDER}/*.json")):
    try:
        with open(p, encoding="utf-8") as f:
            OPTION_CODES.update(json.load(f))
    except Exception:
        continue
