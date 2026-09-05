"""
Central application configuration.

All environment-driven settings live here. Nothing else in the codebase
should read `os.environ` directly — import `settings` from this module
instead, so configuration stays in one predictable place.
"""

import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Plain stdlib logger here (not app.utils.logger) to avoid a circular import:
# app.utils.logger itself imports `settings` from this module.
_bootstrap_logger = logging.getLogger("app.core.config")


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "AI Cybersecurity Mentor"
    app_env: str = "development"
    debug: bool = True

    # --- API ---
    api_v1_prefix: str = "/api/v1"

    # --- CORS ---
    # Comma-separated list of allowed origins, configurable per environment.
    cors_allowed_origins: str = "http://localhost:5173"

    # --- MongoDB ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_cybersec_mentor"

    # --- Auth ---
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- AI provider (Gemini) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — environment is read once per process."""
    resolved = Settings()

    if not resolved.jwt_secret_key:
        # Never run with an empty secret: fall back to a random, per-process
        # secret so the app still starts in a fresh dev checkout, but make
        # noise about it since tokens won't survive a restart with this.
        resolved.jwt_secret_key = secrets.token_urlsafe(32)
        _bootstrap_logger.warning(
            "JWT_SECRET_KEY is not set — generated a temporary secret for this "
            "process. Set JWT_SECRET_KEY in backend/.env for stable sessions "
            "across restarts."
        )

    return resolved


settings = get_settings()
