# Deployment Guide

This guide covers running the Enterprise Task Agent in production. The app is a
stateful FastAPI service: it keeps **server-side sessions** (access tokens never
leave the server) and persists task history + the audit trail to **SQLite**.

---

## 1. Quick start (Docker)

```bash
# 1. Generate a strong session secret
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"

# 2. Build and run
docker compose up --build -d

# 3. Check health
curl http://localhost:8000/api/health     # liveness
curl http://localhost:8000/api/ready       # readiness (DB reachable)
```

The compose file mounts a named volume `eta-data` at `/app/data` so the SQLite
database survives container restarts and rebuilds.

---

## 2. Configuration

All configuration is environment-driven (see [`.env.example`](../.env.example)).
The most important production settings:

| Variable | Purpose | Production value |
| --- | --- | --- |
| `ENVIRONMENT` | Enables production guards | `production` |
| `SESSION_SECRET` | Signs session cookies | **Random 32+ char string** |
| `SESSION_HTTPS_ONLY` | Marks cookies `Secure` | `true` (auto-on in prod) |
| `DB_PATH` | SQLite file location | `/app/data/app.db` |
| `CORS_ALLOW_ORIGINS` | Allowed browser origins | Your front-end origin(s) |
| `TRUSTED_HOSTS` | Allowed `Host` headers | Your domain(s) |
| `HSTS_ENABLED` | Sends HSTS header | `true` behind HTTPS |
| `ENABLE_DOCS` | Exposes `/docs` | `false` (default in prod) |
| `RATE_LIMIT_REQUESTS` | Requests / window / IP | Tune to traffic |
| `LOG_JSON` | Structured JSON logs | `true` |

### Fail-fast validation

When `ENVIRONMENT=production`, the app **refuses to start** if `SESSION_SECRET`
is missing, too short, or still the insecure development default. This prevents
accidentally shipping with a guessable cookie-signing key.

---

## 3. Secrets management

- **Never** commit real secrets. `.env` is git-ignored; only `.env.example` is tracked.
- Inject secrets via your platform's secret store (Docker/Kubernetes secrets,
  AWS SSM, Azure Key Vault, GitHub Actions secrets, etc.).
- Rotate `SESSION_SECRET` and `ENTRA_CLIENT_SECRET` periodically. Rotating the
  session secret invalidates all active sessions (users re-authenticate).

---

## 4. HTTPS & reverse proxy

Run the app behind a TLS-terminating reverse proxy (nginx, Caddy, Traefik, or a
cloud load balancer). The app emits security headers (CSP, HSTS, `X-Frame-Options`,
etc.) and expects HTTPS in production.

Minimal nginx example:

```nginx
location / {
    proxy_pass         http://127.0.0.1:8000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}
```

Set `TRUSTED_HOSTS` to your public domain(s) so the app rejects spoofed `Host`
headers.

---

## 5. Scaling

This service is **single-instance by design**. Sessions and the rate-limiter live
in-process, so the SQLite store and gunicorn run with **one worker** by default.

- **Vertical scaling** (more CPU/RAM on one instance) works out of the box.
- **Horizontal scaling** (multiple workers/replicas) requires shared state:
  - Move sessions to **Redis**.
  - Move task/audit persistence to **PostgreSQL**.
  - Move the rate-limiter to a shared backend (Redis).

  Once shared state is in place, raise `WEB_CONCURRENCY` (gunicorn workers) and
  run multiple replicas behind the load balancer.

The persistence layer is isolated behind [`app/core/db.py`](../app/core/db.py),
[`store.py`](../app/core/store.py) and [`audit.py`](../app/core/audit.py), so
swapping SQLite for Postgres is a contained change.

---

## 6. Health & readiness probes

| Endpoint | Meaning | Use for |
| --- | --- | --- |
| `GET /api/health` | Process is up (no dependencies checked) | Liveness probe |
| `GET /api/ready` | Database is reachable (`SELECT 1`) | Readiness probe / LB |

`/api/ready` returns `503` when the database is unreachable, so load balancers
stop routing traffic until the instance recovers.

Kubernetes example:

```yaml
livenessProbe:
  httpGet: { path: /api/health, port: 8000 }
readinessProbe:
  httpGet: { path: /api/ready, port: 8000 }
```

---

## 7. Persistence & backups

Task history and the audit log live in the SQLite file at `DB_PATH`
(`/app/data/app.db` in Docker), using WAL mode.

- **Back up** by copying the database file (and the `-wal`/`-shm` siblings) or
  using `sqlite3 app.db ".backup backup.db"` for a consistent snapshot.
- In Docker, the `eta-data` volume holds this file; snapshot the volume on your
  schedule.
- The audit trail records every tool invocation with **sensitive parameters
  redacted** (see `redact()` in [`audit.py`](../app/core/audit.py)).

---

## 8. Observability

- Set `LOG_JSON=true` for structured logs that ship cleanly to ELK, Loki,
  CloudWatch, etc.
- Every request is logged with a **request id** (also returned in the
  `X-Request-ID` response header), method, path, status, and duration.
- Tune verbosity with `LOG_LEVEL` (`DEBUG`/`INFO`/`WARNING`/`ERROR`).

---

## 9. Production checklist

- [ ] `ENVIRONMENT=production`
- [ ] Strong random `SESSION_SECRET` injected from a secret store
- [ ] HTTPS terminated by a reverse proxy; `SESSION_HTTPS_ONLY=true`
- [ ] `TRUSTED_HOSTS` and `CORS_ALLOW_ORIGINS` set to your real domains
- [ ] `DB_PATH` points at a persistent volume; backups scheduled
- [ ] `LOG_JSON=true` and logs shipped to your aggregator
- [ ] Liveness (`/api/health`) and readiness (`/api/ready`) probes wired up
- [ ] Entra ID app registration redirect URIs match `ENTRA_REDIRECT_URI`
      (see [AUTH_SETUP.md](AUTH_SETUP.md))
