from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from agent.contracts import APPROVAL_PENDING

_AUTO_APPROVE_SEVERITIES = {"low", "medium"}
_MANUAL_SEVERITIES = {"high", "critical"}
_KNOWN_SEVERITIES = {"pending", "low", "medium", "high", "critical"}

_APPROVE_PHRASES = (
    "approve",
    "approved",
    "go ahead",
    "proceed",
    "ship it",
    "deploy it",
    "allow it",
    "yes",
)
_REJECT_PHRASES = (
    "reject",
    "rejected",
    "deny",
    "hold",
    "stop",
    "abort",
    "cancel",
    "block",
    "do not",
    "don't",
    "no",
)
_REPLAN_PHRASES = (
    "suggest",
    "change",
    "revise",
    "replan",
    "another plan",
    "another fix",
    "instead",
    "feature flag",
    "patch only",
    "do it this way",
)
_CLARIFY_PHRASES = (
    "need more",
    "more information",
    "not sure",
    "think about it",
    "check the logs",
    "later",
)
_PHONE_ESCALATION_PHRASES = (
    "financial",
    "revenue",
    "billing",
    "payment",
    "money",
    "customer impact",
    "user impact",
    "blast radius",
    "security",
    "outage",
    "data loss",
    "production",
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.lower().split())
    return " ".join(str(value).lower().split())


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values: list[str] = []
        for item in value.values():
            values.extend(_collect_strings(item))
        return values
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        values: list[str] = []
        for item in value:
            values.extend(_collect_strings(item))
        return values
    return [str(value)]


def normalize_severity(value: Any) -> str:
    severity = _normalize_text(value)
    if severity in _KNOWN_SEVERITIES:
        return severity
    return "pending"


