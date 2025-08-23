from glob import glob
import argparse
import base64
import json
import os
import time
import hashlib
import requests
import webbrowser
import urllib.parse
import re
import sys

from tesla_stores import TeslaStore
from update_check import main as run_update_check

# Define constants
CLIENT_ID = 'ownerapi'
REDIRECT_URI = 'https://auth.tesla.com/void/callback'
AUTH_URL = 'https://auth.tesla.com/oauth2/v3/authorize'
TOKEN_URL = 'https://auth.tesla.com/oauth2/v3/token'
SCOPE = 'openid email offline_access'
CODE_CHALLENGE_METHOD = 'S256'
STATE = os.urandom(16).hex()
TOKEN_FILE = 'tesla_tokens.json'
ORDERS_FILE = 'tesla_orders.json'
HISTORY_FILE = 'tesla_order_history.json'
APP_VERSION = '9.99.9-9999' # we can use a dummy version here, as the API does not check it strictly

OPTION_CODES = {}
for path in sorted(glob("./option-codes/*.json")):
    with open(path, encoding="utf-8") as f:
        OPTION_CODES.update(json.load(f))  # last wins

parser = argparse.ArgumentParser(description="Retrieve Tesla order status.")
group = parser.add_mutually_exclusive_group()
group.add_argument("--details", action="store_true", help="Show additional details such as financing information.")
group.add_argument("--share", action="store_true", help="Hide personal data like Order ID and VIN for sharing.")
group.add_argument("--status", action="store_true", help="Only report whether there are changes since the last check.")
parser.add_argument("--cached", action="store_true", help="Use locally cached data without contacting the API.")
args = parser.parse_args()

DETAILS_MODE = args.details
SHARE_MODE = args.share
STATUS_MODE = args.status
CACHED_MODE = args.cached

TODAY = time.strftime('%Y-%m-%d')

def decode_option_codes(option_string: str):
    """Return a list of tuples with (code, description)."""
    codes = sorted(c.strip() for c in option_string.split(',') if c.strip())
    return [(code, OPTION_CODES.get(code, "Unknown option code")) for code in codes]

def supports_color():
    """Return True if ANSI colors are supported on this output."""
    if os.getenv("NO_COLOR"):
        return False
    if sys.platform == "win32":
        try:
            import colorama

            colorama.init()  # type: ignore
            return True
        except Exception:
            return False
    return sys.stdout.isatty()


_USE_COLOR = supports_color()

def color_text(text, color_code):
    if _USE_COLOR:
        return f"\033[{color_code}m{text}\033[0m"
    return text

def generate_code_verifier_and_challenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(
        b'=').decode('utf-8')
    return code_verifier, code_challenge


def get_auth_code():
    auth_params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': SCOPE,
        'state': STATE,
        'code_challenge': code_challenge,
        'code_challenge_method': CODE_CHALLENGE_METHOD,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    print(color_text("To retrieve your order status, you need to authenticate with your Tesla account.", '93'))
    print(color_text("A browser window will open with the Tesla login page. After logging in you will likely see a 'Page Not Found' page.", '93'))
    print(color_text("Copy the full URL of that page and return here. The authentication happens only between you and Tesla; no data leaves your system.", '93'))
    if input(color_text("Proceed to open the login page? (y/n): ", '93')).lower() != 'y':
        print(color_text("Authentication cancelled.", '91'))
        sys.exit(0)
    webbrowser.open(auth_url)
    redirected_url = input(color_text("Please enter the redirected URL here: ", '93'))
    parsed_url = urllib.parse.urlparse(redirected_url)
    return urllib.parse.parse_qs(parsed_url.query).get('code')[0]


def exchange_code_for_tokens(auth_code):
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier,
    }
    response = requests.post(TOKEN_URL, data=token_data)
    response.raise_for_status()
    return response.json()


def save_tokens_to_file(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)
    if not STATUS_MODE:
        print(color_text(f"> Tokens saved to '{TOKEN_FILE}'", '94'))


def load_tokens_from_file():
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)


