"""JSONL audit trail for article classification.

Writes a line-delimited JSON file (``logs/classifier.jsonl`` by default) that
records every classification decision as well as any failures encountered
during the pipeline run.  Each line is a valid JSON object, so the file can
be inspected with standard JSONL tooling (``jq``, ``pandas.read_json``,
etc.).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from miniflux_ai_filter.models import Article, ClassificationLog


class JsonlLogger:
    """Append-only JSONL logger for classification audit trails.

    Parameters
    ----------
    file_path:
        Path to the JSONL file.  The parent directory is created automatically
        if it does not exist.  Defaults to ``logs/classifier.jsonl`` relative
        to the project root.
    """

    def __init__(self, file_path: str | Path = "logs/classifier.jsonl") -> None:
        self._path = Path(file_path)

        # Ensure the parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────

    def log_classification(
        self,
        article: Article,
        interesting: bool,
        reason: str,
        run_id: str,
        model: str,
        prompt: str,
    ) -> None:
        """Record a single classification result as a JSONL entry.

        Parameters
        ----------
        article:
            The article that was classified.
        interesting:
            Whether the article was deemed interesting.
        reason:
            Explanation provided by the LLM.
        run_id:
            Unique identifier for this pipeline run.
        model:
            OpenRouter model identifier used for classification.
        prompt:
            Classification system prompt used.
        """
        entry = ClassificationLog(
            run_id=run_id,
            timestamp=_now_iso(),
            article_id=article.id,
            feed_id=article.feed_id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            interesting=interesting,
            reason=reason,
            model=model,
            prompt=prompt,
        )
        self._write_line(entry.model_dump())

    def log_error(
        self,
        run_id: str,
        error_type: str,
        error_message: str,
        article_id: int | None = None,
    ) -> None:
        """Record a pipeline failure (LLM, Miniflux, etc.) as a JSONL entry.

        Error log entries have a different shape from classification entries:
        they include ``error_type`` and ``error_message`` fields instead of
        the classification-specific fields.  This keeps the audit trail
        unambiguous.

        Parameters
        ----------
        run_id:
            Unique identifier for this pipeline run.
        error_type:
            A short machine-readable tag, e.g. ``"llm_failure"`` or
            ``"miniflux_failure"``.
        error_message:
            A human-readable description of the error.
        article_id:
            The article ID that was being processed when the error occurred,
            if applicable.
        """
        line: dict[str, Any] = {
            "run_id": run_id,
            "timestamp": _now_iso(),
            "error_type": error_type,
            "error_message": error_message,
        }
        if article_id is not None:
            line["article_id"] = article_id

        self._write_line(line)

    # ── Internal helpers ──────────────────────────────────────────────

    def _write_line(self, data: dict[str, Any]) -> None:
        """Append a single JSON line to the log file."""
        with self._path.open("a", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.write("\n")


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string (with timezone)."""
    return datetime.now(timezone.utc).isoformat()