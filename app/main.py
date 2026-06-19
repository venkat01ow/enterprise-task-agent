"""FastAPI application factory.

Mounts the REST/SSE API and serves the static chat UI from ``frontend/``.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router
from app.auth.routes import router as auth_router
from app.config import settings
from app.tools import bootstrap_tools

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    # Signed session cookie. It carries only an opaque session id + transient
    # sign-in state — never an access token (those live server-side).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=settings.session_cookie,
        https_only=settings.session_https_only,
        same_site="lax",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bootstrap_tools()
    app.include_router(router)
    app.include_router(auth_router)

    # Serve the chat UI at the root. Mounted last so /api/* and /auth/* win.
    if _FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
