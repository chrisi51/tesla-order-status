from __future__ import annotations
from typing import Any, Dict, List

from app.utils.colors import color_text
from app.utils.helpers import get_date_from_timestamp, normalize_str
from app.utils.history import get_history_of_order
from app.utils.locale import t

TIMELINE_WHITELIST = {
    t('Reservation'),
    t('Order Booked'),
    'Delivery Window',
    t('Expected Registration Date'),
    t('ETA to Delivery Center'),
    t('Delivery Appointment Date'),
    t('VIN'),
    t('Order Status'),
    t('CAR BUILT'),
    t('Vehicle Odometer')
}
TIMELINE_WHITELIST_NORMALIZED = {normalize_str(key) for key in TIMELINE_WHITELIST}

def is_order_key_in_timeline(timeline, key, value = None):
    """Return ``True`` if *timeline* contains an entry with *key* and *value*."""

    for entry in timeline:
        # if key is the same
        if normalize_str(entry.get('key')) == normalize_str(key):
            # if value empty or the same
            if value is None or entry.get('value') == value:
                return True
    return False


def get_timeline_from_history(order_index: int, startdate) -> List[Dict[str, Any]]:
    # history liefert bereits Einträge mit timestamp/key/value (übersetzbar in history.py)
    history = get_history_of_order(order_index)
    timeline = []
    new_car = False
    first_delivery_window = True
    for entry in history:
        key = entry["key"]
        key_normalized = normalize_str(key)

        if key_normalized == t("Vehicle Odometer"):
            if new_car or entry.get("value") in [None, "", "N/A"]:
                continue
            timeline.append(
                {
                   "timestamp": entry["timestamp"],
                   "key": t("CAR BUILT"),
                   "value": "",
                }
            )
            new_car = True
            continue

        if key_normalized == t("Delivery Window") and first_delivery_window:
            if not entry["old_value"] in ['None', 'N/A', '']:
                timeline.append(
                    {
                       "timestamp": startdate,
                       "key": t("Delivery Window"),
                       "value": entry["old_value"],
                    }
                )
                first_delivery_window = False

        if normalize_str(key) not in TIMELINE_WHITELIST_NORMALIZED:
            continue

        timeline.append(entry)
    return timeline

def get_timeline_from_order(order_id: int, detailed_order: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    timeline_from_history = get_timeline_from_history(order_id, get_date_from_timestamp(order_info.get("reservationDate")))

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
        if not is_order_key_in_timeline(timeline_from_history, t('Expected Registration Date')):
            timeline.append(
                {
                    "timestamp": get_date_from_timestamp(registration_data.get("expectedRegDate")),
                    "key": t("Expected Registration Date"),
                    "value": "",
                }
            )
        
    if final_payment_data.get('etaToDeliveryCenter'):
        if not is_order_key_in_timeline(timeline_from_history, t('ETA To Delivery Center')):
            timeline.append(
                {
                    "timestamp": get_date_from_timestamp(final_payment_data.get("etaToDeliveryCenter")),
                    "key": t("ETA To Delivery Center"),
                    "value": "",
                }
            )
        
    if scheduling.get('deliveryAppointmentDate'):
        if not is_order_key_in_timeline(timeline_from_history, t('Delivery Appointment Date')):
            timeline.append({
                "timestamp": get_date_from_timestamp(scheduling.get("deliveryAppointmentDate")),
                "key": t("Delivery Appointment Date"),
                "value": "",
            })

    timeline.extend(timeline_from_history)
    return timeline


def print_timeline(order_id: int, detailed_order: Dict[str, Any]) -> None:
    timeline = get_timeline_from_order(order_id, detailed_order)
    if not timeline:
        return

    print(f"\n{color_text(t('Order Timeline') + ':', '94')}")
    printed_keys: set[str] = set()
    for entry in timeline:
        key = entry.get("key", "")
        msg_parts = []
        if key in printed_keys:
            msg_parts.append(t("new") + " ")
        msg_parts.append(t(key))
        if entry.get("value"):
            msg_parts.append(f": {entry['value']}")
        msg = "".join(msg_parts)
        print(f"- {entry.get('timestamp')}: {msg}")
        printed_keys.add(key)
