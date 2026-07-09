"""Generic OpenRouter AI client for chat completions.

Provides a thin wrapper around the OpenRouter API (OpenAI-compatible chat
completions endpoint).  No domain-specific classification logic lives here;
that belongs in :mod:`miniflux_ai_filter.classifier`.
"""

from __future__ import annotations

from typing import Any

import requests


from miniflux_ai_filter.protocols import LLMError


class OpenRouterError(LLMError):
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

    def send_message(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """Send a chat completion request and return the response content.

        Parameters
        ----------
        system_prompt:
            The system-level instruction for the LLM.
        user_message:
            The user message content.

        Returns
        -------
        str:
            The raw content string from the model's response.

        Raises
        ------
        OpenRouterError:
            If the API call fails or the response structure is unexpected.
        """
        payload = self._build_payload(system_prompt, user_message)

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

        return self._extract_content(response.json())

    # ── Internal helpers ──────────────────────────────────────────────

    def _build_payload(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Construct the chat completion request payload."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Extract the response text from the API response dict."""
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            return message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError(
                f"Unexpected OpenRouter response structure: {exc}"
            ) from exc
