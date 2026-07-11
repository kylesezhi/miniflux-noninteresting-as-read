"""Integration tests for the full multi-feed pipeline."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from miniflux_ai_filter.classifier import Classifier
from miniflux_ai_filter.feeds_config import FeedsConfig
from miniflux_ai_filter.main import run_pipeline
from miniflux_ai_filter.miniflux import MinifluxClient
from miniflux_ai_filter.models import Article, ClassificationResult


class TestMultiFeedPipeline:
    """Integration tests for processing multiple feeds independently."""

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _make_article(
        id: int,
        feed_id: int,
        title: str = "Article",
    ) -> Article:
        return Article(
            id=id,
            feed_id=feed_id,
            title=title,
            url=f"https://example.com/{id}",
            published_at="2026-07-09T12:00:00Z",
            summary="Summary",
            content="Content",
        )

    # ── Tests ────────────────────────────────────────────────────────────

    @patch("miniflux_ai_filter.main.JsonlLogger")
    @patch("miniflux_ai_filter.main.Classifier.classify")
    @patch("miniflux_ai_filter.main.MinifluxClient.mark_entry_read")
    @patch("miniflux_ai_filter.main.MinifluxClient.get_unread_entries")
    @patch("miniflux_ai_filter.main.FeedsConfig.load")
    def test_pipeline_processes_multiple_feeds(
        self,
        mock_feeds_load: MagicMock,
        mock_get_unread: MagicMock,
        mock_mark_read: MagicMock,
        mock_classify: MagicMock,
        mock_logger_cls: MagicMock,
        multi_feed_config: FeedsConfig,
    ) -> None:
        """Each feed is fetched independently and processed with its own prompt."""
        mock_feeds_load.return_value = multi_feed_config

        # Feed 1 returns 2 articles, Feed 2 returns 1 article
        mock_get_unread.side_effect = [
            [
                self._make_article(1, 1, "Interesting AI"),
                self._make_article(2, 1, "Boring Car"),
            ],
            [
                self._make_article(3, 2, "Space News"),
            ],
        ]

        mock_classify.side_effect = [
            ClassificationResult(interesting=True, reason="AI topic."),
            ClassificationResult(interesting=False, reason="Car topic."),
            ClassificationResult(interesting=False, reason="Sports topic."),
        ]

        test_env = {
            "MINIFLUX_URL": "https://reader.example.com",
            "MINIFLUX_API_TOKEN": "test-token",
            "OPENROUTER_API_KEY": "test-key",
            "LLM_PROVIDER": "openrouter",
            "CLASSIFICATION_DELAY_SECONDS": "1",
        }

        with patch.dict(os.environ, test_env):
            run_pipeline()

        # Both feeds queried with correct feed_ids
        assert mock_get_unread.call_count == 2
        assert mock_get_unread.call_args_list[0][0][0] == 1
        assert mock_get_unread.call_args_list[1][0][0] == 2

        # Only uninteresting articles marked read
        assert mock_mark_read.call_count == 2
        marked_ids = [call[0][0] for call in mock_mark_read.call_args_list]
        assert 1 not in marked_ids
        assert 2 in marked_ids
        assert 3 in marked_ids

        # Classifier received correct per-feed prompts
        assert mock_classify.call_count == 3
        prompt_1 = multi_feed_config.feeds[0].prompt
        prompt_2 = multi_feed_config.feeds[1].prompt
        assert mock_classify.call_args_list[0][1]["system_prompt"] == prompt_1
        assert mock_classify.call_args_list[1][1]["system_prompt"] == prompt_1
        assert mock_classify.call_args_list[2][1]["system_prompt"] == prompt_2

    @patch("miniflux_ai_filter.main.JsonlLogger")
    @patch("miniflux_ai_filter.main.Classifier.classify")
    @patch("miniflux_ai_filter.main.MinifluxClient.mark_entry_read")
    @patch("miniflux_ai_filter.main.MinifluxClient.get_unread_entries")
    @patch("miniflux_ai_filter.main.FeedsConfig.load")
    def test_pipeline_logs_prompt_field(
        self,
        mock_feeds_load: MagicMock,
        mock_get_unread: MagicMock,
        mock_mark_read: MagicMock,
        mock_classify: MagicMock,
        mock_logger_cls: MagicMock,
        multi_feed_config: FeedsConfig,
    ) -> None:
        """JSONL log entries contain the correct per-feed prompt."""
        mock_feeds_load.return_value = multi_feed_config

        mock_get_unread.side_effect = [
            [self._make_article(1, 1, "Feed 1 Article")],
            [self._make_article(2, 2, "Feed 2 Article")],
        ]

        mock_classify.side_effect = [
            ClassificationResult(interesting=False, reason="Not interesting."),
            ClassificationResult(interesting=False, reason="Not interesting."),
        ]

        mock_logger = MagicMock()
        mock_logger_cls.return_value = mock_logger

        test_env = {
            "MINIFLUX_URL": "https://reader.example.com",
            "MINIFLUX_API_TOKEN": "test-token",
            "OPENROUTER_API_KEY": "test-key",
            "LLM_PROVIDER": "openrouter",
            "CLASSIFICATION_DELAY_SECONDS": "1",
        }

        with patch.dict(os.environ, test_env):
            run_pipeline()

        assert mock_logger.log_classification.call_count == 2

        call_1 = mock_logger.log_classification.call_args_list[0]
        assert call_1[1]["prompt"] == multi_feed_config.feeds[0].prompt
        assert call_1[1]["article"].feed_id == 1

        call_2 = mock_logger.log_classification.call_args_list[1]
        assert call_2[1]["prompt"] == multi_feed_config.feeds[1].prompt
        assert call_2[1]["article"].feed_id == 2

    @patch("miniflux_ai_filter.main.JsonlLogger")
    @patch("miniflux_ai_filter.main.Classifier.classify")
    @patch("miniflux_ai_filter.main.MinifluxClient.mark_entry_read")
    @patch("miniflux_ai_filter.main.MinifluxClient.get_unread_entries")
    @patch("miniflux_ai_filter.main.FeedsConfig.load")
    def test_pipeline_handles_missing_feed(
        self,
        mock_feeds_load: MagicMock,
        mock_get_unread: MagicMock,
        mock_mark_read: MagicMock,
        mock_classify: MagicMock,
        mock_logger_cls: MagicMock,
        multi_feed_config: FeedsConfig,
    ) -> None:
        """A feed with no unread articles is skipped; remaining feeds proceed."""
        mock_feeds_load.return_value = multi_feed_config

        # Feed 1 returns articles, Feed 2 returns nothing (no unread / missing)
        mock_get_unread.side_effect = [
            [
                self._make_article(1, 1, "Feed 1 Article"),
            ],
            [],  # feed 2 has no unread articles
        ]

        mock_classify.side_effect = [
            ClassificationResult(interesting=True, reason="Keep this one."),
        ]

        test_env = {
            "MINIFLUX_URL": "https://reader.example.com",
            "MINIFLUX_API_TOKEN": "test-token",
            "OPENROUTER_API_KEY": "test-key",
            "LLM_PROVIDER": "openrouter",
            "CLASSIFICATION_DELAY_SECONDS": "1",
        }

        with patch.dict(os.environ, test_env):
            run_pipeline()

        # Both feeds were queried
        assert mock_get_unread.call_count == 2
        assert mock_get_unread.call_args_list[0][0][0] == 1
        assert mock_get_unread.call_args_list[1][0][0] == 2

        # Only feed 1 articles were classified
        assert mock_classify.call_count == 1

        # No articles were marked read (the only article was interesting)
        assert mock_mark_read.call_count == 0
