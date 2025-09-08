import argparse

parser = argparse.ArgumentParser(description="Retrieve Tesla order status.")
group = parser.add_mutually_exclusive_group()
group.add_argument("--details", action="store_true", help="Show additional details such as financing information.")
group.add_argument("--share", action="store_true", help="Hide personal data like Order ID and VIN for sharing.")
group.add_argument("--status", action="store_true", help="Only report whether there are changes since the last check.")
parser.add_argument("--cached", action="store_true", help="Use locally cached data without contacting the API.")

_args, _ = parser.parse_known_args()

DETAILS_MODE = _args.details
SHARE_MODE = _args.share
STATUS_MODE = _args.status
CACHED_MODE = _args.cached