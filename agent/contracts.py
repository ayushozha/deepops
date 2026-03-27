from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, TypedDict, cast
import json
import time
import uuid


STATUS_DETECTED = "detected"
STATUS_STORED = "stored"
STATUS_DIAGNOSING = "diagnosing"
STATUS_FIXING = "fixing"
STATUS_GATING = "gating"
STATUS_AWAITING_APPROVAL = "awaiting_approval"
STATUS_DEPLOYING = "deploying"
STATUS_RESOLVED = "resolved"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"

DIAGNOSIS_PENDING = "pending"
DIAGNOSIS_RUNNING = "running"
DIAGNOSIS_COMPLETE = "complete"
DIAGNOSIS_FAILED = "failed"

FIX_PENDING = "pending"
FIX_RUNNING = "running"
FIX_COMPLETE = "complete"
FIX_FAILED = "failed"

APPROVAL_PENDING = "pending"
SEVERITY_PENDING = "pending"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"


class SourcePayload(TypedDict, total=False):
    provider: str
    path: str
    error_type: str
    error_message: str
    source_file: str
    timestamp_ms: int
    fingerprint: str | None
    raw_payload: dict[str, Any] | None


class DiagnosisPayload(TypedDict, total=False):
    status: str
    root_cause: str | None
    suggested_fix: str | None
    affected_components: list[str]
    confidence: float
    severity_reasoning: str | None
    macroscope_context: str | None
    started_at_ms: int | None
    completed_at_ms: int | None


class FixPayload(TypedDict, total=False):
    status: str
    spec_markdown: str | None
    diff_preview: str | None
    files_changed: list[str]
    test_plan: list[str]
    started_at_ms: int | None
    completed_at_ms: int | None


class ApprovalPayload(TypedDict, total=False):
    required: bool
    mode: str
    status: str
    channel: str | None
    decider: str | None
    bland_call_id: str | None
    notes: str | None
    decision_at_ms: int | None


class DeploymentPayload(TypedDict, total=False):
    provider: str
    status: str
    service_name: str | None
    environment: str | None
    commit_sha: str | None
    deploy_url: str | None
    started_at_ms: int | None
    completed_at_ms: int | None
    failure_reason: str | None


class ObservabilityPayload(TypedDict, total=False):
    overmind_trace_id: str | None
    overmind_trace_url: str | None
    airbyte_sync_id: str | None
    auth0_decision_id: str | None


class TimelineEvent(TypedDict):
    at_ms: int
    status: str
    actor: str
    message: str
    sponsor: str
    metadata: dict[str, Any] | None


class IncidentRecord(TypedDict, total=False):
    incident_id: str
    status: str
    severity: str
    service: str
    environment: str
    created_at_ms: int
    updated_at_ms: int
    resolution_time_ms: int | None
    source: SourcePayload
    diagnosis: DiagnosisPayload
    fix: FixPayload
    approval: ApprovalPayload
    deployment: DeploymentPayload
    observability: ObservabilityPayload
    timeline: list[TimelineEvent]


def now_ms() -> int:
    return int(time.time() * 1000)


def default_source() -> SourcePayload:
    return {
        "provider": "demo-app",
        "path": "",
        "error_type": "",
        "error_message": "",
        "source_file": "",
        "timestamp_ms": now_ms(),
        "fingerprint": None,
        "raw_payload": None,
    }


def default_diagnosis() -> DiagnosisPayload:
    return {
        "status": DIAGNOSIS_PENDING,
        "root_cause": None,
        "suggested_fix": None,
        "affected_components": [],
        "confidence": 0.0,
        "severity_reasoning": None,
        "macroscope_context": None,
        "started_at_ms": None,
        "completed_at_ms": None,
    }


def default_fix() -> FixPayload:
    return {
        "status": FIX_PENDING,
        "spec_markdown": None,
        "diff_preview": None,
        "files_changed": [],
        "test_plan": [],
        "started_at_ms": None,
        "completed_at_ms": None,
    }


def default_approval() -> ApprovalPayload:
    return {
        "required": False,
        "mode": "auto",
        "status": APPROVAL_PENDING,
        "channel": None,
        "decider": None,
        "bland_call_id": None,
        "notes": None,
        "decision_at_ms": None,
    }


