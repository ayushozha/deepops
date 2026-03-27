from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent.contracts import (
    APPROVAL_PENDING,
    STATUS_AWAITING_APPROVAL,
    STATUS_BLOCKED,
    STATUS_DEPLOYING,
    STATUS_DIAGNOSING,
    STATUS_FAILED,
    STATUS_FIXING,
    STATUS_GATING,
    STATUS_RESOLVED,
    STATUS_STORED,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
)


FLOW_AUTONOMOUS = "autonomous_continue"
FLOW_APPROVAL = "requires_approval"
FLOW_ESCALATION = "requires_phone_escalation"
FLOW_REPLAN = "replan_required"
FLOW_FOLLOW_UP = "deploy_or_blocked_follow_up"

MODE_AUTONOMOUS = "autonomous"
MODE_APPROVAL = "approval"
MODE_ESCALATION = "escalation"
MODE_REPLAN = "replan"
MODE_FOLLOW_UP = "follow_up"

SUGGESTION_MODES = {"suggested", "revision_requested", "replan", "suggestion"}
ESCALATION_MODES = {"voice_call", "phone", "escalation"}
APPROVAL_MODES = {"manual", "approval"}
TERMINAL_STATUSES = {STATUS_BLOCKED, STATUS_RESOLVED, STATUS_FAILED}
FOLLOW_UP_DEPLOYMENT_STATUSES = {STATUS_DEPLOYING, STATUS_BLOCKED, STATUS_RESOLVED}


@dataclass(frozen=True)
class FlowDecision:
    action: str
    mode: str
    reason: str
    next_status: str | None
    requires_human: bool = False
    should_call_human: bool = False


def route_incident(incident: Mapping[str, Any]) -> FlowDecision:
    """Return the next demo-flow action for an incident.

    The router is intentionally pure and only inspects canonical incident fields.
    It does not mutate state, emit events, or depend on framework objects.
    """
    status = str(incident.get("status", STATUS_STORED))
    severity = str(incident.get("severity", "pending"))
    approval = _as_mapping(incident.get("approval"))
    deployment = _as_mapping(incident.get("deployment"))
    diagnosis = _as_mapping(incident.get("diagnosis"))
    fix = _as_mapping(incident.get("fix"))

    if _needs_follow_up(status, deployment):
        return FlowDecision(
            action=FLOW_FOLLOW_UP,
            mode=MODE_FOLLOW_UP,
            reason=_follow_up_reason(status, deployment),
            next_status=status,
        )

    if _needs_replan(approval, diagnosis, fix):
        return FlowDecision(
            action=FLOW_REPLAN,
            mode=MODE_REPLAN,
            reason=_replan_reason(approval),
            next_status=STATUS_DIAGNOSING,
            requires_human=True,
        )

    if _needs_phone_escalation(severity, approval):
        return FlowDecision(
            action=FLOW_ESCALATION,
            mode=MODE_ESCALATION,
            reason=_escalation_reason(severity, approval),
            next_status=STATUS_AWAITING_APPROVAL,
            requires_human=True,
            should_call_human=True,
        )

    if _needs_approval(status, approval):
        return FlowDecision(
            action=FLOW_APPROVAL,
            mode=MODE_APPROVAL,
            reason=_approval_reason(status, severity, approval),
            next_status=STATUS_AWAITING_APPROVAL,
            requires_human=True,
        )

    return FlowDecision(
        action=FLOW_AUTONOMOUS,
        mode=MODE_AUTONOMOUS,
        reason=_autonomous_reason(status, severity, diagnosis, fix, approval),
        next_status=_autonomous_next_status(status, diagnosis, fix, approval),
    )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _needs_follow_up(status: str, deployment: Mapping[str, Any]) -> bool:
    deployment_status = str(deployment.get("status", "") or "")
    return status in TERMINAL_STATUSES or deployment_status in FOLLOW_UP_DEPLOYMENT_STATUSES


def _needs_replan(
    approval: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    fix: Mapping[str, Any],
) -> bool:
    approval_mode = str(approval.get("mode", "") or "").strip().lower()
    approval_notes = str(approval.get("notes", "") or "").strip()
    diagnosis_status = str(diagnosis.get("status", "") or "")
    fix_status = str(fix.get("status", "") or "")

    if approval_mode in SUGGESTION_MODES:
        return True
    if approval_notes and approval_mode in {"manual", "approval"}:
        # Human supplied a change request through the approval channel.
        return True
    if diagnosis_status == "failed" or fix_status == "failed":
        return False
    return False


