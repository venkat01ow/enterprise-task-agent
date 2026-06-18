"""Pydantic schemas shared across the agent pipeline."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

StepStatus = Literal["completed", "failed", "denied"]
TaskStatus = Literal["completed", "failed", "partial", "empty"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = "u-001"
    role: str = "employee"


class PlannedStep(BaseModel):
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class StepResult(BaseModel):
    tool: str
    status: StepStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)


class TaskRun(BaseModel):
    id: str
    user_id: str
    message: str
    steps: list[StepResult] = Field(default_factory=list)
    status: TaskStatus = "completed"
    created_at: datetime
