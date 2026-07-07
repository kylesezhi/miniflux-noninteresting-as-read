"""OpenRouter AI client for article classification.

Provides a thin wrapper around the OpenRouter API (OpenAI-compatible chat
completions endpoint) for classifying articles as interesting or not.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from miniflux_ai_filter.models import Article, ClassificationResult


class OpenRouterError(Exception):
    """Raised when the OpenRouter API call or response parsing fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OpenRouterClient:
    """Client for the OpenRouter chat completions API.

    Parameters
    ----------
    api_key:
        OpenRouter API key.
    model:
        Model identifier to use (e.g. ``openai/gpt-oss-120b:free``).
    temperature:
        Sampling temperature (default 0.2).
    timeout:
        Request timeout in seconds (default 30).
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        self.headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ── Public API ────────────────────────────────────────────────────

    def classify_article(self, article: Article) -> ClassificationResult:
        """Send an article to the LLM and return a classification result.

        Parameters
        ----------
        article:
            The article to classify.

        Returns
        -------
        ClassificationResult:
            Parsed classification from the LLM response.

        Raises
        ------
        OpenRouterError:
            If the API call fails, the response is not valid JSON, or the
            parsed JSON does not match the ``ClassificationResult`` schema.
        """
        payload = self._build_payload(article)

        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise OpenRouterError(
                f"OpenRouter request timed out after {self.timeout}s"
            ) from exc
        except requests.ConnectionError as exc:
            raise OpenRouterError(
                f"OpenRouter connection failed: {exc}"
            ) from exc
        except requests.RequestException as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        if not response.ok:
            raise OpenRouterError(
                f"OpenRouter API error [{response.status_code}]: {response.text}"
            )

        return self._parse_response(response.json())

    # ── Internal helpers ──────────────────────────────────────────────

    def _build_payload(self, article: Article) -> dict[str, Any]:
        """Construct the chat completion request payload."""
        system_prompt = (
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

        # Truncate content to first 2000 characters
        content_preview = article.content[:2000]

        user_message = (
            f"Title: {article.title}\n"
            f"URL: {article.url}\n"
            f"Feed ID: {article.feed_id}\n"
            f"Published: {article.published_at}\n"
            f"Summary: {article.summary}\n"
            f"Content: {content_preview}"
        )

        return {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

    def _parse_response(self, data: dict[str, Any]) -> ClassificationResult:
        """Extract and validate the classification from the API response.

        Parameters
        ----------
        data:
            The parsed JSON response from the OpenRouter API.

        Returns
        -------
        ClassificationResult:
            Validated classification result.

        Raises
        ------
        OpenRouterError:
            If the response structure is unexpected or the content cannot
            be parsed into a valid ``ClassificationResult``.
        """
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError(
                f"Unexpected OpenRouter response structure: {exc}"
            ) from exc

        # Attempt to parse the content as JSON
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenRouterError(
                f"OpenRouter response is not valid JSON: {exc}\n"
                f"Raw content: {content}"
            ) from exc

        # Validate against the ClassificationResult schema
        try:
            return ClassificationResult.model_validate(parsed)
        except Exception as exc:
            raise OpenRouterError(
                f"OpenRouter response failed validation: {exc}\n"
                f"Parsed content: {parsed}"
            ) from exc