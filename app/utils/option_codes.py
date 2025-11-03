"""Utilities for retrieving Tesla option codes from the remote API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config import PRIVATE_DIR, PUBLIC_DIR
from app.utils.connection import request_with_retry

FETCH_URL = "https://www.tesla-order-status-tracker.de/get/option_codes.php"
CACHE_FILE = PRIVATE_DIR / "option_codes_cache.json"
CACHE_TTL = timedelta(hours=24)
SCHEMA_VERSION = 2
_OPTION_CODES: Optional[Dict[str, Dict[str, Any]]] = None


def _normalize_entry(value: Any) -> Optional[Dict[str, Any]]:
    """Return a uniform option-code payload with at least label/category."""
    if isinstance(value, dict):
        label = value.get("label") or value.get("label_en") or value.get("label_en_us")
        if label is None and "raw" in value:
            raw = value.get("raw")
            if isinstance(raw, dict):
                label = raw.get("label") or raw.get("label_en")
        category = value.get("category")
        raw_payload = value.get("raw")
        if raw_payload is None:
            # Preserve original payload for future use if we have access to it
            raw_payload = {
                k: v for k, v in value.items()
                if k not in {"label", "label_en", "label_en_us", "category", "raw"}
            } or None
        if label is None:
            return None
        entry = {
            "label": str(label),
            "category": str(category).strip().lower() if isinstance(category, str) else None,
        }
        if raw_payload:
            entry["raw"] = raw_payload
        return entry

    if value is None:
        return None

    return {
        "label": str(value),
        "category": None,
    }


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


def _load_cache(allow_expired: bool = False) -> Optional[Dict[str, Dict[str, Any]]]:
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

    schema_version = payload.get("schema_version")
    requires_refresh = schema_version != SCHEMA_VERSION

    if not allow_expired:
        fetched_at = _parse_timestamp(payload.get("fetched_at"))
        if fetched_at is None:
            return None
        if datetime.now(timezone.utc) - fetched_at > CACHE_TTL:
            return None

    normalized: Dict[str, Dict[str, Any]] = {}
    for code, value in option_codes.items():
        key = str(code).strip().upper()
        entry = _normalize_entry(value)
        if entry:
            normalized[key] = entry
            if not isinstance(value, dict):
                requires_refresh = True
        else:
            requires_refresh = True

    if requires_refresh and not allow_expired:
        return None

    return normalized


def _write_cache(option_codes: Dict[str, Dict[str, Any]], fetched_at: Optional[str]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(),
        "option_codes": option_codes,
        "schema_version": SCHEMA_VERSION,
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_remote() -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
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

    option_codes: Dict[str, Dict[str, Any]] = {}
    for entry in payload.get("option_codes", []):
        if not isinstance(entry, dict):
            continue
        code = entry.get("code")
        label = entry.get("label_en")
        if not code or label is None:
            continue
        category = entry.get("category")
        normalized_entry = {
            "label": str(label),
            "category": str(category).strip().lower() if isinstance(category, str) else None,
            "raw": entry,
        }
        option_codes[str(code).strip().upper()] = normalized_entry

    fetched_at = payload.get("fetched_at")
    return option_codes, fetched_at


def _load_local_overrides() -> Dict[str, Dict[str, Any]]:
    folder = PUBLIC_DIR / "option-codes"
    option_codes: Dict[str, Dict[str, Any]] = {}
    if not folder.exists() or not folder.is_dir():
        return option_codes

    for path in sorted(glob(str(folder / "*.json"))):
        try:
            with Path(path).open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            for code, value in payload.items():
                key = str(code).strip().upper()
                entry = _normalize_entry(value)
                if entry:
                    option_codes[key] = entry
    return option_codes


def _apply_local_overrides(option_codes: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    overrides = _load_local_overrides()
    if not overrides:
        return option_codes
    merged = option_codes.copy()
    merged.update(overrides)
    return merged


def get_option_codes(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Return a dictionary mapping option codes to their metadata."""
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
    entry = get_option_codes().get(code.strip().upper())
    if not entry:
        return None
    return entry.get("label")


def get_option_entry(code: str) -> Optional[Dict[str, Any]]:
    """Return the normalized option-code entry if available."""
    if not isinstance(code, str):
        return None
    entry = get_option_codes().get(code.strip().upper())
    if entry is None:
        return None
    # Return a shallow copy to prevent accidental mutations of the cache
    return dict(entry)


def get_option_category(code: str) -> Optional[str]:
    """Return the normalized category for *code*."""
    entry = get_option_entry(code)
    if not entry:
        return None
    return entry.get("category")
