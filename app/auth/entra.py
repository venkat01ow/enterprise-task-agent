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


def build_msal_app(cache: msal.SerializableTokenCache | None = None) -> msal.ConfidentialClientApplication:
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


def complete_auth_flow(flow: dict[str, Any], auth_response: dict[str, Any]) -> dict[str, Any]:
    """Exchange the authorization code for tokens.

    ``auth_response`` is the dict of query parameters Microsoft redirected back
    with. Returns the MSAL result (access_token, id_token_claims, expires_in,
    ...). Raises ValueError if the exchange fails.
    """
    app = build_msal_app()
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or "unknown error"
        raise ValueError(f"Token acquisition failed: {error}")
    return result


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
