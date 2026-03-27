"""Normalize raw error payloads into canonical incident records."""

from __future__ import annotations

import hashlib
import logging
import time
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo trigger bug definitions
# ---------------------------------------------------------------------------

_DEMO_BUGS: dict[str, dict] = {
    "calculate_zero": {
        "path": "/calculate/0",
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero",
        "source_file": "demo-app/main.py",
    },
    "user_missing": {
        "path": "/user/unknown",
        "error_type": "KeyError",
        "error_message": "'name'",
        "source_file": "demo-app/main.py",
    },
    "search_timeout": {
        "path": "/search",
        "error_type": "TimeoutError",
        "error_message": "search endpoint timed out",
        "source_file": "demo-app/main.py",
    },
}


def _fingerprint(error_type: str, path: str) -> str:
    """Deterministic fingerprint from error type and path."""
    raw = f"{error_type}:{path}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _make_default_incident(source: dict) -> dict:
    """Create a complete incident dict with all default sections."""
    now = _now_ms()
    return {
        "incident_id": f"inc-{uuid.uuid4()}",
        "status": "stored",
        "severity": "pending",
        "service": "deepops-demo-app",
        "environment": "hackathon",
        "created_at_ms": now,
        "updated_at_ms": now,
        "resolution_time_ms": None,
        "source": source,
        "diagnosis": {
            "status": "pending",
            "root_cause": None,
            "suggested_fix": None,
            "affected_components": [],
            "confidence": 0.0,
            "severity_reasoning": None,
            "macroscope_context": None,
            "started_at_ms": None,
            "completed_at_ms": None,
        },
        "fix": {
            "status": "pending",
            "spec_markdown": None,
            "diff_preview": None,
            "files_changed": [],
            "test_plan": [],
            "started_at_ms": None,
            "completed_at_ms": None,
        },
        "approval": {
            "required": False,
            "mode": "auto",
            "status": "pending",
            "channel": None,
            "decider": None,
            "bland_call_id": None,
            "notes": None,
            "decision_at_ms": None,
        },
        "deployment": {
            "provider": "truefoundry",
            "status": "pending",
            "service_name": None,
            "environment": None,
            "commit_sha": None,
            "deploy_url": None,
            "started_at_ms": None,
            "completed_at_ms": None,
            "failure_reason": None,
        },
        "observability": {
            "overmind_trace_id": None,
            "overmind_trace_url": None,
            "airbyte_sync_id": None,
            "auth0_decision_id": None,
        },
        "timeline": [
            {
                "at_ms": now,
                "status": "stored",
                "actor": "ingestion",
                "message": f"Incident ingested from {source.get('provider', 'unknown')}",
                "sponsor": "Aerospike",
                "metadata": None,
            }
        ],
    }


def normalize_demo_trigger(bug_key: str, raw_payload: dict | None = None) -> dict:
    """Convert a demo trigger into a stored incident."""
    if bug_key not in _DEMO_BUGS:
        raise ValueError(
            f"Unknown bug_key '{bug_key}'. "
            f"Valid keys: {sorted(_DEMO_BUGS.keys())}"
        )

    bug = _DEMO_BUGS[bug_key]
    now = _now_ms()

    source = {
        "provider": "demo-app",
        "path": bug["path"],
        "error_type": bug["error_type"],
        "error_message": bug["error_message"],
        "source_file": bug["source_file"],
        "timestamp_ms": now,
        "fingerprint": _fingerprint(bug["error_type"], bug["path"]),
        "raw_payload": raw_payload,
    }

    incident = _make_default_incident(source)
    logger.info("Normalized demo trigger '%s' -> %s", bug_key, incident["incident_id"])
    return incident


def normalize_demo_app_error(raw_error: dict) -> dict:
    """Convert a raw demo app error event into a stored incident."""
    now = _now_ms()

    source = {
        "provider": "demo-app",
        "path": raw_error.get("path", "/unknown"),
        "error_type": raw_error.get("error_type", "UnknownError"),
        "error_message": raw_error.get("error_message", "No message provided"),
        "source_file": raw_error.get("source_file", "unknown"),
        "timestamp_ms": raw_error.get("timestamp", now),
        "fingerprint": _fingerprint(
            raw_error.get("error_type", "UnknownError"),
            raw_error.get("path", "/unknown"),
        ),
        "raw_payload": {
            k: v
            for k, v in raw_error.items()
            if k in ("method", "status_code", "headers", "query_params")
        } or None,
    }

    incident = _make_default_incident(source)
    logger.info("Normalized demo app error -> %s", incident["incident_id"])
    return incident


