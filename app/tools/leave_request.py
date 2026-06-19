"""Leave request tool (mock implementation)."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.config import settings
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
        token = user.get("access_token")
        if token:
            return self._run_real(params, user, token)
        return self._run_mock(params, user)

    def _run_real(self, params: dict[str, Any], user: dict[str, Any], token: str) -> ToolResult:
        from app.connectors.graph import GraphClient, GraphError
        from app.tools.dates import resolve_date

        days = int(params.get("days", 1) or 1)
        start_day = resolve_date(str(params.get("date", "next week")))
        end_day = start_day + timedelta(days=days)
        start_iso = f"{start_day.isoformat()}T00:00:00"
        end_iso = f"{end_day.isoformat()}T00:00:00"
        day_label = "day" if days == 1 else "days"
        try:
            event = GraphClient(token).create_event(
                subject="Leave / Out of office",
                start_iso=start_iso,
                end_iso=end_iso,
                timezone=settings.default_timezone,
                body="Leave hold created by Enterprise Task Agent.",
                all_day=True,
            )
        except GraphError as exc:
            return ToolResult(
                success=False,
                summary=f"Couldn't add the leave hold to your calendar: {exc}",
            )
        return ToolResult(
            success=True,
            summary=(
                f"Added an all-day 'Leave' hold to your calendar for {days} {day_label} "
                f"starting {start_day.isoformat()}. Note: formal approval via the HR leave "
                "system needs an IT-provisioned API (see docs/CONNECTORS.md)."
            ),
            data={
                "event_id": event.get("id"),
                "web_link": event.get("webLink"),
                "days": days,
                "date": start_day.isoformat(),
            },
        )

    def _run_mock(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
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
