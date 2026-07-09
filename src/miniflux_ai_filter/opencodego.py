"""Generic Opencode Go client for chat completions.

Provides a thin wrapper around the Opencode Go API (OpenAI-compatible chat
completions endpoint).  No domain-specific classification logic lives here;
that belongs in :mod:`miniflux_ai_filter.classifier`.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests


logger = logging.getLogger(__name__)


class OpencodeGoError(Exception):
    """Raised when the Opencode Go API call or response parsing fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OpencodeGoClient:
    """Client for the Opencode Go chat completions API.

    Parameters
    ----------
    api_key:
        Opencode Go API key.
    model:
        Model identifier to use (e.g. ``deepseek-v4-flash``).
    temperature:
        Sampling temperature (default 0.2).
    timeout:
        Request timeout in seconds (default 60).
    """

    BASE_URL = "https://opencode.ai/zen/go/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        timeout: int = 60,
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
        OpencodeGoError:
            If the API call fails or the response structure is unexpected.
        """
        payload = self._build_payload(system_prompt, user_message)
        start = time.monotonic()

        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Opencode Go request timed out after %ss [duration=%.2fs]",
                self.timeout,
                elapsed,
            )
            raise OpencodeGoError(
                f"Opencode Go request timed out after {self.timeout}s"
            ) from exc
        except requests.ConnectionError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Opencode Go connection failed after %.2fs: %s",
                elapsed,
                exc,
            )
            raise OpencodeGoError(
                f"Opencode Go connection failed: {exc}"
            ) from exc
        except requests.RequestException as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Opencode Go request failed after %.2fs: %s",
                elapsed,
                exc,
            )
            raise OpencodeGoError(f"Opencode Go request failed: {exc}") from exc

        elapsed = time.monotonic() - start

        if not response.ok:
            logger.warning(
                "Opencode Go API error [%s] after %.2fs",
                response.status_code,
                elapsed,
            )
            raise OpencodeGoError(
                f"Opencode Go API error [{response.status_code}]: {response.text}"
            )

        logger.info(
            "Opencode Go request succeeded [model=%s, status=%s, duration=%.2fs]",
            self.model,
            response.status_code,
            elapsed,
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
            raise OpencodeGoError(
                f"Unexpected Opencode Go response structure: {exc}"
            ) from exc