def is_token_valid(access_token):
    jwt_decoded = json.loads(base64.b64decode(access_token.split('.')[1] + '==').decode('utf-8'))
    return jwt_decoded['exp'] > time.time()


def refresh_tokens(refresh_token):
    token_data = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'refresh_token': refresh_token,
    }
    response = requests.post(TOKEN_URL, data=token_data)
    response.raise_for_status()
    return response.json()


def retrieve_orders(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    api_url = 'https://owner-api.teslamotors.com/api/1/users/orders'
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()['response']


def get_order_details(order_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    api_url = f'https://akamai-apigateway-vfx.tesla.com/tasks?deviceLanguage=en&deviceCountry=DE&referenceNumber={order_id}&appVersion={APP_VERSION}'
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def save_orders_to_file(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f)
    if not STATUS_MODE:
        print(color_text(f"\n> Orders saved to '{ORDERS_FILE}'", '94'))


def load_orders_from_file():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    return None


def migrate_history_format(history):
    """Convert history entries from the old string format to the new structured format."""
    if not history or not history[0].get('changes'):
        return history
    # Check if migration is necessary (old format uses strings)
    if isinstance(history[0]['changes'][0], dict):
        return history
    migrated = []
    for entry in history:
        new_entry = {'timestamp': entry.get('timestamp'), 'changes': []}
        changes = entry.get('changes', [])
        i = 0
        while i < len(changes):
            change = changes[i]
            if change.startswith("+ Added key '"):
                m = re.match(r"\+ Added key '([^']+)': (.*)", change)
                if m:
                    key = m.group(1).replace('Order ', '', 1)
                    new_entry['changes'].append({
                        'operation': 'added',
                        'key': key,
                        'value': m.group(2)
                    })
                i += 1
            elif change.startswith("- Removed key '"):
                m = re.match(r"- Removed key '([^']+)'", change)
                if m:
                    key = m.group(1).replace('Order ', '', 1)
                    new_entry['changes'].append({
                        'operation': 'removed',
                        'key': key,
                        'old_value': None
                    })
                i += 1
            elif change.startswith("+ Added order "):
                m = re.match(r"\+ Added order (\d+)", change)
                if m:
                    new_entry['changes'].append({
                        'operation': 'added',
                        'key': m.group(1)
                    })
                i += 1
            elif change.startswith("- Removed order "):
                m = re.match(r"- Removed order (\d+)", change)
                if m:
                    new_entry['changes'].append({
                        'operation': 'removed',
                        'key': m.group(1)
                    })
                i += 1
            elif change.startswith('- '):
                if i + 1 < len(changes) and changes[i + 1].startswith('+ '):
                    m_old = re.match(r"- ([^:]+): (.*)", change)
                    m_new = re.match(r"\+ ([^:]+): (.*)", changes[i + 1])
                    if m_old and m_new and m_old.group(1) == m_new.group(1):
                        key = m_old.group(1).replace('Order ', '', 1)
                        new_entry['changes'].append({
                            'operation': 'changed',
                            'key': key,
                            'old_value': m_old.group(2),
                            'value': m_new.group(2)
                        })
                        i += 2
                        continue
                i += 1
            else:
                i += 1
        migrated.append(new_entry)
    return migrated


def load_history_from_file():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        migrated = migrate_history_format(history)
        if migrated != history:
            save_history_to_file(migrated)
        return migrated
    return []


def save_history_to_file(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)


def compare_dicts(old_dict, new_dict, path=''):
    differences = []
    for key in old_dict:
        if key not in new_dict:
            differences.append({
                'operation': 'removed',
                'key': path + key,
                'old_value': old_dict[key]
            })
        elif isinstance(old_dict[key], dict) and isinstance(new_dict[key], dict):
            differences.extend(compare_dicts(old_dict[key], new_dict[key], path + key + '.'))
        elif old_dict[key] != new_dict[key]:
            differences.append({
                'operation': 'changed',
                'key': path + key,
                'old_value': old_dict[key],
                'value': new_dict[key]
            })

    for key in new_dict:
        if key not in old_dict:
            differences.append({
                'operation': 'added',
                'key': path + key,
                'value': new_dict[key]
            })

    return differences


def compare_orders(old_orders, new_orders):
    differences = []
    for i, old_order in enumerate(old_orders):
        if i < len(new_orders):
            differences.extend(compare_dicts(old_order, new_orders[i], path=f'{i}.'))
        else:
            differences.append({'operation': 'removed', 'key': str(i)})
    for i in range(len(old_orders), len(new_orders)):
        differences.append({'operation': 'added', 'key': str(i)})
    return differences

# Define translations for history keys
HISTORY_TRANSLATIONS = {
    'details.tasks.scheduling.deliveryWindowDisplay': 'Delivery Window',
    'details.tasks.scheduling.deliveryAppointmentDate': 'Delivery Appointment',
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

def print_history(history):
    if history:
        print(color_text("\nChange History:", '94'))
        for entry in history:
            for change in entry['changes']:
                if SHARE_MODE:
                    key = change.get('key', '')
                    # Extract just the path after removing order number prefix
                    key_parts = key.split('.', 1)
                    if len(key_parts) > 1:
                        key = key_parts[1]
                    if key not in HISTORY_TRANSLATIONS:
                        continue
                    else:
                        change['key'] = HISTORY_TRANSLATIONS[key]
                msg = format_history_entry(entry['timestamp'], change, entry['timestamp'] == TODAY)
                print(msg)
def format_history_entry(timestamp, entry, colored):
    op = entry.get('operation')
    key = entry.get('key')
    if op == 'added':
        if colored:
            return color_text(f"{timestamp}: + {key}: {entry.get('value')}", '94')
        else:
            return f"{timestamp}: + {key}: {entry.get('value')}"
    if op == 'removed':
        if colored:
            return color_text(f"{timestamp}: - {key}: {entry.get('old_value')}", '94')
        else:
            return f"{timestamp}: - {key}: {entry.get('old_value')}"
    if op == 'changed':
        if colored:
            return f"{color_text(f'{timestamp}: ≠ {key}:', '94')} {color_text(entry.get('old_value'), '91')} {color_text('->', '94')} {color_text(entry.get('value'), '92')}"
        else:
            return f"{timestamp}: ≠ {key}: {entry.get('old_value')} -> {entry.get('value')}"
    return f"{op} {key}"


def truncate_timestamp(timestamp):
    """Truncates timestamp to date only if SHARE_MODE is active."""
    if not timestamp or timestamp == 'N/A':
        return timestamp
    if SHARE_MODE and 'T' in timestamp:
        return timestamp.split('T')[0]
    return timestamp

def display_orders(detailed_orders):
    for detailed_order in detailed_orders:
        order = detailed_order['order']
        order_details = detailed_order['details']
        scheduling = order_details.get('tasks', {}).get('scheduling', {})
        registration_data = order_details.get('tasks', {}).get('registration', {})
        order_info = registration_data.get('orderDetails', {})
        final_payment_data = order_details.get('tasks', {}).get('finalPayment', {}).get('data', {})

        print(f"\n{'-'*45}")
        print(f"{'ORDER INFORMATION':^45}")
        print(f"{'-'*45}")

        print(f"{color_text('Order Details:', '94')}")
        if not SHARE_MODE:
            print(f"{color_text('- Order ID:', '94')} {order['referenceNumber']}")
        print(f"{color_text('- Status:', '94')} {order['orderStatus']}")
        print(f"{color_text('- Model:', '94')} {order['modelCode']}")
        if not SHARE_MODE:
            print(f"{color_text('- VIN:', '94')} {order.get('vin', 'N/A')}")

        decoded_options = decode_option_codes(order.get('mktOptions', ''))
        if decoded_options:
            print(f"\n{color_text('Configuration Options:', '94')}")
            for code, description in decoded_options:
                print(f"{color_text(f'- {code}:', '94')} {description}")

        print(f"\n{color_text('Order Timeline:', '94')}")
        print(f"{color_text('- Reservation Date:', '94')} {truncate_timestamp(order_info.get('reservationDate', 'N/A'))}")
        print(f"{color_text('- Order Booked Date:', '94')} {truncate_timestamp(order_info.get('orderBookedDate', 'N/A'))}")
        if registration_data.get('expectedRegDate'):
            print(f"{color_text('- Expected Registration Date:', '94')} {truncate_timestamp(registration_data.get('expectedRegDate', 'N/A'))}")
        if final_payment_data.get('etaToDeliveryCenter', {}):
            print(f"{color_text('- ETA To Delivery Center:', '94')} {truncate_timestamp(final_payment_data.get('etaToDeliveryCenter', 'N/A'))}")
        if scheduling.get('deliveryAppointmentDate', {}):
            print(f"{color_text('- Delivery Appointment Date:', '94')} {truncate_timestamp(scheduling.get('deliveryAppointmentDate', 'N/A'))}")

        print(f"\n{color_text('Vehicle Status:', '94')}")
        print(f"{color_text('- Vehicle Odometer:', '94')} {order_info.get('vehicleOdometer', 'N/A')} {order_info.get('vehicleOdometerType', 'N/A')}")

        print(f"\n{color_text('Delivery Information:', '94')}")
        print(f"{color_text('- Routing Location:', '94')} {order_info.get('vehicleRoutingLocation', 'N/A')} ({TeslaStore(order_info.get('vehicleRoutingLocation', 0)).label})")
        print(f"{color_text('- Delivery Center:', '94')} {scheduling.get('deliveryAddressTitle', 'N/A')}")
        print(f"{color_text('- Delivery Window:', '94')} {scheduling.get('deliveryWindowDisplay', 'N/A')}")
        print(f"{color_text('- ETA to Delivery Center:', '94')} {final_payment_data.get('etaToDeliveryCenter', 'N/A')}")
        print(f"{color_text('- Delivery Appointment:', '94')} {scheduling.get('apptDateTimeAddressStr', 'N/A')}")

        if DETAILS_MODE:
            print(f"\n{color_text('Financing Information:', '94')}")
            financing_details = final_payment_data.get('financingDetails') or {}
            order_type = financing_details.get('orderType')
            tesla_finance_details = financing_details.get('teslaFinanceDetails') or {}

            # Handle cash purchases where no financing data is present
            if order_type == 'CASH' or not final_payment_data.get('financingIntent'):
                print(f"{color_text('- Payment Type:', '94')} Cash")
                payment_details = final_payment_data.get('paymentDetails') or []
                if payment_details:
                    first_payment = payment_details[0]
                    amount_paid = first_payment.get('amountPaid', 'N/A')
                    payment_type = first_payment.get('paymentType', 'N/A')
                    print(f"{color_text('- Amount Paid:', '94')} {amount_paid}")
                    print(f"{color_text('- Payment Method:', '94')} {payment_type}")
                account_balance = final_payment_data.get('accountBalance')
                if account_balance is not None:
                    print(f"{color_text('- Account Balance:', '94')} {account_balance}")
                amount_due = final_payment_data.get('amountDue')
                if amount_due is not None:
                    print(f"{color_text('- Amount Due:', '94')} {amount_due}")
            else:
                finance_product = financing_details.get('financialProductType', 'N/A')
                print(f"{color_text('- Finance Product:', '94')} {finance_product}")
                finance_partner = tesla_finance_details.get('financePartnerName', 'N/A')
                print(f"{color_text('- Finance Partner:', '94')} {finance_partner}")
                monthly_payment = tesla_finance_details.get('monthlyPayment')
                if monthly_payment is not None:
                    print(f"{color_text('- Monthly Payment:', '94')} {monthly_payment}")
                term_months = tesla_finance_details.get('termsInMonths')
                if term_months is not None:
                    print(f"{color_text('- Term (months):', '94')} {term_months}")
                interest_rate = tesla_finance_details.get('interestRate')
                if interest_rate is not None:
                    print(f"{color_text('- Interest Rate:', '94')} {interest_rate} %")
                mileage = tesla_finance_details.get('mileage')
                if mileage is not None:
                    print(f"{color_text('- Range per Year:', '94')} {mileage}")
                financed_amount = final_payment_data.get('amountDueFinancier')
                if financed_amount is not None:
                    print(f"{color_text('- Financed Amount:', '94')} {financed_amount}")
                approved_amount = tesla_finance_details.get('approvedLoanAmount')
                if approved_amount is not None:
                    print(f"{color_text('- Approved Amount:', '94')} {approved_amount}")

        print(f"{'-'*45}\n")

    print_history(load_history_from_file())

    run_update_check()

    print(f"\n{color_text('try --help for showing the new features, that may be interesting for you =)', '94')}")


 # Main script logic
if CACHED_MODE:
    cached_orders = load_orders_from_file()
    if cached_orders:
        if STATUS_MODE:
            print("0")
        else:
            display_orders(cached_orders)
    else:
        if STATUS_MODE:
            print("-1")
        else:
            print(color_text(f"No cached orders found in '{ORDERS_FILE}'", '91'))
    sys.exit(0)

if not STATUS_MODE:
    print(color_text("\n> Start retrieving the information. Please be patient...\n", '94'))

code_verifier, code_challenge = generate_code_verifier_and_challenge()

if os.path.exists(TOKEN_FILE):
    try:
        token_file = load_tokens_from_file()
        access_token = token_file['access_token']
        refresh_token = token_file['refresh_token']

        if not is_token_valid(access_token):
            if not STATUS_MODE:
                print(color_text("> Access token is not valid. Refreshing tokens...", '94'))
            token_response = refresh_tokens(refresh_token)
            access_token = token_response['access_token']
            # refresh access token in file
            token_file['access_token'] = access_token
            save_tokens_to_file(token_file)

    except (json.JSONDecodeError, KeyError) as e:
        if not STATUS_MODE:
            print(color_text("> Error loading tokens from file. Re-authenticating...", '94'))
            token_response = exchange_code_for_tokens(get_auth_code())
            access_token = token_response['access_token']
            refresh_token = token_response['refresh_token']
            save_tokens_to_file(token_response)
        else:
            print(-1)
            sys.exit(0)

else:
    if not STATUS_MODE:
        token_response = exchange_code_for_tokens(get_auth_code())
        access_token = token_response['access_token']
        refresh_token = token_response['refresh_token']
        if input(color_text("Would you like to save the tokens to a file in the current directory for use in future requests? (y/n): ", '93')).lower() == 'y':
            save_tokens_to_file(token_response)
    else:
        print(-1)
        sys.exit(0)
old_orders = load_orders_from_file()
new_orders = retrieve_orders(access_token)

# Retrieve detailed order information
detailed_new_orders = []
for order in new_orders:
    order_id = order['referenceNumber']
    order_details = get_order_details(order_id, access_token)
    
    if not order_details or not order_details.get('tasks'):
        print(color_text("\nError: Received empty response from Tesla API. Please try again later.", '91'))
        if STATUS_MODE:
            print("-1")
        sys.exit(1)

    detailed_order = {
        'order': order,
        'details': order_details
    }
    detailed_new_orders.append(detailed_order)

if old_orders:
    differences = compare_orders(old_orders, detailed_new_orders)
    if differences:
        if STATUS_MODE:
            print("1")
        save_orders_to_file(detailed_new_orders)
        history = load_history_from_file()
        history.append({
            'timestamp': TODAY,
            'changes': differences
        })
        save_history_to_file(history)
    else:
        if STATUS_MODE:
            print("0")

else:
    if STATUS_MODE:
        print("-1")
    else:
        # ask user if they want to save the new orders to a file for comparison next time
        if input(color_text("Would you like to save the order information to a file for future comparison? (y/n): ", '93')).lower() == 'y':
            save_orders_to_file(detailed_new_orders)

if STATUS_MODE:
    sys.exit(0)

display_orders(detailed_new_orders)
