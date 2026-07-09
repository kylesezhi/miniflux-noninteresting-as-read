#!/usr/bin/env python3
"""Calibration script for testing classifier accuracy against real LLM.

Usage
-----
    uv run python scripts/calibrate.py

Requires a valid ``.env`` file with credentials configured.  Sends each
edge-case article to the configured LLM and reports whether the
classification was correct.

The pass/fail criteria are based on the expected outcomes documented in
Milestone 9 of TODO.md:

**Should filter** (classifier should return interesting=false):
- "Tesla announces new vehicle lineup" (cars)
- "MotoGP championship results" (motorcycles)
- "NFL season preview" (sports)

**Should keep** (classifier should return interesting=true):
- "AI model trains Tesla robot" (AI/programming)
- "NASA spacecraft software update" (space/technology)
- "Linux kernel security vulnerability" (cybersecurity)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from miniflux_ai_filter.classifier import Classifier, ClassificationError
from miniflux_ai_filter.config import Settings
from miniflux_ai_filter.models import Article
from miniflux_ai_filter.opencodego import OpencodeGoClient
from miniflux_ai_filter.openrouter import OpenRouterClient
from miniflux_ai_filter.protocols import LLMClient


@dataclass
class EdgeCase:
    """A single edge case to test."""

    article: Article
    expected_interesting: bool
    description: str


def _build_cases() -> list[EdgeCase]:
    """Build the list of edge case articles."""
    return [
        EdgeCase(
            article=Article(
                id=1001,
                feed_id=1,
                title="Tesla announces new vehicle lineup",
                url="https://example.com/tesla-lineup",
                published_at="2026-07-09T10:00:00Z",
                summary="Tesla unveils three new electric vehicle models.",
                content=(
                    "Tesla has announced a major expansion to its vehicle lineup, "
                    "adding three new electric models that target different market "
                    "segments. The new vehicles include a compact sedan and two SUVs."
                ),
            ),
            expected_interesting=False,
            description="Car news → should filter (uninteresting)",
        ),
        EdgeCase(
            article=Article(
                id=1002,
                feed_id=1,
                title="MotoGP championship results",
                url="https://example.com/motogp-results",
                published_at="2026-07-09T09:00:00Z",
                summary="Final standings for the MotoGP championship.",
                content=(
                    "The MotoGP season has concluded with dramatic final races. "
                    "Championship standings show intense competition throughout the year."
                ),
            ),
            expected_interesting=False,
            description="Motorcycle racing → should filter (uninteresting)",
        ),
        EdgeCase(
            article=Article(
                id=1003,
                feed_id=1,
                title="NFL season preview",
                url="https://example.com/nfl-preview",
                published_at="2026-07-09T08:00:00Z",
                summary="Preview of the upcoming NFL season.",
                content=(
                    "The upcoming NFL season promises exciting matchups and "
                    "storylines. Teams are preparing for what could be one of "
                    "the most competitive seasons yet."
                ),
            ),
            expected_interesting=False,
            description="Sports news → should filter (uninteresting)",
        ),
        EdgeCase(
            article=Article(
                id=2001,
                feed_id=1,
                title="AI model trains Tesla robot",
                url="https://example.com/ai-robot",
                published_at="2026-07-09T07:00:00Z",
                summary="New reinforcement learning approach enables complex manipulation.",
                content=(
                    "Researchers have developed a novel AI training method that "
                    "allows robots to learn complex manipulation tasks with fewer "
                    "demonstrations. The approach uses hierarchical reinforcement "
                    "learning and transfer learning."
                ),
            ),
            expected_interesting=True,
            description="AI/programming → should keep (interesting)",
        ),
        EdgeCase(
            article=Article(
                id=2002,
                feed_id=1,
                title="NASA spacecraft software update",
                url="https://example.com/nasa-software",
                published_at="2026-07-09T06:00:00Z",
                summary="Software update for deep space probes.",
                content=(
                    "NASA has successfully deployed a critical software update "
                    "to its deep space probe fleet, fixing a timing issue in "
                    "the flight computer that could have affected trajectory "
                    "calculations."
                ),
            ),
            expected_interesting=True,
            description="Space/engineering → should keep (interesting)",
        ),
        EdgeCase(
            article=Article(
                id=2003,
                feed_id=1,
                title="Linux kernel security vulnerability",
                url="https://example.com/linux-vuln",
                published_at="2026-07-09T05:00:00Z",
                summary="Critical vulnerability discovered in Linux kernel.",
                content=(
                    "A critical privilege escalation vulnerability has been "
                    "discovered in the Linux kernel's memory management subsystem. "
                    "Patches are being rolled out across distributions. "
                    "Administrators are urged to update immediately."
                ),
            ),
            expected_interesting=True,
            description="Cybersecurity → should keep (interesting)",
        ),
    ]


def _create_client(config: Settings) -> LLMClient:
    """Create an LLM client based on the configured provider."""
    if config.LLM_PROVIDER == "opencodego":
        if not config.OPENCODEGO_API_KEY:
            print(
                "ERROR: OPENCODEGO_API_KEY not set in .env (required for "
                "LLM_PROVIDER=opencodego)"
            )
            sys.exit(1)
        return OpencodeGoClient(
            api_key=config.OPENCODEGO_API_KEY,
            model=config.OPENCODEGO_MODEL,
            timeout=config.OPENCODEGO_TIMEOUT_SECONDS,
        )
    else:
        # Default: OpenRouter
        return OpenRouterClient(
            api_key=config.OPENROUTER_API_KEY,
            model=config.OPENROUTER_MODEL,
        )


def _classify_article(
    classifier: Classifier, case: EdgeCase
) -> tuple[bool, str | None]:
    """Classify a single article and return (passed, error_message)."""
    try:
        result = classifier.classify(case.article)
        passed = result.interesting == case.expected_interesting
        if not passed:
            error = (
                f"  Expected interesting={case.expected_interesting}, "
                f"got interesting={result.interesting}\n"
                f"  Reason: {result.reason}"
            )
        else:
            error = None
        return passed, error
    except ClassificationError as exc:
        return False, f"  ClassificationError: {exc.message}"


def main() -> None:
    """Run the calibration script and report results."""
    print("=" * 70)
    print("Classifier Calibration Script")
    print("=" * 70)

    # 1. Load configuration
    print("\nLoading configuration...")
    try:
        config = Settings()
    except Exception as exc:
        print(f"ERROR loading config: {exc}")
        print("Make sure .env file is properly configured.")
        sys.exit(1)

    # 2. Create client and classifier
    print(f"Provider: {config.LLM_PROVIDER}")
    model = (
        config.OPENCODEGO_MODEL
        if config.LLM_PROVIDER == "opencodego"
        else config.OPENROUTER_MODEL
    )
    print(f"Model: {model}")

    try:
        client = _create_client(config)
    except Exception as exc:
        print(f"ERROR creating client: {exc}")
        sys.exit(1)

    classifier = Classifier(client=client, model=model)

    # 3. Run edge cases
    cases = _build_cases()
    passed = 0
    failed = 0

    print(f"\nRunning {len(cases)} edge cases...\n")

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.description}")
        print(f"  Article: {case.article.title}")

        ok, error = _classify_article(classifier, case)
        if ok:
            passed += 1
            print("  ✅ PASS")
        else:
            failed += 1
            print("  ❌ FAIL")
            if error:
                print(error)
        print()

    # 4. Summary
    print("=" * 70)
    print(f"Results: {passed}/{len(cases)} passed, "
          f"{failed}/{len(cases)} failed")
    print("=" * 70)

    if failed > 0:
        print("\nConsider tuning the SYSTEM_PROMPT in classifier.py and re-running.")
        sys.exit(1)
    else:
        print("\nAll edge cases pass! Classification quality is acceptable.")
        sys.exit(0)


if __name__ == "__main__":
    main()