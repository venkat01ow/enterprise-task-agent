"""Authentication routes: Microsoft sign-in, callback, logout, status."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import entra
from app.auth.identity import public_identity
from app.auth.session_store import create_session, delete_session
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status(request: Request) -> dict[str, object]:
    """Report whether real auth is configured and who (if anyone) is signed in."""
    user = public_identity(request)
    return {
        "auth_enabled": settings.auth_enabled,
        "authenticated": user is not None,
        "user": user,
    }


@router.get("/login")
def login(request: Request) -> RedirectResponse:
    """Kick off the Microsoft Authorization-Code (PKCE) sign-in flow."""
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Microsoft sign-in is not configured.")
    flow = entra.start_auth_flow()
    # The flow carries the PKCE verifier + state; keep it for the callback.
    request.session["auth_flow"] = flow
    return RedirectResponse(flow["auth_uri"])


@router.get("/callback")
def callback(request: Request) -> RedirectResponse:
    """Handle Microsoft's redirect: exchange the code and start a session."""
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Microsoft sign-in is not configured.")

    flow = request.session.pop("auth_flow", None)
    if not flow:
        # No in-progress flow (e.g. stale link) — restart cleanly.
        return RedirectResponse("/auth/login")

    try:
        result, token_cache, home_account_id = entra.complete_auth_flow(
            flow, dict(request.query_params)
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    claims = result.get("id_token_claims", {})
    expires_in = int(result.get("expires_in", 3600))
    now = time.time()
    sid = create_session(
        {
            "oid": claims.get("oid") or claims.get("sub", "unknown"),
            "name": claims.get("name", "User"),
            "email": claims.get("preferred_username") or claims.get("email", ""),
            "role": entra.resolve_role(claims),
            "access_token": result["access_token"],
            "expires_at": now + expires_in - 60,
            "token_cache": token_cache,
            "home_account_id": home_account_id,
            "session_expires_at": now + settings.session_max_age_seconds,
        }
    )
    request.session["sid"] = sid
    return RedirectResponse("/")


@router.get("/logout")
def logout(request: Request) -> RedirectResponse:
    """Clear the local session and sign the user out of Microsoft."""
    delete_session(request.session.get("sid"))
    request.session.clear()
    if settings.auth_enabled:
        return RedirectResponse(entra.build_logout_url())
    return RedirectResponse("/")
