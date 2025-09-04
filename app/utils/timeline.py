from __future__ import annotations
from typing import Any, Dict, List

from app.utils.history import get_history_of_order
from app.utils.helpers import get_date_from_timestamp
from app.utils.colors import color_text

IGNORED_KEYS = {
    'Routing Location',
    'Delivery Details',
    'Model',
    'Configuration',
    'Amount Paid',
    'Payment Method',
    'Finance Product',
    'Finance Partner',
    'Monthly Payment',
    'Term (months)',
    'Interest Rate',
    'Range per Year',
    'Financed Amount',
    'Approved Amount'
}

def is_order_key_in_timeline(timeline, key, value = "###"):

    for entry in timeline:
        if entry.get('key') == key:

            return True
    return False


def get_timeline_from_history(order_index: int, startdate) -> List[Dict[str, Any]]:
    # history liefert bereits Einträge mit timestamp/key/value (übersetzbar in history.py)
    history = get_history_of_order(order_index)
    timeline = []
    new_car = False
    first_delivery_window = True
    for entry in history:
        if entry["key"] == "Vehicle Odometer" and new_car:
            continue
        if entry["key"] == "Vehicle Odometer":
            timeline.append(
                {
                   "timestamp": entry["timestamp"],
                   "key": "your car has been built",
                   "value": "",
                }
            )
            new_car = True
            continue

        if entry["key"] == "Delivery Window" and first_delivery_window:
            timeline.append(
                {
                   "timestamp": startdate,
                   "key": "Delivery Window",
                   "value": entry["old_value"],
                }
            )
            first_delivery_window = False

        if entry["key"] in IGNORED_KEYS:
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
        
    if scheduling.get('deliveryAppointmentDate'):
        if not is_order_key_in_timeline(timeline_from_history, 'Delivery Appointment Date'):
            timeline.append({
                "timestamp": get_date_from_timestamp(scheduling.get("deliveryAppointmentDate")),
                "key": "Delivery Appointment Date",
                "value": "",
            })

    timeline.extend(timeline_from_history)
    return timeline


def print_timeline(order_id: int, detailed_order: Dict[str, Any]) -> None:
    timeline = get_timeline_from_order(order_id, detailed_order)
    if not timeline:
        return

    print(f"\n{color_text('Order Timeline:', '94')}")
    printed_keys = {}
    for entry in timeline:
        msg_parts = []
        if entry.get("key") in printed_keys:
            msg_parts.append("new ")
        msg_parts.append(entry.get("key", ""))
        if entry.get("value"):
            msg_parts.append(f": {entry['value']}")
        msg = "".join(msg_parts)
        print(f"- {entry.get('timestamp')}: {msg}")
        if entry.get("key") not in printed_keys:
            printed_keys[entry.get("key")] = 0
        printed_keys[entry.get("key")] += 1
