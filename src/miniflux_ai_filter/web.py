"""Read-only web viewer for the JSONL classification audit trail.

Serves a single-page HTML dashboard plus a small JSON API over the audit
trail written by :mod:`miniflux_ai_filter.jsonl_logger`:

- ``GET /``              — the dashboard (inline CSS + vanilla JS, no assets)
- ``GET /api/entries``   — JSON view: ``?filter=all|errors|classifications``
                           and ``?limit=`` (1..1000, default 200)

The server is intentionally dependency-free (stdlib ``http.server``) and
configured via :class:`~miniflux_ai_filter.config.WebSettings`
(``WEB_HOST``, ``WEB_PORT``, ``WEB_LOG_PATH``).  It is a long-running
process, distinct from the hourly pipeline run.

Runnable both ways::

    python -m miniflux_ai_filter.web
    python src/miniflux_ai_filter/web.py      # PM2 resolves script as a file
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from miniflux_ai_filter.config import WebSettings
from miniflux_ai_filter.log_reader import DEFAULT_LIMIT, fetch_view

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>AI Filter Log Viewer</title>
<style>
  :root {
    --bg: #0f1115; --panel: #161a22; --border: #262c38;
    --text: #d7dce4; --muted: #8a93a3;
    --green: #4ade80; --red: #f87171; --gray: #9ca3af; --blue: #60a5fa;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  header {
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
    padding: 14px 20px; background: var(--panel);
    border-bottom: 1px solid var(--border);
  }
  h1 { font-size: 16px; margin: 0; font-weight: 600; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-left: auto; }
  .stat {
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 6px; padding: 3px 10px; font-size: 12px; color: var(--muted);
  }
  .stat b { color: var(--text); font-weight: 600; }
  .stat.err b { color: var(--red); }
  .stat.ok b { color: var(--green); }
  .toolbar {
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    padding: 10px 20px; border-bottom: 1px solid var(--border); background: var(--panel);
  }
  .tabs { display: flex; gap: 4px; }
  .tabs button {
    background: transparent; color: var(--muted); border: 1px solid transparent;
    border-radius: 6px; padding: 5px 12px; cursor: pointer; font-size: 13px;
  }
  .tabs button:hover { color: var(--text); }
  .tabs button.active { background: var(--bg); color: var(--text); border-color: var(--border); }
  .toggle { margin-left: auto; display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
  .meta { font-size: 11px; color: var(--muted); }
  main { padding: 0 20px 40px; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th {
    text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .05em;
    color: var(--muted); padding: 8px 10px 6px; border-bottom: 1px solid var(--border);
    position: sticky; top: 0; background: var(--bg);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: top; font-size: 13px; }
  tr:hover td { background: #141821; }
  td.time { white-space: nowrap; color: var(--muted); font-variant-numeric: tabular-nums; }
  td.num { color: var(--muted); text-align: right; white-space: nowrap; }
  .badge { display: inline-block; border-radius: 5px; padding: 1px 8px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .badge.keep { color: var(--green); border: 1px solid rgba(74,222,128,.35); }
  .badge.read { color: var(--gray); border: 1px solid rgba(156,163,175,.35); }
  .badge.error { color: var(--red); border: 1px solid rgba(248,113,113,.4); }
  td.title a { color: var(--text); text-decoration: none; }
  td.title a:hover { color: var(--blue); text-decoration: underline; }
  td.msg { color: var(--muted); font-size: 12px; word-break: break-word; }
  td.model { color: var(--muted); font-size: 12px; white-space: nowrap; }
  .empty { color: var(--muted); padding: 30px; text-align: center; }
  .loading { color: var(--muted); padding: 20px; font-size: 12px; }
</style>
</head>
<body>
<header>
  <h1>AI Filter Log Viewer</h1>
  <div class="stats" id="stats"></div>
</header>
<div class="toolbar">
  <div class="tabs" id="tabs">
    <button data-filter="all" class="active">All</button>
    <button data-filter="classifications">Classifications</button>
    <button data-filter="errors">Errors</button>
  </div>
  <div class="toggle">
    <input type="checkbox" id="autorefresh" checked>
    <label for="autorefresh">auto-refresh 15s</label>
    <span class="meta" id="updated"></span>
  </div>
</div>
<main>
  <div class="loading" id="loading">Loading…</div>
  <table id="table" style="display:none">
    <thead><tr>
      <th>Time</th><th>Verdict</th><th>Article / Error</th>
      <th>Reason / Message</th><th>Model</th><th>Feed</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
</main>
<script>
"use strict";
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { filter: "all", timer: null, busy: false };

function stat(label, value, cls) {
  return `<span class="stat ${cls || ""}">${label} <b>${esc(value)}</b></span>`;
}

function renderStats(s) {
  const last = s.last_timestamp ? fmtTime(s.last_timestamp) : "—";
  document.getElementById("stats").innerHTML =
    statsHtml(s) + stat("Last entry", last);
}

function statsHtml(s) {
  return [
    stat("Entries", s.total),
    stat("Classified", s.classifications),
    `<span class="stat err">Errors <b>${esc(s.errors)}</b></span>`,
    stat("Interesting", s.interesting, "ok"),
    stat("Marked read", s.not_interesting),
  ].join("");
}

const pad2 = n => String(n).padStart(2, "0");

function fmtTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ` +
    `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function row(e) {
  const time = fmtTime(e.timestamp);
  const feed = e.feed_id != null ? e.feed_id : (e.article_id ?? "—");
  if (e.error_type !== undefined) {
    return `<tr>
      <td class="time">${esc(time)}</td>
      <td><span class="badge error">ERROR</span></td>
      <td class="title">${esc(e.error_type)}${e.article_id != null ? ' <span class="msg">(#' + esc(e.article_id) + ")</span>" : ""}</td>
      <td class="msg">${esc(e.error_message)}</td>
      <td class="model"></td>
      <td class="num"></td>
    </tr>`;
  }
  const verdict = e.interesting
    ? '<span class="badge keep">kept</span>'
    : '<span class="badge read">read</span>';
  const title = e.url
    ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>`
    : esc(e.title);
  return `<tr>
    <td class="time">${esc(time)}</td>
    <td>${verdict}</td>
    <td class="title">${title}</td>
    <td class="msg">${esc(e.reason)}</td>
    <td class="model">${esc(e.model)}</td>
    <td class="num">${esc(feed)}</td>
  </tr>`;
}

async function load() {
  if (state.busy) return;
  state.busy = true;
  try {
    const res = await fetch(`/api/entries?filter=${state.filter}&limit=200`);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    document.getElementById("loading").style.display = "none";
    document.getElementById("table").style.display = "";
    renderStats(data.summary);
    const tbody = document.getElementById("rows");
    tbody.innerHTML = data.entries.length
      ? data.entries.map(row).join("")
      : '<tr><td colspan="6" class="empty">No entries.</td></tr>';
    document.getElementById("updated").textContent =
      "updated " + new Date().toLocaleTimeString();
  } catch (err) {
    document.getElementById("loading").textContent = "Failed to load: " + err;
  } finally {
    state.busy = false;
  }
}

document.getElementById("tabs").addEventListener("click", ev => {
  const btn = ev.target.closest("button[data-filter]");
  if (!btn) return;
  document.querySelectorAll("#tabs button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  state.filter = btn.dataset.filter;
  load();
});

document.getElementById("autorefresh").addEventListener("change", ev => {
  if (ev.target.checked) start();
  else { clearInterval(state.timer); state.timer = null; }
});

function start() {
  clearInterval(state.timer);
  state.timer = setInterval(load, 15000);
}

start();
load();
</script>
</body>
</html>
"""


