from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.utils.colors import color_text
from app.utils.helpers import (
    get_date_from_timestamp,
    normalize_str,
    get_delivery_appointment_display,
)
from app.utils.history import get_history_of_order
from app.utils.locale import t

TIMELINE_WHITELIST = {
    'Reservation',
    'Order Booked',
    'Delivery Window',
    'Expected Registration Date',
    'ETA to Delivery Center',
    'Delivery Appointment Date',
    'VIN',
    'Order Status',
    'CAR BUILT',
    'Vehicle Odometer'
}
TIMELINE_WHITELIST_NORMALIZED = {normalize_str(key) for key in TIMELINE_WHITELIST}


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    normalized = raw
    if raw.endswith(("Z", "z")):
        normalized = raw[:-1] + "+00:00"
    if "T" not in normalized and len(normalized) >= 16 and normalized[10] == " ":
        normalized = normalized[:10] + "T" + normalized[11:]
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _split_timestamp(value: Any) -> Tuple[str, Optional[str]]:
    parsed = _parse_timestamp(value)
    if parsed:
        date_display = parsed.date().isoformat()
        has_time_info = isinstance(value, str) and (":" in value or "T" in value)
        time_display = parsed.strftime("%H:%M") if has_time_info else None
        return date_display, time_display if time_display and time_display != "00:00" else None
    if isinstance(value, str) and value.strip():
        return value.strip(), None
    return t("unknown"), None


def _sort_timeline_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enumerated = list(enumerate(entries))
    enumerated.sort(key=lambda item: (_parse_timestamp(item[1].get("timestamp")) or datetime.max, item[0]))
    return [entry for _, entry in enumerated]

def is_order_key_in_timeline(timeline, key, value = None):
    """Return ``True`` if *timeline* contains an entry with *key* and *value*."""

    for entry in timeline:
        # if key is the same
        if normalize_str(entry.get('key')) == normalize_str(key):
            # if value empty or the same
            if value is None or entry.get('value') == value:
                return True
    return False


def get_timeline_from_history(order_reference: str, startdate) -> List[Dict[str, Any]]:
    # history liefert bereits Einträge mit timestamp/key/value (übersetzbar in history.py)
    history = get_history_of_order(order_reference)
    timeline = []
    new_car = False
    first_delivery_window = True
    for entry in history:
        key = entry["key"]
        key_normalized = normalize_str(key)
        value = entry.get("value")
        old_value = entry.get("old_value")

        if key_normalized == normalize_str("Vehicle Odometer"):
            if new_car or value in [None, "", "N/A"]:
                continue
            timeline.append(
                {
                   "timestamp": entry["timestamp"],
                   "key": "CAR BUILT",
                   "value": "",
                }
            )
            new_car = True
            continue

        if key_normalized == normalize_str("Delivery Window") and first_delivery_window:
            if old_value not in ['None', 'N/A', '']:
                timeline.append(
                    {
                       "timestamp": startdate,
                       "key": "Delivery Window",
                       "value": old_value,
                    }
                )
                first_delivery_window = False

        if old_value != "" and value == "":
            entry["value"] = t("removed")

        if key_normalized not in TIMELINE_WHITELIST_NORMALIZED:
            continue

        timeline.append(entry)
    return _sort_timeline_entries(timeline)

def get_timeline_from_order(order_reference: str, detailed_order: Dict[str, Any]) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []

    order_details = detailed_order.get("details", {})
    tasks = order_details.get("tasks", {})
    scheduling = tasks.get('scheduling', {})
    registration_data = tasks.get("registration", {})
    order_info = registration_data.get("orderDetails", {})
    final_payment_data = tasks.get("finalPayment", {}).get("data", {})

    if order_info.get("reservationDate"):
        timeline.append(
            {
                "timestamp": get_date_from_timestamp(order_info.get("reservationDate")),
                "key": "Reservation",
                "value": "",
            }
        )

    if order_info.get("orderBookedDate"):
        timeline.append(
            {
                "timestamp": get_date_from_timestamp(order_info.get("orderBookedDate")),
                "key": "Order Booked",
                "value": "",
            }
        )

    timeline_from_history = get_timeline_from_history(order_reference, get_date_from_timestamp(order_info.get("reservationDate")))

    if scheduling.get('deliveryWindowDisplay'):
        if not is_order_key_in_timeline(timeline_from_history, 'Delivery Window'):
            timeline.append(
                {
                    "timestamp": get_date_from_timestamp(order_info.get("orderBookedDate")),
                    "key": "Delivery Window",
                    "value": scheduling.get('deliveryWindowDisplay'),
                }
            )


    if registration_data.get('expectedRegDate'):
        if not is_order_key_in_timeline(timeline_from_history, 'Expected Registration Date'):
            timeline.append(
                {
                    "timestamp": get_date_from_timestamp(registration_data.get("expectedRegDate")),
                    "key": "Expected Registration Date",
                    "value": "",
                }
            )
        
    if final_payment_data.get('etaToDeliveryCenter'):
        if not is_order_key_in_timeline(timeline_from_history, 'ETA To Delivery Center'):
            timeline.append(
                {
                    "timestamp": get_date_from_timestamp(final_payment_data.get("etaToDeliveryCenter")),
                    "key": "ETA To Delivery Center",
                    "value": "",
                }
            )
        
    appointment_display = get_delivery_appointment_display(tasks)
    if appointment_display:
        if not is_order_key_in_timeline(timeline_from_history, 'Delivery Appointment Date'):
            timeline.append({
                "timestamp": appointment_display,
                "key": "Delivery Appointment Date",
                "value": "",
            })

    timeline.extend(timeline_from_history)
    return _sort_timeline_entries(timeline)


def print_timeline(order_reference: str, detailed_order: Dict[str, Any]) -> None:
    timeline = get_timeline_from_order(order_reference, detailed_order)
    if not timeline:
        return

    print(f"\n{color_text(t('Order Timeline') + ':', '94')}")
    printed_keys: set[str] = set()
    for entry in timeline:
        key = entry.get("key", "")
        normalized_key = normalize_str(key)
        msg_parts = []
        if normalized_key in printed_keys:
            msg_parts.append(t("new") + " ")
        msg_parts.append(t(key))
        if entry.get("value"):
            msg_parts.append(f": {entry['value']}")
        msg = "".join(msg_parts)
        date_display, time_display = _split_timestamp(entry.get("timestamp"))
        line = f"- {date_display}: {msg}"
        if time_display:
            line += f" ({time_display})"
        print(line)
        printed_keys.add(normalized_key)
