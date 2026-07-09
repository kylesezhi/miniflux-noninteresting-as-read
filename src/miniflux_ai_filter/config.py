"""Configuration management for miniflux-ai-filter.

Loads runtime configuration from environment variables (via .env file)
and provides a validated, typed configuration object.
"""

from typing import List

from pydantic import Field, model_validator
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
    MINIFLUX_FEED_IDS: str = Field(
        ...,
        description="Comma-separated list of feed IDs (e.g. '1,2,3')",
    )
    OPENROUTER_API_KEY: str = Field(
        ...,
        description="OpenRouter API key",
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
    LLM_PROVIDER: str = Field(
        default="openrouter",
        description="LLM provider to use (openrouter or opencodego)",
    )

    # ── Computed fields (populated after init) ────────────────────────
    feed_ids: List[int] = Field(default=[], exclude=True)

    @model_validator(mode="after")
    def _parse_feed_ids(self) -> "Settings":
        raw = self.MINIFLUX_FEED_IDS
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            raise ValueError("MINIFLUX_FEED_IDS must contain at least one feed ID")
        try:
            self.feed_ids = [int(p) for p in parts]
        except ValueError as exc:
            raise ValueError(
                f"MINIFLUX_FEED_IDS contains non-numeric values: {exc}"
            ) from exc
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}