"""Pure-ASGI middleware: security headers, request context/logging, rate limit.

Implemented at the ASGI layer (rather than Starlette's BaseHTTPMiddleware) so
they compose cleanly with streaming responses such as the SSE chat endpoint.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings

logger = logging.getLogger("eta.access")


class SecurityHeadersMiddleware:
    """Add hardening response headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                if settings.csp_policy:
                    headers["Content-Security-Policy"] = settings.csp_policy
                if settings.hsts_active:
                    headers["Strict-Transport-Security"] = (
                        "max-age=63072000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestContextMiddleware:
    """Assign a request id, set the X-Request-ID header, and log each request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex[:16]
        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            client = scope.get("client")
            logger.info(
                "%s %s -> %s (%sms)",
                scope.get("method"),
                scope.get("path"),
                status_holder["code"],
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_holder["code"],
                    "duration_ms": duration_ms,
                    "client": client[0] if client else None,
                },
            )


class RateLimitMiddleware:
    """Simple in-process sliding-window rate limiter, keyed by client IP.

    Applies to ``/api`` and ``/auth/login``. Sufficient for a single instance;
    for multiple instances use a shared store (e.g. Redis).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _limited(self, key: str) -> bool:
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_requests
        now = time.time()
        bucket = self._hits[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False

    def reset(self) -> None:
        self._hits.clear()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not (path.startswith("/api") or path == "/auth/login"):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        ip = client[0] if client else "unknown"
        if self._limited(ip):
            response = JSONResponse(
                {"detail": "Rate limit exceeded. Please slow down and try again."},
                status_code=429,
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
