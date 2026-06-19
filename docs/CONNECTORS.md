# Connectors: what's real, and how to add enterprise systems

The agent performs **real actions** through connectors. Today it ships with a
fully working **Microsoft Graph** connector and a documented extension point for
**official, IT-provisioned enterprise APIs** (such as Accenture's internal
portals).

## How a tool decides real vs. mock

Each tool receives the acting `user`. If that user has a delegated
`access_token` (i.e. they signed in with Microsoft), the tool calls the real
connector; otherwise it falls back to a safe mock so the project always runs
offline for demos and tests.

```text
user has access_token?  ──yes──▶  real Microsoft Graph call
        │
        └──no───────────────────▶  deterministic mock result
```

## Microsoft Graph connector (real, included)

`app/connectors/graph.py` uses the signed-in user's delegated token to:

| Tool             | Real Microsoft 365 action                                   |
| ---------------- | ----------------------------------------------------------- |
| `desk_booking`   | Creates a calendar event (09:00–18:00 hold) via `/me/events`|
| `leave_request`  | Creates an all-day **Leave** calendar event                 |
| `timesheet`      | Creates a Microsoft **To-Do** reminder                      |
| `it_request`     | Creates a Microsoft **To-Do** item for the request          |
| (profile)        | Reads `/me` for display name and identity                   |

These are genuine, auditable changes in the user's own Microsoft 365 account.
See [AUTH_SETUP.md](AUTH_SETUP.md) to enable them.

## Enterprise systems (e.g. Accenture seat booking, HR leave, ServiceNow)

Internal corporate portals — for example the seat-booking app at
`acpindia-mobile.accenture.com`, the HR leave system, or the IT service desk —
are **not** open APIs. Integrating with them correctly and securely requires an
**officially provisioned API** from the owning IT organization, typically:

1. An API/OAuth client registered with the enterprise (client id + scopes),
   often fronted by an API gateway or Azure API Management.
2. Delegated or app permissions granted by IT/security governance.
3. A published, supported endpoint contract (OpenAPI/Swagger).

When that is available, add a connector beside `graph.py` and point the tool's
real path at it. The configuration hooks already exist:

```dotenv
ACCENTURE_API_BASE_URL=https://<provisioned-gateway>/seat-booking
ACCENTURE_API_SCOPE=api://<app-id>/.default
```

```python
# app/connectors/accenture.py  (sketch — fill in once IT provides the contract)
class AccentureSeatClient:
    def __init__(self, access_token: str): ...
    def reserve_seat(self, floor: str, date: str, seat: str): ...
```

### What this project will *not* do

To stay within security and acceptable-use boundaries, this project will **not**:

- Harvest or store users' corporate passwords.
- Script/automate the human login of internal SSO portals at scale to
  impersonate users.
- Bypass authentication, MFA, or access controls on systems we don't own.

Those approaches are brittle and violate enterprise security policy. The
supported, durable path is an IT-provisioned API, which the connector framework
above is ready to consume. Until then, the agent does the closest legitimate
real action (e.g. a calendar hold) and tells the user exactly what happened.
