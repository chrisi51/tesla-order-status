import io
import json
import os
import re
import sys
from typing import List, Dict, Any, Callable
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

from app.config import APP_VERSION, HISTORY_FILE, ORDERS_FILE, TESLA_STORES, TODAY
from app.utils.colors import color_text, strip_color
from app.utils.connection import request_with_retry
from app.utils.helpers import decode_option_codes, get_date_from_timestamp, compare_dicts
from app.utils.history import load_history_from_file, save_history_to_file, print_history
from app.utils.locale import t, LANGUAGE, use_default_language
import app.utils.history as history_module
from app.utils.params import DETAILS_MODE, SHARE_MODE, STATUS_MODE, CACHED_MODE
from app.utils.telemetry import track_usage
from app.utils.timeline import print_timeline


def _get_all_orders(access_token):
    orders = _retrieve_orders(access_token)

    new_orders = []
    for order in orders:
        order_id = order['referenceNumber']
        order_details = _retrieve_order_details(order_id, access_token)

        if not order_details or not order_details.get('tasks'):
            print(color_text(t("Error: Received empty response from Tesla API. Please try again later."), '91'))
            if STATUS_MODE:
                print("-1")
            sys.exit(1)

        detailed_order = {
            'order': order,
            'details': order_details
        }
        new_orders.append(detailed_order)

    return new_orders

