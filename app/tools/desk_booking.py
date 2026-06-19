"""Desk / seat booking tool (mock implementation)."""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.tools.base import Tool, ToolResult


def _reference(*parts: Any) -> str:
    return f"DESK-{abs(hash(parts)) % 100000:05d}"


class DeskBookingTool(Tool):
    name = "desk_booking"
    description = "Book a desk or seat for a given date and floor."
    required_role = "employee"
    examples = [
        "Book a desk on Floor 6 for Thursday",
        "Reserve seat 004 tomorrow",
        "Book a desk for next Monday",
    ]

    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        token = user.get("access_token")
        if token:
            return self._run_real(params, user, token)
        return self._run_mock(params, user)

    def _run_real(self, params: dict[str, Any], user: dict[str, Any], token: str) -> ToolResult:
        from app.connectors.graph import GraphClient, GraphError
        from app.tools.dates import resolve_date, work_window

        floor = str(params.get("floor", "6"))
        seat = str(params.get("seat", "auto"))
        when = resolve_date(str(params.get("date", "today")))
        start_iso, end_iso = work_window(when)
        subject = f"Desk \u2014 Floor {floor}" + ("" if seat == "auto" else f" \u00b7 seat {seat}")
        try:
            event = GraphClient(token).create_event(
                subject=subject,
                start_iso=start_iso,
                end_iso=end_iso,
                timezone=settings.default_timezone,
                body="Desk reservation hold created by Enterprise Task Agent.",
                location=f"Floor {floor}",
            )
        except GraphError as exc:
            return ToolResult(
                success=False,
                summary=f"Couldn't create the desk hold in your calendar: {exc}",
            )
        return ToolResult(
            success=True,
            summary=(
                f"Created a calendar hold '{subject}' for {when.isoformat()} (09:00\u201318:00). "
                "Note: reserving the physical seat in the corporate portal needs an "
                "IT-provisioned API (see docs/CONNECTORS.md)."
            ),
            data={
                "event_id": event.get("id"),
                "web_link": event.get("webLink"),
                "floor": floor,
                "date": when.isoformat(),
                "seat": seat,
            },
        )

    def _run_mock(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        floor = str(params.get("floor", "6"))
        date = str(params.get("date", "today"))
        seat = str(params.get("seat", "auto"))
        ref = _reference(user.get("user_id"), date, floor, seat)
        seat_label = "an available seat" if seat == "auto" else f"seat {seat}"
        return ToolResult(
            success=True,
            summary=f"Booked {seat_label} on Floor {floor} for {date}. Confirmation: {ref}.",
            data={"reference": ref, "floor": floor, "date": date, "seat": seat},
        )
