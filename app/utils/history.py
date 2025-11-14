import json
import os
from typing import Any, Dict, List

from app.config import HISTORY_FILE, TODAY
from app.utils.colors import color_text
from app.utils.helpers import get_date_from_timestamp, pretty_print
from app.utils.locale import t
from app.utils.params import DETAILS_MODE, SHARE_MODE, ALL_KEYS_MODE


# uninteresting history entries
HISTORY_TRANSLATIONS_IGNORED = {
    "order.vin", # we use details.tasks.deliveryDetails.regData.orderDetails.vin
    "details.tasks.registration.orderDetails.vin",
    "details.tasks.registration.regData.orderDetails.vin",
    "details.tasks.finalPayment.data.vin",
    "details.tasks.tradeIn.isMatched",
    "details.tasks.registration.isMatched",
    "details.tasks.registration.orderDetails.vehicleModelYear",
    "details.state.",
    "details.strings.",
    "details.scheduling.card.",
    "details.scheduling.strings.",
    "details.tasks.carbonCredit.card.",
    "details.tasks.carbonCredit.strings.",
    "details.tasks.finalPayment.card.",
    "details.tasks.finalPayment.strings.",
    "details.tasks.scheduling.card.",
    "details.tasks.scheduling.strings.",
    "details.tasks.scheduling.isDeliveryEstimatesEnabled",
    "details.tasks.registration.orderDetails.isAvailableForMatch",
    "details.tasks.finalPayment.data.isAvailableForMatch",
    "details.tasks.finalPayment.data.deliveryReadinessDetail.",
    "details.tasks.finalPayment.data.deliveryReadiness.",
    "details.tasks.finalPayment.data.agreementDetails",
    "details.tasks.finalPayment.data.vehicleId",
    "details.tasks.deliveryAcceptance.gates",
    "details.tasks.deliveryAcceptance.card.",
    "details.tasks.deliveryAcceptance.strings.",
    "details.tasks.deliveryDetails.regData.reggieRegistrationStatus",
    "details.tasks.deliveryDetails.strings.",
    "details.tasks.deliveryDetails.card.",
    "details.tasks.registration.card.",
    "details.tasks.registration.regData.reggieRegistrationStatus",
    "details.tasks.registration.strings.",
    "details.tasks.finalPayment.complete",
    "details.tasks.finalPayment.data.finalPaymentStatus",
    "details.tasks.scheduling.apptDateTimeAddressStr",
    "details.tasks.scheduling.isInventoryOrMatched",
    "details.tasks.finalPayment.data.hasFinalInvoice",
    "details.tasks.finalPayment.data.hasActiveInvoice",
    "details.tasks.finalPayment.data.selfSchedulingDetails.deliveryLocationId",
    "details.tasks.finalPayment.data.selfSchedulingDetails.",
    "details.tasks.financing.card.",
    "details.tasks.financing.strings.",
    "details.tasks.tradeIn.card.",
    "details.tasks.tradeIn.strings."
}

# Define translations for history keys
HISTORY_TRANSLATIONS = {
    'details.tasks.scheduling.deliveryWindowDisplay': 'Delivery Window',
    'details.tasks.scheduling.deliveryAppointmentDate': 'Delivery Appointment Date',
    'details.tasks.scheduling.deliveryAddressTitle': 'Delivery Center',
    'details.tasks.finalPayment.data.etaToDeliveryCenter': 'ETA to Delivery Center',
    'details.tasks.registration.orderDetails.vehicleRoutingLocation': 'Routing Location',
    'details.tasks.registration.expectedRegDate': 'Expected Registration Date',
    'details.orderStatus': 'Order Status',
    'details.tasks.registration.orderDetails.reservationDate': 'Reservation Date',
    'details.tasks.registration.orderDetails.orderBookedDate': 'Order Booked Date',
    'details.tasks.registration.orderDetails.vehicleOdometer': 'Vehicle Odometer',
    'order.modelCode': 'Model',
    'order.mktOptions': 'Configuration'
}

HISTORY_TRANSLATIONS_ANONYMOUS = {
    'details.tasks.deliveryDetails.regData.orderDetails.vin': 'VIN',
}


