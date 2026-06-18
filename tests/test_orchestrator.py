"""Tests for the orchestrator (planning + RBAC + execution)."""
from __future__ import annotations

from app.agent.orchestrator import run_task
from app.core import audit
from app.core.store import all_tasks


def test_run_task_completes_booking():
    task = run_task("Book a desk on Floor 6 for Thursday", {"user_id": "u1", "role": "employee"})
    assert task.status == "completed"
    assert task.steps[0].tool == "desk_booking"
    assert task.steps[0].status == "completed"


def test_run_task_persists_history():
    run_task("Log 8 hours today", {"user_id": "u1", "role": "employee"})
    assert len(all_tasks()) == 1


def test_rbac_denies_employee_approval():
    task = run_task("Approve the pending leave request", {"user_id": "u1", "role": "employee"})
    assert task.steps[0].tool == "approval"
    assert task.steps[0].status == "denied"
    assert task.status == "failed"


def test_rbac_allows_manager_approval():
    task = run_task("Approve the pending leave request", {"user_id": "m1", "role": "manager"})
    assert task.steps[0].status == "completed"


def test_audit_trail_records_actions():
    run_task("Book a desk for Thursday", {"user_id": "u1", "role": "employee"})
    entries = audit.all_entries()
    assert any(e["tool"] == "desk_booking" and e["status"] == "completed" for e in entries)


def test_empty_plan_status():
    task = run_task("hello there", {"user_id": "u1", "role": "employee"})
    assert task.status == "empty"
    assert task.steps == []