def default_deployment() -> DeploymentPayload:
    return {
        "provider": "truefoundry",
        "status": "pending",
        "service_name": None,
        "environment": None,
        "commit_sha": None,
        "deploy_url": None,
        "started_at_ms": None,
        "completed_at_ms": None,
        "failure_reason": None,
    }


def default_observability() -> ObservabilityPayload:
    return {
        "overmind_trace_id": None,
        "overmind_trace_url": None,
        "airbyte_sync_id": None,
        "auth0_decision_id": None,
    }


def default_incident(
    *,
    status: str = STATUS_STORED,
    service: str = "deepops-person-a",
    environment: str = "hackathon",
) -> IncidentRecord:
    created_at = now_ms()
    source = default_source()
    source["timestamp_ms"] = created_at
    return {
        "incident_id": f"inc-{uuid.uuid4()}",
        "status": status,
        "severity": SEVERITY_PENDING,
        "service": service,
        "environment": environment,
        "created_at_ms": created_at,
        "updated_at_ms": created_at,
        "resolution_time_ms": None,
        "source": source,
        "diagnosis": default_diagnosis(),
        "fix": default_fix(),
        "approval": default_approval(),
        "deployment": default_deployment(),
        "observability": default_observability(),
        "timeline": [],
    }


def deep_merge_dict(base: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = deepcopy(dict(base))
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge_dict(cast(Mapping[str, Any], merged[key]), value)
        else:
            merged[key] = deepcopy(value)
    return merged


def make_timeline_event(
    *,
    status: str,
    actor: str,
    message: str,
    sponsor: str,
    metadata: dict[str, Any] | None = None,
    at_ms: int | None = None,
) -> TimelineEvent:
    return {
        "at_ms": at_ms if at_ms is not None else now_ms(),
        "status": status,
        "actor": actor,
        "message": message,
        "sponsor": sponsor,
        "metadata": metadata,
    }


def normalize_incident(
    payload: Mapping[str, Any],
    *,
    status: str = STATUS_STORED,
    service: str = "deepops-person-a",
    environment: str = "hackathon",
) -> IncidentRecord:
    candidate: Mapping[str, Any] = payload
    if isinstance(candidate.get("incident"), Mapping):
        candidate = cast(Mapping[str, Any], candidate["incident"])
    elif isinstance(candidate.get("input"), Mapping):
        candidate = cast(Mapping[str, Any], candidate["input"])

    incident = default_incident(status=status, service=service, environment=environment)
    incident = cast(IncidentRecord, deep_merge_dict(incident, candidate))

    if not incident.get("incident_id"):
        incident["incident_id"] = f"inc-{uuid.uuid4()}"

    created_at = incident.get("created_at_ms") or incident.get("source", {}).get("timestamp_ms") or now_ms()
    incident["created_at_ms"] = created_at
    incident["updated_at_ms"] = incident.get("updated_at_ms", created_at)
    incident.setdefault("source", default_source())
    incident["source"]["timestamp_ms"] = incident["source"].get("timestamp_ms", created_at)
    incident.setdefault("diagnosis", default_diagnosis())
    incident.setdefault("fix", default_fix())
    incident.setdefault("approval", default_approval())
    incident.setdefault("deployment", default_deployment())
    incident.setdefault("observability", default_observability())
    incident.setdefault("timeline", [])
    incident["status"] = incident.get("status", status)
    incident["severity"] = incident.get("severity", SEVERITY_PENDING)
    incident["service"] = incident.get("service", service)
    incident["environment"] = incident.get("environment", environment)
    return incident


def load_incident_from_path(path: str | Path) -> IncidentRecord:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_incident(payload)


def build_person_a_output(incident: Mapping[str, Any]) -> dict[str, Any]:
    diagnosis = cast(Mapping[str, Any], incident.get("diagnosis", {}))
    fix = cast(Mapping[str, Any], incident.get("fix", {}))
    return {
        "incident_id": incident.get("incident_id"),
        "status": incident.get("status"),
        "severity": incident.get("severity"),
        "root_cause": diagnosis.get("root_cause"),
        "suggested_fix": diagnosis.get("suggested_fix"),
        "affected_components": diagnosis.get("affected_components", []),
        "confidence": diagnosis.get("confidence"),
        "severity_reasoning": diagnosis.get("severity_reasoning"),
        "spec_markdown": fix.get("spec_markdown"),
        "diff_preview": fix.get("diff_preview"),
        "files_changed": fix.get("files_changed", []),
        "test_plan": fix.get("test_plan", []),
    }
