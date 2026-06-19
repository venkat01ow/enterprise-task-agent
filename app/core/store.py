"""Durable task-run history store (SQLite-backed).

Persists every task run so history survives restarts and deploys. The public
API is unchanged from the original in-memory version, so call sites and tests
remain identical.
"""
from __future__ import annotations

from app.agent.schemas import TaskRun
from app.core import db


def save_task(task: TaskRun) -> None:
    """Persist a completed task run."""
    db.execute(
        "INSERT OR REPLACE INTO tasks (id, user_id, message, status, created_at, payload) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            task.id,
            task.user_id,
            task.message,
            task.status,
            task.created_at.isoformat(),
            task.model_dump_json(),
        ),
    )


def all_tasks() -> list[TaskRun]:
    """Return all task runs, newest first."""
    rows = db.query("SELECT payload FROM tasks ORDER BY created_at DESC, rowid DESC")
    return [TaskRun.model_validate_json(row["payload"]) for row in rows]


def clear() -> None:
    """Delete all stored tasks (used in tests)."""
    db.execute("DELETE FROM tasks")
