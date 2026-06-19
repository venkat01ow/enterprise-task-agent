"""Production-hardening tests: security headers, readiness, rate limiting,
persistence durability, and fail-fast config validation."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.agent.schemas import StepResult, TaskRun
from app.config import settings
from app.core import audit
from app.core.store import all_tasks, save_task
from app.main import app, create_app

client = TestClient(app)


def test_security_headers_present():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    # Every response carries a correlation id.
    assert response.headers["X-Request-ID"]


def test_readiness_probe_ok():
    response = client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] is True


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    # Fresh app → fresh in-process rate-limit buckets.
    limited_client = TestClient(create_app())

    statuses = [limited_client.get("/api/health").status_code for _ in range(4)]

    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429


def test_task_persistence_round_trip():
    task = TaskRun(
        id="task-prod-1",
        user_id="u-123",
        message="Book a desk on Floor 6",
        steps=[StepResult(tool="desk_booking", status="completed", summary="done")],
        status="completed",
        created_at=datetime.now(timezone.utc),
    )
    save_task(task)

    stored = {t.id: t for t in all_tasks()}
    assert "task-prod-1" in stored
    assert stored["task-prod-1"].message == "Book a desk on Floor 6"


def test_audit_persistence_and_redaction():
    audit.record(
        {"user_id": "u-9", "role": "admin"},
        "desk_booking",
        "completed",
        {"password": "hunter2", "floor": 6},
    )

    entries = audit.all_entries()
    assert entries[0]["tool"] == "desk_booking"
    assert entries[0]["params"]["password"] == "***redacted***"
    assert entries[0]["params"]["floor"] == 6


def test_production_rejects_insecure_secret(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "session_secret", "dev-insecure-change-me")
    with pytest.raises(RuntimeError):
        settings.validate_runtime()


def test_production_accepts_strong_secret(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "session_secret", "x" * 48)
    # Strong secret → no raise; returns a (possibly empty) warnings list.
    assert isinstance(settings.validate_runtime(), list)


def test_production_property_toggles(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    assert settings.is_production is True
    assert settings.secure_cookies is True
    assert settings.hsts_active is True
    assert settings.docs_enabled is False
