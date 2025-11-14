"""
Migration: 2025-11-12-history-reference
- Hebt die History-Datei auf das neue Format `{referenceNumber: [entries...]}` an.
- Bestimmt zu jedem Change die passende `referenceNumber`, schneidet den Index-Präfix vom Key ab
  und speichert die Änderungen gruppiert pro Order.
- Verwendet `tesla_orders.json`, um alte numerische Indizes den richtigen Referenzen zuzuordnen.
- Idempotent: Wenn die Datei bereits im neuen Dict-Format vorliegt, passiert nichts.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.config import ORDERS_FILE, HISTORY_FILE


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _extract_reference(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    order_payload = entry.get("order")
    if isinstance(order_payload, dict):
        ref = order_payload.get("referenceNumber")
        if ref:
            return str(ref)
    ref = entry.get("referenceNumber")
    if ref:
        return str(ref)
    return None


def _build_index_map() -> Dict[str, str]:
    if not ORDERS_FILE.exists():
        return {}
    try:
        orders_data = _load_json(ORDERS_FILE)
    except Exception:
        return {}

    mapping: Dict[str, str] = {}
    if isinstance(orders_data, list):
        for idx, entry in enumerate(orders_data):
            ref = _extract_reference(entry)
            if ref:
                mapping[str(idx)] = ref
    elif isinstance(orders_data, dict):
        for key, entry in orders_data.items():
            ref = _extract_reference(entry)
            if ref:
                mapping[str(key)] = ref
    return mapping


def _resolve_reference_and_key(change: Dict[str, Any], index_map: Dict[str, str]) -> Tuple[str | None, str]:
    if not isinstance(change, dict):
        return None, ""

    raw_key = change.get("key")
    key_str = raw_key if isinstance(raw_key, str) else ""

    if "." in key_str:
        prefix, remainder = key_str.split(".", 1)
    else:
        prefix, remainder = key_str, ""

    reference = change.get("order_reference")
    if reference is None and prefix:
        if prefix in index_map:
            reference = index_map[prefix]
        elif prefix.upper().startswith("RN"):
            reference = prefix
        elif prefix.isdigit():
            reference = prefix  # legacy fallback (numeric index)

    if reference is None:
        return None, key_str

    ref_str = str(reference)
    drop_prefix = False
    if prefix:
        if prefix == ref_str or prefix in index_map or prefix.upper().startswith("RN") or prefix.isdigit():
            drop_prefix = True
    normalized_key = remainder if drop_prefix else key_str
    return ref_str, normalized_key


def _migrate_history(history: List[Dict[str, Any]], index_map: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    grouped_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for entry in history:
        if not isinstance(entry, dict):
            continue
        timestamp = entry.get("timestamp")
        entry_changes = entry.get("changes", [])
        if not isinstance(entry_changes, list):
            continue

        per_reference: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for change in entry_changes:
            reference, key = _resolve_reference_and_key(change, index_map)
            if not reference:
                continue
            normalized_change = {
                "operation": change.get("operation"),
                "key": key,
                "value": change.get("value"),
                "old_value": change.get("old_value"),
            }
            per_reference[reference].append(normalized_change)

        for reference, changes in per_reference.items():
            if not changes:
                continue
            grouped_history[str(reference)].append({
                "timestamp": timestamp,
                "changes": changes
            })

    return dict(grouped_history)


def run() -> None:  # noqa: ARG001
    if not HISTORY_FILE.exists():
        return
    try:
        history = _load_json(HISTORY_FILE)
    except Exception:
        return

    if isinstance(history, dict):
        return
    if not isinstance(history, list):
        return

    index_map = _build_index_map()
    migrated = _migrate_history(history, index_map)
    if migrated:
        _save_json(HISTORY_FILE, migrated)
