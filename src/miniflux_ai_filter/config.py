"""Configuration management for miniflux-ai-filter.

Loads runtime configuration from environment variables (via .env file)
and provides a validated, typed configuration object.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


load_dotenv()


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables.

    All required variables must be set or a ``ValidationError`` is raised
    with a clear message describing which field is missing.
    """

    # ── Required ──────────────────────────────────────────────────────
    MINIFLUX_URL: str = Field(
        ...,
        description="Base URL of the Miniflux instance (e.g. https://reader.example.com)",
    )
    MINIFLUX_API_TOKEN: str = Field(
        ...,
        description="Miniflux API token",
    )
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="OpenRouter API key (required when LLM_PROVIDER=openrouter)",
    )
    OPENCODEGO_API_KEY: str = Field(
        default="",
        description="Opencode Go API key (required when LLM_PROVIDER=opencodego)",
    )

    # ── Optional (with sensible defaults) ─────────────────────────────
    MAX_ARTICLES_PER_RUN: int = Field(
        default=100,
        ge=1,
        description="Maximum number of articles to process per run",
    )
    OPENROUTER_MODEL: str = Field(
        default="openai/gpt-oss-120b:free",
        description="OpenRouter model identifier",
    )
    OPENCODEGO_MODEL: str = Field(
        default="deepseek-v4-flash",
        description="Opencode Go model identifier",
    )
    OPENCODEGO_TIMEOUT_SECONDS: int = Field(
        default=60,
        ge=1,
        description="Opencode Go request timeout in seconds",
    )
    OPENCODEGO_SESSION_ID: str = Field(
        default="",
        description=(
            "Opencode Go session ID (x-opencode-session). Empty = a fresh "
            "session per run"
        ),
    )
    LLM_PROVIDER: str = Field(
        default="opencodego",
        description="LLM provider to use (opencodego or openrouter)",
    )
    CLASSIFICATION_DELAY_SECONDS: int = Field(
        default=2,
        ge=1,
        description="Delay in seconds between LLM classification calls to avoid rate limiting",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


class WebSettings(BaseSettings):
    """Typed configuration for the read-only web log viewer.

    Kept separate from :class:`Settings` so the viewer can run without the
    Miniflux/LLM credentials the classification pipeline requires.
    """

    WEB_HOST: str = Field(
        default="0.0.0.0",
        description="Host interface the log viewer binds to (0.0.0.0 = LAN)",
    )
    WEB_PORT: int = Field(
        default=5000,
        ge=1,
        le=65535,
        description="Port the log viewer listens on",
    )
    WEB_LOG_PATH: str = Field(
        default="logs/classifier.jsonl",
        description="Path to the JSONL audit trail displayed by the viewer",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}
