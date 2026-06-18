"""Tests for the FastAPI endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_tools():
    response = client.get("/api/tools")
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "desk_booking" in names


def test_chat_endpoint_completes():
    response = client.post(
        "/api/chat",
        json={"message": "Book a desk on Floor 6 for Thursday", "role": "employee"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["steps"][0]["tool"] == "desk_booking"


def test_chat_endpoint_rbac_denied():
    response = client.post(
        "/api/chat",
        json={"message": "Approve the pending request", "role": "employee"},
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["status"] == "denied"


def test_frontend_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Enterprise Task Agent" in response.text
