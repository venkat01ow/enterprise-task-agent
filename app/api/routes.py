"""REST + SSE routes for the Enterprise Task Agent."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.orchestrator import iter_task_events, run_task
from app.agent.schemas import ChatRequest, TaskRun
from app.auth.identity import build_user
from app.config import settings
from app.core import audit, db
from app.core.store import all_tasks
from app.tools import all_tools

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe — process is up. No external dependencies checked."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "auth_enabled": settings.auth_enabled,
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
    }


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness probe — checks dependencies (database) before taking traffic."""
    db_ok = db.ping()
    checks = {"database": db_ok}
    ready_now = all(checks.values())
    return JSONResponse(
        status_code=200 if ready_now else 503,
        content={"status": "ready" if ready_now else "not_ready", "checks": checks},
    )


@router.get("/tools")
def list_tools() -> dict[str, object]:
    return {"tools": [tool.manifest() for tool in all_tools()]}


@router.post("/chat", response_model=TaskRun)
def chat(payload: ChatRequest, request: Request) -> TaskRun:
    """Plan and execute a request synchronously, returning the full task run.

    When Microsoft sign-in is configured, the acting user (and their Graph
    access token) is taken from the authenticated session; the role/user_id in
    the request body are ignored. In offline dev mode the body values are used.
    """
    user = build_user(request, dev_role=payload.role, dev_user_id=payload.user_id)
    return run_task(payload.message, user)


@router.get("/chat/stream")
async def chat_stream(
    request: Request,
    message: str = Query(..., min_length=1, max_length=2000),
    role: str = Query("employee"),
    user_id: str = Query("u-001"),
) -> StreamingResponse:
    """Stream progressive task events as Server-Sent Events (SSE)."""
    user = build_user(request, dev_role=role, dev_user_id=user_id)

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