class LogViewerHandler(BaseHTTPRequestHandler):
    """HTTP handler for the dashboard and its JSON API."""

    log_path: str = "logs/classifier.jsonl"

    server_version = "MinifluxAIFilterLogViewer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_html(_PAGE)
        elif parsed.path == "/api/entries":
            self._send_api(parsed)
        else:
            self._send_error_page(f"404 Not Found: {parsed.path}")

    def _send_html(self, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_api(self, parsed: Any) -> None:
        query = parse_qs(parsed.query)
        filter_name = query.get("filter", ["all"])[0]
        try:
            limit = int(query.get("limit", [DEFAULT_LIMIT])[0])
        except ValueError:
            limit = DEFAULT_LIMIT
        view = fetch_view(self.log_path, filter_name=filter_name, limit=limit)
        self._send_json(view)

    def _send_error_page(self, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Route access logs to stdout so they land in PM2's out log
        # (err.log stays reserved for real failures).
        sys.stdout.write(
            f"[web] {self.address_string()} {format % args}\n"
        )
        sys.stdout.flush()


def create_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    log_path: str = "logs/classifier.jsonl",
) -> ThreadingHTTPServer:
    """Create the threaded HTTP server bound to ``host:port``.

    The log file path is attached to the handler class so tests can start
    isolated servers on ephemeral ports with their own fixture files.
    """
    LogViewerHandler.log_path = log_path
    return ThreadingHTTPServer((host, port), LogViewerHandler)


def main() -> None:
    """Entry point: configure, bind and serve until interrupted."""
    settings = WebSettings()
    server = create_server(
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        log_path=settings.WEB_LOG_PATH,
    )
    print(
        f"Log viewer listening on http://{settings.WEB_HOST}:{settings.WEB_PORT} "
        f"(log: {settings.WEB_LOG_PATH})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
