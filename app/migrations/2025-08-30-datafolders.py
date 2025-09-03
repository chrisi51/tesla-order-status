"""
Migration: 2025-08-30-datafolders
- Moves old private JSON files from repo root to data/private
- Creates backups of older file versions (data/private/backup/*.old)
- Idempotent.

Called by the migration runner in the main script.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

from app.config import BASE_DIR, PRIVATE_DIR, PUBLIC_DIR


def _safe_move_with_backup(src: Path, dst: Path, backup_dir: Path) -> None:
    """Moves *src* to *dst*.
    If *dst* exists, the older file is moved to *backup_dir*/*.old
    and the newer one remains at *dst*.
    """
    try:
        src_stat = src.stat()
        if dst == "":
            src.unlink()
            return
        if dst.exists():
            dst_stat = dst.stat()
            backup_dir.mkdir(parents=True, exist_ok=True)
            if src_stat.st_mtime > dst_stat.st_mtime:
                # src is newer → backup dst, move src to dst
                shutil.move(str(dst), str(backup_dir / (dst.name + ".old")))
                shutil.move(str(src), str(dst))
            else:
                # dst is newer → backup src
                shutil.move(str(src), str(backup_dir / (src.name + ".old")))
        else:
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
        "option-codes": PUBLIC_DIR / "option-codes",
        "update_check.py": "",
        "tesla_stores.py": ""
    }

    for legacy_name, dst in legacy_map.items():
        src = BASE_DIR / legacy_name
        if src.exists():
            _safe_move_with_backup(src, dst, backup_dir)

