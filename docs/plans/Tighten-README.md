---
plan name: Tighten-README
plan description: Tighten README from 436 to ~220 lines
plan status: done
---

## Idea
Aggressively trim the README by removing redundant sections and condensing verbose ones. Target ~220 lines from current 436.

## Implementation
- Remove Project Structure section (lines 141-177) — self-evident from repo
- Remove Classification Topics section (lines 119-137) — already shown in feeds.yaml example
- Condense Deployment section (lines 265-432) from ~170 lines to ~30-40 lines: keep PM2 quickstart (install, start, save), collapse log rotation, cron alternative, monitoring, and file layout into brief mentions
- Shorten Logging section (lines 179-195): replace field-by-field listing with a one-liner mentioning JSONL audit trail exists
- Condense Unit Tests section (lines 199-231): keep `uv run pytest` command, remove granular pytest examples and coverage table
- Trim Calibration section (lines 233-253): remove edge-case table, keep command and purpose in 2-3 sentences

## Required Specs
<!-- SPECS_START -->
<!-- SPECS_END -->