"""Tests for the stdlib HTTP log viewer (web.py).

Starts an isolated server on an ephemeral port (bound127.0.0.1) backed by a
temporary JSONL fixture file, then exercises the routes with urllib.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Generator
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from miniflux_ai_filter.web import create_server, LogViewerHandler
from tests.test_log_reader import (
    ENTRY_ERROR,
    ENTRY_NEWEST,
    ENTRY_OLDEST,
)


@pytest.fixture
def web_server(
    tmp_path: Any,
) -> Generator[str, None, None]:
    """Start a log-viewer server on an ephemeral port; yield its base URL."""
    log = tmp_path / "classifier.jsonl"
    log.write_text(
        "\n".join(
            json.dumps(e)
            for e in (ENTRY_OLDEST, ENTRY_ERROR, ENTRY_NEWEST)
        )
        + "\n",
        encoding="utf-8",
    )
    server = create_server("127.0.0.1", 0, str(log))
    assert LogViewerHandler.log_path == str(log)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()


# ── Dashboard ─────────────────────────────────────────────────────────


class TestDashboard:
    def test_root_serves_html(self, web_server: str) -> None:
        with urlopen(f"{web_server}/") as res:
            assert res.status == 200
            assert res.headers["Content-Type"].startswith("text/html")
            body = res.read().decode("utf-8")

        assert "AI Filter Log Viewer" in body
        assert "/api/entries" in body

    def test_index_html_alias(self, web_server: str) -> None:
        with urlopen(f"{web_server}/index.html") as res:
            assert res.status == 200


# ── JSON API ──────────────────────────────────────────────────────────


class TestApiEntries:
    def test_returns_entries_and_summary(self, web_server: str) -> None:
        with urlopen(f"{web_server}/api/entries") as res:
            assert res.status == 200
            assert res.headers["Content-Type"].startswith("application/json")
            data = json.loads(res.read().decode("utf-8"))

        assert data["filter"] == "all"
        assert len(data["entries"]) == 3
        # Newest first (reversed append order)
        assert data["entries"][0]["timestamp"] == ENTRY_NEWEST["timestamp"]
        assert data["entries"][1]["error_type"] == "llm_failure"
        assert data["entries"][-1]["timestamp"] == ENTRY_OLDEST["timestamp"]

        summary = data["summary"]
        assert summary["total"] == 3
        assert summary["classifications"] == 2
        assert summary["errors"] == 1
        assert summary["interesting"] == 1
        assert summary["not_interesting"] == 1
        assert summary["last_run_id"] == ENTRY_NEWEST["run_id"]

    def test_filter_errors(self, web_server: str) -> None:
        data = json.loads(urlopen(f"{web_server}/api/entries?filter=errors").read())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["error_type"] == "llm_failure"
        assert data["summary"]["total"] == 3  # summary stays unfiltered

    def test_filter_classifications(self, web_server: str) -> None:
        data = json.loads(
            urlopen(f"{web_server}/api/entries?filter=classifications").read()
        )
        assert len(data["entries"]) == 2
        assert all("interesting" in e for e in data["entries"])

    def test_limit(self, web_server: str) -> None:
        data = json.loads(urlopen(f"{web_server}/api/entries?limit=1").read())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["timestamp"] == ENTRY_NEWEST["timestamp"]

    def test_invalid_limit_falls_back_to_default(self, web_server: str) -> None:
        data = json.loads(urlopen(f"{web_server}/api/entries?limit=abc").read())
        assert len(data["entries"]) == 3

    def test_unknown_filter_falls_back_to_all(self, web_server: str) -> None:
        data = json.loads(
            urlopen(f"{web_server}/api/entries?filter=nope").read()
        )
        assert data["filter"] == "all"
        assert len(data["entries"]) == 3

    def test_missing_log_file_yields_empty_view(self, tmp_path: Any) -> None:
        server = create_server("127.0.0.1", 0, str(tmp_path / "nonesuch.jsonl"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            data = json.loads(urlopen(f"{base}/api/entries").read())
        finally:
            server.shutdown()
            server.server_close()
        assert data["entries"] == []
        assert data["summary"]["total"] == 0


# ── Errors ────────────────────────────────────────────────────────────


class TestUnknownPaths:
    def test_unknown_path_returns_404(self, web_server: str) -> None:
        try:
            urlopen(f"{web_server}/definitely-not-here")
        except HTTPError as exc:
            assert exc.code == 404
            assert b"404" in exc.read()
        else:
            raise AssertionError("expected HTTP 404")
