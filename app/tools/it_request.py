"""IT support ticket tool (mock implementation)."""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolResult


class ITRequestTool(Tool):
    name = "it_request"
    description = "Raise an IT support ticket (VPN, laptop, access, software, etc.)."
    required_role = "employee"
    examples = [
        "Raise an IT ticket: VPN not working",
        "I need access to the analytics dashboard",
        "Reset my software license",
    ]

    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        token = user.get("access_token")
        if token:
            return self._run_real(params, user, token)
        return self._run_mock(params, user)

    def _run_real(self, params: dict[str, Any], user: dict[str, Any], token: str) -> ToolResult:
        from app.connectors.graph import GraphClient

        summary_text = str(params.get("summary", "IT support request")).strip()
        category = str(params.get("category", "general"))
        title = f"IT request ({category}): {summary_text}"
        try:
            task = GraphClient(token).create_todo_task(
                title=title,
                note="Tracked by Enterprise Task Agent until the IT service desk API is connected.",
            )
        except Exception as exc:  # noqa: BLE001 - surface any Graph failure clearly
            return ToolResult(
                success=False,
                summary=f"Couldn't create the IT request reminder: {exc}",
            )
        return ToolResult(
            success=True,
            summary=(
                f"Logged your IT request in Microsoft To-Do: \"{summary_text}\" ({category}). "
                "Note: filing it directly in the IT service desk (e.g. ServiceNow) needs an "
                "IT-provisioned API (see docs/CONNECTORS.md)."
            ),
            data={"task_id": task.get("id"), "category": category, "request": summary_text},
        )

    def _run_mock(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        summary_text = str(params.get("summary", "IT support request")).strip()
        category = str(params.get("category", "general"))
        ref = f"INC-{abs(hash((user.get('user_id'), summary_text))) % 100000:05d}"
        return ToolResult(
            success=True,
            summary=f"Opened IT ticket {ref} ({category}): \"{summary_text}\". "
            f"You'll receive updates by email.",
            data={"reference": ref, "category": category, "request": summary_text},
        )
