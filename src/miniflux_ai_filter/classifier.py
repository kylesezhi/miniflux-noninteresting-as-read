"""Article classifier that uses an LLM to determine interest.

Owns the classification prompt and formatting logic, delegating the actual
API call to a generic :class:`~miniflux_ai_filter.openrouter.OpenRouterClient`.
"""

from __future__ import annotations

import json

from miniflux_ai_filter.models import Article, ClassificationResult
from miniflux_ai_filter.openrouter import OpenRouterClient, OpenRouterError


class ClassificationError(Exception):
    """Raised when classification fails (LLM error, parsing error, etc.)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Classifier:
    """Classifies articles using an LLM via OpenRouter.

    Parameters
    ----------
    client:
        A configured :class:`~miniflux_ai_filter.openrouter.OpenRouterClient`
        instance.
    """

    # ── Prompt template ───────────────────────────────────────────────

    SYSTEM_PROMPT = (
        "You are a content classifier. Given an article's details, "
        "determine whether it is interesting or not. "
        "Respond with a JSON object containing exactly two fields:\n"
        '  "interesting": true or false\n'
        '  "reason": a short explanation for your decision\n\n'
        "Rules:\n"
        "- Only filter when the primary topic is unwanted.\n"
        "- Do not filter incidental mentions of unwanted topics.\n\n"
        "Interested topics: programming, AI, science, cybersecurity, "
        "space, technology, engineering, general interesting news.\n"
        "Uninteresting topics: cars, motorcycles, sports."
    )

    def __init__(self, client: OpenRouterClient) -> None:
        self._client = client

    # ── Public API ────────────────────────────────────────────────────

    def classify(self, article: Article) -> ClassificationResult:
        """Classify a single article as interesting or not.

        Parameters
        ----------
        article:
            The article to classify.

        Returns
        -------
        ClassificationResult:
            The validated classification result.

        Raises
        ------
        ClassificationError:
            If the LLM call fails, the response is not valid JSON, or the
            parsed JSON does not match the ``ClassificationResult`` schema.
        """
        user_message = self._format_article(article)

        try:
            raw_content = self._client.send_message(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
            )
        except OpenRouterError as exc:
            raise ClassificationError(
                f"LLM classification failed: {exc.message}"
            ) from exc

        return self._parse_response(raw_content)

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _format_article(article: Article) -> str:
        """Format an article into a user message for the LLM.

        Includes the title, URL, feed ID, publication date, summary,
        and the first 2000 characters of content.
        """
        content_preview = article.content[:2000]
        return (
            f"Title: {article.title}\n"
            f"URL: {article.url}\n"
            f"Feed ID: {article.feed_id}\n"
            f"Published: {article.published_at}\n"
            f"Summary: {article.summary}\n"
            f"Content: {content_preview}"
        )

    @staticmethod
    def _parse_response(raw_content: str) -> ClassificationResult:
        """Parse and validate the LLM response as a ClassificationResult.

        Parameters
        ----------
        raw_content:
            The raw response string from the LLM.

        Returns
        -------
        ClassificationResult:
            Validated classification result.

        Raises
        ------
        ClassificationError:
            If the response cannot be parsed as valid JSON or fails
            Pydantic validation.
        """
        # Attempt to parse the content as JSON
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ClassificationError(
                f"LLM response is not valid JSON: {exc}\n"
                f"Raw content: {raw_content}"
            ) from exc

        # Validate against the ClassificationResult schema
        try:
            return ClassificationResult.model_validate(parsed)
        except Exception as exc:
            raise ClassificationError(
                f"LLM response failed validation: {exc}\n"
                f"Parsed content: {parsed}"
            ) from exc