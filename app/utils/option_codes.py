"""Utilities for retrieving Tesla option codes from the remote API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.config import PRIVATE_DIR, PUBLIC_DIR
from app.utils.connection import request_with_retry

FETCH_URL = "https://www.tesla-order-status-tracker.de/get/option_codes.php"
CACHE_FILE = PRIVATE_DIR / "option_codes_cache.json"
CACHE_TTL = timedelta(hours=24)
_OPTION_CODES: Optional[Dict[str, str]] = None


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_cache(allow_expired: bool = False) -> Optional[Dict[str, str]]:
    if not CACHE_FILE.exists():
        return None
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError):
        return None

    option_codes = payload.get("option_codes")
    if not isinstance(option_codes, dict):
        return None

    if not allow_expired:
        fetched_at = _parse_timestamp(payload.get("fetched_at"))
        if fetched_at is None:
            return None
        if datetime.now(timezone.utc) - fetched_at > CACHE_TTL:
            return None

    return {str(code).strip().upper(): str(label) for code, label in option_codes.items()}


def _write_cache(option_codes: Dict[str, str], fetched_at: Optional[str]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(),
        "option_codes": option_codes,
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_remote() -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    try:
        response = request_with_retry(FETCH_URL, exit_on_error=False)
    except RuntimeError:
        return None, None
    if response is None:
        return None, None
    try:
        payload = response.json()
    except ValueError:
        return None, None

    if not isinstance(payload, dict) or not payload.get("ok"):
        return None, None

    option_codes: Dict[str, str] = {}
    for entry in payload.get("option_codes", []):
        if not isinstance(entry, dict):
            continue
        code = entry.get("code")
        label = entry.get("label_en")
        if not code or label is None:
            continue
        option_codes[str(code).strip().upper()] = str(label)

    fetched_at = payload.get("fetched_at")
    return option_codes, fetched_at


def _load_local_overrides() -> Dict[str, str]:
    folder = PUBLIC_DIR / "option-codes"
    option_codes: Dict[str, str] = {}
    if not folder.exists() or not folder.is_dir():
        return option_codes

    for path in sorted(glob(str(folder / "*.json"))):
        try:
            with Path(path).open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            option_codes.update({
                str(code).strip().upper(): str(label)
                for code, label in payload.items()
            })
    return option_codes


def _apply_local_overrides(option_codes: Dict[str, str]) -> Dict[str, str]:
    overrides = _load_local_overrides()
    if not overrides:
        return option_codes
    merged = option_codes.copy()
    merged.update(overrides)
    return merged


def get_option_codes(force_refresh: bool = False) -> Dict[str, str]:
    """Return a dictionary mapping option codes to their English label."""
    global _OPTION_CODES

    if not force_refresh and _OPTION_CODES is not None:
        return _OPTION_CODES

    if not force_refresh:
        cached = _load_cache(allow_expired=False)
        if cached is not None:
            final_codes = _apply_local_overrides(cached)
            _OPTION_CODES = final_codes
            return final_codes

    option_codes, fetched_at = _fetch_remote()
    if option_codes is not None:
        _write_cache(option_codes, fetched_at)
        final_codes = _apply_local_overrides(option_codes)
        _OPTION_CODES = final_codes
        return final_codes

    cached = _load_cache(allow_expired=True)
    if cached is not None:
        final_codes = _apply_local_overrides(cached)
        _OPTION_CODES = final_codes
        return final_codes

    fallback = _load_local_overrides()
    _OPTION_CODES = fallback
    return fallback


def get_option_label(code: str) -> Optional[str]:
    """Return the label for *code* if it exists."""
    if not isinstance(code, str):
        return None
    return get_option_codes().get(code.strip().upper())