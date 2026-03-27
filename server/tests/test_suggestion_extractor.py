"""Tests for the suggestion extraction service."""

from __future__ import annotations

import time

import pytest

from server.services.suggestion_extractor import (
    build_replan_packet,
    extract_file_guidance,
    extract_safety_requirements,
    extract_scope_limits,
    extract_suggestions,
    extract_urgency,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_INCIDENT: dict = {
    "incident_id": "inc-test-001",
    "severity": "high",
    "source": {
        "path": "/user/unknown",
        "error_type": "KeyError",
        "error_message": "'name'",
        "source_file": "demo-app/main.py",
    },
    "diagnosis": {
        "root_cause": "Null reference on missing user",
        "suggested_fix": "Add null check",
        "affected_components": ["demo-app/main.py"],
        "confidence": 0.93,
    },
}


# ---------------------------------------------------------------------------
# File guidance tests
# ---------------------------------------------------------------------------


def test_extract_files_to_avoid():
    """'don't touch auth.py' should yield files_to_avoid: ['auth.py']."""
    result = extract_suggestions("don't touch auth.py")
    assert "auth.py" in result["files_to_avoid"]


def test_extract_files_to_target():
    """'focus on main.py' should yield files_to_target: ['main.py']."""
    result = extract_suggestions("focus on main.py")
    assert "main.py" in result["files_to_target"]


# ---------------------------------------------------------------------------
# Scope tests
# ---------------------------------------------------------------------------


def test_extract_scope_hotfix():
    """'just do a hotfix' should include 'hotfix' in scope_limits."""
    result = extract_suggestions("just do a hotfix")
    assert any("hotfix" in s for s in result["scope_limits"])


def test_extract_scope_minimal():
    """'keep it simple' should include 'minimal' in scope_limits."""
    result = extract_suggestions("keep it simple")
    assert any("minimal" in s for s in result["scope_limits"])


# ---------------------------------------------------------------------------
# Urgency tests
# ---------------------------------------------------------------------------


def test_extract_urgency_immediate():
    """'do it now' should map to urgency 'immediate'."""
    assert extract_urgency("do it now") == "immediate"


def test_extract_urgency_low():
    """'no rush' should map to urgency 'low'."""
    assert extract_urgency("no rush") == "low"


def test_extract_urgency_default():
    """'fix the bug' should default to urgency 'normal'."""
    assert extract_urgency("fix the bug") == "normal"


# ---------------------------------------------------------------------------
# Safety tests
# ---------------------------------------------------------------------------


def test_extract_safety_dont_break():
    """'don't break the login' should include 'login' in safety."""
    reqs = extract_safety_requirements("don't break the login")
    assert any("login" in r for r in reqs)


def test_extract_safety_backward_compat():
    """'keep it backward compatible' should include 'backward compatible'."""
    reqs = extract_safety_requirements("keep it backward compatible")
    assert any("backward compatible" in r for r in reqs)


# ---------------------------------------------------------------------------
# Re-plan packet tests
# ---------------------------------------------------------------------------


def test_build_replan_packet_has_required_fields():
    """Re-plan packet must contain all documented fields."""
    packet = build_replan_packet(
        "focus on main.py and don't touch auth.py",
        FIXTURE_INCIDENT,
    )
    required_keys = {
        "incident_id",
        "revised_intent",
        "original_diagnosis",
        "original_fix",
        "extracted_constraints",
        "inferred_urgency",
        "plan_notes",
        "interpretation_confidence",
        "source",
        "timestamp_ms",
    }
    assert required_keys.issubset(packet.keys())


def test_build_replan_packet_includes_constraints():
    """Constraints extracted from input must appear in the packet."""
    packet = build_replan_packet(
        "don't touch auth.py and focus on main.py",
        FIXTURE_INCIDENT,
    )
    constraints = packet["extracted_constraints"]
    assert "auth.py" in constraints["files_to_avoid"]
    assert "main.py" in constraints["files_to_target"]


def test_build_replan_packet_plan_notes_non_empty():
    """plan_notes must have at least 1 item."""
    packet = build_replan_packet(
        "just do a hotfix, don't break the login",
        FIXTURE_INCIDENT,
    )
    assert len(packet["plan_notes"]) >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_extract_suggestions_empty_input():
    """Empty string should return sensible defaults without errors."""
    result = extract_suggestions("")
    assert result["files_to_avoid"] == []
    assert result["files_to_target"] == []
    assert result["scope_limits"] == []
    assert result["urgency"] == "normal"
    assert result["safety_requirements"] == []
    assert result["rollback_expectations"] is None
    assert result["deployment_constraints"] == []
    assert result["raw_suggestions"] == []
    assert result["confidence"] == 0.0


def test_extract_rollback_expectation():
    """'roll back if it fails' should set rollback_expectations."""
    result = extract_suggestions("roll back if it fails")
    assert result["rollback_expectations"] is not None
    assert "roll back" in result["rollback_expectations"].lower()
