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

    # Misc
    request_timeout_seconds: float = 30.0

    @property
    def llm_enabled(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "azure":
            return bool(self.azure_openai_api_key and self.azure_openai_endpoint)
        return False


settings = Settings()
