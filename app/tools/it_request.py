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
        summary_text = str(params.get("summary", "IT support request")).strip()
        category = str(params.get("category", "general"))
        ref = f"INC-{abs(hash((user.get('user_id'), summary_text))) % 100000:05d}"
        return ToolResult(
            success=True,
            summary=f"Opened IT ticket {ref} ({category}): \"{summary_text}\". "
            f"You'll receive updates by email.",
            data={"reference": ref, "category": category, "request": summary_text},
        )
