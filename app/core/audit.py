"""Append-only audit trail with sensitive-value redaction (SQLite-backed).

Every tool invocation (allowed, denied, or failed) is recorded durably so the
agent's actions are traceable across restarts — a key governance and compliance
requirement for enterprise adoption.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core import db

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
    db.execute(
        "INSERT INTO audit (timestamp, user_id, role, tool, status, params) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            user.get("user_id", "unknown"),
            user.get("role", "unknown"),
            tool,
            status,
            json.dumps(redact(params or {})),
        ),
    )


def all_entries() -> list[dict[str, Any]]:
    """Return audit entries, newest first."""
    rows = db.query(
        "SELECT timestamp, user_id, role, tool, status, params FROM audit ORDER BY id DESC"
    )
    return [
        {
            "timestamp": row["timestamp"],
            "user_id": row["user_id"],
            "role": row["role"],
            "tool": row["tool"],
            "status": row["status"],
            "params": json.loads(row["params"]),
        }
        for row in rows
    ]


def clear() -> None:
    """Delete the audit trail (used in tests)."""
    db.execute("DELETE FROM audit")
