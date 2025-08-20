## Download
Download the complete projekt. 
If you don't know how to do so, just follow that link: https://github.com/chrisi51/tesla-order-status/archive/refs/heads/main.zip 

Don't try to just run single scripts without the context of the entire projekt =)

## Installation

To run the script, you need to install python3 for your operating system.

https://www.python.org/downloads/

### General
Then you need to install the `requests` library by running:
```sh
pip install requests
```

### MacOS
On MacOS it may be better to create a virtual environment:
```sh
# creating the environment
python3 -m venv .venv
# using the environment
source .venv/bin/activate
# installing dependency only in the environment instead of globally
python3 -m pip install requests
```

## Usage
Then you can run the script by running:
```sh
python3 tesla_order_status.py
```

## Configuration
In the folder `option-codes` all known tesla option codes are stored. You can put in your own json files to extend the list. Files get loaded in alphabetic order and last occurence of any option codes win.

## History
The script stores the latest order information in `tesla_orders.json` and keeps a change log in `tesla_order_history.json`. Each time a difference is detected (for example a VIN assignment), the change is appended to the history file and displayed after the current status.
The Order Information screen will always show you the current data but below that you will see the history of your runs with changing data. 

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

Reservation Details:
- Reservation Date: 2025-08-07T12:00:00.000000
- Order Booked Date: 2025-08-07T12:00:00.000000

Vehicle Status:
- Vehicle Odometer: 30 KM

Delivery Information:
- Routing Location: None (N/A)
- Delivery Center: Tesla Delivery & Used Car Center Hanau Holzpark
- Delivery Window: 6 September - 30 September
- ETA to Delivery Center: None
- Delivery Appointment: None

Financing Information:
- Finance Partner: Santander Consumer Leasing GmbH
---------------------------------------------
```


#### Change History
```
Change History:
2025-08-19: - Order 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Maximilian Mustermann
2025-08-19: + Order 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Max Mustermann
2025-08-19: - Order 0.details.tasks.deliveryDetails.regData.orderDetails.vin: None
2025-08-19: + Order 0.details.tasks.deliveryDetails.regData.orderDetails.vin: 131232
2025-08-19: + Added key 'Order 0.details.tasks.deliveryDetails.regData.orderDetails.userId': 10000000
2025-08-19: - Removed key 'Order 0.details.tasks.deliveryDetails.regData.orderDetails.ritzbitz'
```
## Disclaimer
- the script is working on your host
- no connection to me is done in any way at any time
- you need to login via browser and return the resulting url to the script to extract the login token which is used for tha api
- the script just uses the token to work with for the moment
- with your permission the script stores the token on your harddisk

## Support
If you want to support me, you can use my link on your next tesla order =)
https://ts.la/christian906959

as this is a fork i have to say thx @ https://github.com/niklaswa/tesla-order-status for the script
