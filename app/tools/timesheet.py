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
        hours = params.get("hours", 8)
        date = str(params.get("date", "today"))
        ref = f"TS-{abs(hash((user.get('user_id'), date, hours))) % 100000:05d}"
        return ToolResult(
            success=True,
            summary=f"Logged {hours} hours for {date}. Timesheet entry: {ref}.",
            data={"reference": ref, "hours": hours, "date": date},
        )
