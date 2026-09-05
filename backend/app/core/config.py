"""
Central application configuration.

All environment-driven settings live here. Nothing else in the codebase
should read `os.environ` directly — import `settings` from this module
instead, so configuration stays in one predictable place.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # --- Auth (reserved for a future step; not used yet) ---
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"

    # --- AI provider (reserved for a future step; not used yet) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

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
    return Settings()


settings = get_settings()
