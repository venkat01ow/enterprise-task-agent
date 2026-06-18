"""In-memory task-run history store.

Kept intentionally simple (process memory) so the demo has zero external
dependencies. Swap with a database by replacing these functions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agent.schemas import TaskRun

_TASKS: list["TaskRun"] = []


def save_task(task: "TaskRun") -> None:
    """Persist a completed task run (newest first)."""
    _TASKS.insert(0, task)


def all_tasks() -> list["TaskRun"]:
    """Return all task runs, newest first."""
    return list(_TASKS)


def clear() -> None:
    """Clear stored tasks (used in tests)."""
    _TASKS.clear()
