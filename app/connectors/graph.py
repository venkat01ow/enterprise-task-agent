"""Microsoft Graph connector — performs REAL Microsoft 365 actions.

Uses the signed-in user's delegated access token to act on their behalf:
read profile, create calendar events, send mail, and create To-Do tasks.

Every method raises :class:`GraphError` on failure so callers can fall back or
surface a clear message. Tokens are never logged.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class GraphError(RuntimeError):
    """Raised when a Microsoft Graph call fails."""


class GraphClient:
    def __init__(self, access_token: str) -> None:
        self._token = access_token
        self._base = settings.graph_base_url.rstrip("/")
        self._timeout = settings.request_timeout_seconds

    # ── internal helpers ─────────────────────────────────────────────
    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(method, url, headers=self._headers, json=payload)
        except httpx.HTTPError as exc:  # network-level failure
            raise GraphError(f"Network error calling Graph: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_error(response)
            raise GraphError(f"Graph {response.status_code}: {detail}")
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ── real actions ─────────────────────────────────────────────────
    def get_profile(self) -> dict[str, Any]:
        """GET /me — the signed-in user's profile."""
        return self._request("GET", "/me")

    def create_event(
        self,
        subject: str,
        start_iso: str,
        end_iso: str,
        timezone: str,
        body: str = "",
        location: str = "",
        all_day: bool = False,
    ) -> dict[str, Any]:
        """POST /me/events — create a calendar event."""
        payload: dict[str, Any] = {
            "subject": subject,
            "isAllDay": all_day,
            "start": {"dateTime": start_iso, "timeZone": timezone},
            "end": {"dateTime": end_iso, "timeZone": timezone},
        }
        if body:
            payload["body"] = {"contentType": "text", "content": body}
        if location:
            payload["location"] = {"displayName": location}
        return self._request("POST", "/me/events", payload)

    def send_mail(self, subject: str, body: str, to_recipients: list[str]) -> None:
        """POST /me/sendMail — send an email as the signed-in user."""
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "text", "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": addr}} for addr in to_recipients
                ],
            },
            "saveToSentItems": True,
        }
        self._request("POST", "/me/sendMail", payload)

    def create_todo_task(self, title: str, note: str = "", due_date: str | None = None) -> dict[str, Any]:
        """Create a Microsoft To-Do task in the user's default list."""
        list_id = self._default_todo_list_id()
        payload: dict[str, Any] = {"title": title}
        if note:
            payload["body"] = {"contentType": "text", "content": note}
        if due_date:
            payload["dueDateTime"] = {"dateTime": f"{due_date}T17:00:00", "timeZone": settings.default_timezone}
        return self._request("POST", f"/me/todo/lists/{list_id}/tasks", payload)

    def _default_todo_list_id(self) -> str:
        data = self._request("GET", "/me/todo/lists")
        lists = data.get("value", [])
        if not lists:
            raise GraphError("No To-Do lists found for user.")
        # Prefer the well-known default list when present.
        for item in lists:
            if item.get("wellknownListName") == "defaultList":
                return item["id"]
        return lists[0]["id"]


def _extract_error(response: httpx.Response) -> str:
    try:
        data = response.json()
        return data.get("error", {}).get("message", response.text[:200])
    except Exception:
        return response.text[:200]
