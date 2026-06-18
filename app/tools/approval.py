"""Approval tool — requires manager role (demonstrates RBAC governance)."""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolResult


class ApprovalTool(Tool):
    name = "approval"
    description = "Approve a pending request (leave, expense, access). Manager only."
    required_role = "manager"
    examples = [
        "Approve the pending leave request",
        "Authorize the access request for John",
    ]

    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        summary_text = str(params.get("summary", "pending request")).strip()
        ref = f"APR-{abs(hash((user.get('user_id'), summary_text))) % 100000:05d}"
        return ToolResult(
            success=True,
            summary=f"Approved: \"{summary_text}\". Approval reference: {ref}.",
            data={"reference": ref, "request": summary_text, "state": "approved"},
        )