def _needs_phone_escalation(severity: str, approval: Mapping[str, Any]) -> bool:
    approval_channel = str(approval.get("channel", "") or "").strip().lower()
    approval_mode = str(approval.get("mode", "") or "").strip().lower()
    bland_call_id = str(approval.get("bland_call_id", "") or "").strip()

    if severity == SEVERITY_CRITICAL:
        return True
    if severity == SEVERITY_HIGH and (approval_channel in ESCALATION_MODES or approval_mode in ESCALATION_MODES or bland_call_id):
        return True
    if approval_channel in ESCALATION_MODES or approval_mode in ESCALATION_MODES or bland_call_id:
        return True
    return False


def _needs_approval(status: str, approval: Mapping[str, Any]) -> bool:
    approval_required = bool(approval.get("required", False))
    approval_status = str(approval.get("status", "") or "").strip().lower()
    approval_mode = str(approval.get("mode", "") or "").strip().lower()

    if status == STATUS_GATING and approval_status == APPROVAL_PENDING:
        return True
    if approval_required and approval_status == APPROVAL_PENDING:
        return True
    if approval_mode in APPROVAL_MODES and approval_status == APPROVAL_PENDING:
        return True
    return False


def _autonomous_next_status(
    status: str,
    diagnosis: Mapping[str, Any],
    fix: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> str | None:
    diagnosis_status = str(diagnosis.get("status", "") or "")
    fix_status = str(fix.get("status", "") or "")
    approval_status = str(approval.get("status", "") or "")

    if status == STATUS_STORED:
        return STATUS_DIAGNOSING
    if status == STATUS_DIAGNOSING and diagnosis_status != "complete":
        return STATUS_DIAGNOSING
    if status == STATUS_DIAGNOSING and diagnosis_status == "complete" and fix_status != "complete":
        return STATUS_FIXING
    if status == STATUS_FIXING and fix_status != "complete":
        return STATUS_FIXING
    if status == STATUS_GATING and approval_status == "approved":
        return STATUS_DEPLOYING
    if status == STATUS_GATING:
        return STATUS_GATING
    return None


def _follow_up_reason(status: str, deployment: Mapping[str, Any]) -> str:
    deployment_status = str(deployment.get("status", "") or "")
    if status in TERMINAL_STATUSES:
        return f"Incident is already in terminal state '{status}'."
    return f"Deployment status is '{deployment_status}', so the router is in post-deploy follow-up."


def _replan_reason(approval: Mapping[str, Any]) -> str:
    approval_mode = str(approval.get("mode", "") or "").strip().lower() or "unknown"
    notes = str(approval.get("notes", "") or "").strip()
    if notes:
        return f"Human suggestion captured in approval mode '{approval_mode}': {notes}"
    return f"Approval mode '{approval_mode}' requires the plan to be regenerated."


def _escalation_reason(severity: str, approval: Mapping[str, Any]) -> str:
    channel = str(approval.get("channel", "") or "").strip().lower()
    bland_call_id = str(approval.get("bland_call_id", "") or "").strip()
    if severity == SEVERITY_CRITICAL:
        return "Critical severity requires phone escalation."
    if bland_call_id:
        return f"Phone escalation already in progress via Bland call {bland_call_id}."
    return f"Approval channel '{channel or 'unknown'}' indicates phone escalation is required."


def _approval_reason(status: str, severity: str, approval: Mapping[str, Any]) -> str:
    if status == STATUS_GATING:
        return f"Incident is in gating with severity '{severity}', so human approval is pending."
    channel = str(approval.get("channel", "") or "").strip().lower()
    return f"Approval channel '{channel or 'manual'}' requires a human decision before continuing."


def _autonomous_reason(
    status: str,
    severity: str,
    diagnosis: Mapping[str, Any],
    fix: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> str:
    diagnosis_status = str(diagnosis.get("status", "") or "")
    fix_status = str(fix.get("status", "") or "")
    approval_required = bool(approval.get("required", False))

    if status == STATUS_STORED:
        return "Stored incident should move into diagnosis."
    if status == STATUS_DIAGNOSING and diagnosis_status != "complete":
        return "Diagnosis is still in progress."
    if status == STATUS_DIAGNOSING and diagnosis_status == "complete" and fix_status != "complete":
        return "Diagnosis is complete; continue into fix generation."
    if status == STATUS_FIXING and fix_status != "complete":
        return "Fix generation is still in progress."
    if status == STATUS_GATING and not approval_required:
        return f"Severity '{severity}' does not require human approval; continue to deployment."
    if status == STATUS_GATING and approval.get("status") == "approved":
        return "Approval is granted; continue to deployment."
    return "Incident can continue without human intervention."
