import json
from typing import List, Dict

from app.config import TELEMETRIC_URL, cfg as Config
from app.utils.helpers import pseudonymize_data
from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE
from app.utils.connection import request_with_retry






def ensure_telemetry_consent() -> None:
    """Ask user for tracking consent if not already given."""
    if Config.has("telemetry-consent"):
        if Config.get("telemetry-consent"):
            return
        else:
            counter = Config.get("telemetry-consent-counter", 10) - 1
            if counter <= 0:
                counter = 10
                ask_for_telemetry_consent()
            Config.set("telemetry-consent-counter", counter)
    else:
        ask_for_telemetry_consent()

def ask_for_telemetry_consent() -> None:
    answer = input(
        "Do you allow collection of non-personalised usage data to improve the script? (y/n): "
    ).strip().lower()
    consent = answer == "y"
    Config.set("telemetry-consent", consent)
    if answer == "y":
        print(f"Telemetrie aktiviert.")
    else:
        print("Telemetrie deaktiviert. Ich frage später erneut.")


def track_usage(orders: List[dict]) -> None:
    if not Config.get("telemetry-consent"):
        return

    # avoid circular dependency with orders module
    from app.utils.orders import get_model_from_order

    user_orders: List[Dict[str, str]] = []
    for order in orders:
        ref = order.get("order", {}).get("referenceNumber")
        if ref:
            order_id = pseudonymize_data(ref, 16)
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

    data = {
        "id": Config.get("fingerprint"),
        "orders": user_orders,
        "params": params
    }

    print(data)

    try:
        request_with_retry(TELEMETRIC_URL, json=data, max_retries=3)
    except Exception:
        pass