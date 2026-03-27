"""Tests for the decision parser service."""

from __future__ import annotations

from server.services.decision_parser import (
    parse_human_decision,
    parse_transcript_to_actions,
)


# ---------------------------------------------------------------------------
# parse_human_decision tests
# ---------------------------------------------------------------------------


def test_parse_approve():
    result = parse_human_decision("Yes, go ahead")
    assert result["decision"] == "approve"


def test_parse_reject():
    result = parse_human_decision("No, don't deploy")
    assert result["decision"] == "reject"


def test_parse_revise():
    result = parse_human_decision("Can you try a different approach?")
    assert result["decision"] == "revise"


def test_parse_suggest():
    result = parse_human_decision("Try fixing the validation instead")
    assert result["decision"] == "suggest"


def test_parse_defer():
    result = parse_human_decision("Let me check and get back to you")
    assert result["decision"] == "defer"


def test_parse_ask_context():
    result = parse_human_decision("Can you show me the diff?")
    assert result["decision"] == "ask_context"


def test_parse_empty_input():
    result = parse_human_decision("")
    assert result["decision"] == "no_answer"
    assert result["confidence"] == 1.0


def test_parse_approve_with_constraint():
    result = parse_human_decision("Go ahead but avoid the auth module")
    assert result["decision"] == "approve"
    assert any("auth module" in c for c in result["constraints"])


def test_parse_hotfix_only():
    result = parse_human_decision("Just do a hotfix")
    assert result["decision"] == "approve"
    assert any("hotfix" in c for c in result["constraints"])


# ---------------------------------------------------------------------------
# Constraint and reference extraction tests
# ---------------------------------------------------------------------------


def test_extract_constraints_dont_touch():
    result = parse_transcript_to_actions("Go ahead but don't touch auth.py")
    assert result["primary_action"] == "approve"
    assert any("auth.py" in c for c in result["constraints"])


def test_extract_file_references():
    result = parse_transcript_to_actions(
        "Please fix main.py and also check utils.js"
    )
    assert "main.py" in result["mentioned_files"]


def test_extract_people_references():
    result = parse_transcript_to_actions("Ask Sarah about this before deploying")
    assert "Sarah" in result["mentioned_people"]


# ---------------------------------------------------------------------------
# Transcript format tests
# ---------------------------------------------------------------------------


def test_transcript_list_format():
    transcript = [
        {"speaker": "agent", "text": "We found a bug in auth. Should we deploy the fix?"},
        {"speaker": "human", "text": "Yes go ahead and deploy it."},
    ]
    result = parse_transcript_to_actions(transcript)
    assert result["primary_action"] == "approve"
    assert result["confidence"] > 0.5


# ---------------------------------------------------------------------------
# Confidence level tests
# ---------------------------------------------------------------------------


def test_confidence_high_for_clear_input():
    result = parse_human_decision("yes deploy now")
    assert result["confidence"] > 0.8


def test_confidence_low_for_ambiguous_input():
    result = parse_human_decision("hmm maybe")
    assert result["confidence"] < 0.5


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_none_text_treated_as_no_answer():
    # Passing None should not crash; treated as empty.
    result = parse_human_decision(None)
    assert result["decision"] == "no_answer"


def test_whitespace_only_treated_as_no_answer():
    result = parse_human_decision("   \n\t  ")
    assert result["decision"] == "no_answer"


def test_source_is_preserved():
    result = parse_human_decision("yes", source="phone")
    assert result["source"] == "phone"


def test_raw_input_is_preserved():
    original = "Ship it to prod right now!"
    result = parse_human_decision(original)
    assert result["raw_input"] == original


def test_urgency_immediate():
    result = parse_transcript_to_actions("Deploy now, this is urgent!")
    assert result["urgency"] == "immediate"


def test_urgency_deferred():
    result = parse_transcript_to_actions("No rush, do it tomorrow")
    assert result["urgency"] == "deferred"


def test_reject_overrides_suggestion():
    # "No" + suggestions should still classify as reject
    result = parse_human_decision("No, and maybe try something else")
    assert result["decision"] == "reject"


def test_staging_constraint():
    result = parse_human_decision("Go ahead but deploy to staging first")
    assert result["decision"] == "approve"
    assert any("staging" in c for c in result["constraints"])


def test_rollback_constraint():
    result = parse_human_decision("Approve, but roll back if it fails")
    assert result["decision"] == "approve"
    assert any("rollback" in c for c in result["constraints"])


def test_escalation_with_defer():
    result = parse_transcript_to_actions("Ask Sarah instead, I'm not sure")
    assert result["primary_action"] == "defer"
    assert "Sarah" in result["mentioned_people"]