HISTORY_TRANSLATIONS_DETAILS = {
    **HISTORY_TRANSLATIONS,
    **HISTORY_TRANSLATIONS_ANONYMOUS,
    'details.tasks.finalPayment.data.paymentDetails.amountPaid': 'Amount Paid',
    'details.tasks.finalPayment.data.paymentDetails.paymentType': 'Payment Method',
    'details.tasks.finalPayment.data.accountBalance': 'Account Balance',
    'details.tasks.finalPayment.data.amountDue': 'Amount Due',
    'details.tasks.finalPayment.data.financingDetails.financialProductType': 'Finance Product',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.financePartnerName': 'Finance Partner',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.monthlyPayment': 'Monthly Payment',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.termsInMonths': 'Term (months)',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.interestRate': 'Interest Rate',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.mileage': 'Range per Year',
    'details.tasks.finalPayment.data.amountDueFinancier': 'Financed Amount',
    'details.tasks.finalPayment.data.financingDetails.teslaFinanceDetails.approvedLoanAmount': 'Approved Amount',
    'details.tasks.finalPayment.data.paymentDetails': 'Payment Details',
    'details.tasks.finalPayment.amountDue': 'Amount Due',
    'details.tasks.finalPayment.data.amountDueAfterRefund': 'Amount Due After Refund',
    'details.tasks.finalPayment.status': 'Payment Status',
    'details.tasks.registration.orderDetails.vehicleId': 'VehicleID',
    'details.tasks.registration.orderDetails.registrationStatus': 'Registration Status',
    'details.tasks.finalPayment.data.vehicleregistration': 'Vehicle Registration',
    'details.tasks.finalPayment.data.vehicleParts': 'Vehicle Parts',
    'details.tasks.scheduling.apptDateTimeAddressStr': 'Delivery Details'
}

HistoryEntry = Dict[str, Any]
HistoryStore = Dict[str, List[HistoryEntry]]

def load_history_from_file() -> HistoryStore:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
            if isinstance(history, dict):
                normalized: HistoryStore = {}
                for reference, entries in history.items():
                    if not isinstance(entries, list):
                        continue
                    normalized[str(reference)] = [
                        entry for entry in entries
                        if isinstance(entry, dict)
                    ]
                return normalized
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_history_to_file(history: HistoryStore) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f)


def get_history_of_order(order_reference) -> List[Dict[str, Any]]:
    history = load_history_from_file()
    entries = history.get(str(order_reference), [])
    changes: List[Dict[str, Any]] = []
    for entry in entries:
        timestamp = entry.get('timestamp')
        entry_changes = entry.get('changes', [])
        if not isinstance(entry_changes, list):
            continue
        for change in entry_changes:
            if not isinstance(change, dict):
                continue

            key = change.get('key')
            key_str = key if isinstance(key, str) else ""
            display_key = key_str

            if not ALL_KEYS_MODE:
                if any(key_str.startswith(pref) for pref in HISTORY_TRANSLATIONS_IGNORED):
                    continue

                if not DETAILS_MODE:
                    if key_str not in HISTORY_TRANSLATIONS and key_str not in HISTORY_TRANSLATIONS_ANONYMOUS:
                        continue

                if key_str in HISTORY_TRANSLATIONS_DETAILS:
                    display_key = HISTORY_TRANSLATIONS_DETAILS[key_str]
                else:
                    continue

                if SHARE_MODE and key_str in HISTORY_TRANSLATIONS_ANONYMOUS:
                    change = dict(change)
                    for field in ['value', 'old_value']:
                        if isinstance(change.get(field), str):
                            change[field] = None

            sanitized_change = {
                'operation': change.get('operation'),
                'key': display_key,
                'value': change.get('value'),
                'old_value': change.get('old_value'),
                'timestamp': timestamp
            }

            for field in ['value', 'old_value']:
                if isinstance(sanitized_change.get(field), str):
                    sanitized_change[field] = get_date_from_timestamp(sanitized_change[field])

            changes.append(sanitized_change)
    return changes

def _format_value(value):
    if isinstance(value, (list, dict)):
        if DETAILS_MODE or ALL_KEYS_MODE:
            return f"\n {pretty_print(value)}"
        return t("Too much data - only available in --details view")
    return value

def print_history(order_reference) -> None:
    history = get_history_of_order(order_reference)
    if history:
        print("\n")
        print(color_text(t("Change History") + ':', '94'))
        for change in history:
            msg = format_history_entry(change, change['timestamp'] == TODAY)
            print(msg)


def format_history_entry(entry, colored):
    op = entry.get('operation')
    key = entry.get('key')
    timestamp = entry.get('timestamp')

    value = _format_value(entry.get('value'))
    old_value = _format_value(entry.get('old_value'))

    if op == 'added':
        if colored:
            return color_text(f"- {timestamp}: + {t(key)}: {value}", '94')
        else:
            return f"- {timestamp}: + {t(key)}: {value}"
    if op == 'removed':
        if colored:
            return color_text(f"- {timestamp}: - {t(key)}: {old_value}", '94')
        else:
            return f"- {timestamp}: - {t(key)}: {old_value}"
    if op == 'changed':
        if colored:
            return (
                f"{color_text(f'- {timestamp}: ≠ {t(key)}:', '94')} "
                f"{color_text(old_value, '91')} "
                f"{color_text('->', '94')} "
                f"{color_text(value, '92')}"
            )
        else:
            return f"- {timestamp}: ≠ {t(key)}: {old_value} -> {value}"
    return f"{op} {t(key)}"
