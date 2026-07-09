"""Tests for the article classifier."""

from __future__ import annotations

import json

import pytest

from miniflux_ai_filter.classifier import Classifier, ClassificationError
from miniflux_ai_filter.models import Article, ClassificationResult


class TestFormatArticle:
    """Tests for ``Classifier._format_article``."""

    def test_format_includes_all_fields(self, sample_article: Article) -> None:
        result = Classifier._format_article(sample_article)
        assert "Title: Test Article" in result
        assert "URL: https://example.com/test-article" in result
        assert "Feed ID: 1" in result
        assert "Published: 2026-07-09T12:00:00Z" in result
        assert "Summary: A test article summary." in result
        assert "Content: <p>This is the article content.</p>" in result

    def test_format_truncates_content(self) -> None:
        long_content = "x" * 5000
        article = Article(
            id=1,
            feed_id=1,
            title="Long Content",
            url="https://example.com/long",
            published_at="2026-01-01T00:00:00Z",
            summary="Summary",
            content=long_content,
        )
        result = Classifier._format_article(article)
        # Content should be truncated to 2000 characters
        assert len(result.split("Content: ")[1]) == 2000

    def test_format_empty_content(self) -> None:
        article = Article(
            id=1,
            feed_id=1,
            title="Empty",
            url="https://example.com/empty",
            published_at="2026-01-01T00:00:00Z",
            summary="",
            content="",
        )
        result = Classifier._format_article(article)
        assert "Content: " in result

    def test_format_special_characters(self) -> None:
        article = Article(
            id=1,
            feed_id=1,
            title="Title with special: chars & more",
            url="https://example.com/special?q=a&b=c",
            published_at="2026-01-01T00:00:00Z",
            summary="Summary with emoji 😊",
            content="<p>Content with <b>HTML</b></p>",
        )
        result = Classifier._format_article(article)
        assert "Title with special: chars & more" in result
        assert "special?q=a&b=c" in result


class TestParseResponse:
    """Tests for ``Classifier._parse_response``."""

    def test_valid_json(self) -> None:
        raw = '{"interesting": true, "reason": "AI and programming topic."}'
        result = Classifier._parse_response(raw)
        assert isinstance(result, ClassificationResult)
        assert result.interesting is True
        assert result.reason == "AI and programming topic."

    def test_valid_json_not_interesting(self) -> None:
        raw = '{"interesting": false, "reason": "Sports article."}'
        result = Classifier._parse_response(raw)
        assert result.interesting is False
        assert result.reason == "Sports article."

    def test_invalid_json_raises_error(self) -> None:
        raw = "not valid json"
        with pytest.raises(ClassificationError, match="not valid JSON"):
            Classifier._parse_response(raw)

    def test_missing_interesting_field(self) -> None:
        raw = '{"reason": "Something."}'
        with pytest.raises(ClassificationError, match="failed validation"):
            Classifier._parse_response(raw)

    def test_missing_reason_field(self) -> None:
        raw = '{"interesting": true}'
        with pytest.raises(ClassificationError, match="failed validation"):
            Classifier._parse_response(raw)

    def test_extra_fields_ignored(self) -> None:
        raw = '{"interesting": false, "reason": "Test.", "extra": "ignored"}'
        result = Classifier._parse_response(raw)
        assert result.interesting is False
        assert result.reason == "Test."

    def test_wrong_type_for_interesting(self) -> None:
        raw = '{"interesting": 123, "reason": "Test."}'
        with pytest.raises(ClassificationError, match="failed validation"):
            Classifier._parse_response(raw)

    def test_empty_string(self) -> None:
        with pytest.raises(ClassificationError, match="not valid JSON"):
            Classifier._parse_response("")

    def test_json_with_triple_backticks(self) -> None:
        """LLMs sometimes wrap JSON in markdown code fences."""
        raw = '```json\n{"interesting": true, "reason": "Test."}\n```'
        with pytest.raises(ClassificationError, match="not valid JSON"):
            # Our parser doesn't handle markdown fences; the LLM prompt
            # should instruct it to return JSON only. This test documents
            # current behavior.
            Classifier._parse_response(raw)


class TestClassifier:
    """Tests for the full ``Classifier.classify`` method."""

    def test_classify_interesting(self, mock_llm_client, sample_article) -> None:
        classifier = Classifier(client=mock_llm_client, model="test-model")
        result = classifier.classify(sample_article)

        assert result.interesting is True
        assert result.reason == "Interesting topic."
        mock_llm_client.send_message.assert_called_once()

    def test_classify_not_interesting(
        self, mock_llm_client_not_interesting, sample_article
    ) -> None:
        classifier = Classifier(
            client=mock_llm_client_not_interesting, model="test-model"
        )
        result = classifier.classify(sample_article)
        assert result.interesting is False
        assert result.reason == "Uninteresting primary topic."

    def test_classify_llm_error(self, mock_llm_client_failure, sample_article) -> None:
        classifier = Classifier(client=mock_llm_client_failure, model="test-model")
        with pytest.raises(ClassificationError, match="LLM classification failed"):
            classifier.classify(sample_article)

    def test_classify_sends_correct_prompt(
        self, mock_llm_client, sample_article
    ) -> None:
        classifier = Classifier(client=mock_llm_client, model="test-model")
        classifier.classify(sample_article)

        call_args = mock_llm_client.send_message.call_args
        assert call_args is not None
        kwargs = call_args[1]
        assert "system_prompt" in kwargs
        assert "user_message" in kwargs

        # Check system prompt contains key instructions
        system_prompt = kwargs["system_prompt"]
        assert "Interested topics" in system_prompt
        assert "Uninteresting topics" in system_prompt
        assert "cars" in system_prompt
        assert "sports" in system_prompt

        # Check user message contains article details
        user_message = kwargs["user_message"]
        assert "Test Article" in user_message
        assert "https://example.com/test-article" in user_message

    def test_model_property(self, mock_llm_client) -> None:
        classifier = Classifier(client=mock_llm_client, model="my-model")
        assert classifier.model == "my-model"

    def test_car_article_classified_as_not_interesting(
        self, mock_llm_client_not_interesting, article_car_news
    ) -> None:
        classifier = Classifier(
            client=mock_llm_client_not_interesting, model="test-model"
        )
        result = classifier.classify(article_car_news)
        assert result.interesting is False

    def test_motogp_article_classified_as_not_interesting(
        self, mock_llm_client_not_interesting, article_motogp
    ) -> None:
        classifier = Classifier(
            client=mock_llm_client_not_interesting, model="test-model"
        )
        result = classifier.classify(article_motogp)
        assert result.interesting is False

    def test_nfl_article_classified_as_not_interesting(
        self, mock_llm_client_not_interesting, article_nfl
    ) -> None:
        classifier = Classifier(
            client=mock_llm_client_not_interesting, model="test-model"
        )
        result = classifier.classify(article_nfl)
        assert result.interesting is False

    def test_ai_robot_article_classified_as_interesting(
        self, mock_llm_client, article_ai_robot
    ) -> None:
        classifier = Classifier(client=mock_llm_client, model="test-model")
        result = classifier.classify(article_ai_robot)
        assert result.interesting is True

    def test_nasa_article_classified_as_interesting(
        self, mock_llm_client, article_nasa
    ) -> None:
        classifier = Classifier(client=mock_llm_client, model="test-model")
        result = classifier.classify(article_nasa)
        assert result.interesting is True

    def test_linux_article_classified_as_interesting(
        self, mock_llm_client, article_linux
    ) -> None:
        classifier = Classifier(client=mock_llm_client, model="test-model")
        result = classifier.classify(article_linux)
        assert result.interesting is True