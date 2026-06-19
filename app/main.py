"""FastAPI application factory.

Wires middleware (security headers, rate limiting, request logging, sessions,
CORS), persistence, the REST/SSE API, auth routes, and the static chat UI.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router
from app.auth.routes import router as auth_router
from app.config import settings
from app.core import db
from app.core.logging_config import configure_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.tools import bootstrap_tools

logger = logging.getLogger("eta")

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistence on startup, release it on shutdown."""
    db.init_db()
    logger.info(
        "Enterprise Task Agent started (env=%s, auth=%s, db=%s)",
        settings.environment,
        settings.auth_enabled,
        settings.db_path,
    )
    yield
    db.close()


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a sanitized 500 so internals never leak to clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def create_app() -> FastAPI:
    configure_logging()
    for warning in settings.validate_runtime():
        logger.warning("Config warning: %s", warning)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_exception_handler(Exception, _unhandled_exception_handler)

    # Middleware. Order matters: the LAST added is the OUTERMOST. Final stack
    # (outer→inner): TrustedHost → SecurityHeaders → CORS → RequestContext →
    # RateLimit → Session → routes.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=settings.session_cookie,
        https_only=settings.secure_cookies,
        same_site="lax",
        max_age=settings.session_max_age_seconds,
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.trusted_hosts_list:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

    bootstrap_tools()
    app.include_router(router)
    app.include_router(auth_router)

    # Serve the chat UI at the root. Mounted last so /api/* and /auth/* win.
    if _FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
