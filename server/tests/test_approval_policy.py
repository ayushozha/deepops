from __future__ import annotations

from server.services.approval_policy import (
    ApprovalPolicyDecision,
    build_approval_patch,
    classify_human_instruction,
    evaluate_approval_policy,
    normalize_severity,
)


def _incident(*, severity: str, error_message: str = "division by zero", extra: dict | None = None) -> dict:
    incident = {
        "incident_id": "inc-123",
        "severity": severity,
        "source": {
            "error_message": error_message,
            "path": "/calculate/0",
            "provider": "demo-app",
        },
        "diagnosis": {
            "root_cause": "guard missing",
            "severity_reasoning": "risk is localized",
        },
    }
    if extra:
        incident.update(extra)
    return incident


def test_normalize_severity_defaults_to_pending() -> None:
    assert normalize_severity(None) == "pending"
    assert normalize_severity("MEDIUM") == "medium"
    assert normalize_severity("unexpected") == "pending"


def test_classify_human_instruction_covers_core_intents() -> None:
    assert classify_human_instruction("Please approve this") == "approve"
    assert classify_human_instruction("No, reject it") == "reject"
    assert classify_human_instruction("Suggest a feature flag instead") == "replan"
    assert classify_human_instruction("Need more information first") == "clarify"
    assert classify_human_instruction("") == "unknown"


def test_low_severity_auto_approves() -> None:
    decision = evaluate_approval_policy(_incident(severity="low"))
    assert decision.required is False
    assert decision.mode == "auto"
    assert decision.status == "approved"
    assert decision.route == "auto-deploy"
    assert decision.decider == "auth0:auto-deploy"
    assert decision.requires_phone_escalation is False


def test_medium_severity_auto_approves() -> None:
    decision = evaluate_approval_policy(_incident(severity="medium"))
    assert decision.status == "approved"
    assert decision.next_action == "deploy"


def test_high_severity_requires_manual_and_phone_escalation() -> None:
    decision = evaluate_approval_policy(_incident(severity="high"))
    assert decision.required is True
    assert decision.mode == "manual"
    assert decision.status == "pending"
    assert decision.route == "phone-escalation"
    assert decision.next_action == "call_human"
    assert decision.requires_phone_escalation is True


def test_critical_severity_requires_manual_and_phone_escalation() -> None:
    decision = evaluate_approval_policy(_incident(severity="critical"))
    assert decision.route == "phone-escalation"
    assert decision.requires_phone_escalation is True


def test_high_impact_keywords_trigger_phone_escalation() -> None:
    decision = evaluate_approval_policy(
        _incident(
            severity="low",
            error_message="Payment outage causing revenue impact across production",
        )
    )
    assert decision.requires_phone_escalation is True
    assert decision.route == "phone-escalation"


def test_human_suggestion_routes_to_replan() -> None:
    decision = evaluate_approval_policy(_incident(severity="medium"), "Suggest a feature flag and replan")
    assert decision.status == "pending"
    assert decision.route == "replan"
    assert decision.next_action == "replan"
    assert decision.suggestion_allowed is True


def test_human_rejection_blocks() -> None:
    decision = evaluate_approval_policy(_incident(severity="critical"), "Reject the plan")
    assert decision.status == "rejected"
    assert decision.route == "blocked"
    assert decision.next_action == "block"


def test_human_approval_overrides_manual_gate() -> None:
    decision = evaluate_approval_policy(_incident(severity="critical"), "Approve and continue")
    assert decision.status == "approved"
    assert decision.mode == "manual"
    assert decision.next_action == "deploy"


def test_build_approval_patch_is_schema_safe() -> None:
    patch = build_approval_patch(_incident(severity="medium"), notes="ok", decision_at_ms=123)
    assert patch == {
        "required": False,
        "mode": "auto",
        "status": "approved",
        "channel": "auth0-rbac",
        "decider": "auth0:auto-deploy",
        "bland_call_id": None,
        "notes": "ok",
        "decision_at_ms": 123,
    }


def test_decision_patch_supports_manual_flow() -> None:
    decision = evaluate_approval_policy(_incident(severity="critical"))
    assert isinstance(decision, ApprovalPolicyDecision)
    patch = decision.to_approval_patch(bland_call_id="call-123")
    assert patch["bland_call_id"] == "call-123"
