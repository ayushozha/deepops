from __future__ import annotations

from agent.contracts import (
    APPROVAL_PENDING,
    STATUS_BLOCKED,
    STATUS_DEPLOYING,
    STATUS_DIAGNOSING,
    STATUS_FIXING,
    STATUS_GATING,
    STATUS_RESOLVED,
    STATUS_STORED,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    default_incident,
)
from server.services.flow_router import (
    FLOW_APPROVAL,
    FLOW_AUTONOMOUS,
    FLOW_ESCALATION,
    FLOW_FOLLOW_UP,
    FLOW_REPLAN,
    MODE_APPROVAL,
    MODE_AUTONOMOUS,
    MODE_ESCALATION,
    MODE_FOLLOW_UP,
    MODE_REPLAN,
    route_incident,
)


def _incident(**patch):
    incident = default_incident()
    incident.update(patch)
    return incident


def test_autonomous_from_stored_moves_to_diagnosis():
    decision = route_incident(
        _incident(
            status=STATUS_STORED,
            severity=SEVERITY_LOW,
        )
    )
    assert decision.action == FLOW_AUTONOMOUS
    assert decision.mode == MODE_AUTONOMOUS
    assert decision.next_status == STATUS_DIAGNOSING


def test_autonomous_from_fixing_continues_fix_work():
    decision = route_incident(
        _incident(
            status=STATUS_FIXING,
            severity=SEVERITY_MEDIUM,
            fix={"status": "pending"},
        )
    )
    assert decision.action == FLOW_AUTONOMOUS
    assert decision.next_status == STATUS_FIXING


def test_requires_approval_when_gating_and_pending():
    decision = route_incident(
        _incident(
            status=STATUS_GATING,
            severity=SEVERITY_HIGH,
            approval={"required": True, "status": APPROVAL_PENDING, "mode": "manual"},
        )
    )
    assert decision.action == FLOW_APPROVAL
    assert decision.mode == MODE_APPROVAL
    assert decision.next_status == "awaiting_approval"
    assert decision.requires_human is True


def test_requires_phone_escalation_for_critical():
    decision = route_incident(
        _incident(
            status=STATUS_GATING,
            severity=SEVERITY_CRITICAL,
            approval={"required": True, "status": APPROVAL_PENDING, "mode": "manual"},
        )
    )
    assert decision.action == FLOW_ESCALATION
    assert decision.mode == MODE_ESCALATION
    assert decision.should_call_human is True
    assert decision.next_status == "awaiting_approval"


def test_replan_when_human_suggests_change():
    decision = route_incident(
        _incident(
            status=STATUS_GATING,
            severity=SEVERITY_HIGH,
            approval={
                "required": True,
                "status": APPROVAL_PENDING,
                "mode": "suggested",
                "notes": "Keep the auth layer unchanged and patch only the endpoint.",
            },
        )
    )
    assert decision.action == FLOW_REPLAN
    assert decision.mode == MODE_REPLAN
    assert decision.next_status == STATUS_DIAGNOSING
    assert decision.requires_human is True


def test_follow_up_for_blocked_or_resolved_incidents():
    blocked = route_incident(
        _incident(
            status=STATUS_BLOCKED,
            severity=SEVERITY_HIGH,
        )
    )
    resolved = route_incident(
        _incident(
            status=STATUS_RESOLVED,
            severity=SEVERITY_LOW,
            deployment={"status": STATUS_RESOLVED},
        )
    )
    assert blocked.action == FLOW_FOLLOW_UP
    assert blocked.mode == MODE_FOLLOW_UP
    assert resolved.action == FLOW_FOLLOW_UP
    assert resolved.mode == MODE_FOLLOW_UP


def test_approval_then_deploy_is_autonomous_continue():
    decision = route_incident(
        _incident(
            status=STATUS_GATING,
            severity=SEVERITY_MEDIUM,
            approval={"required": False, "status": "approved", "mode": "auto"},
            deployment={"status": "pending"},
        )
    )
    assert decision.action == FLOW_AUTONOMOUS
    assert decision.mode == MODE_AUTONOMOUS
    assert decision.next_status == STATUS_DEPLOYING
