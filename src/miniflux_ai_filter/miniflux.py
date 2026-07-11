"""Miniflux API client wrapper.

Provides a small typed wrapper around the Miniflux REST API for fetching
unread entries and marking entries as read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class MinifluxError(Exception):
    """Raised when the Miniflux API returns a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Miniflux API error [{status_code}]: {body}")


@dataclass
class MinifluxEntry:
    """Normalized representation of a single Miniflux entry (article)."""

    id: int
    feed_id: int
    title: str
    url: str
    published_at: str
    summary: str
    content: str

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> "MinifluxEntry":
        """Create an entry from the raw Miniflux API response dictionary."""
        return cls(
            id=data["id"],
            feed_id=data["feed_id"],
            title=data.get("title", ""),
            url=data.get("url", ""),
            published_at=data.get("published_at", ""),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
        )


class MinifluxClient:
    """Thin client for the Miniflux REST API.

    Parameters
    ----------
    base_url:
        Base URL of the Miniflux instance (e.g. ``https://reader.example.com``).
    api_token:
        Miniflux API authentication token.
    timeout:
        Request timeout in seconds (default 30).
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Auth-Token": api_token,
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    # ── Public API ────────────────────────────────────────────────────

    def get_unread_entries(self, feed_id: int) -> list[MinifluxEntry]:
        """Fetch all unread entries for a single feed.

        Parameters
        ----------
        feed_id:
            The numeric feed ID to fetch unread entries from.

        Returns
        -------
        list[MinifluxEntry]:
            Normalized entries for the requested feed.
        """
        return self._fetch_feed_entries(feed_id)

    def mark_entry_read(self, entry_id: int) -> None:
        """Mark a single entry as read.

        Parameters
        ----------
        entry_id:
            The numeric ID of the entry to mark as read.
        """
        payload = {
            "entry_ids": [entry_id],
            "status": "read",
        }
        url = f"{self.base_url}/v1/entries"
        response = requests.put(
            url,
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        if not response.ok:
            raise MinifluxError(response.status_code, response.text)

    # ── Internal helpers ──────────────────────────────────────────────

    def _fetch_feed_entries(self, feed_id: int) -> list[MinifluxEntry]:
        """Retrieve all unread entries for a single feed."""
        url = f"{self.base_url}/v1/entries"
        params: dict[str, Any] = {
            "status": "unread",
            "feed_id": feed_id,
            "limit": 100,
        }

        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )

        if not response.ok:
            raise MinifluxError(response.status_code, response.text)

        data = response.json()
        raw_entries = data.get("entries", [])
        return [MinifluxEntry.from_api_dict(e) for e in raw_entries]