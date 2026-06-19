"""Application configuration loaded from environment variables / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_name: str = "Enterprise Task Agent"
    environment: str = "development"

    # Tooling
    use_mock_tools: bool = True

    # Planner / LLM
    llm_provider: str = "mock"  # mock | openai | azure
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-06-01"

    # ── Microsoft Entra ID (Azure AD) authentication ──
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_redirect_uri: str = "http://localhost:8000/auth/callback"
    entra_post_logout_redirect_uri: str = "http://localhost:8000/"

    # App-role / group names that map to elevated agent roles. A signed-in user
    # whose token carries one of these (in the 'roles' or 'groups' claim) is
    # granted the corresponding agent role; everyone else is 'employee'.
    role_claim_admin: str = "TaskAgent.Admin"
    role_claim_manager: str = "TaskAgent.Manager"

    # ── Session ──
    # Used to sign the session cookie. MUST be overridden in production.
    session_secret: str = "dev-insecure-change-me"
    session_cookie: str = "eta_session"
    session_https_only: bool = False
    session_max_age_seconds: int = 8 * 3600        # how long a sign-in lasts
    token_refresh_skew_seconds: int = 300          # refresh the access token this early

    # ── Microsoft Graph ──
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    default_timezone: str = "Asia/Kolkata"

    # Optional: official Accenture internal API (provisioned by IT). When set,
    # the Accenture connector calls real endpoints instead of staying inert.
    accenture_api_base_url: str = ""
    accenture_api_scope: str = ""

    # ── Server ──
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Persistence ──
    # SQLite path for the durable task history + audit trail. Use a mounted
    # volume in production. ':memory:' keeps everything in process memory.
    db_path: str = "data/app.db"

    # ── CORS ── (comma-separated origins; empty = same-origin only)
    cors_allow_origins: str = ""

    # ── Security headers ──
    csp_policy: str = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    hsts_enabled: bool | None = None               # None → on in production
    trusted_hosts: str = ""                         # comma-separated; empty = any host

    # ── Rate limiting (per client IP, in-process) ──
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # ── Observability ──
    log_level: str = "INFO"
    log_json: bool = False

    # ── API docs ── (None → disabled in production)
    enable_docs: bool | None = None

    # Misc
    request_timeout_seconds: float = 30.0

    @property
    def llm_enabled(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "azure":
            return bool(self.azure_openai_api_key and self.azure_openai_endpoint)
        return False

    @property
    def auth_enabled(self) -> bool:
        """Real Microsoft sign-in is active only when an app registration exists."""
        return bool(
            self.entra_tenant_id and self.entra_client_id and self.entra_client_secret
        )

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def secure_cookies(self) -> bool:
        """Cookies are marked Secure in production or when explicitly requested."""
        return self.session_https_only or self.is_production

    @property
    def hsts_active(self) -> bool:
        return self.hsts_enabled if self.hsts_enabled is not None else self.is_production

    @property
    def docs_enabled(self) -> bool:
        return self.enable_docs if self.enable_docs is not None else not self.is_production

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    def validate_runtime(self) -> list[str]:
        """Fail fast on insecure production config; return non-fatal warnings.

        Raises RuntimeError for unsafe production secrets so the app refuses to
        boot with an insecure configuration.
        """
        warnings: list[str] = []
        if not self.is_production:
            return warnings
        if self.session_secret == "dev-insecure-change-me" or len(self.session_secret) < 32:
            raise RuntimeError(
                "SESSION_SECRET must be a strong random value (>= 32 chars) in production."
            )
        if (
            self.auth_enabled
            and self.entra_redirect_uri.startswith("http://")
            and "localhost" not in self.entra_redirect_uri
        ):
            warnings.append("ENTRA_REDIRECT_URI should use https in production.")
        if self.cors_allow_origins.strip() == "*":
            warnings.append("CORS is open to '*'; restrict CORS_ALLOW_ORIGINS in production.")
        return warnings


settings = Settings()
