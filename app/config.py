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

    # ── Microsoft Graph ──
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    default_timezone: str = "Asia/Kolkata"

    # Optional: official Accenture internal API (provisioned by IT). When set,
    # the Accenture connector calls real endpoints instead of staying inert.
    accenture_api_base_url: str = ""
    accenture_api_scope: str = ""

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


settings = Settings()
