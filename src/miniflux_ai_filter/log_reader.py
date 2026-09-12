"""Reading and summarizing the JSONL audit trail for the web log viewer.

Pure, side-effect-free helpers over ``logs/classifier.jsonl`` (see
:mod:`miniflux_ai_filter.jsonl_logger` for the writing side).  The audit
trail mixes two entry shapes:

- Classification entries — written by ``JsonlLogger.log_classification``
  (contain ``interesting``, ``reason``, article metadata, …)
- Error entries — written by ``JsonlLogger.log_error`` (contain
  ``error_type`` and ``error_message``)

Both shapes are represented as plain dicts; entries are distinguished by the
presence of the ``error_type`` key.  Malformed lines are skipped so a
half-written final line (from a crash or concurrent tail) never breaks the
viewer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_FILTERS = ("all", "errors", "classifications")

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000


def parse_log_file(file_path: str | Path) -> list[dict[str, Any]]:
    """Read every entry from the JSONL audit trail, oldest first.

    Malformed lines (blank, non-JSON, truncated) are skipped silently.

    Parameters
    ----------
    file_path:
        Path to the JSONL file.  A missing file yields an empty list.
    """
    path = Path(file_path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return []

    entries: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            entries.append(data)
    return entries


def classify_entry(entry: dict[str, Any]) -> str:
    """Return ``"error"`` or ``"classification"`` for a parsed entry."""
    if "error_type" in entry:
        return "error"
    return "classification"


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate stats over the full (unfiltered) entry list.

        Returns
        -------
        dict
            ``total``, ``classifications``, ``errors``, ``interesting``,
            ``not_interesting``, ``last_timestamp`` and ``last_run_id`` —
            the latter two taken from the newest entry in the file.
    """
    classifications = [e for e in entries if classify_entry(e) == "classification"]
    errors = [e for e in entries if classify_entry(e) == "error"]

    last_timestamp: str | None = entries[-1].get("timestamp") if entries else None
    last_run_id: str | None = entries[-1].get("run_id") if entries else None

    return {
        "total": len(entries),
        "classifications": len(classifications),
        "errors": len(errors),
        "interesting": sum(
            1 for e in classifications if e.get("interesting") is True
        ),
        "not_interesting": sum(
            1 for e in classifications if e.get("interesting") is False
        ),
        "last_timestamp": last_timestamp,
        "last_run_id": last_run_id,
    }


def fetch_view(
    file_path: str | Path,
    filter_name: str = "all",
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Read the log and return the filtered view plus a full summary.

    Entries are returned newest first (the JSONL file is append-only, so the
    last lines are the newest).

    Parameters
    ----------
    file_path:
        Path to the JSONL audit trail.
    filter_name:
        One of ``all``, ``errors`` or ``classifications``.  Any other value
        falls back to ``all``.
    limit:
        Maximum number of entries to return (clamped to 1..MAX_LIMIT).
    """
    if filter_name not in VALID_FILTERS:
        filter_name = "all"
    if not isinstance(limit, int) or isinstance(limit, bool):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    entries = parse_log_file(file_path)
    summary = summarize(entries)

    if filter_name == "errors":
        entries = [e for e in entries if classify_entry(e) == "error"]
    elif filter_name == "classifications":
        entries = [e for e in entries if classify_entry(e) == "classification"]

    return {
        "filter": filter_name,
        "entries": list(reversed(entries[-limit:])),
        "summary": summary,
    }
