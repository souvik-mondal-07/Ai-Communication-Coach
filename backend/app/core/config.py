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

    # --- Request limits ---
    # Hard ceiling for any non-audio request body (JSON etc.). Audio upload routes
    # enforce their own, larger limit (VOICE_MAX_AUDIO_BYTES).
    max_request_body_bytes: int = 1_048_576

    # --- Python practice (Phase 26) ---
    # Master switch for running submitted Python in the isolated runner. Even when true, the runner stays disabled unless
    # its start-up self-test proves isolation on this host (Linux with unprivileged user namespaces).
    python_runner_enabled: bool = True

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

    # --- Voice: speech-to-text (Step 8) ---
    # Local faster-whisper. "auto" lets it pick GPU when available, else CPU.
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    # ISO code the recogniser is pinned to (the coach is English-first).
    # Set empty to let Whisper auto-detect the language per recording.
    whisper_language: str = "en"

    # --- Voice: audio upload limits & temporary files ---
    voice_max_audio_bytes: int = 10 * 1024 * 1024
    voice_max_audio_seconds: int = 300
    # Where temporary audio is written while it is being transcribed.
    # Empty = the operating system's temp directory. Files are deleted
    # immediately after processing.
    voice_temp_dir: str = ""

    # --- Voice: text-to-speech (Step 8) ---
    # All backend-only. Leave TTS_PROVIDER empty to run without spoken
    # replies; text mode is unaffected.  Supported: "openai", "google".
    tts_provider: str = ""
    tts_api_key: str = ""
    tts_model: str = ""
    tts_voice: str = ""
    # Optional override for OpenAI-compatible servers (self-hosted TTS etc.)
    tts_base_url: str = ""

    # --- Voice conversation (Step 13) ---
    # Longest single spoken answer accepted in a voice conversation. Checked
    # against the transcribed audio duration (VOICE_MAX_AUDIO_SECONDS stays the
    # global hard ceiling used by the Step 8 pipeline).
    voice_max_recording_seconds: int = 120
    # Exchanges (AI turn + user turn) of history sent to Gemini each turn.
    # Older turns stay in MongoDB. AIService itself caps history at 40 messages.
    voice_conversation_max_turns: int = 20
    # User answers allowed in one voice session before it is completed
    # automatically (protects against unbounded, expensive sessions).
    voice_conversation_max_session_turns: int = 40
    # How long a generated AI audio clip stays fetchable (in memory only).
    voice_audio_url_ttl_seconds: int = 120
    # Hint to the UI: try to play AI speech automatically (browsers may block it).
    voice_auto_play: bool = True

    # --- Speaking analysis (Step 8) ---
    # Comma-separated override for the filler-word list. Empty = built-in list.
    filler_words: str = ""

    # --- Public cybersecurity news (Phase 22) ---
    # The list of sources is fixed in code (app/services/news/sources.py); it is deliberately
    # not configurable from the environment, so no setting can turn the fetcher into an
    # arbitrary-URL client. Settings below only tune *how* those sources are used.
    news_enabled: bool = True
    # Cached articles older than this are refreshed in the background on the next request.
    news_refresh_interval_minutes: int = 30
    # Articles published longer ago than this are not stored; stored ones expire after it.
    news_retention_days: int = 45
    news_fetch_timeout_seconds: float = 8.0
    # Hard ceiling for one feed download (streamed; the rest is discarded).
    news_max_feed_bytes: int = 3 * 1024 * 1024
    # Comma-separated source ids to switch off (e.g. "bleepingcomputer,schneier").
    news_disabled_sources: str = ""
    # Optional. A free NVD key raises NVD's rate limit; it is sent only in a request header.
    nvd_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def filler_words_list(self) -> list[str] | None:
        """Configured filler-word override, or None to use the built-in list."""
        words = [w.strip().lower() for w in self.filler_words.split(",") if w.strip()]
        return words or None

    @property
    def news_disabled_sources_set(self) -> frozenset[str]:
        return frozenset(p.strip().lower() for p in self.news_disabled_sources.split(",") if p.strip())

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


class ConfigurationError(RuntimeError):
    """Raised at startup when the configuration is unsafe for the current environment."""


MIN_PRODUCTION_JWT_SECRET_LENGTH = 32
ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})  # symmetric only; never "none"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — environment is read once per process."""
    resolved = Settings()

    if resolved.jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
        raise ConfigurationError(
            f"JWT_ALGORITHM must be one of {', '.join(sorted(ALLOWED_JWT_ALGORITHMS))}."
        )

    if resolved.is_production:
        # Fail fast and clearly (the message never contains a secret value).
        if len(resolved.jwt_secret_key) < MIN_PRODUCTION_JWT_SECRET_LENGTH:
            raise ConfigurationError(
                "JWT_SECRET_KEY must be set to a random value of at least "
                f"{MIN_PRODUCTION_JWT_SECRET_LENGTH} characters when APP_ENV=production."
            )
        if "*" in resolved.cors_origins_list:
            raise ConfigurationError(
                "CORS_ALLOWED_ORIGINS must list explicit origins when APP_ENV=production."
            )
    elif not resolved.jwt_secret_key:
        # Development convenience only: a random per-process secret so a fresh
        # checkout still starts. Tokens won't survive a restart with this.
        resolved.jwt_secret_key = secrets.token_urlsafe(32)
        _bootstrap_logger.warning(
            "JWT_SECRET_KEY is not set — generated a temporary secret for this "
            "process. Set JWT_SECRET_KEY in backend/.env for stable sessions "
            "across restarts."
        )

    return resolved


settings = get_settings()
