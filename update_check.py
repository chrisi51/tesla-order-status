#!/usr/bin/env python3
# coding: utf-8
"""
check_files_fixed_list.py

Die zu prüfenden Dateien stehen in FILES_TO_CHECK (Array).
Vergleicht das neueste mtime aus dieser Liste mit dem letzten Commit
des festen Atom-Feeds:
  https://github.com/chrisi51/tesla-order-status/commits/main.atom

Exitcodes:
  0 -> alles aktuell
  1 -> Repo hat neueren Commit (Update available)
  2 -> Fehler (Feed laden oder keine gültigen Dateien)
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
import requests
import sys

# ---------------------------
# Konfiguration: hier die Dateien eintragen (relative oder absolute Pfade)
# ---------------------------
FILES_TO_CHECK: List[str] = [
    "tesla_order_status.py",
    "tesla_stores.py",
    "option-codes/000_teslahunt.json",
    "option-codes/050_directlease.json",
    "option-codes/100_chrisi51.json",
    "update_check.py"
]

FEED_URL = "https://github.com/chrisi51/tesla-order-status"
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
        raise ValueError("Kein <entry> im Atom-Feed gefunden")
    updated = entry.find('atom:updated', ns)
    if updated is None or not updated.text:
        raise ValueError("Kein <updated>-Tag im ersten <entry> gefunden")
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
    """Gibt mtime als timezone-aware UTC datetime zurück oder None, wenn nicht existent / kein File."""
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

# ---------------------------
# Main-Logic
# ---------------------------
def main() -> int:
    # Lade Feed
    try:
        last_commit_dt = get_latest_updated_from_atom(f"{FEED_URL}/commits/main.atom")
    except Exception as e:
        print(f"[FEHLER] Atom-Feed konnte nicht geladen werden: {e}", file=sys.stderr)
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
        print("[FEHLER] Keine gültigen Dateien in FILES_TO_CHECK gefunden.", file=sys.stderr)

    if errors > 0:
        print("[PACKAGE CORRUPT]")
        print("Your Project is missing some files. Please download the complete project.")
        print(f"Download: {FEED_URL}/archive/refs/heads/main.zip")
        return 2

    # Neuestes (jüngstes) mtime unter den angegebenen Dateien
    newest_path, newest_dt = max(mtimes.items(), key=lambda kv: kv[1])

    if last_commit_dt > newest_dt:
        print("[UPDATE AVAILABLE]")
        print(f"Last Update: {human_delta(last_commit_dt, newest_dt)}")
        print(f"Download: {FEED_URL}/archive/refs/heads/main.zip")
        return 1
    else:
        return 0

if __name__ == "__main__":
    code = main()
    sys.exit(code)
