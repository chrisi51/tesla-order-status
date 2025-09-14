

from app.update_check import main as run_update_check
from app.utils.migration import main as run_all_migrations

# Run all migrations at startup
run_all_migrations()
run_update_check()



from app.config import cfg as Config
from app.utils.auth import main as run_tesla_auth
from app.utils.banner import display_banner
from app.utils.helpers import generate_token
from app.utils.orders import main as run_orders
from app.utils.params import STATUS_MODE
from app.utils.telemetry import ensure_telemetry_consent

if not Config.has("secret"):
    Config.set("secret", generate_token(32,None))

if not Config.has("fingerprint"):
    Config.set("fingerprint", generate_token(16,32))


ensure_telemetry_consent()
if not STATUS_MODE:
    display_banner()
access_token = run_tesla_auth()
run_orders(access_token)

