# Enterprise Task Agent

> A role-aware **Agentic AI** assistant that turns plain-language requests into completed enterprise tasks — desk booking, timesheet logging, leave requests, and IT support — with planning, tool execution, RBAC, audit trails, and real-time progress streaming.

Built for the **AEH Federal Hackathon** · Category: **Agentic AI** · Sub-category: **Tool-Using Agents (APIs, Databases, Applications)**.

---

## What it does

Ask in natural language → the agent **plans** the steps, **executes** the right tools, enforces **role-based access**, records an **audit trail**, and streams **live progress** back to the UI.

```
"Book a desk on Floor 6 for Thursday and log 8 hours today"
        │
        ▼
  ┌──────────────┐   plan    ┌──────────────┐  execute  ┌──────────────┐
  │   Planner    │ ────────▶ │ Orchestrator │ ────────▶ │ Tool Plugins │
  │ (rules/LLM)  │           │  + RBAC      │           │ desk/time/.. │
  └──────────────┘           └──────┬───────┘           └──────┬───────┘
                                    │ audit + SSE               │
                                    ▼                           ▼
                              Live status: running → completed / failed / denied
```

## Why it wins

- **True agentic flow** — plans and executes multi-step actions, not just chat.
- **Real or demo-proof** — sign in with **Microsoft** for real Microsoft 365 actions, or run fully offline in deterministic **mock mode** (no keys needed).
- **Governance built-in** — RBAC denial + redacted audit log for every action.
- **Measurable impact** — minutes saved per task × tasks × employees.

---

## Quick start (Windows PowerShell)

```powershell
# 1. Create & activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (serves API + chat UI)
python run.py
```

Then open http://127.0.0.1:8000 and try a suggestion chip.

> Default mode needs **no API keys** — it uses deterministic mock tools and a rule-based planner so your demo never fails on stage.

### Run with Docker

```powershell
docker compose up --build
# open http://127.0.0.1:8000
```

### Run tests

```powershell
pip install -r requirements-dev.txt
pytest -q
```

---

## Try these prompts

| Prompt | What the agent does |
|--------|---------------------|
| `Book a desk on Floor 6 for Thursday` | Reserves a seat, returns a confirmation ref |
| `Log 8 hours today` | Submits a timesheet entry |
| `Apply 2 days leave next week` | Files a leave request |
| `Raise an IT ticket: VPN not working` | Opens an IT support ticket |
| `Book a desk tomorrow and log 8 hours` | **Multi-step** plan in one request |
| `Approve the pending request` (as employee) | **Denied** — demonstrates RBAC governance |

Switch the **role** selector to `manager` to see the approval tool succeed.

---

## Enabling real AI (optional)

By default the planner is rule-based. To use a real LLM for planning, set environment variables (see [.env.example](.env.example)):

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Azure OpenAI is also supported (`LLM_PROVIDER=azure`). If the LLM call fails for any reason, the agent **automatically falls back** to the rule-based planner — so the demo is always safe.

---

## Real Microsoft sign-in + Microsoft 365 actions

The agent runs in two modes, auto-detected from your configuration:

| Mode | When | Sign-in | Tool actions |
|------|------|---------|--------------|
| **Dev / demo** | no Entra config | role dropdown | deterministic mocks |
| **Live** | Entra app configured | **Sign in with Microsoft** | **real Microsoft 365** |

In **Live** mode, each user authenticates with their own Microsoft work account
(OAuth2 Authorization Code + **PKCE** via MSAL — the app never sees a password),
and the agent acts **on their behalf** through the **Microsoft Graph** API:

| Request | Real action performed |
|---------|----------------------|
| `Book a desk on Floor 6 for Thursday` | Creates a **calendar hold** (09:00–18:00) in your Outlook calendar |
| `Apply 2 days leave next week` | Adds an **all-day Leave event** to your calendar |
| `Log 8 hours today` | Creates a **Microsoft To-Do** reminder |
| `Raise an IT ticket: VPN not working` | Creates a **Microsoft To-Do** item |

Manager/admin roles can be driven by **Entra app roles** (`TaskAgent.Manager`,
`TaskAgent.Admin`) instead of the dropdown.

**Security:** access tokens are kept **server-side**; the browser cookie holds
only a signed, opaque session id (never a token). Tokens never appear in SSE
events or the audit log.

▶ **Setup (5 minutes):** [docs/AUTH_SETUP.md](docs/AUTH_SETUP.md) walks through the
Azure app registration, Graph permissions, and `.env` values.

### Connecting internal enterprise portals

Real calendar/To-Do actions work out of the box. Internal corporate systems
(e.g. the seat-booking portal, HR leave, ServiceNow) require an **officially
IT-provisioned API** — the connector framework and config hooks are ready for
them. See [docs/CONNECTORS.md](docs/CONNECTORS.md) for the extension points and the
security boundaries this project deliberately respects (no password harvesting,
no bypassing access controls).

---

## Architecture & docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, data flow, extension points
- [docs/AUTH_SETUP.md](docs/AUTH_SETUP.md) — Microsoft Entra ID sign-in + Microsoft 365 setup
- [docs/CONNECTORS.md](docs/CONNECTORS.md) — real vs. mock actions and enterprise API extension points
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — exact demo walkthrough for judges

## Project layout

```
enterprise-task-agent/
├── app/
│   ├── main.py              # FastAPI app factory + session + static UI mount
│   ├── config.py            # Settings (env-driven)
│   ├── agent/               # schemas, planner, orchestrator
│   ├── auth/                # Entra ID (MSAL) sign-in, session store, identity
│   ├── connectors/          # Microsoft Graph client (real M365 actions)
│   ├── tools/               # tool plugins (real + mock) + registry
│   ├── core/                # rbac, audit, in-memory store
│   └── api/                 # REST + SSE routes
├── frontend/                # vanilla chat UI with Microsoft sign-in (no build step)
├── tests/                   # pytest suite
├── run.py                   # dev launcher
├── Dockerfile / docker-compose.yml
└── requirements*.txt
```

## License

MIT — see [LICENSE](LICENSE).
