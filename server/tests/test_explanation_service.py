"""Tests for the explanation service."""

import pytest

from server.services.explanation_service import (
    build_approval_explanation,
    build_call_script,
    build_follow_up_questions,
    build_phone_explanation,
    build_short_explanation,
)

FIXTURE_INCIDENT = {
    "incident_id": "inc-test-001",
    "severity": "high",
    "source": {
        "provider": "demo-app",
        "path": "/user/unknown",
        "error_type": "KeyError",
        "error_message": "'name'",
        "source_file": "demo-app/main.py",
    },
    "diagnosis": {
        "status": "complete",
        "root_cause": "Null reference when accessing non-existent user. users.get() returns None, then ['name'] fails.",
        "suggested_fix": "Add null check: if not user: raise HTTPException(404, 'User not found')",
        "affected_components": ["demo-app/main.py", "/user endpoint"],
        "confidence": 0.93,
        "severity_reasoning": "User-facing 500 error on any invalid username lookup.",
    },
    "fix": {
        "status": "complete",
        "diff_preview": "+    if not user:\n+        raise HTTPException(404, 'User not found')",
        "files_changed": ["demo-app/main.py"],
        "test_plan": ["Call /user/unknown and confirm 404", "Call /user/valid and confirm success"],
    },
}

CRITICAL_INCIDENT = {**FIXTURE_INCIDENT, "severity": "critical", "incident_id": "inc-test-002"}


class TestBuildApprovalExplanation:
    def test_has_all_fields(self):
        result = build_approval_explanation(FIXTURE_INCIDENT)
        for key in ("summary", "what_broke", "what_we_want_to_do",
                     "why_approval_needed", "blast_radius", "if_we_proceed",
                     "if_we_dont", "severity", "confidence", "incident_id"):
            assert key in result, f"Missing key: {key}"

    def test_references_error(self):
        result = build_approval_explanation(FIXTURE_INCIDENT)
        assert "KeyError" in result["what_broke"]

    def test_references_fix(self):
        result = build_approval_explanation(FIXTURE_INCIDENT)
        assert "null check" in result["what_we_want_to_do"].lower() or "HTTPException" in result["what_we_want_to_do"]


class TestBuildShortExplanation:
    def test_is_compact(self):
        text = build_short_explanation(FIXTURE_INCIDENT)
        assert len(text) <= 300

    def test_mentions_error(self):
        text = build_short_explanation(FIXTURE_INCIDENT)
        assert "KeyError" in text


class TestBuildPhoneExplanation:
    def test_no_code_jargon(self):
        text = build_phone_explanation(FIXTURE_INCIDENT)
        assert "`" not in text
        assert "```" not in text


class TestBuildCallScript:
    def test_critical_urgency(self):
        script = build_call_script(CRITICAL_INCIDENT)
        assert "urgent" in script["greeting"].lower()

    def test_high_professional(self):
        script = build_call_script(FIXTURE_INCIDENT)
        assert "urgent" not in script["greeting"].lower()
        assert "approval" in script["greeting"].lower() or "incident" in script["greeting"].lower()

    def test_has_all_parts(self):
        script = build_call_script(FIXTURE_INCIDENT)
        for key in ("greeting", "incident_explanation", "proposed_action",
                     "ask_for_decision", "follow_up_if_unclear",
                     "follow_up_if_away_from_computer", "closing", "full_script"):
            assert key in script, f"Missing key: {key}"


class TestBuildFollowUpQuestions:
    def test_non_empty(self):
        questions = build_follow_up_questions(FIXTURE_INCIDENT)
        assert len(questions) >= 2
        assert all(isinstance(q, str) and len(q) > 0 for q in questions)
