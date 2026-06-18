"""FastAPI application factory.

Mounts the REST/SSE API and serves the static chat UI from ``frontend/``.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.tools import bootstrap_tools

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bootstrap_tools()
    app.include_router(router)

    # Serve the chat UI at the root. Mounted last so /api/* routes win.
    if _FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
