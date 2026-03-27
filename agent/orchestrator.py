from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agent.contracts import (
    APPROVAL_PENDING,
    DIAGNOSIS_COMPLETE,
    DIAGNOSIS_FAILED,
    DIAGNOSIS_RUNNING,
    FIX_COMPLETE,
    FIX_FAILED,
    FIX_RUNNING,
    IncidentRecord,
    STATUS_DIAGNOSING,
    STATUS_FAILED,
    STATUS_FIXING,
    STATUS_GATING,
    STATUS_STORED,
    build_person_a_output,
    deep_merge_dict,
    make_timeline_event,
    normalize_incident,
    now_ms,
)
from agent.detector import detect_ready_incidents
from agent.severity import assess_severity
from agent.store_adapter import IncidentStore, InMemoryIncidentStore
from agent.tracing import NullTracer, TracerLike

DiagnosisRunner = Callable[[IncidentRecord], Mapping[str, Any]]
FixRunner = Callable[[IncidentRecord, Mapping[str, Any]], Mapping[str, Any]]


@dataclass
class AgentRuntime:
    store: IncidentStore
    diagnose: DiagnosisRunner
    generate_fix: FixRunner
    tracer: TracerLike = field(default_factory=NullTracer)
    actor_name: str = "agent-core"


def _persist(
    runtime: AgentRuntime,
    incident: IncidentRecord,
    patch: Mapping[str, Any],
    *,
    persist: bool,
) -> IncidentRecord:
    merged = normalize_incident(deep_merge_dict(incident, patch))
    if persist:
        runtime.store.patch_incident(incident["incident_id"], dict(patch))
    return merged


def _append_event(
    runtime: AgentRuntime,
    incident: IncidentRecord,
    event: Mapping[str, Any],
    *,
    persist: bool,
) -> IncidentRecord:
    timeline = [*incident.get("timeline", []), dict(event)]
    if persist:
        runtime.store.append_timeline_event(incident["incident_id"], dict(event))
    return _persist(runtime, incident, {"timeline": timeline}, persist=False)


def _transition(
    runtime: AgentRuntime,
    incident: IncidentRecord,
    *,
    status: str,
    sponsor: str,
    message: str,
    patch: Mapping[str, Any] | None = None,
    persist: bool,
) -> IncidentRecord:
    at_ms = now_ms()
    base_patch = {"status": status, "updated_at_ms": at_ms}
    if patch:
        base_patch = deep_merge_dict(base_patch, patch)
    updated = _persist(runtime, incident, base_patch, persist=persist)
    event = make_timeline_event(
        status=status,
        actor=runtime.actor_name,
        message=message,
        sponsor=sponsor,
        at_ms=at_ms,
    )
    return _append_event(runtime, updated, event, persist=persist)


def process_incident(runtime: AgentRuntime, incident: IncidentRecord, *, persist: bool = True) -> IncidentRecord:
    incident = normalize_incident(incident)

    with runtime.tracer.start_as_current_span("person-a.process-incident") as span:
        span.set_attribute("incident_id", incident["incident_id"])
        span.set_attribute("status_before", incident.get("status"))

        try:
            incident = _transition(
                runtime,
                incident,
                status=STATUS_DIAGNOSING,
                sponsor="Macroscope",
                message="Person A started diagnosis.",
                patch={"diagnosis": {"status": DIAGNOSIS_RUNNING, "started_at_ms": now_ms()}},
                persist=persist,
            )

            diagnosis = dict(runtime.diagnose(deepcopy(incident)))
            incident = _persist(
                runtime,
                incident,
                {
                    "diagnosis": deep_merge_dict(
                        incident.get("diagnosis", {}),
                        {
                            "status": DIAGNOSIS_COMPLETE,
                            "completed_at_ms": now_ms(),
                            **diagnosis,
                        },
                    )
                },
                persist=persist,
            )

            incident = _transition(
                runtime,
                incident,
                status=STATUS_FIXING,
                sponsor="Kiro",
                message="Person A started fix generation.",
                patch={"fix": {"status": FIX_RUNNING, "started_at_ms": now_ms()}},
                persist=persist,
            )

            fix = dict(runtime.generate_fix(deepcopy(incident), deepcopy(incident["diagnosis"])))
            incident = _persist(
                runtime,
                incident,
                {
                    "fix": deep_merge_dict(
                        incident.get("fix", {}),
                        {
                            "status": FIX_COMPLETE,
                            "completed_at_ms": now_ms(),
                            **fix,
                        },
                    )
                },
                persist=persist,
            )

            decision = assess_severity(incident, incident["diagnosis"])
            incident = _transition(
                runtime,
                incident,
                status=STATUS_GATING,
                sponsor="Auth0",
                message="Person A completed routing handoff.",
                patch={
                    "severity": decision.severity,
                    "diagnosis": {"severity_reasoning": decision.reason},
                    "approval": {
                        "required": decision.severity in {"high", "critical"},
                        "mode": "manual" if decision.severity in {"high", "critical"} else "auto",
                        "status": APPROVAL_PENDING,
                    },
                },
                persist=persist,
            )

            span.set_attribute("status_after", incident.get("status"))
            span.set_attribute("severity", incident.get("severity"))
            return incident
        except Exception as exc:
            failure_patch = {
                "status": STATUS_FAILED,
                "updated_at_ms": now_ms(),
            }
            if incident.get("status") == STATUS_DIAGNOSING:
                failure_patch["diagnosis"] = {"status": DIAGNOSIS_FAILED}
            elif incident.get("status") == STATUS_FIXING:
                failure_patch["fix"] = {"status": FIX_FAILED}

            incident = _persist(runtime, incident, failure_patch, persist=persist)
            event = make_timeline_event(
                status=STATUS_FAILED,
                actor=runtime.actor_name,
                message=f"Person A failed: {exc}",
                sponsor="Overmind",
            )
            incident = _append_event(runtime, incident, event, persist=persist)
            span.set_attribute("status_after", incident.get("status"))
            span.set_attribute("error", str(exc))
            raise


def process_next_incident(runtime: AgentRuntime, *, persist: bool = True, limit: int = 1) -> IncidentRecord | None:
    ready = detect_ready_incidents(runtime.store, limit=limit, allowed_statuses=(STATUS_STORED,))
    if not ready:
        return None
    return process_incident(runtime, ready[0], persist=persist)


def run_case(
    input_case: Mapping[str, Any],
    *,
    diagnose: DiagnosisRunner,
    generate_fix: FixRunner,
    tracer: TracerLike | None = None,
) -> dict[str, Any]:
    incident = normalize_incident(input_case, status=STATUS_STORED)
    store = InMemoryIncidentStore([incident])
    runtime = AgentRuntime(
        store=store,
        diagnose=diagnose,
        generate_fix=generate_fix,
        tracer=tracer or NullTracer(),
    )
    processed = process_next_incident(runtime, persist=True)
    return build_person_a_output(processed or incident)
