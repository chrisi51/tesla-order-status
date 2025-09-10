import json
import os
import re
from typing import List, Dict, Any, Callable

from app.config import HISTORY_FILE, TODAY
from app.utils.colors import color_text
from app.utils.helpers import get_date_from_timestamp
from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE


# uninteresting history entries
HISTORY_TRANSLATIONS_IGNORED = {
    'order.vin', # we use details.tasks.deliveryDetails.regData.orderDetails.vin
    'details.tasks.registration.orderDetails.vin',
    'details.tasks.registration.regData.orderDetails.vin',
    'details.tasks.finalPayment.data.vin',
    'details.tasks.tradeIn.isMatched',
    'details.tasks.registration.isMatched',
    'details.tasks.registration.orderDetails.vehicleModelYear',
    'details.state.',
    'details.strings.',
    'details.scheduling.card.',
    'details.scheduling.strings.',
    'details.tasks.finalPayment.card.',
    'details.tasks.finalPayment.strings.',
    'details.tasks.scheduling.card.',
    'details.tasks.scheduling.strings.',
    'details.tasks.scheduling.isDeliveryEstimatesEnabled',
    'details.tasks.registration.orderDetails.isAvailableForMatch',
    'details.tasks.finalPayment.data.isAvailableForMatch',
    'details.tasks.finalPayment.data.deliveryReadinessDetail.',
    'details.tasks.finalPayment.data.deliveryReadiness.',
    'details.tasks.finalPayment.data.agreementDetails',
    'details.tasks.finalPayment.data.vehicleId',
    'details.tasks.deliveryAcceptance.gates',
    'details.tasks.deliveryDetails.regData.reggieRegistrationStatus',
    'details.tasks.registration.regData.reggieRegistrationStatus',
    'details.tasks.finalPayment.complete',
    'details.tasks.finalPayment.data.finalPaymentStatus',
    'details.tasks.scheduling.isInventoryOrMatched',
    'details.tasks.finalPayment.data.hasFinalInvoice',
    'details.tasks.finalPayment.data.hasActiveInvoice',
    'details.tasks.finalPayment.data.selfSchedulingDetails.deliveryLocationId',
    'details.tasks.finalPayment.data.selfSchedulingDetails.'
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
    'details.tasks.scheduling.apptDateTimeAddressStr': 'Delivery Details',
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
    'details.tasks.finalPayment.data.vehicleregistration': 'Vehicle Registration'
}

def load_history_from_file():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        return history
    return []


def save_history_to_file(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)


def get_history_of_order(order_id):
    order_id_str = str(order_id)
    history = load_history_from_file()
    changes = []
    if history:
        for entry in history:
            for change in entry['changes']:
                key = change.get('key', '')

                # Skip if not matching order_id
                key_parts = key.split('.', 1)
                if len(key_parts) == 0 or key_parts[0] != order_id_str:
                    continue

                # Extract just the path after removing order number prefix
                if len(key_parts) > 1:
                    key = key_parts[1]

                # skip if key is uninteresting
                if any(key.startswith(pref) for pref in HISTORY_TRANSLATIONS_IGNORED):
                    continue

                # translate if key is known
                if key in HISTORY_TRANSLATIONS_DETAILS:
                    change['key'] = HISTORY_TRANSLATIONS_DETAILS[key]

                if SHARE_MODE:
                    # dont print if in SHARE_MODE and not in HISTORY_TRANSLATIONS
                    if key not in HISTORY_TRANSLATIONS and key not in HISTORY_TRANSLATIONS_ANONYMOUS:
                        continue

                    # dont print if not in DETAILS MODE and not in HISTORY_TRANSLATIONS_DETAILS EXCEPT its a NEW Entry
                    if key in HISTORY_TRANSLATIONS_ANONYMOUS:
                        for field in ['value', 'old_value']:
                            if isinstance(change.get(field), str):
                                change[field] = None

                # dont print if not in DETAILS MODE and not in HISTORY_TRANSLATIONS_DETAILS EXCEPT its a NEW Entry
                if key not in HISTORY_TRANSLATIONS_DETAILS and not DETAILS_MODE and entry['timestamp'] != TODAY:
                    continue

                # Check and convert timestamps in value and old_value
                for field in ['value', 'old_value']:
                    if isinstance(change.get(field), str):
                        change[field] = get_date_from_timestamp(change[field])

                change['timestamp'] = entry['timestamp']

                changes.append(change)
    return changes


def print_history(order_id: str) -> None:
    history = get_history_of_order(order_id)
    if history:
        print(color_text("\nChange History:", '94'))
        for change in history:
            msg = format_history_entry(change, change['timestamp'] == TODAY)
            print(msg)


def format_history_entry(entry, colored):
    op = entry.get('operation')
    key = entry.get('key')
    if op == 'added':
        if colored:
            return color_text(f"{entry.get('timestamp')}: + {key}: {entry.get('value')}", '94')
        else:
            return f"{entry.get('timestamp')}: + {key}: {entry.get('value')}"
    if op == 'removed':
        if colored:
            return color_text(f"{entry.get('timestamp')}: - {key}: {entry.get('old_value')}", '94')
        else:
            return f"{entry.get('timestamp')}: - {key}: {entry.get('old_value')}"
    if op == 'changed':
        if colored:
            timestamp = entry.get("timestamp")
            old_value = entry.get("old_value")
            new_value = entry.get("value")
            return (
                f"{color_text(f'{timestamp}: ≠ {key}:', '94')} "
                f"{color_text(old_value, '91')} "
                f"{color_text('->', '94')} "
                f"{color_text(new_value, '92')}"
            )
        else:
            return f"{entry.get('timestamp')}: ≠ {key}: {entry.get('old_value')} -> {entry.get('value')}"
    return f"{op} {key}"