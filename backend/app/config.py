"""
Application configuration.

All secrets and environment-specific values are loaded from environment
variables (via a local .env file in development). Nothing is hardcoded.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # CORS - the Vite dev server default origin
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def has_valid_api_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cached so we don't re-read the environment on every request."""
    return Settings()
