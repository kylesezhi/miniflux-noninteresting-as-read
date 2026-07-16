"""Tests for configuration management."""

from __future__ import annotations


import pytest
from pydantic import ValidationError

from miniflux_ai_filter.config import Settings


class TestRequiredFields:
    """Tests that required fields produce clear errors."""

    def test_missing_miniflux_url(self) -> None:
        with pytest.raises(ValidationError, match="MINIFLUX_URL"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_API_TOKEN="token",
                OPENROUTER_API_KEY="key",
            )

    def test_missing_api_token(self) -> None:
        with pytest.raises(ValidationError, match="MINIFLUX_API_TOKEN"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                OPENROUTER_API_KEY="key",
            )

    def test_openrouter_api_key_defaults_to_empty(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
        )
        assert settings.OPENROUTER_API_KEY == ""


class TestDefaults:
    """Tests for default values."""

    def test_provider_defaults_to_opencodego(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
        )
        assert settings.LLM_PROVIDER == "opencodego"

    def test_max_articles_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            OPENROUTER_API_KEY="key",
        )
        assert settings.MAX_ARTICLES_PER_RUN == 100

    def test_opencodego_api_key_defaults_to_empty(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            OPENROUTER_API_KEY="key",
        )
        assert settings.OPENCODEGO_API_KEY == ""

    def test_opencodego_model_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            OPENROUTER_API_KEY="key",
        )
        assert settings.OPENCODEGO_MODEL == "deepseek-v4-flash"

    def test_opencodego_timeout_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            OPENROUTER_API_KEY="key",
        )
        assert settings.OPENCODEGO_TIMEOUT_SECONDS == 60


class TestProviderConfig:
    """Tests for provider-specific configuration."""

    def test_opencodego_provider_requires_api_key(self) -> None:
        """Opencode Go API key is optional in the schema but the runtime
        should validate it when LLM_PROVIDER=opencodego."""
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            OPENROUTER_API_KEY="key",
            OPENCODEGO_API_KEY="",
            LLM_PROVIDER="opencodego",
        )
        # The config allows empty opencodego key; runtime validation
        # happens in main.py when instantiating the client
        assert settings.LLM_PROVIDER == "opencodego"
        assert settings.OPENCODEGO_API_KEY == ""
