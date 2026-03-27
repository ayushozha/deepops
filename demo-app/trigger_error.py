from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


DEFAULT_DEMO_APP_BASE_URL = os.environ.get(
    "DEEPOPS_DEMO_APP_BASE_URL",
    "http://127.0.0.1:8001",
)
DEFAULT_BACKEND_BASE_URL = os.environ.get(
    "DEEPOPS_BACKEND_BASE_URL",
    "http://127.0.0.1:8000",
)


@dataclass(frozen=True)
class BugSpec:
    bug_key: str
    path: str
    synthetic_error_type: str
    synthetic_error_message: str
    synthetic_status_code: int


BUG_SPECS: dict[str, BugSpec] = {
    "calculate_zero": BugSpec(
        bug_key="calculate_zero",
        path="/calculate/0",
        synthetic_error_type="ZeroDivisionError",
        synthetic_error_message="division by zero",
        synthetic_status_code=500,
    ),
    "user_missing": BugSpec(
        bug_key="user_missing",
        path="/user/unknown",
        synthetic_error_type="KeyError",
        synthetic_error_message="'name'",
        synthetic_status_code=500,
    ),
    "search_timeout": BugSpec(
        bug_key="search_timeout",
        path="/search?q=test",
        synthetic_error_type="TimeoutError",
        synthetic_error_message="search endpoint timed out",
        synthetic_status_code=504,
    ),
}


def http_json(
    *,
    method: str,
    url: str,
    timeout: float,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    body = None
    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, method=method, data=body, headers=headers)

    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else None


def build_synthetic_payload(
    *,
    spec: BugSpec,
    elapsed_ms: int,
) -> dict[str, Any]:
    timestamp_ms = int(time.time() * 1000)
    return {
        "timestamp_ms": timestamp_ms,
        "timestamp": timestamp_ms,
        "path": spec.path.split("?", 1)[0],
        "error_type": spec.synthetic_error_type,
        "error_message": spec.synthetic_error_message,
        "source_file": "demo-app/main.py",
        "method": "GET",
        "status_code": spec.synthetic_status_code,
        "metadata": {
            "trigger_mode": "synthetic",
            "elapsed_ms": elapsed_ms,
            "bug_key": spec.bug_key,
        },
    }


def normalize_payload(
    *,
    spec: BugSpec,
    status: int,
    payload: dict[str, Any] | None,
    elapsed_ms: int,
    timeout_threshold_ms: int,
) -> dict[str, Any]:
    if payload and {"path", "error_type", "error_message", "source_file"} <= payload.keys():
        normalized = dict(payload)
        normalized.setdefault("method", "GET")
        normalized.setdefault("status_code", status)
        normalized.setdefault("timestamp_ms", int(time.time() * 1000))
        normalized.setdefault("timestamp", normalized["timestamp_ms"])
        return normalized

    if spec.bug_key == "search_timeout" and elapsed_ms >= timeout_threshold_ms:
        return build_synthetic_payload(spec=spec, elapsed_ms=elapsed_ms)

    raise RuntimeError(
        f"Could not derive an error payload for '{spec.bug_key}'. "
        f"HTTP status was {status}."
    )


def trigger_demo_app_error(
    *,
    spec: BugSpec,
    demo_app_base_url: str,
    request_timeout: float,
    timeout_threshold_ms: int,
) -> dict[str, Any]:
    target_url = f"{demo_app_base_url.rstrip('/')}{spec.path}"
    started_at = time.time()
    status, payload = http_json(method="GET", url=target_url, timeout=request_timeout)
    elapsed_ms = int((time.time() - started_at) * 1000)

    error_payload = normalize_payload(
        spec=spec,
        status=status,
        payload=payload,
        elapsed_ms=elapsed_ms,
        timeout_threshold_ms=timeout_threshold_ms,
    )

    print(
        json.dumps(
            {
                "bug_key": spec.bug_key,
                "target_url": target_url,
                "status": status,
                "elapsed_ms": elapsed_ms,
                "payload": error_payload,
            },
            indent=2,
        )
    )

    return error_payload


def ingest_into_backend(
    *,
    backend_base_url: str,
    payload: dict[str, Any],
    request_timeout: float,
) -> dict[str, Any]:
    target_url = f"{backend_base_url.rstrip('/')}/api/ingest/demo-app"
    status, response_payload = http_json(
        method="POST",
        url=target_url,
        timeout=request_timeout,
        payload={"payload": payload},
    )

    if status >= 400 or not response_payload:
        raise RuntimeError(f"Backend ingest failed with status {status}.")

    print(
        json.dumps(
            {
                "backend_status": status,
                "incident_id": response_payload.get("incident", {}).get("incident_id"),
                "provider": response_payload.get("provider"),
            },
            indent=2,
        )
    )

    return response_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger one of the planned DeepOps demo errors.",
    )
    parser.add_argument(
        "bug_key",
        choices=[*BUG_SPECS.keys(), "all"],
        help="Which demo bug to trigger.",
    )
    parser.add_argument(
        "--demo-app-base-url",
        default=DEFAULT_DEMO_APP_BASE_URL,
        help="Base URL for the demo app.",
    )
    parser.add_argument(
        "--backend-base-url",
        default=DEFAULT_BACKEND_BASE_URL,
        help="Base URL for the DeepOps backend.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="After triggering the error, POST it to /api/ingest/demo-app.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--timeout-threshold-ms",
        type=int,
        default=3000,
        help="If a slow route takes longer than this, treat it as TimeoutError.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bug_keys = (
        list(BUG_SPECS.keys()) if args.bug_key == "all" else [args.bug_key]
    )

    try:
        for bug_key in bug_keys:
            payload = trigger_demo_app_error(
                spec=BUG_SPECS[bug_key],
                demo_app_base_url=args.demo_app_base_url,
                request_timeout=args.request_timeout,
                timeout_threshold_ms=args.timeout_threshold_ms,
            )
            if args.ingest:
                ingest_into_backend(
                    backend_base_url=args.backend_base_url,
                    payload=payload,
                    request_timeout=args.request_timeout,
                )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
