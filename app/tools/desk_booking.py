"""Desk / seat booking tool (mock implementation)."""
from __future__ import annotations

from typing import Any

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
