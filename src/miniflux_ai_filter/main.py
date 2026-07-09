"""Orchestration: connects all components into a single pipeline run.

Flow
----
1. Load configuration
2. Generate a unique run ID
3. Fetch unread articles from Miniflux
4. Sort newest first
5. Limit to ``MAX_ARTICLES_PER_RUN``
6. Classify each article via the LLM
7. Mark uninteresting articles as read on the Miniflux server
8. Write every classification decision (and any errors) to the JSONL audit log
"""

from __future__ import annotations

import uuid

from miniflux_ai_filter.classifier import Classifier, ClassificationError
from miniflux_ai_filter.config import Settings
from miniflux_ai_filter.logging import JsonlLogger
from miniflux_ai_filter.miniflux import MinifluxClient, MinifluxError
from miniflux_ai_filter.models import Article
from miniflux_ai_filter.opencodego import OpencodeGoClient
from miniflux_ai_filter.openrouter import OpenRouterClient
from miniflux_ai_filter.protocols import LLMClient


def run_pipeline() -> None:
    """Execute the full classification pipeline.

    This is the top-level entry point for the application.  It wires together
    configuration, the Miniflux API client, the classifier, and the JSONL
    logger into a single run that:

    - Fetches unread articles from the configured feeds
    - Classifies each with the LLM
    - Marks uninteresting articles as read on Miniflux
    - Logs every decision (and any errors) to ``logs/classifier.jsonl``
    """
    # ── 1. Load configuration ──────────────────────────────────────────
    config = Settings()

    # ── 2. Generate run_id ─────────────────────────────────────────────
    run_id = uuid.uuid4().hex

    # ── 3. Instantiate clients ─────────────────────────────────────────
    miniflux_client = MinifluxClient(
        base_url=config.MINIFLUX_URL,
        api_token=config.MINIFLUX_API_TOKEN,
    )

    llm_client: LLMClient
    if config.LLM_PROVIDER == "opencodego":
        llm_client = OpencodeGoClient(
            api_key=config.OPENCODEGO_API_KEY,
            model=config.OPENCODEGO_MODEL,
            timeout=config.OPENCODEGO_TIMEOUT_SECONDS,
        )
        model_name = config.OPENCODEGO_MODEL
    else:
        llm_client = OpenRouterClient(
            api_key=config.OPENROUTER_API_KEY,
            model=config.OPENROUTER_MODEL,
        )
        model_name = config.OPENROUTER_MODEL

    classifier = Classifier(client=llm_client, model=model_name)
    logger = JsonlLogger()

    # ── 4. Fetch unread articles ───────────────────────────────────────
    print(f"Fetching unread articles for feed IDs: {config.feed_ids}")
    articles = miniflux_client.get_unread_entries(config.feed_ids)
    print(f"  Found {len(articles)} unread articles")

    # ── 5. Sort newest first ───────────────────────────────────────────
    articles.sort(key=lambda e: e.published_at, reverse=True)

    # ── 6. Limit to MAX_ARTICLES_PER_RUN ───────────────────────────────
    articles = articles[: config.MAX_ARTICLES_PER_RUN]
    print(f"  Processing up to {len(articles)} articles")

    # ── 7. Process each article ────────────────────────────────────────
    marked_read = 0
    errors = 0

    for entry in articles:
        article = Article(
            id=entry.id,
            feed_id=entry.feed_id,
            title=entry.title,
            url=entry.url,
            published_at=entry.published_at,
            summary=entry.summary,
            content=entry.content,
        )

        try:
            result = classifier.classify(article)

            if not result.interesting:
                miniflux_client.mark_entry_read(entry.id)
                marked_read += 1

            logger.log_classification(
                article=article,
                interesting=result.interesting,
                reason=result.reason,
                run_id=run_id,
                model=classifier.model,
            )

        except (ClassificationError, MinifluxError) as exc:
            errors += 1
            logger.log_error(
                run_id=run_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                article_id=entry.id,
            )
            print(f"  ERROR processing article {entry.id}: {exc}")

    # ── 8. Summary ─────────────────────────────────────────────────────
    processed = len(articles)
    print(f"\nRun {run_id} complete:")
    print(f"  Processed: {processed}")
    print(f"  Marked read: {marked_read}")
    print(f"  Errors: {errors}")