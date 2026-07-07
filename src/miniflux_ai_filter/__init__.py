"""miniflux_ai_filter — AI-powered article filtering for Miniflux."""

from miniflux_ai_filter.classifier import Classifier, ClassificationError
from miniflux_ai_filter.config import Settings
from miniflux_ai_filter.logging import JsonlLogger
from miniflux_ai_filter.miniflux import MinifluxClient
from miniflux_ai_filter.models import Article, ClassificationResult, ClassificationLog
from miniflux_ai_filter.openrouter import OpenRouterClient, OpenRouterError

__all__ = [
    "Article",
    "ClassificationError",
    "ClassificationLog",
    "ClassificationResult",
    "Classifier",
    "JsonlLogger",
    "MinifluxClient",
    "OpenRouterClient",
    "OpenRouterError",
    "Settings",
]
