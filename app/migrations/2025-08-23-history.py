"""
Migration: 2025-08-23-history
- Migriert die History-Datei vom alten String-Deltaformat zu strukturierten Dict-Einträgen.
- Schaut zuerst in PRIVATE_DIR/tesla_order_history.json, dann (Fallback) in BASE_DIR/tesla_order_history.json.
- **Kein Verschieben/Kopieren** der Datei: wird, falls gefunden, *in-place* migriert.
- Idempotent: wenn schon migriert, passiert nix.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, List, Dict

from app.config import BASE_DIR, PRIVATE_DIR

def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _migrate_history_format(history: List[Dict[str, Any]]):
    if not history or not history[0].get("changes"):
        return history
    # Neuformat schon vorhanden?
    first_changes = history[0]["changes"]
    if first_changes and isinstance(first_changes[0], dict):
        return history

    migrated = []
    for entry in history:
        new_entry = {"timestamp": entry.get("timestamp"), "changes": []}
        changes = entry.get("changes", [])
        i = 0
        while i < len(changes):
            change = changes[i]
            if isinstance(change, dict):
                # Falls Mischformat vorkommt, einfach übernehmen
                new_entry["changes"].append(change)
                i += 1
                continue

            if change.startswith("+ Added key '"):
                m = re.match(r"\+ Added key '([^']+)': (.*)", change)
                if m:
                    key = m.group(1).replace('Order ', '', 1)
                    new_entry["changes"].append({
                        "operation": "added",
                        "key": key,
                        "value": m.group(2),
                    })
                i += 1
            elif change.startswith("- Removed key '"):
                m = re.match(r"- Removed key '([^']+)'", change)
                if m:
                    key = m.group(1).replace('Order ', '', 1)
                    new_entry["changes"].append({
                        "operation": "removed",
                        "key": key,
                        "old_value": None,
                    })
                i += 1
            elif change.startswith("+ Added order "):
                m = re.match(r"\+ Added order (\d+)", change)
                if m:
                    new_entry["changes"].append({
                        "operation": "added",
                        "key": m.group(1),
                    })
                i += 1
            elif change.startswith("- Removed order "):
                m = re.match(r"- Removed order (\d+)", change)
                if m:
                    new_entry["changes"].append({
                        "operation": "removed",
                        "key": m.group(1),
                    })
                i += 1
            elif change.startswith('- '):
                if i + 1 < len(changes) and isinstance(changes[i + 1], str) and changes[i + 1].startswith('+ '):
                    m_old = re.match(r"- ([^:]+): (.*)", change)
                    m_new = re.match(r"\+ ([^:]+): (.*)", changes[i + 1])
                    if m_old and m_new and m_old.group(1) == m_new.group(1):
                        key = m_old.group(1).replace('Order ', '', 1)
                        new_entry["changes"].append({
                            'operation': 'changed',
                            'key': key,
                            'old_value': m_old.group(2),
                            'value': m_new.group(2)
                        })
                        i += 2
                        continue
                i += 1
            else:
                i += 1
        migrated.append(new_entry)
    return migrated


def run() -> None:  # noqa: ARG001
    """Finde History-Datei in den bekannten Orten und migriere *in place*."""
    candidates = [
        BASE_DIR / "tesla_order_history.json",
        PRIVATE_DIR / "tesla_order_history.json",
    ]

    target_path = None
    for p in candidates:
        if p.exists():
            target_path = p
            break

    if target_path is None:
        return

    try:
        history = _load_json(target_path)
    except Exception:
        return

    migrated = _migrate_history_format(history)
    if migrated != history:
        _save_json(target_path, migrated)
