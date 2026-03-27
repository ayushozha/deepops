from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from uuid import uuid4

from agent.contracts import TimelineEvent, make_timeline_event, now_ms


PLAN_STATES = {
    "pending",
    "approved",
    "superseded",
    "executed",
    "blocked",
    "rejected",
}

PLAN_SOURCES = {
    "autonomous",
    "ui",
    "phone",
    "backend",
}

PLAN_REQUEST_CHANNELS = {
    "ui",
    "phone",
    "autonomous",
    "backend",
}


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_lines(items: Sequence[str] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    for item in items or ():
        text = _normalize_text(item)
        if text and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned)


def _generate_plan_id() -> str:
    return f"plan-{uuid4().hex[:12]}"


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured execution plan stored in timeline metadata and notes."""

    title: str
    summary: str
    source: str
    requested_by: str
    requested_via: str
    target_stage: str
    steps: tuple[str, ...] = field(default_factory=tuple)
    constraints: tuple[str, ...] = field(default_factory=tuple)
    state: str = "pending"
    plan_id: str = field(default_factory=_generate_plan_id)
    revision: int = 1
    parent_plan_id: str | None = None
    created_at_ms: int = field(default_factory=now_ms)
    updated_at_ms: int = field(default_factory=now_ms)
    instruction_text: str | None = None

    def __post_init__(self) -> None:
        title = _normalize_text(self.title)
        summary = _normalize_text(self.summary)
        source = _normalize_text(self.source)
        requested_by = _normalize_text(self.requested_by)
        requested_via = _normalize_text(self.requested_via)
        target_stage = _normalize_text(self.target_stage)
        state = _normalize_text(self.state)

        if not title:
            raise ValueError("title is required")
        if not summary:
            raise ValueError("summary is required")
        if source not in PLAN_SOURCES:
            raise ValueError(f"source must be one of {sorted(PLAN_SOURCES)}")
        if not requested_by:
            raise ValueError("requested_by is required")
        if requested_via not in PLAN_REQUEST_CHANNELS:
            raise ValueError(f"requested_via must be one of {sorted(PLAN_REQUEST_CHANNELS)}")
        if not target_stage:
            raise ValueError("target_stage is required")
        if state not in PLAN_STATES:
            raise ValueError(f"state must be one of {sorted(PLAN_STATES)}")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if self.created_at_ms < 0 or self.updated_at_ms < 0:
            raise ValueError("timestamps must be non-negative")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "requested_by", requested_by)
        object.__setattr__(self, "requested_via", requested_via)
        object.__setattr__(self, "target_stage", target_stage)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "steps", _normalize_lines(self.steps))
        object.__setattr__(self, "constraints", _normalize_lines(self.constraints))
        object.__setattr__(self, "instruction_text", _normalize_text(self.instruction_text) or None)

    def snapshot(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "requested_by": self.requested_by,
            "requested_via": self.requested_via,
            "target_stage": self.target_stage,
            "steps": list(self.steps),
            "constraints": list(self.constraints),
            "state": self.state,
            "revision": self.revision,
            "parent_plan_id": self.parent_plan_id,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
            "instruction_text": self.instruction_text,
        }


@dataclass(frozen=True)
class PlanStateMutation:
    """Canonical-safe patch plus timeline event for execution plan persistence."""

    plan: ExecutionPlan
    notes: str
    timeline_event: TimelineEvent
    patch: dict[str, Any]


def create_execution_plan(
    *,
    title: str,
    summary: str,
    source: str,
    requested_by: str,
    requested_via: str,
    target_stage: str,
    steps: Sequence[str] | None = None,
    constraints: Sequence[str] | None = None,
    state: str = "pending",
    plan_id: str | None = None,
    revision: int = 1,
    parent_plan_id: str | None = None,
    created_at_ms: int | None = None,
    updated_at_ms: int | None = None,
    instruction_text: str | None = None,
) -> ExecutionPlan:
    created = created_at_ms if created_at_ms is not None else now_ms()
    updated = updated_at_ms if updated_at_ms is not None else created
    return ExecutionPlan(
        title=title,
        summary=summary,
        source=source,
        requested_by=requested_by,
        requested_via=requested_via,
        target_stage=target_stage,
        steps=_normalize_lines(steps),
        constraints=_normalize_lines(constraints),
        state=state,
        plan_id=plan_id or _generate_plan_id(),
        revision=revision,
        parent_plan_id=parent_plan_id,
        created_at_ms=created,
        updated_at_ms=updated,
        instruction_text=instruction_text,
    )


def revise_execution_plan(
    previous: ExecutionPlan,
    *,
    summary: str | None = None,
    title: str | None = None,
    source: str | None = None,
    requested_by: str | None = None,
    requested_via: str | None = None,
    target_stage: str | None = None,
    steps: Sequence[str] | None = None,
    constraints: Sequence[str] | None = None,
    state: str = "pending",
    instruction_text: str | None = None,
    updated_at_ms: int | None = None,
) -> ExecutionPlan:
    return create_execution_plan(
        title=title or previous.title,
        summary=summary or previous.summary,
        source=source or previous.source,
        requested_by=requested_by or previous.requested_by,
        requested_via=requested_via or previous.requested_via,
        target_stage=target_stage or previous.target_stage,
        steps=steps if steps is not None else previous.steps,
        constraints=constraints if constraints is not None else previous.constraints,
        state=state,
        parent_plan_id=previous.plan_id,
        revision=previous.revision + 1,
        instruction_text=instruction_text if instruction_text is not None else previous.instruction_text,
        updated_at_ms=updated_at_ms,
    )


def build_plan_notes(plan: ExecutionPlan) -> str:
    lines = [
        f"# Execution Plan: {plan.title}",
        "",
        f"- Plan ID: `{plan.plan_id}`",
        f"- State: `{plan.state}`",
        f"- Source: `{plan.source}`",
        f"- Requested by: `{plan.requested_by}`",
        f"- Requested via: `{plan.requested_via}`",
        f"- Target stage: `{plan.target_stage}`",
        f"- Revision: `{plan.revision}`",
    ]

    if plan.parent_plan_id:
        lines.append(f"- Parent plan: `{plan.parent_plan_id}`")

    lines.extend(["", "## Summary", plan.summary])

    if plan.instruction_text:
        lines.extend(["", "## Human Instruction", plan.instruction_text])

    lines.extend(["", "## Steps"])
    if plan.steps:
        lines.extend([f"- {step}" for step in plan.steps])
    else:
        lines.append("- None provided")

    lines.extend(["", "## Constraints"])
    if plan.constraints:
        lines.extend([f"- {constraint}" for constraint in plan.constraints])
    else:
        lines.append("- None provided")

    return "\n".join(lines).rstrip() + "\n"


def build_plan_snapshot(plan: ExecutionPlan) -> dict[str, Any]:
    return plan.snapshot()


def build_plan_timeline_event(
    plan: ExecutionPlan,
    *,
    actor: str,
    sponsor: str,
    message: str,
    incident_status: str,
    at_ms: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> TimelineEvent:
    payload: dict[str, Any] = {
        "plan_state": build_plan_snapshot(plan),
    }
    if metadata:
        payload.update(dict(metadata))

    return make_timeline_event(
        status=incident_status,
        actor=actor,
        message=message,
        sponsor=sponsor,
        metadata=payload,
        at_ms=at_ms,
    )


def build_plan_state_mutation(
    plan: ExecutionPlan,
    *,
    actor: str,
    sponsor: str,
    incident_status: str,
    message: str,
    approval_patch: Mapping[str, Any] | None = None,
    at_ms: int | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
) -> PlanStateMutation:
    notes = build_plan_notes(plan)
    patch_approval: dict[str, Any] = dict(approval_patch or {})
    patch_approval.setdefault("notes", notes)

    timeline_event = build_plan_timeline_event(
        plan,
        actor=actor,
        sponsor=sponsor,
        message=message,
        incident_status=incident_status,
        at_ms=at_ms,
        metadata=extra_metadata,
    )

    return PlanStateMutation(
        plan=plan,
        notes=notes,
        timeline_event=timeline_event,
        patch={"approval": patch_approval},
    )


def extract_latest_plan_snapshot(incident: Mapping[str, Any]) -> dict[str, Any] | None:
    timeline = incident.get("timeline") or []
    for event in reversed(list(timeline)):
        metadata = event.get("metadata") if isinstance(event, Mapping) else None
        if not isinstance(metadata, Mapping):
            continue
        plan_state = metadata.get("plan_state")
        if isinstance(plan_state, Mapping):
            return dict(plan_state)
    return None

