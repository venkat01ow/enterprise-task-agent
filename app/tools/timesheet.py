"""Timesheet logging tool (mock implementation)."""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolResult


class TimesheetTool(Tool):
    name = "timesheet"
    description = "Log working hours to the timesheet for a given date."
    required_role = "employee"
    examples = [
        "Log 8 hours today",
        "Fill my timesheet with 6 hours for Friday",
    ]

    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        token = user.get("access_token")
        if token:
            return self._run_real(params, user, token)
        return self._run_mock(params, user)

    def _run_real(self, params: dict[str, Any], user: dict[str, Any], token: str) -> ToolResult:
        from app.connectors.graph import GraphClient, GraphError
        from app.tools.dates import resolve_date

        hours = params.get("hours", 8)
        when = resolve_date(str(params.get("date", "today")))
        title = f"Timesheet: log {hours} hours for {when.isoformat()}"
        try:
            task = GraphClient(token).create_todo_task(
                title=title,
                note="Reminder created by Enterprise Task Agent.",
                due_date=when.isoformat(),
            )
        except GraphError as exc:
            return ToolResult(
                success=False,
                summary=f"Couldn't create the timesheet reminder: {exc}",
            )
        return ToolResult(
            success=True,
            summary=(
                f"Created a Microsoft To-Do reminder to log {hours} hours for {when.isoformat()}. "
                "Note: posting to the official timesheet system needs an IT-provisioned API "
                "(see docs/CONNECTORS.md)."
            ),
            data={"task_id": task.get("id"), "hours": hours, "date": when.isoformat()},
        )

    def _run_mock(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        hours = params.get("hours", 8)
        date = str(params.get("date", "today"))
        ref = f"TS-{abs(hash((user.get('user_id'), date, hours))) % 100000:05d}"
        return ToolResult(
            success=True,
            summary=f"Logged {hours} hours for {date}. Timesheet entry: {ref}.",
            data={"reference": ref, "hours": hours, "date": date},
        )
