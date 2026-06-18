"""Leave request tool (mock implementation)."""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolResult


class LeaveRequestTool(Tool):
    name = "leave_request"
    description = "Submit a leave / time-off request for a number of days."
    required_role = "employee"
    examples = [
        "Apply 2 days leave next week",
        "Request time off on Friday",
    ]

    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        days = params.get("days", 1)
        date = str(params.get("date", "next week"))
        ref = f"LV-{abs(hash((user.get('user_id'), date, days))) % 100000:05d}"
        day_label = "day" if days == 1 else "days"
        return ToolResult(
            success=True,
            summary=f"Submitted a leave request for {days} {day_label} starting {date}. "
            f"Reference: {ref} (pending manager approval).",
            data={"reference": ref, "days": days, "date": date, "state": "pending"},
        )
