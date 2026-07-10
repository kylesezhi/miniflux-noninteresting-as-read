"""YAML feed configuration for per-feed definitions.

Replaces the ``MINIFLUX_FEED_IDS`` environment variable with a structured
YAML config file (``feeds.yaml`` by default) that maps feed IDs to their
``max_articles`` limit and classification prompt.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class FeedConfig(BaseModel):
    """Configuration for a single feed.

    Attributes
    ----------
    feed_id:
        The numeric Miniflux feed ID.
    max_articles:
        Maximum number of articles to process per run for this feed
        (default 100).
    prompt:
        The classification system prompt to use for this feed.
    """

    feed_id: int = Field(..., description="Miniflux feed ID")
    max_articles: int = Field(
        default=100,
        ge=1,
        description="Maximum articles to process per run for this feed",
    )
    prompt: str = Field(..., description="Classification system prompt for this feed")


class FeedsConfig(BaseModel):
    """Collection of feed configurations loaded from a YAML file.

    Usage::

        config = FeedsConfig.load("feeds.yaml")
        for feed in config.feeds:
            print(feed.feed_id, feed.max_articles)
    """

    feeds: list[FeedConfig] = Field(
        ..., min_length=1, description="List of feed configurations"
    )

    @classmethod
    def load(cls, path: str | Path = "feeds.yaml") -> "FeedsConfig":
        """Parse and validate a YAML feed configuration file.

        Parameters
        ----------
        path:
            Path to the YAML file.  Defaults to ``feeds.yaml`` in the
            current working directory.

        Returns
        -------
        FeedsConfig:
            The validated feed configuration.

        Raises
        ------
        FileNotFoundError:
            If the file does not exist at *path*.
        ValueError:
            If the file contains invalid YAML, the ``feeds`` list is
            empty, or required fields are missing.
        """
        path_obj = Path(path)

        # ── File existence ─────────────────────────────────────────────
        if not path_obj.exists():
            raise FileNotFoundError(
                f"Feeds config file not found: {path_obj.resolve()}"
            )

        # ── YAML parsing ───────────────────────────────────────────────
        try:
            raw = yaml.safe_load(path_obj.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Invalid YAML in feeds config '{path_obj}': {exc}"
            ) from exc

        if raw is None:
            raise ValueError(
                f"Feeds config '{path_obj}' is empty or contains only null"
            )

        if not isinstance(raw, dict):
            raise ValueError(
                f"Feeds config '{path_obj}' must contain a top-level mapping, "
                f"got {type(raw).__name__}"
            )

        # ── Validate structure with Pydantic ────────────────────────────
        try:
            return cls.model_validate(raw)
        except Exception as exc:
            # Pydantic will give field-level errors; re-raise with clear context
            raise ValueError(
                f"Invalid feeds config in '{path_obj}': {exc}"
            ) from exc