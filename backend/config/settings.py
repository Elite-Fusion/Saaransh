"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate and type-check every config value
at startup. Fail fast if anything required is missing or malformed.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the Saaransh backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "Saaransh AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v: object) -> bool:
        """Accept 'true'/'false'/'1'/'0' and ignore non-boolean system vars."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.strip().lower() in ("true", "1", "yes"):
                return True
            return False
        return bool(v)
    api_v1_prefix: str = "/api/v1"

    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- Database ----
    # Supabase Postgres connection string.
    # Example: postgresql+psycopg2://postgres:<password>@db.<ref>.supabase.co:5432/postgres
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/saaransh",
        description="SQLAlchemy database URL",
    )
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # ---- CORS ----
    cors_origins: list[str] = [
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


    # ---- Logging ----
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "text"

    # ---- AI (Phase 5) ----
    # The provider abstraction supports "gemini" today; Claude,
    # OpenAI, Groq, and OpenRouter plug into the same interface in
    # later phases. Switching providers = changing ``ai_provider``
    # and setting the matching ``<PROVIDER>_API_KEY``.
    ai_provider: Literal["gemini", "nvidia"] = Field(
        default="gemini",
        description=(
            "Which LLM provider to use. Supported: 'gemini', 'nvidia'."
        ),
    )
    gemini_api_key: str = Field(default="", description="Google AI Studio API key.")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model name.")
    nvidia_api_key: str = Field(default="", description="NVIDIA NIM API key (nvapi-...).")
    nvidia_model: str = Field(default="meta/llama-3.1-8b-instruct", description="NVIDIA NIM model name.")
    ai_request_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        description="Per-attempt timeout (seconds) for an LLM call.",
    )
    ai_max_retries: int = Field(
        default=3,
        ge=0,
        description=(
            "Number of retry attempts on transient failures "
            "(429, 5xx, timeout). Total attempts = 1 + ai_max_retries."
        ),
    )
    ai_prompts_dir: str = Field(
        default="",
        description=(
            "Optional override for the prompts directory. "
            "Empty = use the default backend/ai/prompts/."
        ),
    )

    # ---- JWT / Auth (Phase 10) ----
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="HMAC secret for signing JWTs. Use a long random string.",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Access token lifetime in minutes.",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Refresh token lifetime in days.",
    )

    # ---- Validators ----
    @model_validator(mode="after")
    def _validate_ai_credentials(self) -> "Settings":
        """Fail fast if the selected provider has no API key.

        The rule is provider-specific:

          * ``"gemini"`` — ``gemini_api_key`` must be non-empty.
          * Future providers (claude / openai / groq / openrouter)
            will add their own branches here.

        Validation happens at app startup — never on the first
        user request.
        """
        provider = (self.ai_provider or "").strip().lower()
        if provider == "gemini" and not (self.gemini_api_key or "").strip():
            raise ValueError(
                "GEMINI_API_KEY is empty. Set the environment variable "
                "before starting the backend (see backend/.env.example)."
            )
        if provider == "nvidia" and not (self.nvidia_api_key or "").strip():
            raise ValueError(
                "NVIDIA_API_KEY is empty. Set the environment variable "
                "before starting the backend."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read .env once, reuse everywhere."""
    return Settings()


# Module-level singleton for convenient imports: `from backend.config import settings`
settings = get_settings()
