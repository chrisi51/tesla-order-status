## Download
Download the complete projekt. 
If you don't know how to do so, just follow that link: https://github.com/chrisi51/tesla-order-status/archive/refs/heads/main.zip 

Don't try to just run single scripts without the context of the entire projekt =)

## Installation

To run the script, you need to install python3 for your operating system.

https://www.python.org/downloads/

### General
Then you need to install the additional libraries by running:
```sh
pip install requests pyperclip
```

- requests: for the api calls (required)
- pyperclip: for copying share output to the clipboard automatically (optional)
- 
### MacOS
On MacOS it may be better to create a virtual environment:
```sh
# creating the environment
python3 -m venv .venv
# using the environment
source .venv/bin/activate
# installing dependency only in the environment instead of globally
python3 -m pip install requests pyperclip
```

## Usage
Then you can run the script by running:
```sh
python3 tesla_order_status.py
```
### Optional flags:
```sh
python3 tesla_order_status.py --help
```
#### Output Modes
Only one of the options can be used at a time.
- `--details` show additional information such as financing details.
- `--share` hide personal data like order ID and VIN for sharing. the history is reduced to date and status changes.
- `--status` only report whether the order information has changed since the last run. no login happens, so tesla_tokens.json have to be present already. token will get refreshed if necessary.
  - 0 => no changes
  - 1 => changes detected
  - 2 => pending updates
  - -1 => error ... you better run the script once without any params to make sure, it is working. Possibly the api token is invalid or there is no tesla_orders.json already
    
Note: A share-friendly version of the output is always copied to your clipboard when `pyperclip` is installed. Use `--share` if you also want to see this anonymized output in the console.
#### Work Modes
can be combined with Output Modes
  - `--cached` use locally cached order data without performing any API requests. Useful combined with `--share` to get a share friendly output without polling API again.

## Configuration
### General Settings
The script stores the configuration in `data/private/settings.json`. You can change the settings on your own risk.
If the config becomes invalid, it will be reset to the default values.
### Option Codes
In the folder `option-codes` all known tesla option codes are stored. You can put in your own json files to extend the list. Files get loaded in alphabetic order and last occurence of any option codes win.

## History
The script stores the latest order information in `tesla_orders.json` and keeps a change log in `tesla_order_history.json`. Each time a difference is detected (for example a VIN assignment), the change is appended to the history file and displayed after the current status.
The Order Information screen will always show you the current data but below that you will see the history of your runs with changing data. 

## Issues
If you have any issues, running the script or getting error messages, pleas feel free to ask for help in the [isses](https://github.com/chrisi51/tesla-order-status/issues) section or pm me at the [tff-forum](https://tff-forum.de/u/chrisi51/summary)

## Preview

#### Order Information
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

#### Timeline
```
Order Timeline:
- 2025-08-07: Reservation
- 2025-08-07: Order Booked
- 2025-08-07: Delivery Window: 6 September - 30 September
- 2025-08-23: new Delivery Window: 10 September - 30 September
```

#### Change History
```
Change History:
2025-08-19: ≠ 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Maximilian Mustermann -> Max Mustermann
2025-08-19: ≠ 0.details.tasks.deliveryDetails.regData.orderDetails.vin: None -> 131232
2025-08-19: + 0.details.tasks.deliveryDetails.regData.orderDetails.userId: 10000000
2025-08-19: - 0.details.tasks.deliveryDetails.regData.orderDetails.ritzbitz
```

#### In SHARED_MODE (`--share`) you get a very compact output:
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

- a randomly generated fingerprint that identifies your installation (not tied to your identity)
- for each tracked order: a pseudonymized order reference number and the associated Tesla model
- which command line flags were used (e.g. `--details`, `--share`, `--status`, `--cached`)

### How is your data protected?

- **No personal data** such as VINs, names, email addresses, tokens, credentials or raw order IDs ever leave your machine.
- Order IDs are **irreversibly pseudonymized** locally using a secret-based HMAC before transmission. Even if someone had access to the data, it cannot be reversed into the original ID.
- The installation fingerprint is just a random string generated once on your system. It contains no information about your device or account.
- All traffic is sent over encrypted HTTPS.
- Data is used exclusively in aggregate to understand general usage patterns, not to track individual users.

### Controlling telemetry

You are always in control: telemetry is opt-in. Consent is requested on first run, and you can disable or revoke it at any time by editing the configuration file (`data/private/settings.json`) and setting `"telemetry-consent": false`.


## Disclaimer
- the script is working on your host
- - no connection to me is done in any way at any time unless you explicitly allow telemetry as described above
- you need to login via browser and return the resulting url to the script to extract the login token which is used for tha api
- the script just uses the token to work with for the moment
- with your permission the script stores the token on your harddisk

## Support
If you want to support me, you can use my link on your next tesla order =)
https://ts.la/christian906959

as this is a fork i have to say thx @ https://github.com/niklaswa/tesla-order-status for the script
