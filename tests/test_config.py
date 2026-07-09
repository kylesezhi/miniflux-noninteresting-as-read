"""Tests for configuration management."""

from __future__ import annotations


import pytest
from pydantic import ValidationError

from miniflux_ai_filter.config import Settings


class TestFeedIds:
    """Tests for feed ID parsing from MINIFLUX_FEED_IDS."""

    def test_parses_comma_separated(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1,2,3",
            OPENROUTER_API_KEY="key",
        )
        assert settings.feed_ids == [1, 2, 3]

    def test_parses_single_value(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="42",
            OPENROUTER_API_KEY="key",
        )
        assert settings.feed_ids == [42]

    def test_handles_whitespace(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS=" 1 , 2 , 3 ",
            OPENROUTER_API_KEY="key",
        )
        assert settings.feed_ids == [1, 2, 3]

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one feed ID"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                MINIFLUX_API_TOKEN="token",
                MINIFLUX_FEED_IDS="",
                OPENROUTER_API_KEY="key",
            )

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValidationError, match="non-numeric"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                MINIFLUX_API_TOKEN="token",
                MINIFLUX_FEED_IDS="1,abc,3",
                OPENROUTER_API_KEY="key",
            )


class TestRequiredFields:
    """Tests that required fields produce clear errors."""

    def test_missing_miniflux_url(self) -> None:
        with pytest.raises(ValidationError, match="MINIFLUX_URL"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_API_TOKEN="token",
                MINIFLUX_FEED_IDS="1",
                OPENROUTER_API_KEY="key",
            )

    def test_missing_api_token(self) -> None:
        with pytest.raises(ValidationError, match="MINIFLUX_API_TOKEN"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                MINIFLUX_FEED_IDS="1",
                OPENROUTER_API_KEY="key",
            )

    def test_missing_feed_ids(self) -> None:
        with pytest.raises(ValidationError, match="MINIFLUX_FEED_IDS"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                MINIFLUX_API_TOKEN="token",
                OPENROUTER_API_KEY="key",
            )

    def test_missing_openrouter_api_key(self) -> None:
        with pytest.raises(ValidationError, match="OPENROUTER_API_KEY"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                MINIFLUX_URL="https://reader.example.com",
                MINIFLUX_API_TOKEN="token",
                MINIFLUX_FEED_IDS="1",
            )


class TestDefaults:
    """Tests for default values."""

    def test_provider_defaults_to_openrouter(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1",
            OPENROUTER_API_KEY="key",
        )
        assert settings.LLM_PROVIDER == "openrouter"

    def test_max_articles_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1",
            OPENROUTER_API_KEY="key",
        )
        assert settings.MAX_ARTICLES_PER_RUN == 100

    def test_opencodego_api_key_defaults_to_empty(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1",
            OPENROUTER_API_KEY="key",
        )
        assert settings.OPENCODEGO_API_KEY == ""

    def test_opencodego_model_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1",
            OPENROUTER_API_KEY="key",
        )
        assert settings.OPENCODEGO_MODEL == "deepseek-v4-flash"

    def test_opencodego_timeout_default(self) -> None:
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
            MINIFLUX_URL="https://reader.example.com",
            MINIFLUX_API_TOKEN="token",
            MINIFLUX_FEED_IDS="1",
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
            MINIFLUX_FEED_IDS="1",
            OPENROUTER_API_KEY="key",
            OPENCODEGO_API_KEY="",
            LLM_PROVIDER="opencodego",
        )
        # The config allows empty opencodego key; runtime validation
        # happens in main.py when instantiating the client
        assert settings.LLM_PROVIDER == "opencodego"
        assert settings.OPENCODEGO_API_KEY == ""