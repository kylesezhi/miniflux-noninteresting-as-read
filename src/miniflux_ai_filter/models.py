"""Typed data models for API responses and LLM classification results.

Provides three Pydantic models:

- ``Article``        — a canonical representation of a Miniflux entry
- ``ClassificationResult`` — the expected JSON shape returned by the LLM
- ``ClassificationLog``    — a single audit-trail record written to JSONL
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Article(BaseModel):
    """Normalized representation of a single article (Miniflux entry).

    Maps directly from the Miniflux API entry object (and equivalently from
    :class:`~miniflux_ai_filter.miniflux.MinifluxEntry`).
    """

    id: int = Field(..., description="Miniflux entry ID")
    feed_id: int = Field(..., description="Feed ID this entry belongs to")
    title: str = Field(default="", description="Entry title")
    url: str = Field(default="", description="Entry URL")
    published_at: str = Field(default="", description="ISO 8601 publish timestamp")
    summary: str = Field(default="", description="Entry summary / excerpt")
    content: str = Field(default="", description="Entry HTML content")


class ClassificationResult(BaseModel):
    """Classification produced by the LLM for a single article.

    Validation is performed automatically by Pydantic — if the LLM returns
    a response where ``interesting`` is not a boolean or ``reason`` is not a
    string, a ``ValidationError`` is raised.
    """

    interesting: bool = Field(
        ...,
        description="Whether the article is considered interesting",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation for the classification",
    )


class ClassificationLog(BaseModel):
    """A single JSONL log entry recording the classification of one article.

    Every processed article produces exactly one ``ClassificationLog`` record,
    regardless of whether the article was marked as read or kept as unread.
    """

    run_id: str = Field(..., description="Unique identifier for this pipeline run")
    timestamp: str = Field(..., description="ISO 8601 timestamp of classification")
    article_id: int = Field(..., description="Miniflux entry ID")
    feed_id: int = Field(..., description="Feed ID this entry belongs to")
    title: str = Field(..., description="Entry title")
    url: str = Field(..., description="Entry URL")
    published_at: str = Field(..., description="ISO 8601 publish timestamp")
    interesting: bool = Field(..., description="Classification result")
    reason: str = Field(..., description="Classification explanation")
    model: str = Field(..., description="OpenRouter model identifier used")