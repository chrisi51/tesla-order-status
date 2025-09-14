#!/usr/bin/env python3
"""Entry point for the Tesla order status tool.

If anything goes wrong during startup, a hint is printed telling the
user to run the standalone ``hotfixer.py`` script which can update the
installation without additional dependencies.
"""

import sys
import traceback


def main() -> None:
    """Import and run the application modules."""
    from app.update_check import main as run_update_check
    from app.utils.migration import main as run_all_migrations
    from app.config import cfg as Config
    from app.utils.auth import main as run_tesla_auth
    from app.utils.banner import display_banner
    from app.utils.helpers import generate_token
    from app.utils.orders import main as run_orders
    from app.utils.params import STATUS_MODE
    from app.utils.telemetry import ensure_telemetry_consent

    # Run all migrations and check for updates at startup
    run_all_migrations()
    run_update_check()

    if not Config.has("secret"):
        Config.set("secret", generate_token(32, None))

    if not Config.has("fingerprint"):
        Config.set("fingerprint", generate_token(16, 32))

    ensure_telemetry_consent()
    if not STATUS_MODE:
        display_banner()
    access_token = run_tesla_auth()
    run_orders(access_token)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - catch-all for user guidance
        print(f"\n[ERROR] {e}\n")
        traceback.print_exc()
        print("\n\nYou can attempt to fix the installation by running:")
        print("hotfix.py instead of tesla_order_status.py")
        print("\nIf the problem persists, please create an issue including the complete output of tesla_order_status.py")
        print("GitHub Issues: https://github.com/chrisi51/tesla-order-status/issues")
        sys.exit(1)
