"""Tests for the Opencode Go client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from miniflux_ai_filter.opencodego import OpencodeGoClient, OpencodeGoError


class TestBuildPayload:
    """Tests for ``OpencodeGoClient._build_payload``."""

    def test_build_payload_structure(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="deepseek-v4-flash"
        )
        payload = client._build_payload(
            system_prompt="You are a classifier.",
            user_message="Classify this article.",
        )

        assert payload["model"] == "deepseek-v4-flash"
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

    def test_build_payload_custom_temperature(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", temperature=0.5
        )
        payload = client._build_payload(
            system_prompt="System.", user_message="User."
        )
        assert payload["temperature"] == 0.5


class TestExtractContent:
    """Tests for ``OpencodeGoClient._extract_content``."""

    def test_extract_normal_response(self, opencodego_response) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        content = client._extract_content(opencodego_response)
        assert content == '{"interesting": true, "reason": "Test reason."}'

    def test_extract_missing_choices(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        with pytest.raises(OpencodeGoError, match="Unexpected"):
            client._extract_content({})

    def test_extract_empty_choices(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        with pytest.raises(OpencodeGoError, match="Unexpected"):
            client._extract_content({"choices": []})

    def test_extract_missing_message(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        with pytest.raises(OpencodeGoError, match="Unexpected"):
            client._extract_content({"choices": [{}]})

    def test_extract_missing_content(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        with pytest.raises(OpencodeGoError, match="Unexpected"):
            client._extract_content(
                {"choices": [{"message": {}}]}
            )

    def test_extract_empty_content(self) -> None:
        """Empty content is technically valid; classifier catches it later."""
        client = OpencodeGoClient(api_key="key", model="m")
        content = client._extract_content(
            {"choices": [{"message": {"content": ""}}]}
        )
        assert content == ""


class TestSendMessage:
    """Tests for ``OpencodeGoClient.send_message``."""

    def test_successful_request(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", timeout=10
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
        mock_post.assert_called_once_with(
            client.BASE_URL,
            headers=client.headers,
            json=client._build_payload("System.", "User."),
            timeout=10,
        )

    def test_http_error(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", timeout=10
        )

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(OpencodeGoError, match="401"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_timeout_error(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", timeout=1
        )

        with patch(
            "requests.post", side_effect=requests.Timeout("timed out")
        ):
            with pytest.raises(OpencodeGoError, match="timed out"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_connection_error(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", timeout=10
        )

        with patch(
            "requests.post",
            side_effect=requests.ConnectionError("connection failed"),
        ):
            with pytest.raises(OpencodeGoError, match="connection failed"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_generic_request_error(self) -> None:
        client = OpencodeGoClient(
            api_key="test-key", model="test-model", timeout=10
        )

        with patch(
            "requests.post",
            side_effect=requests.RequestException("generic error"),
        ):
            with pytest.raises(OpencodeGoError, match="generic error"):
                client.send_message(
                    system_prompt="System.", user_message="User."
                )

    def test_headers_contain_auth(self) -> None:
        client = OpencodeGoClient(
            api_key="my-secret-key", model="test-model"
        )
        assert client.headers["Authorization"] == "Bearer my-secret-key"
        assert client.headers["Content-Type"] == "application/json"


class TestClientIdentification:
    """Tests for User-Agent and x-opencode-session headers."""

    def test_user_agent_identifies_app(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        ua = client.headers["User-Agent"]
        assert ua.startswith("miniflux-noninteresting-as-read/")
        assert not ua.startswith("python-requests")

    def test_session_id_defaults_to_uuid_hex(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")
        session_id = client.headers["x-opencode-session"]
        assert len(session_id) == 32
        int(session_id, 16)
        assert session_id == client.session_id

    def test_explicit_session_id_is_used(self) -> None:
        client = OpencodeGoClient(
            api_key="key", model="m", session_id="my-session-123"
        )
        assert client.headers["x-opencode-session"] == "my-session-123"

    def test_empty_session_id_falls_back_to_uuid(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m", session_id="")
        assert len(client.headers["x-opencode-session"]) == 32

    def test_session_id_stable_across_calls(self) -> None:
        client = OpencodeGoClient(api_key="key", model="m")

        mock_response = MagicMock(spec=requests.Response)
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }

        with patch(
            "requests.post", return_value=mock_response
        ) as mock_post:
            client.send_message(system_prompt="S.", user_message="U1.")
            client.send_message(system_prompt="S.", user_message="U2.")

        assert mock_post.call_count == 2
        first = mock_post.call_args_list[0].kwargs["headers"]
        second = mock_post.call_args_list[1].kwargs["headers"]
        assert first["x-opencode-session"] == second["x-opencode-session"]
        assert first["User-Agent"] == second["User-Agent"]