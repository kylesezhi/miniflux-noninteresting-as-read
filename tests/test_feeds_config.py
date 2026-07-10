"""Tests for YAML feed configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from miniflux_ai_filter.feeds_config import FeedConfig, FeedsConfig


# ── Helpers ────────────────────────────────────────────────────────────


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    """Write *data* as YAML to *path*."""
    path.write_text(yaml.dump(data), encoding="utf-8")


# ── FeedConfig unit tests ──────────────────────────────────────────────


class TestFeedConfig:
    """Tests for the single-feed model."""

    def test_valid_config(self) -> None:
        feed = FeedConfig(feed_id=1, prompt="Classify this.")
        assert feed.feed_id == 1
        assert feed.prompt == "Classify this."
        assert feed.max_articles == 100  # default

    def test_custom_max_articles(self) -> None:
        feed = FeedConfig(feed_id=2, max_articles=50, prompt="A prompt.")
        assert feed.max_articles == 50

    def test_zero_max_articles_raises(self) -> None:
        with pytest.raises(ValueError, match="Input should be greater than or equal to 1"):
            FeedConfig(feed_id=1, max_articles=0, prompt="Prompt")

    def test_negative_max_articles_raises(self) -> None:
        with pytest.raises(ValueError, match="Input should be greater than or equal to 1"):
            FeedConfig(feed_id=1, max_articles=-5, prompt="Prompt")

    def test_missing_feed_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Field required"):
            FeedConfig(prompt="Prompt")  # type: ignore[call-arg]

    def test_missing_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="Field required"):
            FeedConfig(feed_id=1)  # type: ignore[call-arg]


# ── FeedsConfig.load() tests ───────────────────────────────────────────


class TestFeedsConfigLoad:
    """Tests for loading and validating the full YAML config file."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(
            path,
            {
                "feeds": [
                    {"feed_id": 1, "prompt": "First prompt"},
                    {"feed_id": 5, "max_articles": 30, "prompt": "Second prompt"},
                ]
            },
        )
        config = FeedsConfig.load(path)
        assert len(config.feeds) == 2
        assert config.feeds[0].feed_id == 1
        assert config.feeds[0].max_articles == 100
        assert config.feeds[1].feed_id == 5
        assert config.feeds[1].max_articles == 30

    def test_default_path_is_feeds_yaml(self) -> None:
        """When no path is given, it defaults to 'feeds.yaml' in the CWD."""
        cwd = Path.cwd()
        candidate = cwd / "feeds.yaml"
        assert candidate.exists(), (
            "Expected a feeds.yaml in the project root for the default-path test. "
            "Create one or adjust the test."
        )
        config = FeedsConfig.load()
        assert len(config.feeds) > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Feeds config file not found"):
            FeedsConfig.load(path)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty or contains only null"):
            FeedsConfig.load(path)

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        path.write_text("{invalid: yaml: [}", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid YAML"):
            FeedsConfig.load(path)

    def test_not_a_dict_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        path.write_text(yaml.dump(["a", "list"]), encoding="utf-8")
        with pytest.raises(ValueError, match="top-level mapping"):
            FeedsConfig.load(path)

    def test_empty_feeds_list_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(path, {"feeds": []})
        with pytest.raises(ValueError, match="List should have at least 1 item"):
            FeedsConfig.load(path)

    def test_missing_feeds_key_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(path, {"not_feeds": []})
        with pytest.raises(ValueError, match="Field required"):
            FeedsConfig.load(path)

    def test_missing_feed_id_in_entry_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(path, {"feeds": [{"prompt": "No feed_id here"}]})
        with pytest.raises(ValueError, match="Field required"):
            FeedsConfig.load(path)

    def test_missing_prompt_in_entry_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(path, {"feeds": [{"feed_id": 1}]})
        with pytest.raises(ValueError, match="Field required"):
            FeedsConfig.load(path)

    def test_non_int_feed_id_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "feeds.yaml"
        _write_yaml(path, {"feeds": [{"feed_id": "abc", "prompt": "Prompt"}]})
        with pytest.raises(ValueError, match="Input should be a valid integer"):
            FeedsConfig.load(path)