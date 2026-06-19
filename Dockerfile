# syntax=docker/dockerfile:1

# ── Build stage: install dependencies into an isolated prefix ──────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage: copy deps, run as non-root ─────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    PORT=8000 \
    DB_PATH=/app/data/app.db

WORKDIR /app

# Non-root user for least privilege.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /install /usr/local
COPY . .

# Writable data dir for the SQLite store (mount a volume here in production).
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

# Gunicorn manages a uvicorn worker for robust production serving.
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
