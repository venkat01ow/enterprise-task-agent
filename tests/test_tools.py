"""Tests for individual tool plugins."""
from __future__ import annotations

from app.tools import all_tools, get_tool

USER = {"user_id": "u-test", "role": "employee"}


def test_all_tools_registered():
    names = {tool.name for tool in all_tools()}
    assert {
        "desk_booking",
        "timesheet",
        "leave_request",
        "it_request",
        "approval",
    } <= names


def test_desk_booking_returns_reference():
    tool = get_tool("desk_booking")
    result = tool.run({"floor": "6", "date": "Thursday", "seat": "004"}, USER)
    assert result.success
    assert "Floor 6" in result.summary
    assert result.data["reference"].startswith("DESK-")


def test_timesheet_logs_hours():
    tool = get_tool("timesheet")
    result = tool.run({"hours": 8, "date": "today"}, USER)
    assert result.success
    assert "8 hours" in result.summary
    assert result.data["hours"] == 8


def test_leave_request_pending():
    tool = get_tool("leave_request")
    result = tool.run({"days": 2, "date": "next week"}, USER)
    assert result.success
    assert result.data["state"] == "pending"


def test_it_request_opens_ticket():
    tool = get_tool("it_request")
    result = tool.run({"summary": "VPN not working"}, USER)
    assert result.success
    assert result.data["reference"].startswith("INC-")


def test_manifest_shape():
    tool = get_tool("approval")
    manifest = tool.manifest()
    assert manifest["name"] == "approval"
    assert manifest["required_role"] == "manager"
