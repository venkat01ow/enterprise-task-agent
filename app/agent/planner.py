"""Intent planner: turns a natural-language message into ordered tool steps.

Two strategies are available:

* **rule_based_plan** — deterministic keyword + regex extraction. Always works,
  needs no network, and powers the offline-safe demo.
* **llm_plan** — asks a configured LLM to produce a JSON plan from the tool
  catalog. Used only when ``LLM_PROVIDER`` is set and a key is present.

``plan`` selects the LLM strategy when enabled and silently falls back to the
rule-based planner on any error, so the agent never fails to respond.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.agent.schemas import PlannedStep
from app.config import settings
from app.tools import all_tools

# ── Parameter extraction helpers ─────────────────────────────────────────────

_DATE_WORDS = [
    "today",
    "tomorrow",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "next week",
    "next monday",
]


def _find_date(text: str) -> str:
    for word in _DATE_WORDS:
        if word in text:
            return word
    match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", text)
    return match.group(1) if match else "today"


def _find_floor(text: str) -> str:
    match = re.search(r"floor\s*(\d{1,2})", text)
    return match.group(1) if match else "6"


def _find_seat(text: str) -> str:
    match = re.search(r"seat\s*([a-z]?\d{1,4})", text)
    return match.group(1) if match else "auto"


def _find_hours(text: str) -> int:
    match = re.search(r"(\d{1,2})\s*(?:hours|hrs|hr|h)\b", text)
    return int(match.group(1)) if match else 8


def _find_days(text: str) -> int:
    match = re.search(r"(\d{1,2})\s*(?:days|day)\b", text)
    return int(match.group(1)) if match else 1


def _has(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


# ── Rule-based planner ───────────────────────────────────────────────────────


def rule_based_plan(message: str, user: dict[str, Any]) -> list[PlannedStep]:
    text = message.lower()
    steps: list[PlannedStep] = []

    # Approval is an exclusive manager action. A phrase like "approve the pending
    # leave request" is about approving — not creating a new leave request — so we
    # short-circuit to a single approval step.
    if _has(text, ["approve", "approval", "authorize", "sign off"]):
        return [
            PlannedStep(
                tool="approval",
                params={"summary": message.strip()},
                rationale="Detected an approval intent.",
            )
        ]

    if _has(text, ["desk", "seat", "reserve", "booking", "book"]) and not _has(
        text, ["leave", "vacation"]
    ):
        steps.append(
            PlannedStep(
                tool="desk_booking",
                params={
                    "floor": _find_floor(text),
                    "date": _find_date(text),
                    "seat": _find_seat(text),
                },
                rationale="Detected a desk / seat booking intent.",
            )
        )

    if _has(text, ["timesheet", "hours", "log", "logging"]):
        steps.append(
            PlannedStep(
                tool="timesheet",
                params={"hours": _find_hours(text), "date": _find_date(text)},
                rationale="Detected a timesheet logging intent.",
            )
        )

    if _has(text, ["leave", "vacation", "pto", "holiday", "time off", "off"]):
        steps.append(
            PlannedStep(
                tool="leave_request",
                params={"days": _find_days(text), "date": _find_date(text)},
                rationale="Detected a leave / time-off intent.",
            )
        )

    if _has(text, ["it", "vpn", "laptop", "access", "reset", "software", "ticket", "wifi"]):
        steps.append(
            PlannedStep(
                tool="it_request",
                params={"summary": message.strip()},
                rationale="Detected an IT support intent.",
            )
        )

    return steps


# ── LLM planner (optional) ───────────────────────────────────────────────────


def _catalog_text() -> str:
    lines = []
    for tool in all_tools():
        lines.append(f"- {tool.name}: {tool.description} (role: {tool.required_role})")
    return "\n".join(lines)


def _build_messages(message: str) -> list[dict[str, str]]:
    system = (
        "You are an enterprise task planner. Given a user request and a catalog "
        "of tools, return a JSON object with a 'steps' array. Each step has "
        "'tool' (one of the catalog names), 'params' (object), and 'rationale' "
        "(short string). Only use tools from the catalog. If nothing matches, "
        "return an empty steps array. Respond with JSON only.\n\n"
        f"Tool catalog:\n{_catalog_text()}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


def _parse_plan(content: str) -> list[PlannedStep]:
    data = json.loads(content)
    raw_steps = data.get("steps", []) if isinstance(data, dict) else []
    valid_names = {tool.name for tool in all_tools()}
    steps: list[PlannedStep] = []
    for item in raw_steps:
        name = item.get("tool")
        if name in valid_names:
            steps.append(
                PlannedStep(
                    tool=name,
                    params=item.get("params", {}) or {},
                    rationale=item.get("rationale", ""),
                )
            )
    return steps


def llm_plan(message: str, user: dict[str, Any]) -> list[PlannedStep]:
    messages = _build_messages(message)
    timeout = settings.request_timeout_seconds

    if settings.llm_provider == "azure":
        url = (
            f"{settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
            f"{settings.azure_openai_deployment}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )
        headers = {"api-key": settings.azure_openai_api_key}
        payload: dict[str, Any] = {"messages": messages, "temperature": 0}
    else:  # openai
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
    content = body["choices"][0]["message"]["content"]
    return _parse_plan(content)


# ── Public entry point ───────────────────────────────────────────────────────


def plan(message: str, user: dict[str, Any]) -> list[PlannedStep]:
    """Return an ordered plan, preferring the LLM when configured."""
    if settings.llm_enabled:
        try:
            return llm_plan(message, user)
        except Exception:
            # Network / parsing / auth issues must never break the demo.
            return rule_based_plan(message, user)
    return rule_based_plan(message, user)
