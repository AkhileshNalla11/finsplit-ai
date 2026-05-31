"""Supabase persistence for splits, with graceful degradation.

If Supabase is not configured or is unavailable, store_split() returns None and
fetch_split() returns None — the core splitting feature still works, only
sharing is disabled. We never raise to the caller for storage failures.
"""

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_client = None
_initialized = False


def _get_client():
    """Lazily create the Supabase client. Returns None if unconfigured/unavailable."""
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.warning("Supabase not configured — sharing disabled, splits won't be stored.")
        return None

    try:
        from supabase import create_client

        _client = create_client(url, key)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any init failure
        logger.error("Failed to initialize Supabase client: %s", exc)
        _client = None
    return _client


def store_split(result: dict[str, Any]) -> str | None:
    """Insert a split and return its UUID, or None if storage is unavailable."""
    client = _get_client()
    if client is None:
        return None

    split_id = str(uuid.uuid4())
    try:
        client.table("splits").insert({"id": split_id, "data": result}).execute()
        return split_id
    except Exception as exc:  # noqa: BLE001 - sharing is best-effort
        logger.error("Failed to store split in Supabase: %s", exc)
        return None


def fetch_split(split_id: str) -> dict[str, Any] | None:
    """Fetch a stored split row by UUID, or None if missing/unavailable."""
    client = _get_client()
    if client is None:
        return None

    try:
        resp = client.table("splits").select("*").eq("id", split_id).limit(1).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch split from Supabase: %s", exc)
        return None

    rows = resp.data or []
    return rows[0] if rows else None