def _retrieve_orders(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    api_url = 'https://owner-api.teslamotors.com/api/1/users/orders'
    response = request_with_retry(api_url, headers)
    return response.json()['response']


def _retrieve_order_details(order_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    api_url = f'https://akamai-apigateway-vfx.tesla.com/tasks?deviceLanguage={LANGUAGE}&deviceCountry=DE&referenceNumber={order_id}&appVersion={APP_VERSION}'
    response = request_with_retry(api_url, headers)
    return response.json()


def _save_orders_to_file(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f)
    if not STATUS_MODE:
        print(color_text(t("> Orders saved to '{file}'").format(file=ORDERS_FILE), '94'))

def _load_orders_from_file():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    return None


def _compare_orders(old_orders, new_orders):
    differences = []
    for i, old_order in enumerate(old_orders):
        if i < len(new_orders):
            differences.extend(compare_dicts(old_order, new_orders[i], path=f'{i}.'))
        else:
            differences.append({'operation': 'removed', 'key': str(i)})
    for i in range(len(old_orders), len(new_orders)):
        differences.append({'operation': 'added', 'key': str(i)})
    return differences


def get_order(order_id):
    orders = _load_orders_from_file()
    if not isinstance(orders, dict):
        return {}
    return orders.get(order_id)

def get_model_from_order(detailed_order) -> str:
    order = detailed_order.get('order', {})
    decoded_options = decode_option_codes(order.get('mktOptions', ''))
    model = "unknown"
    for _, description in decoded_options:
        if 'Model' in description and len(description) > 10:
           # Extract model name and configuration suffix using regex
           # Model Y Long Range Dual Motor - AWD LR (Juniper) => Model Y - AWD LR
           match = re.match(r'(Model [YSX3]).*?((AWD|RWD) (LR|SR|P)).*?$', description)
           if match:
               model_name = match.group(1)
               config_suffix = match.group(2)
               value = f"{model_name} - {config_suffix}"
               model = value.strip()
               break

    return model

def _render_share_output(detailed_orders):
    order_number = 0
    for detailed_order in detailed_orders:
        order = detailed_order['order']
        order_details = detailed_order['details']
        scheduling = order_details.get('tasks', {}).get('scheduling', {})
        registration_data = order_details.get('tasks', {}).get('registration', {})
        order_info = registration_data.get('orderDetails', {})
        final_payment_data = order_details.get('tasks', {}).get('finalPayment', {}).get('data', {})

        model = paint = interior = "unknown"

        decoded_options = decode_option_codes(order.get('mktOptions', ''))
        if decoded_options:
            print(f"---\n{color_text('Order Details:', '94')}")
            for code, description in decoded_options:
                if 'Paint:' in description:
                    value = description.replace('Paint:', '').replace('Metallic', '').replace('Multi-Coat','').strip()
                    paint = value
                if 'Interior:' in description:
                    value = description.replace('Interior:', '').strip()
                    interior = value
                if 'Model' in description and len(description) > 10:
                   # Extract model name and configuration suffix using regex
                   # Model Y Long Range Dual Motor - AWD LR (Juniper) => Model Y - AWD LR
                   match = re.match(r'(Model [YSX3]).*?((AWD|RWD) (LR|SR|P)).*?$', description)
                   if match:
                       model_name = match.group(1)
                       config_suffix = match.group(2)
                       value = f"{model_name} - {config_suffix}"
                       model = value.strip()

            if model and paint and interior:
                msg = f"{model} / {paint} / {interior}"
                print(f"- {msg}")

        if scheduling.get('deliveryAddressTitle'):
            print(f"- {scheduling.get('deliveryAddressTitle')}")

        print_timeline(order_number, detailed_order)

        order_number += 1

def generate_share_output(detailed_orders):
    original_share_mode = history_module.SHARE_MODE
    history_module.SHARE_MODE = True
    output_capture = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_capture
    try:
        with use_default_language():
            _render_share_output(detailed_orders)

    finally:
        sys.stdout = original_stdout
        history_module.SHARE_MODE = original_share_mode

    if HAS_PYPERCLIP:
        # Create advertising text but don't print it
        ad_text = (f"\n{strip_color('Do you want to share your data and compete with others?')}\n"
                   f"{strip_color('Check it out on GitHub: https://github.com/chrisi51/tesla-order-status')}")
        pyperclip.copy("```\n" + strip_color(output_capture.getvalue()) + ad_text + "\n```")

    return output_capture.getvalue()

def display_orders_SHARE_MODE(detailed_orders):
    share_output = generate_share_output(detailed_orders)
    print(share_output, end='')


def display_orders(detailed_orders):
    if HAS_PYPERCLIP:
        share_output = generate_share_output(detailed_orders)

    order_number = 0
    for detailed_order in detailed_orders:
        order = detailed_order['order']
        order_details = detailed_order['details']
        scheduling = order_details.get('tasks', {}).get('scheduling', {})
        registration_data = order_details.get('tasks', {}).get('registration', {})
        order_info = registration_data.get('orderDetails', {})
        final_payment_data = order_details.get('tasks', {}).get('finalPayment', {}).get('data', {})

        print(f"{'-'*45}")

        print(f"{color_text(t('Order Details') + ':', '94')}")
        print(f"{color_text('- ' + t('Order ID') + ':', '94')} {order['referenceNumber']}")
        print(f"{color_text('- ' + t('Status') + ':', '94')} {order['orderStatus']}")
        print(f"{color_text('- ' + t('VIN') + ':', '94')} {order.get('vin', t('unknown'))}")

        decoded_options = decode_option_codes(order.get('mktOptions', ''))
        if decoded_options:
            print(f"\n{color_text(t('Configuration') + ':', '94')}")
            for code, description in decoded_options:
                print(f"{color_text(f'- {code}:', '94')} {description}")

        odometer = order_info.get('vehicleOdometer')
        odometer_type = order_info.get('vehicleOdometerType')
        if odometer is not None and odometer != 30 and odometer_type is not None:
            print(f"\n{color_text(t('Vehicle Status') + ':', '94')}")
            print(f"{color_text('- ' + t('Vehicle Odometer') + ':', '94')} {odometer} {odometer_type}")

        print(f"\n{color_text(t('Delivery Information') + ':', '94')}")
        location_id = order_info.get('vehicleRoutingLocation')
        store = TESLA_STORES.get(str(location_id) if location_id is not None else '', {})
        if store:
            print(f"{color_text('- ' + t('Routing Location') + ':', '94')} {store['display_name']} ({location_id or t('unknown')})")
            if DETAILS_MODE:
                address = store.get('address', {})
                print(f"    {color_text(t('Address') + ':', '94')} {address.get('address_1', t('unknown'))}")
                print(f"    {color_text(t('City') + ':', '94')} {address.get('city', t('unknown'))}")
                print(f"    {color_text(t('Postal Code') + ':', '94')} {address.get('postal_code', t('unknown'))}")
                if store.get('phone'):
                    print(f"    {color_text(t('Phone') + ':', '94')} {store['phone']}")
                if store.get('store_email'):
                    print(f"    {color_text(t('Email') + ':', '94')} {store['store_email']}")
            else:
                print(f"    {color_text(t('More Information in --details mode'), '94')}")
        else:
            print(f"{color_text('- ' + t('Delivery Center') + ':', '94')} {scheduling.get('deliveryAddressTitle', 'N/A')}")

        if final_payment_data.get('etaToDeliveryCenter'):
            print(f"{color_text('- ' + t('ETA to Delivery Center') + ':', '94')} {final_payment_data.get('etaToDeliveryCenter', 'N/A')}")
        if scheduling.get('deliveryAppointmentDate'):
            delivery_window = get_date_from_timestamp(scheduling.get('deliveryAppointmentDate'))
            print(f"{color_text('- ' + t('Delivery Appointment Date') + ':', '94')} {delivery_window}")
        else:
            print(f"{color_text('- ' + t('Delivery Window') + ':', '94')} {scheduling.get('deliveryWindowDisplay', t('unknown'))}")

        if DETAILS_MODE:
            print(f"\n{color_text(t('Financing Information') + ':', '94')}")
            financing_details = final_payment_data.get('financingDetails') or {}
            order_type = financing_details.get('orderType')
            tesla_finance_details = financing_details.get('teslaFinanceDetails') or {}

            # Handle cash purchases where no financing data is present
            if order_type == 'CASH' or not final_payment_data.get('financingIntent'):
                print(f"{color_text('- ' + t('Payment Type') + ':', '94')} {t('Cash')}")
                payment_details = final_payment_data.get('paymentDetails') or []
                if payment_details:
                    first_payment = payment_details[0]
                    amount_paid = first_payment.get('amountPaid', 'N/A')
                    payment_type = first_payment.get('paymentType', 'N/A')
                    print(f"{color_text('- ' + t('Amount Paid') + ':', '94')} {amount_paid}")
                    print(f"{color_text('- ' + t('Payment Method') + ':', '94')} {payment_type}")
                account_balance = final_payment_data.get('accountBalance')
                if account_balance is not None:
                    print(f"{color_text('- ' + t('Account Balance') + ':', '94')} {account_balance}")
                amount_due = final_payment_data.get('amountDue')
                if amount_due is not None:
                    print(f"{color_text('- ' + t('Amount Due') + ':', '94')} {amount_due}")
            else:
                finance_product = financing_details.get('financialProductType', 'N/A')
                print(f"{color_text('- ' + t('Finance Product') + ':', '94')} {finance_product}")
                finance_partner = tesla_finance_details.get('financePartnerName', 'N/A')
                print(f"{color_text('- ' + t('Finance Partner') + ':', '94')} {finance_partner}")
                monthly_payment = tesla_finance_details.get('monthlyPayment')
                if monthly_payment is not None:
                    print(f"{color_text('- ' + t('Monthly Payment') + ':', '94')} {monthly_payment}")
                term_months = tesla_finance_details.get('termsInMonths')
                if term_months is not None:
                    print(f"{color_text('- ' + t('Term (months)') + ':', '94')} {term_months}")
                interest_rate = tesla_finance_details.get('interestRate')
                if interest_rate is not None:
                    print(f"{color_text('- ' + t('Interest Rate') + ':', '94')} {interest_rate} %")
                mileage = tesla_finance_details.get('mileage')
                if mileage is not None:
                    print(f"{color_text('- ' + t('Range per Year') + ':', '94')} {mileage}")
                financed_amount = final_payment_data.get('amountDueFinancier')
                if financed_amount is not None:
                    print(f"{color_text('- ' + t('Financed Amount') + ':', '94')} {financed_amount}")
                approved_amount = tesla_finance_details.get('approvedLoanAmount')
                if approved_amount is not None:
                    print(f"{color_text('- ' + t('Approved Amount') + ':', '94')} {approved_amount}")

        print(f"{'-'*45}")

        print_timeline(order_number, detailed_order)

        print_history(order_number)

        order_number += 1


def print_bottom_line() -> None:
    print(f"\n{color_text(t('BOTTOM LINE HELP'), '94')}")
    # Inform user about clipboard status
    if HAS_PYPERCLIP:
        print(f"\n{color_text(t('BOTTOM LINE TEXT IN CLIPBOARD'), '93')}")
    else:
        print(f"\n{color_text(t('BOTTOM LINE CLIPBOARD NOT WORKING'), '91')}")
        print(f"{color_text('https://github.com/chrisi51/tesla-order-status?tab=readme-ov-file#general', '91')}")


# ---------------------------
# Main-Logic
# ---------------------------
def main(access_token) -> None:
    old_orders = _load_orders_from_file()
    track_usage(old_orders)

    if CACHED_MODE:
        print(color_text(t("Running in CACHED MODE... no API calls are made"), '93'))

        if old_orders:
            if STATUS_MODE:
                print("0")
            elif SHARE_MODE:
                display_orders_SHARE_MODE(old_orders)
            else:
                display_orders(old_orders)

            print_bottom_line()
        else:
            if STATUS_MODE:
                print("-1")
            else:
                print(color_text(t("No cached orders found in '{file}'").format(file=ORDERS_FILE), '91'))
        sys.exit(0)

    if not STATUS_MODE:
        print(color_text(f"\n> {t('Start retrieving the information. Please be patient...')}\n", '94'))


    new_orders = _get_all_orders(access_token)


    if old_orders:
        differences = _compare_orders(old_orders, new_orders)
        if differences:
            if STATUS_MODE:
                print("1")
            _save_orders_to_file(new_orders)
            history = load_history_from_file()
            history.append({
                'timestamp': TODAY,
                'changes': differences
            })
            save_history_to_file(history)
        else:
            if STATUS_MODE:
                print("0")
            os.utime(ORDERS_FILE, None)
    else:
        if STATUS_MODE:
            print("-1")
        else:
            # ask user if they want to save the new orders to a file for comparison next time
            if input(color_text(t("Would you like to save the order information in a file for change tracking? (y/n): "), '93')).lower() == 'y':
                _save_orders_to_file(new_orders)

    if not STATUS_MODE:
        if SHARE_MODE:
            display_orders_SHARE_MODE(new_orders)
        else:
            display_orders(new_orders)

    print_bottom_line()

