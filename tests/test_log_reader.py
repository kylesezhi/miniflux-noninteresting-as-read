"""Tests for the JSONL audit-trail reader used by the web log viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import pytest

from miniflux_ai_filter.log_reader import (
    fetch_view,
    parse_log_file,
    classify_entry,
    summarize,
)

# ── Sample entries ────────────────────────────────────────────────────

RUN_A = "aaaa"
RUN_B = "bbbb"


def classification(
    timestamp: str,
    article_id: int,
    interesting: bool,
    reason: str = "reason",
    run_id: str = RUN_A,
    feed_id: int = 1,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "article_id": article_id,
        "feed_id": feed_id,
        "title": f"Article {article_id}",
        "url": f"https://example.com/{article_id}",
        "published_at": "2026-07-09T12:00:00Z",
        "interesting": interesting,
        "reason": reason,
        "model": "deepseek-v4-flash",
        "prompt": "p",
    }


def error(
    timestamp: str,
    error_type: str = "llm_failure",
    message: str = "boom",
    run_id: str = RUN_A,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "error_type": error_type,
        "error_message": message,
    }


ENTRY_OLDEST = classification("2026-09-12T07:00:00+00:00", 1, False)
ENTRY_MIDDLE = {
    **classification("2026-09-12T07:05:00+00:00", 2, True),
    "feed_id": 2,
}
ENTRY_ERROR = error("2026-09-12T07:06:00+00:00")
ENTRY_NEWEST = classification(
    "2026-09-12T07:10:00+00:00", 3, True, run_id=RUN_B
)


def write_log(tmp_path: Path, lines: list[str]) -> Path:
    log = tmp_path / "classifier.jsonl"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log


@pytest.fixture
def mixed_log(tmp_path: Path) -> Path:
    """A log with two classification entries, one error and malformed lines."""
    return write_log(
        tmp_path,
        [
            '{"bad json',
            "",  # blank line skipped
            json.dumps(ENTRY_OLDEST),
            json.dumps(ENTRY_MIDDLE),
            json.dumps(ENTRY_ERROR),
            json.dumps(ENTRY_NEWEST),
            '["not", "a", "dict"]',
        ],
    )


# ── Parsing ───────────────────────────────────────────────────────────


class TestParseLogFile:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert parse_log_file(tmp_path / "nope.jsonl") == []

    def test_malformed_lines_are_skipped(self, mixed_log: Path) -> None:
        entries = parse_log_file(mixed_log)
        # 4 valid dict entries, malformed lines and non-dict JSON skipped
        assert len(entries) == 4

    def test_preserves_file_order_oldest_first(self, mixed_log: Path) -> None:
        entries = parse_log_file(mixed_log)
        assert [e["article_id"] for e in entries if "article_id" in e] == [1, 2, 3]
        assert entries[-1].get("article_id") == 3
        assert entries[2].get("error_type") == "llm_failure"


# ── Entry classification ──────────────────────────────────────────────


class TestClassifyEntry:
    def test_error_entry_has_error_type(self) -> None:
        assert classify_entry(ENTRY_ERROR) == "error"

    def test_classification_entry(self) -> None:
        assert classify_entry(ENTRY_OLDEST) == "classification"


# ── Summary ───────────────────────────────────────────────────────────


class TestSummarize:
    def test_counts(self, mixed_log: Path) -> None:
        summary = summarize(parse_log_file(mixed_log))
        assert summary["total"] == 4
        assert summary["classifications"] == 3
        assert summary["errors"] == 1
        assert summary["interesting"] == 2
        assert summary["not_interesting"] == 1

    def test_last_entry_fields(self, mixed_log: Path) -> None:
        summary = summarize(parse_log_file(mixed_log))
        assert summary["last_timestamp"] == ENTRY_NEWEST["timestamp"]
        assert summary["last_run_id"] == RUN_B

    def test_empty_log_summary(self) -> None:
        summary = summarize([])
        assert summary["total"] == 0
        assert summary["last_timestamp"] is None
        assert summary["last_run_id"] is None


# ── Views (filter + ordering + limit) ─────────────────────────────────


class TestFetchView:
    def test_all_newest_first(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log)
        assert data["filter"] == "all"
        assert data["entries"][0]["timestamp"] == ENTRY_NEWEST["timestamp"]
        assert data["entries"][-1]["timestamp"] == ENTRY_OLDEST["timestamp"]

    def test_filter_errors(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log, filter_name="errors")
        assert len(data["entries"]) == 1
        assert data["entries"][0]["error_type"] == "llm_failure"

    def test_filter_classifications(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log, filter_name="classifications")
        assert len(data["entries"]) == 3
        assert all("interesting" in e for e in data["entries"])

    def test_limit_returns_newest_n(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log, limit=2)
        assert len(data["entries"]) == 2
        assert data["entries"][0]["timestamp"] == ENTRY_NEWEST["timestamp"]

    def test_limit_min_is_one(self, mixed_log: Path) -> None:
        assert len(fetch_view(mixed_log, limit=0)["entries"]) >= 1

    def test_limit_above_total_returns_all(self, mixed_log: Path) -> None:
        assert len(fetch_view(mixed_log, limit=1000)["entries"]) == 4

    def test_summary_is_not_affected_by_filter(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log, filter_name="errors")
        assert data["summary"]["total"] == 4
        assert data["summary"]["errors"] == 1

    def test_invalid_filter_falls_back_to_all(self, mixed_log: Path) -> None:
        data = fetch_view(mixed_log, filter_name="bogus")
        assert data["filter"] == "all"
        assert len(data["entries"]) == 4
