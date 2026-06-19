"""Identity resolution helpers used by API routes.

Bridges the server-side session (access token + claims) into the simple ``user``
dict the agent pipeline expects: ``{user_id, role, name, email, access_token}``.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status

from app.auth.session_store import get_session
from app.config import settings


def current_identity(request: Request) -> dict[str, Any] | None:
    """Return the signed-in user's identity, or None when not authenticated."""
    sid = request.session.get("sid")
    data = get_session(sid)
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


def build_user(request: Request, dev_role: str = "employee", dev_user_id: str = "u-001") -> dict[str, Any]:
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
