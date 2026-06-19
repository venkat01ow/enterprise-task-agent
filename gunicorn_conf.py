"""Gunicorn configuration for production serving.

Runs the FastAPI app under a uvicorn worker. Defaults to a SINGLE worker
because the server-side session store and rate limiter are in-process; running
multiple workers requires a shared store (e.g. Redis). Scale vertically, or add
a shared backend and raise WEB_CONCURRENCY.
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("WEB_TIMEOUT", "60"))
graceful_timeout = 30
keepalive = 5
max_requests = int(os.getenv("WEB_MAX_REQUESTS", "1000"))
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
