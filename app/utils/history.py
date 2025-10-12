import json
import os

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

def load_history_from_file():
    if os.path.exists(HISTORY_FILE):
       try:
           with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
               history = json.load(f)
           return history
       except (OSError, json.JSONDecodeError):
           return []
    return []


def save_history_to_file(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f)


def get_history_of_order(order_id):
    order_id_str = str(order_id)
    history = load_history_from_file()
    changes = []
    if history:
        for entry in history:
            for change in entry['changes']:
                key = change.get('key')
                if not isinstance(key, str):
                    continue

                # Skip if not matching order_id
                key_parts = key.split('.', 1)
                if len(key_parts) == 0 or key_parts[0] != order_id_str:
                    continue

                # Extract just the path after removing order number prefix
                if len(key_parts) > 1:
                    key = key_parts[1]

                # skip if key is uninteresting
                if not ALL_KEYS_MODE:
                    if any(key.startswith(pref) for pref in HISTORY_TRANSLATIONS_IGNORED):
                        continue


                    if not DETAILS_MODE:
                        if key not in HISTORY_TRANSLATIONS and key not in HISTORY_TRANSLATIONS_ANONYMOUS:
                            continue

                    # translate if key is known
                    if key in HISTORY_TRANSLATIONS_DETAILS:
                        # skip if not in details mode and old entrys (only show in non details mode if its from today)
                        change['key'] = HISTORY_TRANSLATIONS_DETAILS[key]
                    else:
                        continue


                    if SHARE_MODE:
                        # remove values from keys, which have to be anonymous
                        if key in HISTORY_TRANSLATIONS_ANONYMOUS:
                            for field in ['value', 'old_value']:
                                if isinstance(change.get(field), str):
                                    change[field] = None


                # Check and convert timestamps in value and old_value
                for field in ['value', 'old_value']:
                    if isinstance(change.get(field), str):
                        change[field] = get_date_from_timestamp(change[field])

                change['timestamp'] = entry['timestamp']

                changes.append(change)
    return changes

def _format_value(value):
    if isinstance(value, (list, dict)):
        if DETAILS_MODE or ALL_KEYS_MODE:
            return f"\n {pretty_print(value)}"
        return t("Too much data - only available in --details view")
    return value

def print_history(order_id: int) -> None:
    history = get_history_of_order(order_id)
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
