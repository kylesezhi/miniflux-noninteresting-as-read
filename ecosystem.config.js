// PM2 process configuration for miniflux-ai-filter.
//
// Runs the classifier pipeline once per hour via cron_restart.
// The script exits after each run; PM2 handles rescheduling.
//
// Usage:
//   pm2 start ecosystem.config.js
//   pm2 save                          # save process list for resurrect
//   pm2 startup                       # auto-start on system boot
//
// Logs are written to logs/pmd/ and rotated via pm2-logrotate.
// The project's own JSONL audit trail is at logs/classifier.jsonl
// (rotated separately via system logrotate).

module.exports = {
  apps: [
    {
      name: "miniflux-ai-filter",

      // Use `uv run python -m miniflux_ai_filter` as the command.
      interpreter: "uv",
      interpreter_args: "run python",
      script: "-m",
      args: "miniflux_ai_filter",

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
  ],
};