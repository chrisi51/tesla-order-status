import json
import hashlib
from typing import List

from app.config import SETTINGS_FILE, TELEMETRIC_URL, cfg as Config
from app.utils.helpers import generate_token
from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE
from app.utils.connection import request_with_retry






def ensure_tracking_consent() -> None:
    """Ask user for tracking consent if not already given."""
    if Config.has("telemetry-consent"):
        if Config.get("telemetry-consent"):
            return
        else:
            counter = Config.get("telemetry-consent-counter", 10) - 1
            if counter <= 0:
                Config.set("telemetry-consent-counter", 10)
            Config.set("telemetry-consent-counter", counter)
    answer = input(
        "Do you allow collection of non-personalised usage data to improve the script? (y/n): "
    ).strip().lower()
    consent = answer == "y"
    Config.set("telemetry-consent", consent)
    if answer == "y":
        print(f"Telemetrie aktiviert.")
    else:
        print("Telemetrie deaktiviert. Ich frage später erneut.")


def track_usage(orders) -> None:
    if not Config.get("telemetry-consent"):
        return

    user_orders = {}
    for order in orders:
        if order['order']['referenceNumber']:
            order_id = pseudonymize_data(order['order']['referenceNumber'], 16)
            model = get_model_from_order(order)

            user_orders.append(
                {
                    "order_id": order_id,
                    "model": model
                }
            )

    params = {
        "details": DETAILS_MODE,
        "share": SHARE_MODE,
        "status": STATUS_MODE,
        "cached": CACHED_MODE,
    }
    param_str = json.dumps(params, sort_keys=True)

    for order_id in order_ids:
        hash_id = hashlib.sha256(order_id.encode("utf-8")).hexdigest()
        data = {"id": Config.get("fingerprint"), "orders": user_orders, "params": param_str}
        try:
            request_with_retry(TELEMETRIC_URL, data=data, max_retries=1)
        except Exception:
            pass