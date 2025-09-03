#!/usr/bin/env python3
# coding: utf-8
"""
check_files_fixed_list.py

The files to check are stored in FILES_TO_CHECK (array).
Compares the newest mtime from this list with the last commit
of the fixed Atom feed:
  https://github.com/chrisi51/tesla-order-status/commits/main.atom

Exit codes:
  0 -> everything up to date
  1 -> Repo has newer commit (Update available)
  2 -> Error (Feed loading or no valid files)
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
import requests
import sys
import shutil
import tempfile

from app.config import APP_DIR, BASE_DIR, PRIVATE_DIR, OPTION_CODES_FOLDER, TESLA_STORES_FILE


# ---------------------------
# files to check
# ---------------------------
FILES_TO_CHECK: List[Path] = [
    BASE_DIR / "tesla_order_status.py",
    TESLA_STORES_FILE,
    OPTION_CODES_FOLDER / "000_teslahunt.json",
    OPTION_CODES_FOLDER / "050_directlease.json",
    OPTION_CODES_FOLDER / "100_chrisi51.json",
    APP_DIR / "config.py",
    APP_DIR / "update_check.py",
    APP_DIR / "utils" / "auth.py",
    APP_DIR / "utils" / "colors.py",
    APP_DIR / "utils" / "connection.py",
    APP_DIR / "utils" / "helpers.py",
    APP_DIR / "utils" / "history.py",
    APP_DIR / "utils" / "migration.py",
    APP_DIR / "utils" / "orders.py",
    APP_DIR / "utils" / "params.py",
    APP_DIR / "utils" / "timeline.py",
    APP_DIR / "migrations" / "2025-08-23-history.py",
    APP_DIR / "migrations" / "2025-08-30-datafolders.py",
]

BRANCH = "main"
FEED_URL = "https://github.com/chrisi51/tesla-order-status"
ZIP_URL = f"{FEED_URL}/archive/refs/heads/{BRANCH}.zip"
REQUEST_TIMEOUT = 10  # Sekunden

# ---------------------------
# Helfer
# ---------------------------
def get_latest_updated_from_atom(url: str, timeout: int = REQUEST_TIMEOUT) -> datetime:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entry = root.find('atom:entry', ns)
    if entry is None:
        raise ValueError("No <entry> in Atom-Feed found")
    updated = entry.find('atom:updated', ns)
    if updated is None or not updated.text:
        raise ValueError("No <updated> tag found in first <entry>")
    updated_text = updated.text.strip()
    # "2024-07-01T12:34:56Z" -> make ISO compatible with fromisoformat
    if updated_text.endswith('Z'):
        updated_text = updated_text[:-1] + "+00:00"
    dt = datetime.fromisoformat(updated_text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt

def mtime_of_file(path: Path) -> Optional[datetime]:
    """Returns mtime as timezone-aware UTC datetime or None if non-existent / not a file."""
    try:
        if not path.exists():
            return None
        if not path.is_file():
            return None
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None

def human_delta(a: datetime, b: datetime) -> str:
    delta = a - b
    days = delta.days
    secs = delta.seconds
    hrs = secs // 3600
    mins = (secs % 3600) // 60
    return f"{days}d {hrs}h {mins}m"

def download_and_extract_zip(url: str = ZIP_URL, timeout: int = REQUEST_TIMEOUT) -> bool:
    """
    Download and extract a zip archive to the current directory.
    Existing files will be overwritten.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "repo.zip"
            with open(zip_path, "wb") as f:
                f.write(resp.content)
            shutil.unpack_archive(str(zip_path), tmpdir)
            extracted_dir = next(p for p in Path(tmpdir).iterdir() if p.is_dir())
            for item in extracted_dir.iterdir():
                target = Path(".") / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
        print("[UPDATED] Files successfully downloaded and extracted.")
        print("Please restart the app.")
        sys.exit()
        return True
    except Exception as e:
        print(f"[ERROR] Update failed: {e}")
        return False


def ask_for_update():
    print(f"Download: {ZIP_URL}")
    answer = input("Do you want to download and extract the update? (y/n): ").strip().lower()
    if answer == "y":
        if download_and_extract_zip():
            return 0
        return 1
    return 1

# ---------------------------
# Main-Logic
# ---------------------------
def main() -> int:
    # Lade Feed
    try:
        last_commit_dt = get_latest_updated_from_atom(f"{FEED_URL}/commits/{BRANCH}.atom")
    except Exception as e:
        print(f"[ERROR] Could not load Atom feed: {e}", file=sys.stderr)
        return 2

    errors = 0
    # Prüfe die festgelegten Dateien (keine Ordner-Recursion)
    mtimes: Dict[str, datetime] = {}
    for p in FILES_TO_CHECK:
        path = Path(p)
        m = mtime_of_file(path)
        if m is None:
            if not path.exists():
                errors += 1
                print(f"[WARN] File missing: {p}")
            else:
                errors += 1
                print(f"[WARN] Path is not a file and could not get read: {p} ")
            continue
        mtimes[p] = m

    if not mtimes:
        errors += 1
        print("[ERROR] No valid files found in FILES_TO_CHECK.", file=sys.stderr)
    if errors > 0:
        print("[PACKAGE CORRUPT]")
        print("Your Project is missing some files. Please download the complete project.")
        return ask_for_update()

    # Neuestes (jüngstes) mtime unter den angegebenen Dateien
    newest_path, newest_dt = max(mtimes.items(), key=lambda kv: kv[1])

    if last_commit_dt > newest_dt:
        print("[UPDATE AVAILABLE]")
        print(f"Last Update: {human_delta(last_commit_dt, newest_dt)} younger than your version =)")
        return ask_for_update()
    else:
        return 0

if __name__ == "__main__":
    code = main()
    sys.exit(code)
