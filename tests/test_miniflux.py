"""Tests for the Miniflux API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from miniflux_ai_filter.miniflux import (
    MinifluxClient,
    MinifluxEntry,
    MinifluxError,
)


class TestMinifluxEntry:
    """Tests for ``MinifluxEntry.from_api_dict``."""

    def test_from_api_dict_full_data(self, miniflux_entry_data) -> None:
        entry = MinifluxEntry.from_api_dict(miniflux_entry_data)
        assert entry.id == 42
        assert entry.feed_id == 1
        assert entry.title == "Test Article"
        assert entry.url == "https://example.com/test-article"
        assert entry.published_at == "2026-07-09T12:00:00Z"
        assert entry.summary == "A test article summary."
        assert entry.content == "<p>Article content here.</p>"

    def test_from_api_dict_minimal_data(self) -> None:
        data = {"id": 1, "feed_id": 2}
        entry = MinifluxEntry.from_api_dict(data)
        assert entry.id == 1
        assert entry.feed_id == 2
        assert entry.title == ""
        assert entry.url == ""
        assert entry.published_at == ""
        assert entry.summary == ""
        assert entry.content == ""

    def test_from_api_dict_missing_keys(self) -> None:
        data = {}
        with pytest.raises(KeyError):
            MinifluxEntry.from_api_dict(data)


class TestGetUnreadEntries:
    """Tests for ``MinifluxClient.get_unread_entries``."""

    def test_fetches_single_feed(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com",
            api_token="test-token",
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = True
        mock_response.json.return_value = {
            "entries": [
                {
                    "id": 1,
                    "feed_id": 1,
                    "title": "Article 1",
                    "url": "https://example.com/1",
                    "published_at": "2026-07-09T12:00:00Z",
                    "summary": "Summary 1",
                    "content": "Content 1",
                },
                {
                    "id": 2,
                    "feed_id": 1,
                    "title": "Article 2",
                    "url": "https://example.com/2",
                    "published_at": "2026-07-09T11:00:00Z",
                    "summary": "Summary 2",
                    "content": "Content 2",
                },
            ]
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            entries = client.get_unread_entries(1)

        assert len(entries) == 2
        assert mock_get.call_count == 1

        # Verify request parameters
        call_args = mock_get.call_args
        kwargs = call_args[1]
        assert kwargs["params"]["feed_id"] == 1
        assert kwargs["params"]["status"] == "unread"
        assert kwargs["params"]["limit"] == 100

    def test_http_error_raises_exception(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com",
            api_token="test-token",
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(MinifluxError, match="500"):
                client.get_unread_entries(1)


class TestMarkEntryRead:
    """Tests for ``MinifluxClient.mark_entry_read``."""

    def test_successful_mark_read(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com",
            api_token="test-token",
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = True

        with patch("requests.put", return_value=mock_response) as mock_put:
            client.mark_entry_read(42)

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert call_args is not None
        kwargs = call_args[1]
        assert kwargs["json"] == {
            "entry_ids": [42],
            "status": "read",
        }

    def test_http_error_raises_exception(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com",
            api_token="test-token",
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.put", return_value=mock_response):
            with pytest.raises(MinifluxError, match="401"):
                client.mark_entry_read(42)

    def test_url_construction_no_trailing_slash(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com",
            api_token="test-token",
        )
        assert client.base_url == "https://reader.example.com"

    def test_url_construction_strips_trailing_slash(self) -> None:
        client = MinifluxClient(
            base_url="https://reader.example.com/",
            api_token="test-token",
        )
        assert client.base_url == "https://reader.example.com"