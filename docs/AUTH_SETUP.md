# Authentication & Microsoft 365 setup

This guide turns the Enterprise Task Agent from offline **dev mode** (mock
actions, role dropdown) into a **fully functional** app: real Microsoft sign-in
and real Microsoft 365 actions (calendar holds, To-Do items) performed on the
signed-in user's behalf.

Everything is driven by a standard **Microsoft Entra ID (Azure AD) app
registration** plus delegated Microsoft Graph permissions. No passwords ever
touch this app — users authenticate directly with Microsoft.

---

## 1. Register an application in Microsoft Entra ID

1. Go to the [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** →
   **App registrations** → **New registration**.
2. **Name:** `Enterprise Task Agent`.
3. **Supported account types:** *Accounts in this organizational directory only*
   (single tenant) is the simplest and most secure choice.
4. **Redirect URI:** platform **Web**, value:
   ```
   http://localhost:8000/auth/callback
   ```
   > Use `localhost` (not `127.0.0.1`) so it matches what the app sends.
5. Click **Register**.

From the app's **Overview** page, copy:
- **Application (client) ID** → `ENTRA_CLIENT_ID`
- **Directory (tenant) ID** → `ENTRA_TENANT_ID`

## 2. Create a client secret

1. App → **Certificates & secrets** → **New client secret**.
2. Add a description and expiry, then **Add**.
3. Copy the secret **Value** immediately (it is shown only once) →
   `ENTRA_CLIENT_SECRET`.

## 3. Add delegated Microsoft Graph permissions

App → **API permissions** → **Add a permission** → **Microsoft Graph** →
**Delegated permissions**. Add:

| Permission            | Why the agent needs it                     |
| --------------------- | ------------------------------------------ |
| `User.Read`           | Read the signed-in user's basic profile    |
| `Calendars.ReadWrite` | Create desk / leave calendar holds         |
| `Mail.Send`           | Send mail on the user's behalf (optional)  |
| `Tasks.ReadWrite`     | Create Microsoft To-Do items               |
| `openid`, `profile`, `offline_access` | Sign-in basics (added automatically) |

Click **Grant admin consent** if your tenant requires it. Otherwise each user
consents on first sign-in.

## 4. (Optional) Define app roles for manager / admin

To let Entra decide who is a **manager** or **admin** (instead of the dev
dropdown):

1. App → **App roles** → **Create app role** twice:
   - Display name `Task Agent Manager`, value **`TaskAgent.Manager`**, allowed
     member types *Users/Groups*.
   - Display name `Task Agent Admin`, value **`TaskAgent.Admin`**.
2. **Microsoft Entra ID** → **Enterprise applications** → your app → **Users and
   groups** → assign people to those roles.

Signed-in users carry these in their token's `roles` claim, and the agent maps
them automatically (`TaskAgent.Admin` → admin, `TaskAgent.Manager` → manager,
everyone else → employee). The names are configurable via `ROLE_CLAIM_ADMIN` /
`ROLE_CLAIM_MANAGER`.

## 5. Fill in `.env`

Copy `.env.example` to `.env` and set:

```dotenv
ENTRA_TENANT_ID=<your tenant id>
ENTRA_CLIENT_ID=<your client id>
ENTRA_CLIENT_SECRET=<your client secret>
ENTRA_REDIRECT_URI=http://localhost:8000/auth/callback
ENTRA_POST_LOGOUT_REDIRECT_URI=http://localhost:8000/

SESSION_SECRET=<a long random string>     # e.g. python -c "import secrets;print(secrets.token_urlsafe(48))"
DEFAULT_TIMEZONE=Asia/Kolkata
```

The app auto-detects these: when tenant + client id + secret are all present,
`auth_enabled` becomes `true`, the UI shows **Sign in with Microsoft**, and the
tools switch from mock output to real Graph calls.

## 6. Run

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://localhost:8000>, click **Sign in with Microsoft**, consent once,
and try:

- *"Book a desk on Floor 6 for Thursday"* → a calendar hold appears in **your**
  Outlook/Microsoft 365 calendar.
- *"Apply 2 days leave next week"* → an all-day **Leave** event is added.
- *"Log 8 hours today"* / *"Raise an IT ticket: VPN not working"* → tracked
  Microsoft **To-Do** items.

---

## Security notes

- **No password access.** The app uses the OAuth2 Authorization Code flow with
  PKCE; users sign in on Microsoft's own pages.
- **Tokens stay server-side.** The browser cookie holds only a signed, opaque
  session id. Access tokens live in a server-side store, never in the cookie and
  never in SSE payloads or the audit log.
- **Least privilege.** Only delegated scopes the agent actually uses are
  requested. Remove `Mail.Send` if you don't want the agent able to email.
- **Production:** set a strong `SESSION_SECRET`, set `SESSION_HTTPS_ONLY=true`
  behind HTTPS, and register your real redirect URI in Azure.
