"""Tests for auth wiring (dev mode) and date resolution helpers."""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.tools.dates import resolve_date, work_window

client = TestClient(app)


def test_health_reports_auth_disabled_in_dev():
    body = client.get("/api/health").json()
    assert body["auth_enabled"] is False


def test_auth_status_dev_mode():
    body = client.get("/auth/status").json()
    assert body == {"auth_enabled": False, "authenticated": False, "user": None}


def test_login_disabled_without_app_registration():
    # With no Entra config, sign-in must be unavailable (no broken redirect).
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 400


def test_chat_uses_dev_role_when_auth_disabled():
    # In dev mode the request body role still drives RBAC.
    response = client.post(
        "/api/chat",
        json={"message": "Approve the pending request", "role": "manager"},
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["tool"] == "approval"


def test_resolve_date_keywords():
    base = date(2025, 1, 1)  # a Wednesday
    assert resolve_date("today", base) == base
    assert resolve_date("tomorrow", base) == date(2025, 1, 2)
    assert resolve_date("next week", base) == date(2025, 1, 8)


def test_resolve_date_weekday_picks_future():
    base = date(2025, 1, 1)  # Wednesday
    assert resolve_date("book for thursday", base) == date(2025, 1, 2)
    # Same weekday as base resolves to the next week's occurrence.
    assert resolve_date("wednesday", base) == date(2025, 1, 8)


def test_resolve_date_explicit_day_first():
    assert resolve_date("25-06-2026", date(2025, 1, 1)) == date(2026, 6, 25)


def test_work_window_shape():
    start, end = work_window(date(2026, 6, 25))
    assert start == "2026-06-25T09:00:00"
    assert end == "2026-06-25T18:00:00"
