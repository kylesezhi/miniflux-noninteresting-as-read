# Miniflux Non-Interesting As Read

A Python tool that automatically classifies unread Miniflux articles using an LLM (via OpenRouter) and marks non-interesting ones as read — so you never have to wade through articles you don't care about.

## Features

- Fetches unread articles from a Miniflux RSS reader instance
- Classifies each article as **interesting** or **not interesting** using an LLM (OpenAI-compatible API via OpenRouter)
- Automatically marks non-interesting articles as read in Miniflux
- Configurable via environment variables
- Full audit trail via JSONL logging
- Supports multiple feed IDs

## Prerequisites

- Python 3.12+
- A running [Miniflux](https://miniflux.app/) instance with an API token
- An [OpenRouter](https://openrouter.ai/) API key

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for package management.

```bash
# Clone the repository
git clone https://github.com/kylesezhi/miniflux-noninteresting-as-read.git
cd miniflux-noninteresting-as-read

# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
```

## Configuration

Set the following environment variables in your `.env` file:

| Variable | Required | Description |
|---|---|---|
| `MINIFLUX_URL` | Yes | Base URL of your Miniflux instance (e.g., `https://reader.example.com`) |
| `MINIFLUX_API_TOKEN` | Yes | Miniflux API authentication token |
| `MINIFLUX_FEED_IDS` | Yes | Comma-separated list of feed IDs to process (e.g., `1,2,3`) |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM access |

The following constants are configured in the source code:

| Constant | Default | Description |
|---|---|---|
| `MAX_ARTICLES_PER_RUN` | `100` | Maximum articles to process per execution |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b:free` | LLM model used for classification |

## Usage

```bash
uv run python -m miniflux_ai_filter
```

The tool will:

1. Load configuration from environment variables
2. Generate a unique run ID
3. Fetch unread articles from the configured Miniflux feeds
4. Sort articles newest-first
5. Limit to `MAX_ARTICLES_PER_RUN` articles
6. Classify each article using the LLM
7. Mark non-interesting articles as read in Miniflux
8. Write a JSONL audit log entry for every processed article

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Miniflux   │────▶│  AI Filter   │────▶│  OpenRouter │
│  (RSS Feeds)│     │  (Classifier)│     │  (LLM API)  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       │                    ▼
       │           ┌──────────────┐
       │           │  Interesting? │
       │           └──────────────┘
       │              │         │
       │              │ No      │ Yes
       │              ▼         ▼
       │     ┌────────────┐  ┌──────────┐
       │     │ Mark Read  │  │  Leave   │
       │     │ in Miniflux│  │ Unread   │
       │     └────────────┘  └──────────┘
       │
       ▼
┌─────────────┐
│  JSONL Log  │
│  (Audit)    │
└─────────────┘
```

## Classification Topics

The LLM classifies articles based on the following topic preferences:

**Interesting topics** (kept as unread):
- Programming
- AI / Machine Learning
- Science
- Cybersecurity
- Space
- Technology
- Engineering
- General interesting news

**Uninteresting topics** (marked as read):
- Cars
- Motorcycles
- Sports

The classifier filters only when the **primary topic** of an article is unwanted. Incidental mentions of uninteresting topics within an otherwise interesting article will not trigger filtering.

## Project Structure

```
miniflux-noninteresting-as-read/
├── pyproject.toml          # Project metadata and dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── logs/                   # JSONL audit logs
│   └── .gitkeep
└── src/
    └── miniflux_ai_filter/
        ├── __init__.py     # Package initialization
        ├── __main__.py     # Entry point
        ├── config.py       # Configuration management
        ├── miniflux.py     # Miniflux API client
        ├── models.py       # Data models (Article, ClassificationResult, etc.)
        ├── openrouter.py   # OpenRouter LLM client
        ├── classifier.py   # Article classification logic
        ├── logging.py      # JSONL audit trail
        └── main.py         # Orchestration
```

## Logging

Every processed article produces a JSONL entry in `logs/classifier.jsonl` with the following fields:

- `run_id` — Unique identifier for each execution
- `timestamp` — When the classification occurred
- `article_id` — Miniflux article ID
- `feed_id` — Miniflux feed ID
- `title` — Article title
- `url` — Article URL
- `published_at` — Original publication date
- `interesting` — Boolean classification result
- `reason` — LLM-provided explanation
- `model` — LLM model used

LLM failures and Miniflux update failures are also logged.

## Development

### Running Tests

```bash
uv run pytest
```

### Manual Testing

Run the tool and inspect the JSONL logs to review classification quality:

```bash
uv run python -m miniflux_ai_filter
cat logs/classifier.jsonl | jq .
```

## Deployment

For unattended execution, the project supports:

- **PM2** — Process manager with log rotation
- **cron** — Scheduled execution via system cron
- **Docker** — Containerized deployment (future)
- **Home server** — Self-hosted deployment

## License

MIT