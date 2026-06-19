"""Server-side session store.

The signed session cookie holds only an opaque session id. Sensitive material
(the Microsoft Graph access token, the MSAL token cache) lives here, server-side,
keyed by that id — so access tokens are never exposed to the browser.

This implementation is in-memory (single-process). For multi-instance
deployments, back it with Redis or a database by reimplementing these four
functions; nothing else in the app needs to change.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

_SESSIONS: dict[str, dict[str, Any]] = {}


def create_session(data: dict[str, Any]) -> str:
    """Store ``data`` and return a new opaque session id."""
    sid = secrets.token_urlsafe(32)
    _SESSIONS[sid] = data
    return sid


def get_session(sid: str | None) -> dict[str, Any] | None:
    """Return session data, or None if missing/expired."""
    if not sid:
        return None
    data = _SESSIONS.get(sid)
    if data is None:
        return None
    expires_at = data.get("expires_at", 0)
    if expires_at and time.time() >= expires_at:
        # Token expired: drop the session so the user is asked to re-authenticate.
        _SESSIONS.pop(sid, None)
        return None
    return data


def update_session(sid: str, data: dict[str, Any]) -> None:
    if sid in _SESSIONS:
        _SESSIONS[sid] = data


def delete_session(sid: str | None) -> None:
    if sid:
        _SESSIONS.pop(sid, None)
