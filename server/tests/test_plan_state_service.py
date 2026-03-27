from __future__ import annotations

import json

from server.services.plan_state_service import (
    build_plan_state_mutation,
    build_plan_notes,
    build_plan_snapshot,
    build_plan_timeline_event,
    create_execution_plan,
    extract_latest_plan_snapshot,
    revise_execution_plan,
)


def _plan():
    return create_execution_plan(
        title="Fix zero division path",
        summary="Add a guard before division and keep the endpoint stable.",
        source="autonomous",
        requested_by="codex",
        requested_via="backend",
        target_stage="deploying",
        steps=["Check divisor", "Return handled response", "Verify /calculate/0"],
        constraints=["Do not change unrelated endpoints", "Keep patch minimal"],
        instruction_text="Patch only the division path and keep the hotfix small.",
    )


def test_create_execution_plan_normalizes_inputs():
    plan = create_execution_plan(
        title="  Fix zero division path  ",
        summary="  Add a guard before division.  ",
        source="autonomous",
        requested_by="codex",
        requested_via="backend",
        target_stage="deploying",
        steps=["  Check divisor  ", "Check divisor", ""],
        constraints=["  Keep patch minimal  ", "Keep patch minimal"],
    )

    assert plan.title == "Fix zero division path"
    assert plan.summary == "Add a guard before division."
    assert plan.steps == ("Check divisor",)
    assert plan.constraints == ("Keep patch minimal",)
    assert plan.revision == 1
    assert plan.parent_plan_id is None


def test_build_plan_notes_contains_structured_sections():
    notes = build_plan_notes(_plan())

    assert "Execution Plan" in notes
    assert "Plan ID" in notes
    assert "Summary" in notes
    assert "Human Instruction" in notes
    assert "Steps" in notes
    assert "Constraints" in notes


def test_build_plan_snapshot_is_serializable():
    snapshot = build_plan_snapshot(_plan())
    json.dumps(snapshot)
    assert snapshot["source"] == "autonomous"
    assert snapshot["target_stage"] == "deploying"
    assert snapshot["revision"] == 1


def test_build_plan_state_mutation_uses_canonical_safe_patch():
    plan = _plan()
    mutation = build_plan_state_mutation(
        plan,
        actor="codex",
        sponsor="Auth0",
        incident_status="gating",
        message="Waiting on plan approval.",
        approval_patch={"required": True, "mode": "manual", "status": "pending"},
        extra_metadata={"revision_reason": "human suggested a safer hotfix"},
    )

    assert set(mutation.patch.keys()) == {"approval"}
    assert mutation.patch["approval"]["required"] is True
    assert mutation.patch["approval"]["mode"] == "manual"
    assert "notes" in mutation.patch["approval"]
    assert mutation.timeline_event["status"] == "gating"
    assert mutation.timeline_event["metadata"]["plan_state"]["plan_id"] == plan.plan_id
    assert mutation.timeline_event["metadata"]["revision_reason"] == "human suggested a safer hotfix"


def test_revise_execution_plan_links_parent_and_increments_revision():
    previous = _plan()
    revised = revise_execution_plan(
        previous,
        summary="Patch only the division path and leave other endpoints untouched.",
        instruction_text="Use the smallest possible patch.",
        state="approved",
    )

    assert revised.parent_plan_id == previous.plan_id
    assert revised.revision == previous.revision + 1
    assert revised.state == "approved"
    assert revised.instruction_text == "Use the smallest possible patch."


def test_extract_latest_plan_snapshot_prefers_most_recent_revision():
    first = _plan()
    second = revise_execution_plan(first, state="approved")
    incident = {
        "timeline": [
            build_plan_timeline_event(
                first,
                actor="codex",
                sponsor="Auth0",
                message="Initial plan recorded.",
                incident_status="gating",
                at_ms=1,
            ),
            build_plan_timeline_event(
                second,
                actor="codex",
                sponsor="Auth0",
                message="Revised plan recorded.",
                incident_status="gating",
                at_ms=2,
            ),
        ]
    }

    snapshot = extract_latest_plan_snapshot(incident)
    assert snapshot is not None
    assert snapshot["plan_id"] == second.plan_id
    assert snapshot["revision"] == second.revision
