from __future__ import annotations

import subprocess
import time
import urllib.request
import urllib.error
import json as _json
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="DeepOps Demo App", version="0.1.0")

APP_DIR = Path(__file__).resolve().parent
PITCH_SCRIPT = APP_DIR / "pitch.sh"
ERROR_BUFFER: deque[dict[str, Any]] = deque(maxlen=100)
BACKEND_URL = "http://localhost:8000"

USERS = {
    "alice": {"name": "Alice", "email": "alice@example.com"},
    "bob": {"name": "Bob", "email": "bob@example.com"},
}


def _record_error(
    *,
    request: Request,
    exc: Exception,
    status_code: int = 500,
) -> dict[str, Any]:
    timestamp_ms = int(time.time() * 1000)
    record = {
        "timestamp_ms": timestamp_ms,
        "timestamp": timestamp_ms,
        "path": request.url.path,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "source_file": "demo-app/main.py",
        "method": request.method,
        "status_code": status_code,
    }
    ERROR_BUFFER.appendleft(record)
    return record


def _root_payload() -> dict[str, Any]:
    return {
        "service": "deepops-demo-app",
        "status": "ok",
        "routes": [
            "/",
            "/health",
            "/healthz",
            "/errors",
            "/broken",
            "/calculate/{value}",
            "/calculate/{a}/{b}",
            "/user/{username}",
            "/search?q=test",
        ],
    }


def _root_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>DeepOps Demo App</title>
    <style>
      :root {
        color-scheme: dark;
        font-family: "SF Mono", "Fira Code", monospace;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background:
          radial-gradient(circle at top, rgba(255, 85, 85, 0.18), transparent 40%),
          linear-gradient(160deg, #13151a 0%, #090b0f 100%);
        color: #f5f7fb;
      }
      main {
        width: min(640px, calc(100vw - 48px));
        padding: 32px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        background: rgba(10, 14, 20, 0.88);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.4);
      }
      h1 {
        margin: 0 0 12px;
        font-size: clamp(2rem, 5vw, 3rem);
      }
      p {
        margin: 0 0 24px;
        line-height: 1.6;
        color: #bcc6d8;
      }
      .section-label {
        font-size: 0.7rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #8892a6;
        margin: 0 0 12px;
      }
      .btn-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 20px;
      }
      button {
        border: 0;
        border-radius: 999px;
        padding: 14px 28px;
        background: linear-gradient(135deg, #ff5a5a 0%, #ff9248 100%);
        color: #fff;
        font: inherit;
        font-size: 0.85rem;
        font-weight: 700;
        cursor: pointer;
        transition: filter 0.15s, opacity 0.15s;
      }
      button:hover {
        filter: brightness(1.08);
      }
      button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      button.critical {
        background: linear-gradient(135deg, #ff2222 0%, #cc0000 100%);
      }
      button.high {
        background: linear-gradient(135deg, #ff6622 0%, #dd4400 100%);
      }
      button.medium {
        background: linear-gradient(135deg, #ffaa00 0%, #cc8800 100%);
        color: #1a1a1a;
      }
      button.secondary {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
      }
      #status {
        margin-top: 16px;
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 0.8rem;
        line-height: 1.5;
        display: none;
      }
      #status.success {
        display: block;
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.3);
        color: #88ffbb;
      }
      #status.error {
        display: block;
        background: rgba(255, 68, 68, 0.1);
        border: 1px solid rgba(255, 68, 68, 0.3);
        color: #ff8888;
      }
      #status.loading {
        display: block;
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid rgba(0, 212, 255, 0.3);
        color: #88ddff;
      }
      code {
        color: #ffb07a;
      }
      hr {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin: 24px 0;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>DeepOps Demo App</h1>

      <p class="section-label">Trigger Error &amp; Run Pipeline</p>
      <p>
        Create an incident in the backend and run the full agent pipeline.
        Results appear on the <a href="http://localhost:3000/dashboard" style="color:#88ddff">/dashboard</a>.
      </p>
      <div class="btn-row">
        <button class="critical" onclick="triggerError('search_timeout')">TimeoutError</button>
        <button class="high" onclick="triggerError('user_missing')">KeyError</button>
        <button class="medium" onclick="triggerError('calculate_zero')">ZeroDivision</button>
      </div>

      <hr />

      <p class="section-label">Legacy</p>
      <p>
        Press <code>broken</code> to launch <code>pitch.sh run</code> and then
        intentionally crash this request.
      </p>
      <form method="post" action="/broken">
        <button class="secondary" type="submit">broken</button>
      </form>

      <div id="status"></div>
    </main>
    <script>
      async function triggerError(bugKey) {
        const el = document.getElementById('status');
        const buttons = document.querySelectorAll('button');
        buttons.forEach(b => b.disabled = true);
        el.className = 'loading';
        el.style.display = 'block';
        el.textContent = 'Creating incident & running pipeline for ' + bugKey + '...';
        try {
          const resp = await fetch('/trigger-pipeline/' + bugKey, { method: 'POST' });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.detail || resp.statusText);
          const inc = data.incident;
          el.className = 'success';
          el.innerHTML =
            '<strong>' + inc.source.error_type + '</strong> &rarr; ' +
            inc.status + ' (severity: ' + inc.severity + ')<br>' +
            'ID: <code>' + inc.incident_id.slice(0, 16) + '</code>';
        } catch (e) {
          el.className = 'error';
          el.textContent = 'Failed: ' + e.message;
        } finally {
          buttons.forEach(b => b.disabled = false);
        }
      }
    </script>
  </body>
