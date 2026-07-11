"""Orchestration: connects all components into a single pipeline run.

Flow
----
1. Load configuration
2. Generate a unique run ID
3. Load per-feed configuration from ``feeds.yaml``
4. For each configured feed:
   a. Fetch unread articles from Miniflux
   b. Sort newest first
   c. Limit to the feed's ``max_articles``
   d. Classify each article via the LLM
   e. Mark uninteresting articles as read on the Miniflux server
   f. Pause between LLM calls to respect rate limits
5. Write every classification decision (and any errors) to the JSONL audit log
6. Print per-feed and aggregate summary
"""

from __future__ import annotations

import time
import uuid

from miniflux_ai_filter.classifier import Classifier, ClassificationError
from miniflux_ai_filter.config import Settings
from miniflux_ai_filter.feeds_config import FeedsConfig
from miniflux_ai_filter.jsonl_logger import JsonlLogger
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

    - Fetches unread articles from each configured feed independently
    - Classifies each with the LLM (with rate-limit delays between calls)
    - Marks uninteresting articles as read on Miniflux
    - Logs every decision (and any errors) to ``logs/classifier.jsonl``
    - Reports per-feed and aggregate statistics
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

    # ── 4. Load feeds config ───────────────────────────────────────────
    feeds_config = FeedsConfig.load()

    # ── 5. Process each feed independently ─────────────────────────────
    total_processed = 0
    total_marked_read = 0
    total_errors = 0

    for feed_cfg in feeds_config.feeds:
        feed_id = feed_cfg.feed_id
        print(f"\nFeed {feed_id}: fetching unread articles ...")
        raw_entries = miniflux_client.get_unread_entries(feed_id)

        if not raw_entries:
            print(f"  No unread articles for feed {feed_id}")
            continue

        raw_entries.sort(key=lambda e: e.published_at, reverse=True)

        raw_entries = raw_entries[: feed_cfg.max_articles]
        print(
            f"  Found {len(raw_entries)} unread articles "
            f"(limit: {feed_cfg.max_articles})"
        )

        feed_processed = 0
        feed_marked_read = 0
        feed_errors = 0

        for i, entry in enumerate(raw_entries):
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
                result = classifier.classify(
                    article, system_prompt=feed_cfg.prompt
                )

                if not result.interesting:
                    print(f"  Marking as read: {article.title}")
                    miniflux_client.mark_entry_read(entry.id)
                    feed_marked_read += 1

                logger.log_classification(
                    article=article,
                    interesting=result.interesting,
                    reason=result.reason,
                    run_id=run_id,
                    model=classifier.model,
                    prompt=feed_cfg.prompt,
                )
                feed_processed += 1

            except (ClassificationError, MinifluxError) as exc:
                feed_errors += 1
                logger.log_error(
                    run_id=run_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    article_id=entry.id,
                )
                print(f"  ERROR processing article {entry.id}: {exc}")

            # Rate limiting: sleep between LLM calls
            if i < len(raw_entries) - 1:
                time.sleep(config.CLASSIFICATION_DELAY_SECONDS)

        print(
            f"  Feed {feed_id} done — "
            f"processed: {feed_processed}, "
            f"marked read: {feed_marked_read}, "
            f"errors: {feed_errors}"
        )

        total_processed += feed_processed
        total_marked_read += feed_marked_read
        total_errors += feed_errors

    # ── 6. Aggregate summary ───────────────────────────────────────────
    print(f"\nRun {run_id} complete:")
    print(f"  Total processed: {total_processed}")
    print(f"  Total marked read: {total_marked_read}")
    print(f"  Total errors: {total_errors}")