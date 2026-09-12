// PM2 process configuration for miniflux-ai-filter.
//
// Two apps:
//   1. miniflux-ai-filter     — classifier pipeline, run hourly via cron.
//                               Exits after each run; PM2 reschedules.
//   2. miniflux-ai-filter-web — read-only log viewer, long-running daemon
//                               on port 5000 (autorestart on crash).
//
// Usage:
//   pm2 start ecosystem.config.js
//   pm2 save                          # save process list for resurrect
//   pm2 startup                       # auto-start on system boot
//
// Logs are written to logs/pm2/ and rotated via pm2-logrotate.
// The project's own JSONL audit trail is at logs/classifier.jsonl
// (rotated separately via system logrotate).

module.exports = {
  apps: [
    {
      name: "miniflux-ai-filter",

      // Use `uv run python src/miniflux_ai_filter/__main__.py`
      // instead of `python -m miniflux_ai_filter` because PM2
      // resolves `script` as a file path and cannot handle `-m`.
      // exec_interpreter: "none" avoids a PM2 quirk where it creates
      // a phantom "run" process from interpreter_args.
      script: "uv",
      args: "run python src/miniflux_ai_filter/__main__.py",
      exec_interpreter: "none",

      // Run once every hour on the hour.
      cron_restart: "0 * * * *",

      // The script is designed to exit after one pipeline run.
      // cron_restart handles re-scheduling, so autorestart is off.
      autorestart: false,
      watch: false,

      env: {
        PYTHONUNBUFFERED: "1",
      },

      // PM2 stdout/stderr log files.
      error_file: "logs/pm2/err.log",
      out_file: "logs/pm2/out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    },

    {
      name: "miniflux-ai-filter-web",

      // Long-running read-only viewer for logs/classifier.jsonl
      // (binds WEB_HOST:WEB_PORT, default 0.0.0.0:5000).
      // File-path invocation because PM2 cannot handle `-m`; see above.
      script: "uv",
      args: "run python src/miniflux_ai_filter/web.py",
      exec_interpreter: "none",

      // Daemon: stay up and restart if it crashes.
      autorestart: true,
      watch: false,

      env: {
        PYTHONUNBUFFERED: "1",
      },

      error_file: "logs/pm2/web-err.log",
      out_file: "logs/pm2/web-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    },
  ],
};