"""Append-only audit trail with sensitive-value redaction.

Every tool invocation (allowed, denied, or failed) is recorded so the agent's
actions are traceable — a key governance requirement for enterprise adoption.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_AUDIT: list[dict[str, Any]] = []

_SENSITIVE_KEYS = {"password", "passwd", "token", "secret", "ssn", "api_key", "apikey"}


def redact(params: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``params`` with sensitive values masked."""
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if key.lower() in _SENSITIVE_KEYS:
            cleaned[key] = "***redacted***"
        else:
            cleaned[key] = value
    return cleaned


def record(user: dict[str, Any], tool: str, status: str, params: dict[str, Any]) -> None:
    """Append an audit entry for a tool invocation."""
    _AUDIT.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user.get("user_id", "unknown"),
            "role": user.get("role", "unknown"),
            "tool": tool,
            "status": status,
            "params": redact(params or {}),
        }
    )


def all_entries() -> list[dict[str, Any]]:
    """Return audit entries, newest first."""
    return list(reversed(_AUDIT))


def clear() -> None:
    """Clear the audit trail (used in tests)."""
    _AUDIT.clear()
