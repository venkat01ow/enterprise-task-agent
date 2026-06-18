"""Agent orchestrator: plan -> RBAC check -> execute -> audit -> persist.

Exposes a synchronous ``run_task`` (used by the REST endpoint and tests) and an
asynchronous ``iter_task_events`` generator (used by the SSE endpoint to stream
progressive status updates to the UI).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from app.agent.planner import plan as make_plan
from app.agent.schemas import StepResult, TaskRun
from app.core import audit
from app.core.rbac import can_use
from app.core.store import save_task
from app.tools import get_tool

# Small delay between streamed steps so the UI shows progressive execution.
_STEP_DELAY_SECONDS = 0.6


def _execute_step(tool_name: str, params: dict[str, Any], user: dict[str, Any]) -> StepResult:
    """Run a single planned step with RBAC enforcement and audit recording."""
    tool = get_tool(tool_name)
    role = user.get("role", "employee")

    if tool is None:
        return StepResult(tool=tool_name, status="failed", summary="Unknown tool.")

    if not can_use(role, tool.required_role):
        audit.record(user, tool.name, "denied", params)
        return StepResult(
            tool=tool.name,
            status="denied",
            summary=(
                f"Access denied: role '{role}' cannot use '{tool.name}'. "
                f"Requires '{tool.required_role}'."
            ),
        )

    try:
        result = tool.run(params, user)
        status = "completed" if result.success else "failed"
        audit.record(user, tool.name, status, params)
        return StepResult(tool=tool.name, status=status, summary=result.summary, data=result.data)
    except Exception as exc:  # defensive: a tool bug must not crash the request
        audit.record(user, tool.name, "failed", params)
        return StepResult(tool=tool.name, status="failed", summary=f"Error: {exc}")


def _overall_status(results: list[StepResult]) -> str:
    if not results:
        return "empty"
    statuses = {r.status for r in results}
    if statuses == {"completed"}:
        return "completed"
    if "completed" in statuses:
        return "partial"
    return "failed"


def _new_task(message: str, user: dict[str, Any], results: list[StepResult]) -> TaskRun:
    return TaskRun(
        id=f"task-{uuid.uuid4().hex[:8]}",
        user_id=user.get("user_id", "u-001"),
        message=message,
        steps=results,
        status=_overall_status(results),  # type: ignore[arg-type]
        created_at=datetime.now(timezone.utc),
    )


def run_task(message: str, user: dict[str, Any]) -> TaskRun:
    """Plan and execute a request synchronously, returning the completed run."""
    steps = make_plan(message, user)
    results = [_execute_step(s.tool, s.params, user) for s in steps]
    task = _new_task(message, user, results)
    save_task(task)
    return task


async def iter_task_events(message: str, user: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """Yield progressive events for SSE: plan -> step_started/finished -> done."""
    steps = make_plan(message, user)
    yield {
        "type": "plan",
        "data": {"count": len(steps), "steps": [s.model_dump() for s in steps]},
    }

    if not steps:
        yield {
            "type": "info",
            "data": {
                "message": (
                    "I couldn't find an actionable task. Try: "
                    "'Book a desk on Floor 6 for Thursday' or 'Log 8 hours today'."
                )
            },
        }

    results: list[StepResult] = []
    for step in steps:
        yield {
            "type": "step_started",
            "data": {"tool": step.tool, "params": step.params, "rationale": step.rationale},
        }
        await asyncio.sleep(_STEP_DELAY_SECONDS)
        result = _execute_step(step.tool, step.params, user)
        results.append(result)
        yield {"type": "step_finished", "data": result.model_dump()}

    task = _new_task(message, user, results)
    save_task(task)
    yield {"type": "done", "data": task.model_dump(mode="json")}
