"""Shared test fixtures for miniflux-ai-filter tests."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from miniflux_ai_filter.models import Article
from miniflux_ai_filter.protocols import LLMClient, LLMError


# ── Clean environment for config tests ─────────────────────────────────
# The config module calls load_dotenv() at import time, which populates
# os.environ with values from .env.  We remove them here so config tests
# start from a clean slate.

_CONFIG_ENV_VARS = [
    "MINIFLUX_URL",
    "MINIFLUX_API_TOKEN",
    "MINIFLUX_FEED_IDS",
    "OPENROUTER_API_KEY",
    "OPENCODEGO_API_KEY",
    "LLM_PROVIDER",
    "OPENCODEGO_MODEL",
    "OPENROUTER_MODEL",
    "MAX_ARTICLES_PER_RUN",
    "OPENCODEGO_TIMEOUT_SECONDS",
]


@pytest.fixture(autouse=True)
def _clean_env() -> Any:
    """Remove project-specific env vars before each test.

    This prevents the user's ``.env`` file from leaking into tests that
    exercise :class:`~miniflux_ai_filter.config.Settings`.
    """
    saved: dict[str, str | None] = {}
    for key in _CONFIG_ENV_VARS:
        saved[key] = os.environ.pop(key, None)
    yield
    for key, val in saved.items():
        if val is not None:
            os.environ[key] = val


# ── Mock LLM client factory ────────────────────────────────────────────


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Return a MagicMock satisfying the LLMClient protocol.

    By default ``send_message`` returns a valid JSON classification
    indicating the article is interesting.  Tests can override this by
    setting ``mock_llm_client.send_message.return_value``.
    """
    mock = MagicMock(spec=LLMClient)
    mock.send_message.return_value = '{"interesting": true, "reason": "Interesting topic."}'
    return mock


@pytest.fixture
def mock_llm_client_not_interesting() -> MagicMock:
    """Return a mock that classifies articles as *not* interesting."""
    mock = MagicMock(spec=LLMClient)
    mock.send_message.return_value = '{"interesting": false, "reason": "Uninteresting primary topic."}'
    return mock


@pytest.fixture
def mock_llm_client_failure() -> MagicMock:
    """Return a mock that raises an LLMError on send_message."""
    mock = MagicMock(spec=LLMClient)
    mock.send_message.side_effect = LLMError("API error")
    return mock


# ── Sample articles ────────────────────────────────────────────────────


@pytest.fixture
def sample_article() -> Article:
    """A generic article fixture used across multiple test modules."""
    return Article(
        id=42,
        feed_id=1,
        title="Test Article",
        url="https://example.com/test-article",
        published_at="2026-07-09T12:00:00Z",
        summary="A test article summary.",
        content="<p>This is the article content.</p>",
    )


@pytest.fixture
def article_car_news() -> Article:
    """An article about cars — should be filtered as uninteresting."""
    return Article(
        id=101,
        feed_id=1,
        title="Tesla announces new vehicle lineup",
        url="https://example.com/tesla-lineup",
        published_at="2026-07-09T10:00:00Z",
        summary="Tesla unveils three new electric vehicle models.",
        content=(
            "Tesla has announced a major expansion to its vehicle lineup, "
            "adding three new electric models that target different market segments. "
            "The new vehicles include a compact sedan and two SUVs."
        ),
    )


@pytest.fixture
def article_motogp() -> Article:
    """A MotoGP article — should be filtered as uninteresting."""
    return Article(
        id=102,
        feed_id=1,
        title="MotoGP championship results",
        url="https://example.com/motogp-results",
        published_at="2026-07-09T09:00:00Z",
        summary="Final standings for the MotoGP championship.",
        content=(
            "The MotoGP season has concluded with dramatic final races. "
            "Championship standings show intense competition throughout the year."
        ),
    )


@pytest.fixture
def article_nfl() -> Article:
    """An NFL article — should be filtered as uninteresting."""
    return Article(
        id=103,
        feed_id=1,
        title="NFL season preview",
        url="https://example.com/nfl-preview",
        published_at="2026-07-09T08:00:00Z",
        summary="Preview of the upcoming NFL season.",
        content=(
            "The upcoming NFL season promises exciting matchups and storylines. "
            "Teams are preparing for what could be one of the most competitive seasons yet."
        ),
    )


@pytest.fixture
def article_ai_robot() -> Article:
    """An AI article about Tesla robots — should be kept as interesting."""
    return Article(
        id=201,
        feed_id=1,
        title="AI model trains Tesla robot",
        url="https://example.com/ai-robot",
        published_at="2026-07-09T07:00:00Z",
        summary="New reinforcement learning approach enables complex manipulation.",
        content=(
            "Researchers have developed a novel AI training method that allows "
            "robots to learn complex manipulation tasks with fewer demonstrations. "
            "The approach uses hierarchical reinforcement learning."
        ),
    )


@pytest.fixture
def article_nasa() -> Article:
    """A NASA software article — should be kept as interesting."""
    return Article(
        id=202,
        feed_id=1,
        title="NASA spacecraft software update",
        url="https://example.com/nasa-software",
        published_at="2026-07-09T06:00:00Z",
        summary="Software update for deep space probes.",
        content=(
            "NASA has successfully deployed a critical software update to its "
            "deep space probe fleet, fixing a timing issue in the flight computer."
        ),
    )


@pytest.fixture
def article_linux() -> Article:
    """A Linux security article — should be kept as interesting."""
    return Article(
        id=203,
        feed_id=1,
        title="Linux kernel security vulnerability",
        url="https://example.com/linux-vuln",
        published_at="2026-07-09T05:00:00Z",
        summary="Critical vulnerability discovered in Linux kernel.",
        content=(
            "A critical privilege escalation vulnerability has been discovered "
            "in the Linux kernel's memory management subsystem. Patches are "
            "being rolled out across distributions."
        ),
    )


# ── Sample API response data ───────────────────────────────────────────


@pytest.fixture
def miniflux_entry_data() -> dict[str, Any]:
    """Sample raw API response data for a Miniflux entry."""
    return {
        "id": 42,
        "feed_id": 1,
        "title": "Test Article",
        "url": "https://example.com/test-article",
        "published_at": "2026-07-09T12:00:00Z",
        "summary": "A test article summary.",
        "content": "<p>Article content here.</p>",
    }


@pytest.fixture
def opencodego_response() -> dict[str, Any]:
    """Sample successful Opencode Go API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"interesting": true, "reason": "Test reason."}',
                }
            }
        ]
    }