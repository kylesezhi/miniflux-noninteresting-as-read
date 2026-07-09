"""Tests for the OpenRouter client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from miniflux_ai_filter.openrouter import OpenRouterClient, OpenRouterError


class TestBuildPayload:
    """Tests for ``OpenRouterClient._build_payload``."""

    def test_build_payload_structure(self) -> None:
        client = OpenRouterClient(
            api_key="test-key", model="openai/gpt-oss-120b:free"
        )
        payload = client._build_payload(
            system_prompt="You are a classifier.",
            user_message="Classify this article.",
        )

        assert payload["model"] == "openai/gpt-oss-120b:free"
        assert payload["temperature"] == 0.2
        assert len(payload["messages"]) == 2
        assert payload["messages"][0] == {
            "role": "system",
            "content": "You are a classifier.",
        }
        assert payload["messages"][1] == {
            "role": "user",
            "content": "Classify this article.",
        }


class TestExtractContent:
    """Tests for ``OpenRouterClient._extract_content``."""

    def test_extract_normal_response(self) -> None:
        client = OpenRouterClient(api_key="key", model="m")
        data = {
            "choices": [
                {
                    "message": {
                        "content": '{"interesting": true, "reason": "Test."}',
                    }
                }
            ]
        }
        content = client._extract_content(data)
        assert content == '{"interesting": true, "reason": "Test."}'

    def test_extract_missing_choices(self) -> None:
        client = OpenRouterClient(api_key="key", model="m")
        with pytest.raises(OpenRouterError, match="Unexpected"):
            client._extract_content({})

    def test_extract_empty_choices(self) -> None:
        client = OpenRouterClient(api_key="key", model="m")
        with pytest.raises(OpenRouterError, match="Unexpected"):
            client._extract_content({"choices": []})

    def test_extract_missing_message(self) -> None:
        client = OpenRouterClient(api_key="key", model="m")
        with pytest.raises(OpenRouterError, match="Unexpected"):
            client._extract_content({"choices": [{}]})

    def test_extract_missing_content(self) -> None:
        client = OpenRouterClient(api_key="key", model="m")
        with pytest.raises(OpenRouterError, match="Unexpected"):
            client._extract_content({"choices": [{"message": {}}]})

    def test_extract_empty_content(self) -> None:
        """Empty content is technically valid; classifier catches it later."""
        client = OpenRouterClient(api_key="key", model="m")
        content = client._extract_content(
            {"choices": [{"message": {"content": ""}}]}
        )
        assert content == ""


class TestSendMessage:
    """Tests for ``OpenRouterClient.send_message``."""

    def test_successful_request(self) -> None:
        client = OpenRouterClient(
            api_key="test-key", model="test-model"
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"interesting": false, "reason": "Sports."}',
                    }
                }
            ]
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = client.send_message(
                system_prompt="System.", user_message="User."
            )

        assert result == '{"interesting": false, "reason": "Sports."}'
        mock_post.assert_called_once()

    def test_http_error(self) -> None:
        client = OpenRouterClient(api_key="test-key", model="test-model")

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.text = "Rate limited"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(OpenRouterError, match="429"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_timeout_error(self) -> None:
        client = OpenRouterClient(api_key="test-key", model="test-model")

        with patch(
            "requests.post", side_effect=requests.Timeout("timed out")
        ):
            with pytest.raises(OpenRouterError, match="timed out"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_headers_contain_auth(self) -> None:
        client = OpenRouterClient(api_key="my-secret-key", model="test-model")
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer my-secret-key"
        assert client.headers["Content-Type"] == "application/json"