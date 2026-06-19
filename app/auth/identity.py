"""Identity resolution helpers used by API routes.

Bridges the server-side session (access token + claims) into the simple ``user``
dict the agent pipeline expects: ``{user_id, role, name, email, access_token}``.
Access tokens are refreshed silently (via the cached refresh token) when they
near expiry, so a sign-in stays usable for the full session lifetime.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import HTTPException, Request, status

from app.auth import entra
from app.auth.session_store import delete_session, get_session, update_session
from app.config import settings

logger = logging.getLogger("eta.auth")


def _refresh_if_needed(sid: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Refresh the access token if it is near expiry. Returns updated session.

    Returns None if the token is expired and cannot be refreshed (caller should
    treat the user as unauthenticated).
    """
    if not data.get("token_cache"):
        return data  # dev/mock session, nothing to refresh

    expires_at = data.get("expires_at", 0)
    if time.time() < expires_at - settings.token_refresh_skew_seconds:
        return data  # token still fresh

    result, new_cache = entra.acquire_token_silent(
        data.get("token_cache", ""), data.get("home_account_id")
    )
    if result and "access_token" in result:
        data["access_token"] = result["access_token"]
        data["expires_at"] = time.time() + int(result.get("expires_in", 3600)) - 60
        data["token_cache"] = new_cache
        update_session(sid, data)
        return data

    # Could not refresh. If the current token is already expired, fail closed.
    if time.time() >= expires_at:
        logger.info("Silent token refresh failed and token expired; dropping session.")
        delete_session(sid)
        return None
    return data


def current_identity(request: Request) -> dict[str, Any] | None:
    """Return the signed-in user's identity, or None when not authenticated."""
    sid = request.session.get("sid")
    data = get_session(sid)
    if not data:
        return None
    data = _refresh_if_needed(sid, data)
    if not data:
        return None
    return {
        "user_id": data.get("oid", "unknown"),
        "name": data.get("name", "User"),
        "email": data.get("email", ""),
        "role": data.get("role", "employee"),
        "access_token": data.get("access_token"),
    }


def public_identity(request: Request) -> dict[str, Any] | None:
    """Identity view safe to send to the browser (no access token)."""
    ident = current_identity(request)
    if not ident:
        return None
    return {
        "user_id": ident["user_id"],
        "name": ident["name"],
        "email": ident["email"],
        "role": ident["role"],
    }


def build_user(
    request: Request, dev_role: str = "employee", dev_user_id: str = "u-001"
) -> dict[str, Any]:
    """Resolve the acting user for an agent request.

    * Auth enabled  → require a valid session; identity comes from the token.
    * Auth disabled → offline dev mode; trust the supplied role (local only).
    """
    if settings.auth_enabled:
        ident = current_identity(request)
        if not ident:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in with Microsoft.",
            )
        return ident
    return {"user_id": dev_user_id, "role": dev_role}
