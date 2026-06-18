"""REST + SSE routes for the Enterprise Task Agent."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.agent.orchestrator import iter_task_events, run_task
from app.agent.schemas import ChatRequest, TaskRun
from app.config import settings
from app.core import audit
from app.core.store import all_tasks
from app.tools import all_tools

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
    }


@router.get("/tools")
def list_tools() -> dict[str, object]:
    return {"tools": [tool.manifest() for tool in all_tools()]}


@router.post("/chat", response_model=TaskRun)
def chat(request: ChatRequest) -> TaskRun:
    """Plan and execute a request synchronously, returning the full task run."""
    user = {"user_id": request.user_id, "role": request.role}
    return run_task(request.message, user)


@router.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., min_length=1, max_length=2000),
    role: str = Query("employee"),
    user_id: str = Query("u-001"),
) -> StreamingResponse:
    """Stream progressive task events as Server-Sent Events (SSE)."""
    user = {"user_id": user_id, "role": role}

    async def event_source() -> AsyncIterator[str]:
        async for event in iter_task_events(message, user):
            payload = json.dumps(event["data"])
            yield f"event: {event['type']}\ndata: {payload}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_source(), media_type="text/event-stream", headers=headers)


@router.get("/tasks")
def list_tasks() -> dict[str, object]:
    return {"tasks": [task.model_dump(mode="json") for task in all_tasks()]}


@router.get("/audit")
def list_audit() -> dict[str, object]:
    return {"entries": audit.all_entries()}
