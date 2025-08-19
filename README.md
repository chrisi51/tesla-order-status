## Installation

To run the script, you need to install python3 for your operating system.

https://www.python.org/downloads/

Then you need to install the `requests` library by running:
```sh
pip install requests
```

Optional: Copy the script to a new directory, the script asks to save the tokens and order details in the current directory for reusing the tokens and for comparing the data with the last time you fetched the order details.

Then you can run the script by running:
```sh
python3 tesla_order_status.py
```

The script stores the latest order information in `tesla_orders.json` and keeps a change log in `tesla_order_history.json`. Each time a difference is detected (for example a VIN assignment), the change is appended to the history file and displayed after the current status.

During the summary, additional details such as the delivery center and financing partner are shown to provide more context.

In the folder `option-codes` all known tesla option codes are stored. You can put in your own json files to extend the list. Files get loaded in alphabetic order and last occurence of any option codes win.

## History
I tried to create a function, which will remember all changes between your runs. So if there is any change in a new run, it will get logged in a separate `tesla_order_history.json`. 
The Order Information screen will always show you the current data but below that you will see the history of your runs with changing data. 

## Preview

#### Main information
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


#### Change tracking
```
Change History:
2025-08-19: - Order 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Maximilian Mustermann
2025-08-19: + Order 0.details.tasks.deliveryDetails.regData.regDetails.company.address.careOf: Max Mustermann
2025-08-19: - Order 0.details.tasks.deliveryDetails.regData.orderDetails.vin: None
2025-08-19: + Order 0.details.tasks.deliveryDetails.regData.orderDetails.vin: 131232
2025-08-19: + Added key 'Order 0.details.tasks.deliveryDetails.regData.orderDetails.userId': 10000000
2025-08-19: - Removed key 'Order 0.details.tasks.deliveryDetails.regData.orderDetails.ritzbitz'
```
