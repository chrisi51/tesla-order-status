"""
Migration: 2025-11-12-orders-map
- Konvertiert `tesla_orders.json` von einer Listendarstellung in ein Dict, das per
  `referenceNumber` (oder Legacy-Fallback) indiziert ist.
- Bewahrt die Reihenfolge der ursprünglichen Einträge und ist idempotent.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict

from app.config import ORDERS_FILE


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _extract_reference(entry: Dict[str, Any]) -> str | None:
    if not isinstance(entry, dict):
        return None
    order_payload = entry.get("order")
    if isinstance(order_payload, dict):
        reference = order_payload.get("referenceNumber")
        if reference:
            return str(reference)
    reference = entry.get("referenceNumber")
    if reference:
        return str(reference)
    return None


def run() -> None:  # noqa: ARG001
    if not ORDERS_FILE.exists():
        return

    try:
        orders_data = _load_json(ORDERS_FILE)
    except Exception:
        return

    if isinstance(orders_data, dict):
        return

    if not isinstance(orders_data, list):
        return

    new_orders: OrderedDict[str, Any] = OrderedDict()
    for idx, entry in enumerate(orders_data):
        if not isinstance(entry, dict):
            continue
        reference = _extract_reference(entry) or f"legacy-{idx}"
        candidate = reference
        suffix = 1
        while candidate in new_orders:
            candidate = f"{reference}-{suffix}"
            suffix += 1
        new_orders[candidate] = entry

    if not new_orders:
        return

    _save_json(ORDERS_FILE, new_orders)
