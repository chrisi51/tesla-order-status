"""
Migration: 2025-09-05-history-trim
- Entfernt führende und nachfolgende Whitespaces aus allen string 'value'- und 'old_value'-Feldern in der History.
- Sucht die History-Datei sowohl im BASE_DIR als auch im PRIVATE_DIR.
- Keine Aktion, falls Datei nicht vorhanden.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.config import BASE_DIR, PRIVATE_DIR


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _strip_history_values(history: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    changed = False
    for entry in history:
        for change in entry.get("changes", []):
            for field in ("value", "old_value"):
                val = change.get(field)
                if isinstance(val, str):
                    new_val = val.strip()
                    if new_val != val:
                        change[field] = new_val
                        changed = True
    return history, changed


def run() -> None:  # noqa: ARG001
    candidates = [
        BASE_DIR / "tesla_order_history.json",
        PRIVATE_DIR / "tesla_order_history.json",
    ]
    target_path = next((p for p in candidates if p.exists()), None)
    if target_path is None:
        return
    try:
        history = _load_json(target_path)
    except Exception:
        return
    history, changed = _strip_history_values(history)
    if changed:
        _save_json(target_path, history)