def normalize_airbyte_record(record: dict, sync_id: str | None = None) -> dict:
    """Convert an Airbyte-delivered record into a stored incident."""
    now = _now_ms()

    source = {
        "provider": "airbyte",
        "path": record.get("path", record.get("route", "/unknown")),
        "error_type": record.get("error_type", record.get("exception_class", "UnknownError")),
        "error_message": record.get("error_message", record.get("message", "No message")),
        "source_file": record.get("source_file", record.get("file", "unknown")),
        "timestamp_ms": record.get("timestamp_ms", record.get("timestamp", now)),
        "fingerprint": _fingerprint(
            record.get("error_type", record.get("exception_class", "UnknownError")),
            record.get("path", record.get("route", "/unknown")),
        ),
        "raw_payload": record,
    }

    incident = _make_default_incident(source)

    if sync_id:
        incident["observability"]["airbyte_sync_id"] = sync_id

    logger.info("Normalized Airbyte record -> %s (sync=%s)", incident["incident_id"], sync_id)
    return incident


# ---------------------------------------------------------------------------
# Fallback normalization for unknown/malformed payloads
# ---------------------------------------------------------------------------

# Alternate key names to try when extracting fields from arbitrary payloads
_PATH_KEYS = ("path", "route", "url", "endpoint", "uri", "request_path")
_ERROR_TYPE_KEYS = ("error_type", "exception_class", "exception", "type", "error_class", "exc_type")
_ERROR_MSG_KEYS = ("error_message", "message", "msg", "detail", "description", "error")
_FILE_KEYS = ("source_file", "file", "filename", "module", "source", "filepath")


def _extract_field(payload: dict, keys: tuple[str, ...], default: str) -> str:
    """Try multiple key names to extract a field from an arbitrary payload."""
    for key in keys:
        val = payload.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return default


def _sanitize_source(source: dict) -> dict:
    """Ensure all required source fields have sensible non-null defaults."""
    now = _now_ms()
    source.setdefault("provider", "demo-app")
    source.setdefault("path", "/unknown")
    source.setdefault("error_type", "UnknownError")
    source.setdefault("error_message", "An unidentified error occurred")
    source.setdefault("source_file", "unknown")
    source.setdefault("timestamp_ms", now)
    if not source.get("fingerprint"):
        source["fingerprint"] = _fingerprint(source["error_type"], source["path"])
    # Ensure no None values in required string fields
    for key in ("provider", "path", "error_type", "error_message", "source_file"):
        if source[key] is None:
            source[key] = "unknown"
    return source


def normalize_unknown_payload(payload: dict) -> dict:
    """Normalize an arbitrary/malformed payload into a stored incident.

    Tries to extract path, error_type, error_message from any reasonable
    key names. Falls back to sensible defaults. Always produces a valid
    stored incident. Tags the timeline with fallback_normalization metadata.
    """
    now = _now_ms()

    source = _sanitize_source({
        "provider": _extract_field(payload, ("provider", "source"), "demo-app"),
        "path": _extract_field(payload, _PATH_KEYS, "/unknown"),
        "error_type": _extract_field(payload, _ERROR_TYPE_KEYS, "UnknownError"),
        "error_message": _extract_field(payload, _ERROR_MSG_KEYS, "An unidentified error occurred"),
        "source_file": _extract_field(payload, _FILE_KEYS, "unknown"),
        "timestamp_ms": payload.get("timestamp_ms", payload.get("timestamp", now)),
        "fingerprint": None,  # will be set by _sanitize_source
        "raw_payload": payload,
    })

    incident = _make_default_incident(source)
    # Tag the timeline event so fallback normalization is visible
    incident["timeline"][0]["metadata"] = {"fallback_normalization": True}
    incident["timeline"][0]["message"] = (
        f"Incident ingested from {source['provider']} via fallback normalization"
    )

    logger.info("Normalized unknown payload -> %s (fallback)", incident["incident_id"])
    return incident
