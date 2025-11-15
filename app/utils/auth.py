import os
import base64
import hashlib
import json
import time
import urllib.parse
import webbrowser
import requests
import sys
from app.config import TOKEN_FILE
from app.utils.colors import color_text
from app.utils.connection import request_with_retry
from app.utils.helpers import exit_with_status
from app.utils.locale import t
from app.utils.params import STATUS_MODE

CLIENT_ID = 'ownerapi'
REDIRECT_URI = 'https://auth.tesla.com/void/callback'
AUTH_URL = 'https://auth.tesla.com/oauth2/v3/authorize'
TOKEN_URL = 'https://auth.tesla.com/oauth2/v3/token'
SCOPE = 'openid email offline_access'
CODE_CHALLENGE_METHOD = 'S256'
STATE = os.urandom(16).hex()


def _generate_code_verifier_and_challenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(
        b'=').decode('utf-8')
    return code_verifier, code_challenge


def _get_auth_code(code_challenge: str):
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
    print(color_text(t("To retrieve your order status, you need to authenticate with your Tesla account."), '93'))
    message_parts = [
        color_text(t("A browser window will open with the Tesla login page. After logging in you will likely see a"), 93),
        color_text(t('\"Page Not Found\"'), 91),
        color_text(t("page."), 93),
        color_text(t("That is CORRECT!"), 91),
    ]
    print(" ".join(message_parts))
    print(color_text(t("Copy the full URL of that page and return here. The authentication happens only between you and Tesla; no data leaves your system."), '93'))
    if input(color_text(t("Proceed to open the login page? (y/n): "), '93')).lower() != 'y':
        print(color_text(t("Authentication cancelled."), '91'))
        sys.exit(0)
    try:
        if not webbrowser.open(auth_url):
            print(color_text(t("No GUI detected. Open this URL manually:"), 91))
            print(f"{auth_url}")
    except Exception:
        print(color_text(t("No GUI detected. Open this URL manually:"), 91))
        print(f"{auth_url}")
    redirected_url = input(color_text(t("Please enter the redirected URL here: "), '93'))
    parsed_url = urllib.parse.urlparse(redirected_url)
    params = urllib.parse.parse_qs(parsed_url.query)
    code = params.get('code')
    if not code:
        exit_with_status(t("No authentication code found in the redirected URL."))
    return code[0]

def _exchange_code_for_tokens(auth_code,code_verifier):
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier,
    }
    response = request_with_retry(TOKEN_URL, None, token_data)
    return response.json()


def _save_tokens_to_file(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)
    if not STATUS_MODE:
        print(color_text(t("> Tokens saved to '{file}'").format(file=TOKEN_FILE), '94'))


def _load_tokens_from_file():
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)


def _is_token_valid(access_token):
    jwt_decoded = json.loads(base64.b64decode(access_token.split('.')[1] + '==').decode('utf-8'))
    return jwt_decoded['exp'] > time.time()


def _refresh_tokens(refresh_token):
    token_data = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'refresh_token': refresh_token,
    }
    response = request_with_retry(TOKEN_URL, None, token_data)
    return response.json()



# ---------------------------
# Main-Logic
# ---------------------------
def main() -> str:
    code_verifier, code_challenge = _generate_code_verifier_and_challenge()

    if os.path.exists(TOKEN_FILE):
        try:
            token_file = _load_tokens_from_file()
            access_token = token_file['access_token']
            refresh_token = token_file['refresh_token']

            if not _is_token_valid(access_token):
                if not STATUS_MODE:
                    print(color_text(t("> Access token is not valid anymore. Refreshing tokens..."), '94'))
                token_response = _refresh_tokens(refresh_token)
                access_token = token_response['access_token']
                # refresh access token in file
                token_file['access_token'] = access_token
                _save_tokens_to_file(token_file)

        except (json.JSONDecodeError, KeyError) as e:
            if not STATUS_MODE:
                print(color_text(t("> Error loading tokens from file. Re-authenticating..."), '94'))
                token_response = _exchange_code_for_tokens(_get_auth_code(code_challenge), code_verifier)
                access_token = token_response['access_token']
                _save_tokens_to_file(token_response)
            else:
                print(-1)
                sys.exit(0)

    else:
        if not STATUS_MODE:
            token_response = _exchange_code_for_tokens(_get_auth_code(code_challenge), code_verifier)
            access_token = token_response['access_token']
            if input(color_text(t("Would you like to save the tokens to a file in the current directory for use in future requests? (y/n): "), '93')).lower() == 'y':
                _save_tokens_to_file(token_response)
        else:
            print(-1)
            sys.exit(0)

    return access_token