"""Microsoft Entra ID (Azure AD) integration via MSAL.

Implements the OAuth2 **Authorization Code flow with PKCE** for a confidential
web client. MSAL handles PKCE, the ``state`` parameter (CSRF protection), and
token caching for us.

Delegated Microsoft Graph scopes requested at sign-in: the user consents once,
and the app then acts *on their behalf* with their own permissions — it never
sees their password.
"""
from __future__ import annotations

from typing import Any

import msal

from app.config import settings

# Delegated permissions the agent needs to perform real Microsoft 365 actions.
# 'openid', 'profile' and 'offline_access' are added by MSAL automatically.
GRAPH_SCOPES: list[str] = [
    "User.Read",
    "Calendars.ReadWrite",
    "Mail.Send",
    "Tasks.ReadWrite",
]


def build_msal_app(
    cache: msal.SerializableTokenCache | None = None,
) -> msal.ConfidentialClientApplication:
    """Construct a confidential client application bound to our tenant."""
    return msal.ConfidentialClientApplication(
        client_id=settings.entra_client_id,
        client_credential=settings.entra_client_secret,
        authority=settings.authority,
        token_cache=cache,
    )


def start_auth_flow() -> dict[str, Any]:
    """Begin sign-in: returns a flow dict containing the Microsoft auth URL.

    The full flow dict (which includes the PKCE verifier and state) must be
    stored server-side and passed back to :func:`complete_auth_flow`.
    """
    app = build_msal_app()
    return app.initiate_auth_code_flow(
        scopes=GRAPH_SCOPES,
        redirect_uri=settings.entra_redirect_uri,
    )


def complete_auth_flow(
    flow: dict[str, Any], auth_response: dict[str, Any]
) -> tuple[dict[str, Any], str, str | None]:
    """Exchange the authorization code for tokens.

    ``auth_response`` is the dict of query parameters Microsoft redirected back
    with. Returns ``(result, serialized_cache, home_account_id)`` where the
    serialized MSAL cache + account id enable later silent token refresh. Raises
    ValueError if the exchange fails.
    """
    cache = msal.SerializableTokenCache()
    app = build_msal_app(cache)
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or "unknown error"
        raise ValueError(f"Token acquisition failed: {error}")
    accounts = app.get_accounts()
    home_account_id = accounts[0]["home_account_id"] if accounts else None
    return result, cache.serialize(), home_account_id


def acquire_token_silent(
    serialized_cache: str, home_account_id: str | None
) -> tuple[dict[str, Any] | None, str]:
    """Silently refresh the access token using the cached refresh token.

    Returns ``(result, serialized_cache)``. ``result`` is None when no valid
    token could be obtained (the caller should then require re-authentication).
    """
    cache = msal.SerializableTokenCache()
    if serialized_cache:
        cache.deserialize(serialized_cache)
    app = build_msal_app(cache)

    account = None
    accounts = app.get_accounts()
    for acc in accounts:
        if acc.get("home_account_id") == home_account_id:
            account = acc
            break
    if account is None and accounts:
        account = accounts[0]

    result = app.acquire_token_silent(GRAPH_SCOPES, account=account) if account else None
    new_cache = cache.serialize() if cache.has_state_changed else serialized_cache
    if not result or "access_token" not in result:
        return None, new_cache
    return result, new_cache


def resolve_role(id_token_claims: dict[str, Any]) -> str:
    """Map Entra app-role / group claims to an agent role.

    Defaults to 'employee'. Admins outrank managers.
    """
    claims: list[str] = []
    for key in ("roles", "groups", "wids"):
        value = id_token_claims.get(key)
        if isinstance(value, list):
            claims.extend(str(v) for v in value)
        elif isinstance(value, str):
            claims.append(value)

    if settings.role_claim_admin in claims:
        return "admin"
    if settings.role_claim_manager in claims:
        return "manager"
    return "employee"


def build_logout_url() -> str:
    """URL that signs the user out of Microsoft and returns them to the app."""
    redirect = settings.entra_post_logout_redirect_uri
    return (
        f"{settings.authority}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={redirect}"
    )
