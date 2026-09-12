---
plan name: Log-Viewer-Webpage
plan description: Serve classifier JSONL via HTTP
plan status: done
---

## Idea
A lightweight, zero-dependency web viewer for the classification audit trail, served on port 5000 (bind 0.0.0.0, read-only, no auth). Built with Python stdlib `http.server` (ThreadingHTTPServer) — no new dependencies. Data source is `logs/classifier.jsonl` only (logrotate uses copytruncate so the live path is stable): classification entries plus error entries (`error_type`/`error_message`). The viewer is a separate long-running process from the hourly pipeline: new `WebSettings` pydantic class (WEB_HOST/WEB_PORT/WEB_LOG_PATH) so it does NOT require Miniflux/LLM credentials; new `log_reader.py` with pure parse/filter/summary functions; new `web.py` with `GET /` (single HTML page: inline CSS + vanilla JS, filter tabs All/Classifications/Errors, stats bar, auto-refresh toggle) and `GET /api/entries?filter=&limit=` (JSON). Added as a second PM2 app (`miniflux-ai-filter-web`, autorestart) in ecosystem.config.js. Tests with pytest following existing patterns; README/.env.example updated.

## Implementation
- Add `WebSettings` (pydantic-settings) to src/miniflux_ai_filter/config.py with WEB_HOST (default 0.0.0.0), WEB_PORT (default 5000), WEB_LOG_PATH (default logs/classifier.jsonl) — separate class so the viewer does not require Miniflux/LLM credentials.
- Create src/miniflux_ai_filter/log_reader.py: pure functions to read the JSONL audit trail — parse lines (skip malformed gracefully), distinguish error entries (error_type present) from classification entries, filter by all|errors|classifications, return newest-first up to a limit, and compute a summary (total, errors, interesting vs not, last run_id/timestamp).
- Create src/miniflux_ai_filter/web.py: ThreadingHTTPServer + BaseHTTPRequestHandler with GET / (single HTML page — inline CSS + vanilla JS, filter tabs All/Classifications/Errors, stats bar, auto-refresh every 15s with toggle) and GET /api/entries?filter=&limit= (JSON entries + summary); 404 otherwise; main() runnable both as `python -m miniflux_ai_filter.web` and `python src/miniflux_ai_filter/web.py` (PM2 file-path constraint).
- Add tests: tests/test_log_reader.py (mixed entry shapes, filters, newest-first ordering, malformed lines skipped, missing file → empty) and tests/test_web.py (start server on an ephemeral port in a fixture; assert / returns HTML, /api/entries returns expected JSON shape and honors filter/limit, unknown path → 404).
- Add `miniflux-ai-filter-web` app entry to ecosystem.config.js (script uv, args 'run python src/miniflux_ai_filter/web.py', exec_interpreter none, autorestart true, logs to logs/pm2/web-err.log and web-out.log); document WEB_* vars in .env.example (commented) and add a concise 'Web Log Viewer' section to README.md.
- Verify: run `uv run pytest`; then smoke-test manually — start the server, curl / and /api/entries?filter=errors&limit=10, confirm valid HTML/JSON responses, then stop it.

## Required Specs
<!-- SPECS_START -->
<!-- SPECS_END -->