"""Tool registry and bootstrap.

Tools register themselves into a process-wide registry. ``bootstrap_tools`` is
idempotent and called once at app startup (and lazily by accessors so tests work
without explicit setup).
"""
from __future__ import annotations

from app.tools.approval import ApprovalTool
from app.tools.base import Tool, ToolResult
from app.tools.desk_booking import DeskBookingTool
from app.tools.it_request import ITRequestTool
from app.tools.leave_request import LeaveRequestTool
from app.tools.timesheet import TimesheetTool

_REGISTRY: dict[str, Tool] = {}

_TOOL_CLASSES = [
    DeskBookingTool,
    TimesheetTool,
    LeaveRequestTool,
    ITRequestTool,
    ApprovalTool,
]


def register(tool: Tool) -> None:
    _REGISTRY[tool.name] = tool


def bootstrap_tools() -> None:
    """Populate the registry once. Safe to call multiple times."""
    if _REGISTRY:
        return
    for cls in _TOOL_CLASSES:
        register(cls())


def get_tool(name: str) -> Tool | None:
    bootstrap_tools()
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    bootstrap_tools()
    return list(_REGISTRY.values())


__all__ = [
    "Tool",
    "ToolResult",
    "register",
    "bootstrap_tools",
    "get_tool",
    "all_tools",
]
