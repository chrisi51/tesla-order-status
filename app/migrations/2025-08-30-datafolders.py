"""
Migration: 2025-08-30-datafolders
- Verschiebt alte, private JSON-Dateien aus dem Repo-Root in data/private
- Legt Backups der älteren Datei-Version an (data/private/backup/*.old)
- Idempotent.

Wird vom Migration-Runner im Hauptskript aufgerufen.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

from app.config import BASE_DIR, PRIVATE_DIR, PUBLIC_DIR


def _safe_move_with_backup(src: Path, dst: Path, backup_dir: Path) -> None:
    """Verschiebt *src* nach *dst*.
    Existiert *dst*, wird die ältere Datei nach *backup_dir*/*.old verschoben
    und die neuere bleibt an *dst* liegen.
    """
    try:
        src_stat = src.stat()
        if dst.exists():
            dst_stat = dst.stat()
            backup_dir.mkdir(parents=True, exist_ok=True)
            if src_stat.st_mtime > dst_stat.st_mtime:
                # src ist neuer → dst sichern, src nach dst
                shutil.move(str(dst), str(backup_dir / (dst.name + ".old")))
                shutil.move(str(src), str(dst))
            else:
                # dst ist neuer → src sichern
                shutil.move(str(src), str(backup_dir / (src.name + ".old")))
        else:
            if dst == "":
                src.unlink()
                return
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
    except FileNotFoundError:
        pass


def run() -> None:
    backup_dir = PRIVATE_DIR / "backup"

    # Ensure directories exist (public comes from the Git repo, private is created locally)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)


    legacy_map: Dict[str, Path] = {
        "tesla_tokens.json": PRIVATE_DIR / "tesla_tokens.json",
        "tesla_orders.json": PRIVATE_DIR / "tesla_orders.json",
        "tesla_order_history.json": PRIVATE_DIR / "tesla_order_history.json",
        "tesla_locations.json": PUBLIC_DIR / "tesla_locations.json",
        "option-codes": PUBLIC_DIR / "option-codes"
        "update_check.py": ""
    }

    # Verzeichnisse sicherstellen
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

    for legacy_name, dst in legacy_map.items():
        src = BASE_DIR / legacy_name
        if src.exists():
            _safe_move_with_backup(src, dst, backup_dir)

    # Fertig. Keine Rückgabe nötig.