def classify_human_instruction(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return "unknown"

    for phrase in _REJECT_PHRASES:
        if phrase in text:
            return "reject"
    for phrase in _REPLAN_PHRASES:
        if phrase in text:
            return "replan"
    for phrase in _CLARIFY_PHRASES:
        if phrase in text:
            return "clarify"
    for phrase in _APPROVE_PHRASES:
        if phrase in text:
            return "approve"
    return "unknown"


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _incident_blob(incident: Mapping[str, Any]) -> str:
    pieces = _collect_strings(incident)
    return _normalize_text(" ".join(piece for piece in pieces if piece))


@dataclass(frozen=True)
class ApprovalPolicyDecision:
    incident_id: str | None
    severity: str
    required: bool
    mode: str
    status: str
    route: str
    next_action: str
    channel: str | None
    decider: str | None
    reason: str
    requires_phone_escalation: bool = False
    suggestion_allowed: bool = False
    approval_kind: str = "auth0-rbac"

    def to_approval_patch(
        self,
        *,
        notes: str | None = None,
        bland_call_id: str | None = None,
        decision_at_ms: int | None = None,
    ) -> dict[str, Any]:
        return {
            "required": self.required,
            "mode": self.mode,
            "status": self.status,
            "channel": self.channel,
            "decider": self.decider,
            "bland_call_id": bland_call_id,
            "notes": notes,
            "decision_at_ms": decision_at_ms,
        }

    def to_timeline_metadata(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "severity": self.severity,
            "route": self.route,
            "next_action": self.next_action,
            "requires_phone_escalation": self.requires_phone_escalation,
            "suggestion_allowed": self.suggestion_allowed,
            "approval_kind": self.approval_kind,
        }


def evaluate_approval_policy(
    incident: Mapping[str, Any],
    human_instruction: Any = None,
) -> ApprovalPolicyDecision:
    severity = normalize_severity(incident.get("severity"))
    incident_id = incident.get("incident_id") if isinstance(incident.get("incident_id"), str) else None
    instruction = classify_human_instruction(human_instruction)
    blob = _incident_blob(incident)
    requires_phone_escalation = severity in {"high", "critical"} or _contains_any(blob, _PHONE_ESCALATION_PHRASES)

    if instruction == "reject":
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=True,
            mode="manual",
            status="rejected",
            route="blocked",
            next_action="block",
            channel="auth0-rbac",
            decider="auth0:manual-reject",
            reason="Human rejected the proposed change.",
            requires_phone_escalation=requires_phone_escalation,
            suggestion_allowed=False,
        )

    if instruction == "replan":
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=True,
            mode="manual",
            status=APPROVAL_PENDING,
            route="replan",
            next_action="replan",
            channel="auth0-rbac",
            decider="auth0:human-suggest",
            reason="Human suggested a revised approach and the plan should be regenerated.",
            requires_phone_escalation=requires_phone_escalation,
            suggestion_allowed=True,
        )

    if instruction == "clarify":
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=True,
            mode="manual",
            status=APPROVAL_PENDING,
            route="manual-review",
            next_action="await_human",
            channel="auth0-rbac",
            decider="auth0:manual-review",
            reason="Human asked for more information before approval.",
            requires_phone_escalation=requires_phone_escalation,
            suggestion_allowed=True,
        )

    if instruction == "approve":
        if severity in _AUTO_APPROVE_SEVERITIES and not requires_phone_escalation:
            return ApprovalPolicyDecision(
                incident_id=incident_id,
                severity=severity,
                required=False,
                mode="auto",
                status="approved",
                route="auto-deploy",
                next_action="deploy",
                channel="auth0-rbac",
                decider="auth0:auto-deploy",
                reason="Low/medium severity matched the auto-deploy policy.",
                requires_phone_escalation=False,
                suggestion_allowed=False,
            )
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=True,
            mode="manual",
            status="approved",
            route="manual-approve",
            next_action="deploy",
            channel="auth0-rbac",
            decider="auth0:manual-approve",
            reason="Human approval granted for a higher-risk deployment.",
            requires_phone_escalation=requires_phone_escalation,
            suggestion_allowed=False,
        )

    if severity in _AUTO_APPROVE_SEVERITIES and not requires_phone_escalation:
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=False,
            mode="auto",
            status="approved",
            route="auto-deploy",
            next_action="deploy",
            channel="auth0-rbac",
            decider="auth0:auto-deploy",
            reason="Low/medium severity matched the auto-deploy policy.",
            requires_phone_escalation=False,
            suggestion_allowed=False,
        )

    if severity in _MANUAL_SEVERITIES or requires_phone_escalation:
        return ApprovalPolicyDecision(
            incident_id=incident_id,
            severity=severity,
            required=True,
            mode="manual",
            status=APPROVAL_PENDING,
            route="phone-escalation" if requires_phone_escalation else "manual-review",
            next_action="call_human" if requires_phone_escalation else "await_human",
            channel="auth0-rbac",
            decider="auth0:phone-escalation" if requires_phone_escalation else "auth0:manual-approve",
            reason="Risk is too high for silent auto-deploy." if requires_phone_escalation else "Human approval is required before deployment.",
            requires_phone_escalation=requires_phone_escalation,
            suggestion_allowed=True,
        )

    return ApprovalPolicyDecision(
        incident_id=incident_id,
        severity=severity,
        required=True,
        mode="manual",
        status=APPROVAL_PENDING,
        route="manual-review",
        next_action="await_human",
        channel="auth0-rbac",
        decider="auth0:manual-review",
        reason="Approval policy could not confirm a safe auto-deploy path.",
        requires_phone_escalation=requires_phone_escalation,
        suggestion_allowed=True,
    )


def build_approval_patch(
    incident: Mapping[str, Any],
    human_instruction: Any = None,
    *,
    notes: str | None = None,
    bland_call_id: str | None = None,
    decision_at_ms: int | None = None,
) -> dict[str, Any]:
    decision = evaluate_approval_policy(incident, human_instruction)
    return decision.to_approval_patch(
        notes=notes,
        bland_call_id=bland_call_id,
        decision_at_ms=decision_at_ms,
    )
