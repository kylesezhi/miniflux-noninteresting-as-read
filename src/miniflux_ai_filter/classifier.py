"""Article classifier that uses an LLM to determine interest.

Owns the classification prompt and formatting logic, delegating the actual
API call to any :class:`~miniflux_ai_filter.protocols.LLMClient` implementation.
"""

from __future__ import annotations

import json

from miniflux_ai_filter.models import Article, ClassificationResult
from miniflux_ai_filter.protocols import LLMClient, LLMError


class ClassificationError(Exception):
    """Raised when classification fails (LLM error, parsing error, etc.)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Classifier:
    """Classifies articles using an LLM via any :class:`LLMClient` implementation.

    Parameters
    ----------
    client:
        An :class:`LLMClient`-compatible chat completion client.
    model:
        Human-readable model identifier used for logging and audit trails.
    """

    def __init__(self, client: LLMClient, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        """The model identifier used by this classifier."""
        return self._model

    # ── Public API ────────────────────────────────────────────────────

    def classify(
        self, article: Article, system_prompt: str
    ) -> ClassificationResult:
        """Classify a single article as interesting or not.

        Parameters
        ----------
        article:
            The article to classify.
        system_prompt:
            The system prompt to use for classification.

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
                system_prompt=system_prompt,
                user_message=user_message,
            )
        except LLMError as exc:
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