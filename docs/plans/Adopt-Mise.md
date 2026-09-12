---
plan name: Adopt-Mise
plan description: Pin tools, define run tasks
plan status: done
---

## Idea
Adopt mise-en-place as this repo's tool dependency manager and task runner. Executed BEFORE Log-Viewer-Webpage (that plan's verification then naturally becomes `mise run test` / `mise run web`, and it adds the `web` task itself — deliberately out of scope here).

Create `mise.toml` pinning: python=3.12 (matches .python-version, which is kept since uv reads it), uv=0.5.9 (the version that generated uv.lock — avoids lockfile churn and version skew between mise shims and ~/.local/bin/uv, including for the PM2 daemon's PATH), node=20, npm:pm2 (replaces README's `npm install -g pm2`). Generate `mise.lock` via `mise lock` (best-effort per backend) and commit it. mise 2026.9.3 is already installed and managing node/python/uv at user level.

Tasks: install (uv sync), test (uv run pytest), pipeline (uv run python -m miniflux_ai_filter), calibrate (uv run python scripts/calibrate.py), plus PM2 wrappers: pm2-start (pm2 start ecosystem.config.js), pm2-stop, pm2-restart, pm2-status, pm2-logs, pm2-save.

README updates: Prerequisites gain mise (install + `mise install`); `npm install -g pm2` is removed; Usage/Development/Deployment sections switch to `mise run ...`. Document the PM2-via-mise caveats: run pm2 through `mise run pm2-*` or `mise x npm:pm2 -- pm2 ...` so the daemon spawns with mise's tool PATH, and `pm2 startup` bakes the mise shim path into the systemd unit (shims persist, so `pm2 resurrect` at boot keeps working). Secrets stay in .env — nothing sensitive in mise.toml.

Verification: `mise install` clean; `mise tasks` lists everything; `mise run test` passes with `git diff uv.lock` empty; `mise x npm:pm2 -- pm2 --version` resolves. Do NOT run the pipeline/calibrate tasks during verification (they hit real APIs).

## Implementation
- Create mise.toml at repo root with [tools]: python="3.12", uv="0.5.9", node="20", "npm:pm2"="latest"; then run `mise lock` and commit mise.lock (keep .python-version for uv).
- Define core tasks in mise.toml with descriptions: install=uv sync, test=uv run pytest, pipeline=uv run python -m miniflux_ai_filter, calibrate=uv run python scripts/calibrate.py.
- Define PM2 wrapper tasks in mise.toml: pm2-start (pm2 start ecosystem.config.js), pm2-stop (pm2 stop miniflux-ai-filter miniflux-ai-filter-web), pm2-restart, pm2-status, pm2-logs, pm2-save.
- Update README.md: Prerequisites add mise (curl install + `mise install`), remove `npm install -g pm2`; Usage → `mise run pipeline`; Development → `mise run test` / `mise run calibrate`; Deployment → `mise run pm2-start` etc. with the shim/startup caveats documented.
- Verify: `mise install` completes; `mise tasks` lists all tasks; `mise run test` passes and `git diff uv.lock` is empty; `mise x npm:pm2 -- pm2 --version` works. Do not run pipeline/calibrate (real API calls).

## Required Specs
<!-- SPECS_START -->
<!-- SPECS_END -->