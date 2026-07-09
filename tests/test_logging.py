"""Tests for JSONL audit trail logging."""

from __future__ import annotations

import json

from miniflux_ai_filter.logging import JsonlLogger
from miniflux_ai_filter.models import Article


class TestLogClassification:
    """Tests for ``JsonlLogger.log_classification``."""

    def test_writes_valid_jsonl(self, tmp_path, sample_article: Article) -> None:
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(file_path=str(log_path))

        logger.log_classification(
            article=sample_article,
            interesting=True,
            reason="AI and programming topic.",
            run_id="abc123",
            model="test-model",
        )

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["run_id"] == "abc123"
        assert entry["article_id"] == 42
        assert entry["feed_id"] == 1
        assert entry["title"] == "Test Article"
        assert entry["url"] == "https://example.com/test-article"
        assert entry["published_at"] == "2026-07-09T12:00:00Z"
        assert entry["interesting"] is True
        assert entry["reason"] == "AI and programming topic."
        assert entry["model"] == "test-model"
        assert "timestamp" in entry

    def test_writes_multiple_entries(self, tmp_path, sample_article: Article) -> None:
        log_path = tmp_path / "multi.jsonl"
        logger = JsonlLogger(file_path=str(log_path))

        logger.log_classification(
            article=sample_article,
            interesting=True,
            reason="Reason 1",
            run_id="run1",
            model="model1",
        )
        logger.log_classification(
            article=sample_article,
            interesting=False,
            reason="Reason 2",
            run_id="run2",
            model="model2",
        )

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert entry1["run_id"] == "run1"
        assert entry1["interesting"] is True
        assert entry2["run_id"] == "run2"
        assert entry2["interesting"] is False

    def test_creates_directory_if_not_exists(
        self, tmp_path, sample_article: Article
    ) -> None:
        nested_path = tmp_path / "nested" / "dir" / "test.jsonl"
        logger = JsonlLogger(file_path=str(nested_path))

        logger.log_classification(
            article=sample_article,
            interesting=True,
            reason="Test.",
            run_id="abc",
            model="m",
        )

        assert nested_path.exists()
        lines = nested_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1


class TestLogError:
    """Tests for ``JsonlLogger.log_error``."""

    def test_writes_error_entry(self, tmp_path) -> None:
        log_path = tmp_path / "errors.jsonl"
        logger = JsonlLogger(file_path=str(log_path))

        logger.log_error(
            run_id="abc123",
            error_type="llm_failure",
            error_message="API returned 500",
            article_id=42,
        )

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["run_id"] == "abc123"
        assert entry["error_type"] == "llm_failure"
        assert entry["error_message"] == "API returned 500"
        assert entry["article_id"] == 42
        assert "timestamp" in entry

    def test_error_without_article_id(self, tmp_path) -> None:
        log_path = tmp_path / "errors.jsonl"
        logger = JsonlLogger(file_path=str(log_path))

        logger.log_error(
            run_id="abc123",
            error_type="config_error",
            error_message="Missing API key",
        )

        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "article_id" not in entry

    def test_classification_and_error_in_same_file(
        self, tmp_path, sample_article: Article
    ) -> None:
        log_path = tmp_path / "combined.jsonl"
        logger = JsonlLogger(file_path=str(log_path))

        logger.log_classification(
            article=sample_article,
            interesting=True,
            reason="Good.",
            run_id="run1",
            model="m",
        )
        logger.log_error(
            run_id="run1",
            error_type="miniflux_failure",
            error_message="Connection refused",
            article_id=99,
        )

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert "interesting" in entry1
        assert "error_type" in entry2