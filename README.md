[![Active](https://img.shields.io/badge/status-actively_maintained-darkgreen)](#)  [![Python](https://img.shields.io/badge/python-3.x-blue?logo=python)](#)  [![Platform](https://img.shields.io/badge/platform-cross--platform-lightgrey)](#) [![Telemetry](https://img.shields.io/badge/telemetry-opt--in-darkgreen)](#) [![Privacy](https://img.shields.io/badge/privacy-100%25_local-darkgreen)](#)

[![Stars](https://img.shields.io/github/stars/chrisi51/tesla-order-status?style=social)](https://github.com/chrisi51/tesla-order-status/stargazers) [![Forks](https://img.shields.io/github/forks/chrisi51/tesla-order-status?style=social)](https://github.com/chrisi51/tesla-order-status/network/members) [![Issues](https://img.shields.io/github/issues/chrisi51/tesla-order-status?style=social)](https://github.com/chrisi51/tesla-order-status/issues)

[![Chat](https://img.shields.io/badge/chat-Community-blue?logo=wechat)](https://chat.tesla-order-status-tracker.de) [![Coffee](https://img.shields.io/badge/buy_me-a_coffee-cc0000?logo=buymeacoffee&logoColor=white)](https://www.paypal.com/paypalme/chrisi51) [![Referral](https://img.shields.io/badge/support-via_Tesla_referral-cc0000?logo=tesla&logoColor=white)](https://ts.la/christian906959)

> Prefer reading in German?<br>
> [Hier geht’s zur deutschen Version des README](README_DE.md)

# Tesla Order Status Tracker (TOST) 🚗📦
Stay in control of your Tesla order from the moment you place it until delivery. This open-source Python tool gives you direct access to the Tesla API so you always know what is happening with your vehicle.
> 🖥️ Prefer a GUI? check my TOST app: https://www.tesla-order-status-tracker.de

## Table of Contents
1. [Why You'll Love It](#why-youll-love-it)
2. [Get Started](#get-started)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [History & Preview](#history--preview)
7. [Telemetry](#telemetry)
8. [Disclaimer](#disclaimer)
9. [Support & Contact](#support--contact)

## Why You'll Love It
- 🔍 **Direct Tesla API connection**: Get the latest order information without any detours.
- 🧾 **Display of important details**: Vehicle options, production and delivery progress.
- 🕒 **History at a glance**: Every change (e.g. VIN allocation) is documented locally.
- 📋 **One‑click share mode**: Anonymized clipboard for forums and social media
- 🧩 **Modular & expandable**: Option codes, languages and features can be flexibly expanded.
- 🔐 **Privacy-focused**: Tokens and settings remain on your device – telemetry is completely optional.

The goal is to give users more transparency and control over the ordering process – without depending on external services.

## 🚀 Quick Links
- 💬 Community & Support-Chat: https://chat.tesla-order-status-tracker.de
- ☕ Support via PayPal: https://www.paypal.com/paypalme/chrisi51
- 🚗 Order a Tesla and support me: https://ts.la/christian906959
- 📦 Direct download as ZIP: https://github.com/chrisi51/tesla-order-status/archive/refs/heads/main.zip
- 🖥️ GUI version: https://www.tesla-order-status-tracker.de

## Get Started
Download the complete project to your machine. If you are unsure how, you can grab the ZIP archive directly from GitHub: https://github.com/chrisi51/tesla-order-status/archive/refs/heads/main.zip
> ⚠️ Do not run single scripts without the rest of the repository. Everything is meant to work together.

## Installation

1. Install [Python 3](https://www.python.org/downloads/) for your operating system.
2. Install the required dependencies:
```sh
pip install requests pyperclip
```
- requests: for the api calls (required)
- pyperclip: for copying share output to the clipboard automatically (optional)

### macOS Tip
For a clean setup, create a virtual environment before installing dependencies:
```sh
# create the environment
python3 -m venv .venv
# activate it
source .venv/bin/activate
# install dependencies just for this project
python3 -m pip install requests pyperclip
```

## Usage
Run the main script to fetch and display your order details:
```sh
python3 tesla_order_status.py
```
### Optional flags:
Get an overview of all command-line options:
```sh
python3 tesla_order_status.py --help
```
#### Output Modes
Only one of the options can be used at a time.
- `--all` display every available key in your history (verbose output)
- `--details` show additional information such as financing details.
- `--share` hide personal data like order ID and VIN for sharing. limits output to dates and status changes.
- `--status` only report whether the order information has changed since the last run. no login happens, so tesla_tokens.json have to be present already. token will get refreshed if necessary.
  - 0 => no changes
  - 1 => changes detected
  - 2 => pending updates
  - -1 => error ... you better run the script once without any params to make sure, it is working. Possibly the api token is invalid or there is no tesla_orders.json already
    
> 💡 Whenever `pyperclip` is installed, a share-friendly summary is copied to your clipboard. `--share` is not needed anymore for that.

#### Work Modes
Work modes can be combined with any output mode:
- `--cached` – reuse locally cached order data without calling the API (perfect with `--share`)
- Automatic caching activates when you run the script again within one minute of a successful API request, keeping Tesla happy with fewer calls.

#### Order Filters
- `--order <referenceNumber>` – refresh every order in the background but only print the selected one (e.g. `--order RN123456`).

## Configuration
### General Settings
The script stores the configuration in `data/private/settings.json`. Feel free to tweak it—if something breaks, the script falls back to default values.

On the first run the script detects your system language and stores it as `language` in the settings file. Edit this entry to override the language manually. If no translation is available yet, the setting is simply ignored until one becomes available.

### Option Codes
Known Tesla option codes are now downloaded on demand from
`https://www.tesla-order-status-tracker.de/scripts/php/fetch/option_codes.php` and
cached locally for 24 hours. The cache lives in `data/private/option_codes_cache.json`
and is refreshed automatically whenever it expires. You can still drop custom JSON
files into `data/public/option-codes` to override or extend the remote data; local
entries win if both define the same option code.

## History & Preview
The script stores the latest order information in `tesla_orders.json` and keeps a change log in `tesla_order_history.json`. Every detected difference—like a VIN assignment—is appended to the history file and displayed after the current status. The "Order Information" section always shows live data first, followed by historical changes.

### Order Information
```
---------------------------------------------
              ORDER INFORMATION
---------------------------------------------
Order Details:
- Order ID: RN100000000
- Status: BOOKED
- Model: my
- VIN: N/A

Configuration Options:
- APBS: Autopilot base features
- APPB: Enhanced Autopilot
- CPF0: Standard Connectivity
- IPW8: Interior: Black and White
- MDLY: Model Y
- MTY47: Model Y Long Range Dual Motor
- PPSB: Paint: Deep Blue Metallic
- SC04: Pay-per-use Supercharging
- STY5S: Seating: 5 Seat Interior
- WY19P: 19" Crossflow wheels (Model Y Juniper)

Delivery Information:
- Routing Location: None (N/A)
- Delivery Center: Tesla Delivery & Used Car Center Hanau Holzpark
- Delivery Window: 6 September - 30 September
- ETA to Delivery Center: None
- Delivery Appointment: None

Financing Information:
- Finance Product: OPERATIONAL_LEASE
- Finance Partner: Santander Consumer Leasing GmbH
- Monthly Payment: 683.35
- Term (months): 48
- Interest Rate: 6.95 %
- Range per Year: 10000
- Financed Amount: 60270
- Approved Amount: 60270
---------------------------------------------
```

### Timeline
```
Order Timeline:
- 2025-08-07: Reservation
- 2025-08-07: Order Booked
- 2025-08-07: Delivery Window: 6 September - 30 September
- 2025-08-23: new Delivery Window: 10 September - 30 September
```

### Change History
```
Change History:
2025-08-19: ≠ 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Maximilian Mustermann -> Max Mustermann
2025-08-19: ≠ 0.details.tasks.deliveryDetails.regData.orderDetails.vin: None -> 131232
2025-08-19: + 0.details.tasks.deliveryDetails.regData.orderDetails.userId: 10000000
2025-08-19: - 0.details.tasks.deliveryDetails.regData.orderDetails.ritzbitz
```

#### SHARED MODE example:
```
---
Order Details:
- Model Y - AWD LR / Deep Blue / White
- Tesla Delivery & Used Car Center Hanau Holzpark

Order Timeline:
- 2025-08-07: Reservation
- 2025-08-07: Order Booked
- 2025-08-07: Delivery Window: 6 September - 30 September
- 2025-08-23: new Delivery Window: 10 September - 30 September
```

## Telemetry
To better understand how the tool is used and to improve future development, the script can optionally send **anonymous usage statistics**.
On the very first launch you will be asked for consent. If you decline, nothing is sent. Declining has no negative impact other than not contributing to usage statistics.

### What information is sent?

- A randomly generated fingerprint that identifies your installation (not tied to your identity)
- For each tracked order: a pseudonymized order reference number and the associated Tesla model
- Which command line flags were used (e.g. `--details`, `--share`, `--status`, `--cached`)
- The operating system language (e.g. `en_US`)

### How is your data protected?
- **No personal data** such as VINs, names, email addresses, tokens, credentials or raw order IDs ever leave your machine.
- Order IDs are **irreversibly pseudonymized** locally using a secret-based HMAC before transmission. Even if someone had access to the data, it cannot be reversed into the original ID.
- The installation fingerprint is just a random string generated once on your system. It contains no information about your device or account.
- All traffic is sent over encrypted HTTPS.
- Data is used exclusively in aggregate to understand general usage patterns, not to track individual users.

### Controlling telemetry
You are always in control: telemetry is opt-in. Consent is requested on first run, and you can disable or revoke it at any time by editing the configuration file (`data/private/settings.json`) and setting `"telemetry-consent": false`.

## Issues
If you have any issues, running the script or getting error messages, pleas feel free to ask for help in the [issues](https://github.com/chrisi51/tesla-order-status/issues) section or pm me at the [tff-forum](https://tff-forum.de/u/chrisi51/summary)


## Disclaimer
- The script runs locally on your machine.
- No connection to me is made at any time unless you explicitly allow telemetry as described above.
- You need to log in via browser and return the resulting URL to the script to extract the login token used for the API.
- The script only uses the token to work with for the current session.
- With your permission the script stores the token on your hard disk.

## Support & Contact
If you want to support the project, you can use my link on your next Tesla order: https://ts.la/christian906959

Or just buy me a coffee: https://www.paypal.com/paypalme/chrisi51

As this is a fork I have to say thanks to https://github.com/niklaswa/tesla-order-status for the initial script.

Come say hi in the community chat: https://chat.tesla-order-status-tracker.de
