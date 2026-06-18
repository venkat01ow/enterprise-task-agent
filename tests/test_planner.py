"""Tests for the rule-based planner."""
from __future__ import annotations

from app.agent.planner import rule_based_plan

USER = {"user_id": "u-test", "role": "employee"}


def _tools(message: str) -> list[str]:
    return [step.tool for step in rule_based_plan(message, USER)]


def test_desk_booking_intent():
    plan = rule_based_plan("Book a desk on Floor 6 for Thursday", USER)
    assert plan[0].tool == "desk_booking"
    assert plan[0].params["floor"] == "6"
    assert plan[0].params["date"] == "thursday"


def test_timesheet_intent():
    plan = rule_based_plan("Log 8 hours today", USER)
    assert plan[0].tool == "timesheet"
    assert plan[0].params["hours"] == 8


def test_leave_intent():
    assert "leave_request" in _tools("Apply 2 days leave next week")


def test_it_intent():
    assert "it_request" in _tools("Raise an IT ticket: VPN not working")


def test_multi_step_plan():
    tools = _tools("Book a desk on Floor 6 tomorrow and log 8 hours")
    assert "desk_booking" in tools
    assert "timesheet" in tools


def test_no_match_returns_empty():
    assert rule_based_plan("Tell me a joke about the weather", USER) == []
