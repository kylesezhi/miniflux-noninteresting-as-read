"""Protocol definitions for LLM client abstraction.

Defines the ``LLMClient`` protocol that all LLM provider clients must satisfy,
and the ``LLMError`` base exception that all provider-specific errors should
inherit from.  This allows :mod:`~miniflux_ai_filter.classifier` to depend
only on the protocol rather than any concrete implementation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Base exception for all LLM client errors.

    All provider-specific error classes (e.g. ``OpencodeGoError``,
    ``OpenRouterError``) should inherit from this so that callers can
    catch a single exception type regardless of the provider in use.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol that all LLM chat-completion clients must satisfy.

    Implementations must provide a ``send_message`` method that accepts
    a system prompt and a user message and returns the model's response
    as a plain string.
    """

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
        LLMError:
            If the API call fails or the response structure is unexpected.
        """
        ...