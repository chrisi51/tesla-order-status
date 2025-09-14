#!/usr/bin/env python3
"""Download and apply the latest project files without external dependencies.

This script can be used as a fallback update mechanism if the regular
auto-updater fails. It fetches the current ``main`` branch as a zip
archive from GitHub, extracts it and copies the contents over the local
installation.
"""

import shutil
import sys
import traceback
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ZIP_URL = "https://github.com/chrisi51/tesla-order-status/archive/refs/heads/main.zip"


def main() -> None:
    print("This script will just overwrite your installation with the most recent version.")
    print("It can be used, if your installation and even the autoupdater is broken to fix the installation.")
    print("As long as the autoupdater is working, there is no need, to use this script but it also should not damage your installation in any way.")
    answer = input(
        "You want to proceed the hotfix update? (y/n): "
    ).strip().lower()
    if answer != "y":
        print("\nHotfix canceled...")
        sys.exit(1)


    print("\nDownloading latest files...")
    try:
        with urllib.request.urlopen(ZIP_URL, timeout=10) as resp:
            data = resp.read()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            zip_path = tmp_path / "repo.zip"
            zip_path.write_bytes(data)

            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp_path)

            extracted_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
            for item in extracted_dir.iterdir():
                target = Path('.') / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
        print("...Hotfix applied. Please rerun tesla_order_status.py")
        print("\nIf the problem persists, please create an issue including the complete output of tesla_order_status.py")
        print("GitHub Issues: https://github.com/chrisi51/tesla-order-status/issues")

    except Exception as e:  # noqa: BLE001 - best effort, minimal deps
        print(f"...Hotfix failed: {e}\n")
        traceback.print_exc()
        print("\nIf the problem persists, please create an issue including the complete output of hotfix.py")
        print("GitHub Issues: https://github.com/chrisi51/tesla-order-status/issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
