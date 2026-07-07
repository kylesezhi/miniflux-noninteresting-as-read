# Miniflux AI Filter Project Milestones

## Milestone 1: Bootstrap Python Project

Goal:
Create the project skeleton using uv and establish the package structure.

Tasks:
- Create new uv project
- Create package-based layout
- Add dependencies:
  - requests
  - python-dotenv
  - pydantic
- Add .gitignore
- Add README.md
- Create initial module entry point

Expected structure:

```
miniflux-ai-filter/
├── pyproject.toml
├── .env.example
├── README.md
├── logs/
│   └── .gitkeep
└── src/
    └── miniflux_ai_filter/
        ├── __init__.py
        └── __main__.py
```

Acceptance criteria:
- `uv run python -m miniflux_ai_filter` executes successfully
- Dependencies install correctly


---

## Milestone 2: Configuration Management

Goal:
Load runtime configuration safely.

Tasks:
- Create config.py
- Load environment variables using python-dotenv
- Create typed configuration object

Environment variables:

MINIFLUX_URL=
MINIFLUX_API_TOKEN=
MINIFLUX_FEED_IDS=

OPENROUTER_API_KEY=

Configuration constants:

MAX_ARTICLES_PER_RUN=100
OPENROUTER_MODEL=openai/gpt-oss-120b:free

Acceptance criteria:
- Missing required environment variables fail clearly
- Feed IDs parse from comma-separated string into list[int]


---

## Milestone 3: Build Miniflux API Client

Goal:
Create a small wrapper around the Miniflux API.

Create:

miniflux.py

Functions:

- get_unread_entries(feed_ids)
- mark_entry_read(entry_id)

Implementation:
- Use requests
- Authenticate using API token
- Handle HTTP failures gracefully

Requirements:
- Fetch unread entries only
- Support multiple feed IDs
- Return normalized Python objects

Acceptance criteria:
- Can fetch unread Ars Technica articles
- Can mark a test article read


---

## Milestone 4: Define Data Models

Goal:
Create typed models for API responses and LLM responses.

Create:

models.py

Models:

Article:
- id
- feed_id
- title
- url
- published_at
- summary
- content

ClassificationResult:
- interesting: bool
- reason: str

ClassificationLog:
- run_id
- timestamp
- article_id
- feed_id
- title
- url
- published_at
- interesting
- reason
- model


Acceptance criteria:
- Invalid LLM responses fail validation
- Models serialize cleanly to JSON


---

## Milestone 5: Build OpenRouter Client

Goal:
Create the LLM API integration.

Create:

openrouter.py

Tasks:
- Send OpenAI-compatible chat completion requests
- Use configured API key
- Use configured model
- Set temperature to 0.2
- Parse response content

Requirements:
- Timeout handling
- Clear error messages

Acceptance criteria:
- Can send a test article
- Receives valid JSON classification


---

## Milestone 6: Build Article Classifier

Goal:
Implement classification logic.

Create:

classifier.py

Prompt requirements:

The model should know:

Interested topics:
- programming
- AI
- science
- cybersecurity
- space
- technology
- engineering
- general interesting news

Uninteresting topics:
- cars
- motorcycles
- sports

Rules:
- Filter only when the primary topic is unwanted
- Do not filter incidental mentions

Input:
- title
- URL
- feed
- publication date
- summary
- first 2000 characters of content

Output:

{
  "interesting": true,
  "reason": "..."
}

Acceptance criteria:
- Produces consistent JSON
- Correctly identifies obvious examples


---

## Milestone 7: JSONL Logging

Goal:
Create an audit trail.

Create:

logging.py

Write:

logs/classifier.jsonl

Each entry contains:

- run_id
- timestamp
- article_id
- feed_id
- title
- URL
- published date
- classification result
- reason
- model

Also log:
- LLM failures
- Miniflux update failures

Acceptance criteria:
- Every processed article produces a log entry
- Logs are valid JSONL


---

## Milestone 8: Orchestration

Goal:
Connect all pieces.

Create:

main.py

Flow:

1. Load configuration
2. Generate run_id
3. Fetch unread articles
4. Sort newest first
5. Limit to MAX_ARTICLES_PER_RUN
6. Classify each article
7. If interesting=false:
   - mark read
8. Write JSONL log

Acceptance criteria:
- Full run completes successfully
- Only uninteresting articles are marked read
- Interesting articles remain unread


---

## Milestone 9: Testing and Prompt Calibration

Goal:
Validate behavior before automation.

Tasks:
- Run manually
- Inspect JSONL logs
- Review false positives
- Tune classifier prompt
- Test edge cases:

Examples:

Should filter:
- "Tesla announces new vehicle lineup"
- "MotoGP championship results"
- "NFL season preview"

Should keep:
- "AI model trains Tesla robot"
- "NASA spacecraft software update"
- "Linux kernel security vulnerability"


Acceptance criteria:
- Classification quality is acceptable


---

## Milestone 10: Production Runner

Goal:
Prepare for long-running execution.

Tasks:
- Add PM2 configuration
- Configure log rotation
- Set execution interval
- Document deployment

Future:

- cron alternative
- Docker container
- Home server deployment

Acceptance criteria:
- Runs unattended
- Failures are visible in logs
