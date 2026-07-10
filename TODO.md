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

## Milestone 8.5: Add Opencode Go Client

Goal:
Add support for Opencode Go as an alternative LLM provider.

Create:

src/miniflux_ai_filter/opencodego.py

Responsibilities:
- Send chat completion requests
- Parse responses
- Normalize output for classifier.py
- Hide provider-specific implementation details

---

## Step 1: Configuration

Add environment variables:

OPENCODEGO_API_KEY=
OPENCODEGO_MODEL=deepseek-v4-flash

Optional future setting:

LLM_PROVIDER=opencodego

Acceptance criteria:
- Missing API key fails clearly
- Model can be overridden via environment variable


---

## Step 2: Create Client Interface

Create:

class OpencodeGoClient:
    def classify(self, system_prompt: str, user_prompt: str) -> str:
        ...

Responsibilities:
- Construct request payload
- Execute HTTP request
- Return assistant response text only

Acceptance criteria:
- Caller does not need to know API details
- Returned value is plain text


---

## Step 3: Implement HTTP Request

Endpoint:

https://opencode.ai/zen/go/v1/chat/completions

Headers:

Authorization: Bearer <api_key>
Content-Type: application/json

Request shape:

{
    "model": "...",
    "messages": [
        {
            "role": "system",
            "content": ...
        },
        {
            "role": "user",
            "content": ...
        }
    ]
}

Acceptance criteria:
- Uses configured model
- Supports system prompts
- Supports user prompts


---

## Step 4: Parse Response

Expected response path:

response["choices"][0]["message"]["content"]

Validation:
- Ensure choices exists
- Ensure message exists
- Ensure content is non-empty

Failure cases:
- HTTP errors
- Empty responses
- Malformed responses

Acceptance criteria:
- Raises clear exceptions
- Includes useful error context


---

## Step 5: Add Timeout Configuration

Add configuration:

OPENCODEGO_TIMEOUT_SECONDS=60

Acceptance criteria:
- Timeout is configurable
- Defaults to 60 seconds


---

## Step 6: Add Logging

Log:
- model name
- request duration
- success/failure
- HTTP status on failures

Do not log:
- API key
- full prompts
- article contents

Acceptance criteria:
- Useful operational visibility
- No secret leakage


---

## Step 7: Integrate With classifier.py

Current:

classifier.py
    └── OpenRouterClient

Future:

classifier.py
    └── OpencodeGoClient

No other code should change.

Acceptance criteria:
- Provider swap only affects one file


---

## Step 8: Future Provider Abstraction (Optional)

Possible interface:

class LLMClient(Protocol):
    def classify(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...

Implementations:

- OpenRouterClient
- OpencodeGoClient
- OllamaClient
- OpenAIClient

Acceptance criteria:
- classifier.py depends only on LLMClient


---

## Suggested Final Layout

src/miniflux_ai_filter/
├── __main__.py
├── config.py
├── models.py
├── miniflux.py
├── classifier.py
├── openrouter.py
├── opencodego.py
└── logging.py


---

## Recommendation

Since you're already moving providers, I'd probably skip implementing
OpenRouter entirely and make Opencode Go the first production client.

That avoids carrying dead code and reduces testing effort.

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

Acceptance criteria:
- Configuration is complete
- Failures are visible in logs


---

## Milestone 11: YAML Feed Configuration

Goal:
Replace `MINIFLUX_FEED_IDS` env var with a YAML config file for feed definitions.

### Design Decisions

1. **Config format**: YAML file (`feeds.yaml`) for feed-to-prompt mapping
   - Prompts are multi-line text with special characters — awkward in `.env`
   - Easier to version control and edit
   - Cleaner separation: secrets stay in `.env`, content config in a separate file

2. **Config file location**: Project root (same level as `.env` and `pyproject.toml`)

3. **Single source of truth**: `feeds.yaml` defines which feeds to process; remove `MINIFLUX_FEED_IDS` from `.env`

4. **YAML schema**: Minimal — `feed_id`, `max_articles`, `prompt`
   ```yaml
   feeds:
     - feed_id: 1
       max_articles: 50
       prompt: |
         Your prompt here...
     - feed_id: 5
       max_articles: 30
       prompt: |
         Another prompt...
   ```

5. **YAML config loading**: New `feeds_config.py` module (separation of concerns)

6. **Dependency**: Add `pyyaml` to `pyproject.toml`

Tasks:
- Create `feeds_config.py` with `FeedConfig` and `FeedsConfig` Pydantic models
- Add YAML loading with validation
- Create example `feeds.yaml`
- Add `pyyaml` to `pyproject.toml`
- Remove `MINIFLUX_FEED_IDS` from `config.py` and `.env.example`
- Add tests for `feeds_config.py`

Acceptance criteria:
- `FeedsConfig.load()` parses and validates `feeds.yaml`
- Missing/invalid file fails with clear error


---

## Milestone 12: Per-Feed Classification Prompts

Goal:
Allow each feed to have its own classification prompt.

Tasks:
- Remove hardcoded `SYSTEM_PROMPT` from `classifier.py`
- Add `system_prompt` parameter to `classify()` method
- Add `prompt` field to `ClassificationLog` model
- Update `jsonl_logger.py` to accept and log prompt
- Update existing classifier tests

Acceptance criteria:
- `Classifier` is stateless regarding prompts
- Each classification logs which prompt was used


---

## Milestone 13: Per-Feed Processing Loop

Goal:
Rewrite the orchestration to process feeds sequentially with per-feed limits.

Tasks:
- Rewrite `main.py` to iterate over `FeedsConfig.feeds`
- Simplify `miniflux.py` `get_unread_entries()` to single feed_id
- Apply per-feed `max_articles` limit
- Add `CLASSIFICATION_DELAY_SECONDS` to `config.py` and `.env.example`
- Add `time.sleep()` between LLM calls
- Skip articles with unknown feed_id (log warning)
- Update summary output to show per-feed stats

Acceptance criteria:
- Each feed processed independently
- Rate limiting works
- Unknown feeds are skipped gracefully


---

## Milestone 14: Integration Testing

Goal:
Validate the multi-feed system end-to-end.

Tasks:
- Update `conftest.py` fixtures for new config structure
- Add integration test with multiple feeds
- Verify JSONL logs include prompt field
- Test missing feed_id handling
- Run full pipeline manually

Acceptance criteria:
- All tests pass
- Manual run with 2+ feeds works correctly