</html>
"""


def _launch_pitch_script() -> None:
    if not PITCH_SCRIPT.exists():
        raise FileNotFoundError(f"Missing pitch script: {PITCH_SCRIPT}")

    subprocess.Popen(
        [str(PITCH_SCRIPT), "run"],
        cwd=str(APP_DIR),
        start_new_session=True,
    )


@app.get("/", response_model=None)
async def root(request: Request) -> Any:
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(_root_html())
    return _root_payload()


@app.get("/health")
@app.get("/healthz")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "deepops-demo-app",
        "timestamp_ms": int(time.time() * 1000),
        "recent_errors": len(ERROR_BUFFER),
    }


@app.get("/errors")
async def get_errors(since: int | None = None) -> dict[str, Any]:
    errors = list(ERROR_BUFFER)
    if since is not None:
        errors = [
            error for error in errors if int(error.get("timestamp_ms", 0)) >= since
        ]
    return {"errors": errors}


@app.delete("/errors")
async def clear_errors() -> dict[str, Any]:
    ERROR_BUFFER.clear()
    return {"cleared": True}


@app.get("/calculate/{value}")
async def calculate(value: int) -> dict[str, Any]:
    result = 100 / value
    return {"result": result}


@app.get("/calculate/{a}/{b}")
async def calculate_pair(a: int, b: int) -> dict[str, Any]:
    result = a // b
    return {"result": result}


@app.get("/user/{username}")
async def get_user(username: str) -> dict[str, Any]:
    user = USERS.get(username)
    return {"name": user["name"], "email": user["email"]}


@app.get("/search")
async def search(q: str = "") -> dict[str, Any]:
    time.sleep(5)
    return {"query": q, "results": []}


@app.post("/trigger-pipeline/{bug_key}")
async def trigger_pipeline(bug_key: str) -> dict[str, Any]:
    """Trigger a demo error, ingest it into the backend, and run the agent pipeline."""
    # 1. Ingest into backend
    ingest_body = _json.dumps({"bug_key": bug_key}).encode()
    ingest_req = urllib.request.Request(
        f"{BACKEND_URL}/api/ingest/demo-trigger",
        data=ingest_body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(ingest_req, timeout=15) as resp:
            ingest_data = _json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Ingest failed: {detail}") from exc

    incident_id = ingest_data["incident"]["incident_id"]

    # 2. Run pipeline
    run_req = urllib.request.Request(
        f"{BACKEND_URL}/api/agent/run-once?incident_id={urllib.request.quote(incident_id)}",
        headers={"Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(run_req, timeout=120) as resp:
            run_data = _json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Pipeline failed: {detail}") from exc

    return {"incident": run_data.get("incident", ingest_data["incident"])}


@app.post("/broken")
async def broken() -> dict[str, Any]:
    _launch_pitch_script()
    raise RuntimeError("broken button launched pitch.sh and intentionally crashed")


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    error_record = _record_error(request=request, exc=exc)
    return JSONResponse(status_code=500, content=error_record)
