from __future__ import annotations

import time
from collections import deque
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="DeepOps Demo App", version="0.1.0")

ERROR_BUFFER: deque[dict[str, Any]] = deque(maxlen=100)

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


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "deepops-demo-app",
        "status": "ok",
        "routes": [
            "/health",
            "/healthz",
            "/errors",
            "/calculate/{value}",
            "/calculate/{a}/{b}",
            "/user/{username}",
            "/search?q=test",
        ],
    }


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


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    error_record = _record_error(request=request, exc=exc)
    return JSONResponse(status_code=500, content=error_record)
