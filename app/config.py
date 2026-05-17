import json
import re
import time
from pathlib import Path
from typing import Any, Dict

# -------------------------
# Constants
# -------------------------
TESLA_APP_VERSION = "4.55.5-4193"
TESLA_USER_AGENT = "Tesla/4.55.5 (com.teslamotors.tesla; build:4193; Android 14)"
TESLA_X_USER_AGENT = "TeslaApp/4.55.5-4193/4193/android/14"
TODAY = time.strftime('%Y-%m-%d')
TELEMETRIC_URL = "https://www.tesla-order-status-tracker.de/push/telemetry.php"
OPTION_CODES_URL = "https://www.tesla-order-status-tracker.de/push/option_codes.php"
VERSION = "p1.2.5"

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
TESLA_STORES_FILE = PUBLIC_DIR / 'tesla_locations.json'
SETTINGS_FILE = PRIVATE_DIR / 'settings.json'

# -------------------------
# Dataobjects
# -------------------------
try:
    with open(TESLA_STORES_FILE, encoding="utf-8") as f:
        TESLA_STORES = json.load(f)
except:
    TESLA_STORES = {}

class Config:
    def __init__(self, path: Path):
        self._path = path
        self._cfg: Dict[str, Any] = {}
        self.load()  # gleich beim Init laden

    def load(self) -> None:
        if not self._path.exists():
            self._cfg = {}
            return
        try:
            with self._path.open(encoding="utf-8") as f:
                text = f.read()
                # remove trailing commas before } or ]
                text = re.sub(r",\s*([\]\}])", r"\1", text)
                self._cfg = json.loads(text)
        except json.JSONDecodeError as e:
            self._cfg = {}
            return

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            self._cfg,
            indent=2,
            sort_keys=True,
            ensure_ascii=False
        ) + "\n"
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self._path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._cfg.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cfg[key] = value
        self.save()

    def has(self, key: str) -> bool:
        return key in self._cfg

    def delete(self, key: str) -> None:
        self._cfg.pop(key, None)
        self.save()

cfg = Config(SETTINGS_FILE)
