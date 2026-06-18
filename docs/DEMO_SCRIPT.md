# Demo Script — Enterprise Task Agent

A tight 3–4 minute walkthrough designed to score on **agentic behavior**,
**working prototype**, **governance**, and **business impact**.

## Setup (before you present)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000. Keep the **role** selector on `employee`.

## 1. The hook (20s)

> "Employees lose time every day jumping between portals for routine tasks —
> booking desks, logging hours, raising IT tickets. Our agent does it from one
> sentence."

## 2. Single task (30s)

Type or click: **"Book a desk on Floor 6 for Thursday"**

Point out:
- The agent **plans** the step, then shows it **executing** (spinner →✓).
- It returns a real **confirmation reference**.

## 3. Multi-step agentic plan (40s)

Click: **"Book a desk on Floor 6 tomorrow and log 8 hours"**

> "One request, two actions. The agent planned and executed both — this is
> agentic orchestration, not a single API call."

## 4. Governance / RBAC (40s)

With role = `employee`, click: **"Approve the pending leave request"**

> "The agent refuses — approvals require a manager. Every attempt is logged."

Switch role to `manager`, send it again → it now **succeeds**.

Open **Audit log** (footer link) to show the recorded, redacted trail.

## 5. Business impact (30s)

> "Each task saved ~3–5 minutes of navigation. Across thousands of employees
> and daily tasks, that's a measurable productivity and cost saving — and a
> fully auditable one."

## 6. How it's built (20s)

> "Built with GitHub Copilot. FastAPI agent core, a pluggable tool registry,
> RBAC and audit on the execution path, and real-time SSE streaming. It runs
> offline in mock mode, and plugs into a real LLM with one environment variable."

## Backup plan

- Everything runs in **mock mode** — no network needed.
- If the browser SSE stalls, refresh once; task history persists at
  `/api/tasks`.
- API docs at `/docs` provide a fallback live demo via Swagger UI.

## Talking points (judging criteria map)

| Criterion | Evidence in demo |
|-----------|------------------|
| Agentic AI | Multi-step plan + tool execution |
| Working prototype | Live, end-to-end, on localhost |
| Innovation | Role-aware tool-using agent with audit |
| Business value | Time saved × tasks × employees |
| Built with Copilot | Codebase scaffolded with Copilot |
