"""Tests for prompt building and response parsing."""

import json

import pytest

from agent.prompts import (
    build_diagnosis_prompt,
    build_unknown_error_prompt,
    parse_diagnosis_response,
    DiagnosisParseError,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

VALID_DIAGNOSIS_JSON = json.dumps({
    "root_cause": "Division by zero when b parameter is 0",
    "suggested_fix": "Add a guard clause to check b != 0 before dividing",
    "affected_components": ["demo-app/main.py", "/calculate endpoint"],
    "confidence": 0.92,
    "severity_reasoning": "Medium severity: only affects the calculate endpoint",
})

FIXTURE_INCIDENT = {
    "source": {
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero",
        "source_file": "demo-app/main.py",
        "path": "/calculate/0",
    },
    "severity": "medium",
}


# ---------------------------------------------------------------------------
# parse_diagnosis_response tests
# ---------------------------------------------------------------------------


class TestParseDiagnosisResponse:
    """Tests for parse_diagnosis_response."""

    def test_parse_valid_json(self):
        result = parse_diagnosis_response(VALID_DIAGNOSIS_JSON)
        assert isinstance(result, dict)
        assert result["root_cause"] == "Division by zero when b parameter is 0"
        assert result["suggested_fix"] == "Add a guard clause to check b != 0 before dividing"
        assert isinstance(result["affected_components"], list)
        assert len(result["affected_components"]) == 2
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_parse_json_in_markdown_fences(self):
        wrapped = f"```json\n{VALID_DIAGNOSIS_JSON}\n```"
        result = parse_diagnosis_response(wrapped)
        assert result["root_cause"] == "Division by zero when b parameter is 0"
        assert isinstance(result["affected_components"], list)

    def test_parse_json_in_plain_fences(self):
        wrapped = f"```\n{VALID_DIAGNOSIS_JSON}\n```"
        result = parse_diagnosis_response(wrapped)
        assert result["root_cause"] == "Division by zero when b parameter is 0"

    def test_parse_missing_required_field(self):
        incomplete = json.dumps({
            "suggested_fix": "Add a check",
            "affected_components": [],
            "confidence": 0.5,
        })
        with pytest.raises(DiagnosisParseError):
            parse_diagnosis_response(incomplete)

    def test_parse_invalid_json(self):
        with pytest.raises(DiagnosisParseError):
            parse_diagnosis_response("this is not json at all!!!")

    def test_parse_normalizes_confidence(self):
        data = {
            "root_cause": "Some cause",
            "suggested_fix": "Some fix",
            "affected_components": ["file.py"],
            "confidence": 1,  # int, not float
        }
        result = parse_diagnosis_response(json.dumps(data))
        assert isinstance(result["confidence"], float)
        assert result["confidence"] == 1.0


# ---------------------------------------------------------------------------
# Prompt building tests
# ---------------------------------------------------------------------------


class TestBuildDiagnosisPrompt:
    """Tests for build_diagnosis_prompt."""

    def test_build_diagnosis_prompt_contains_error_info(self):
        macroscope_ctx = "The calculate function performs integer division."
        prompt = build_diagnosis_prompt(FIXTURE_INCIDENT, macroscope_ctx)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # The prompt should reference the error details from the incident
        assert "division by zero" in prompt.lower() or "ZeroDivisionError" in prompt
        # The prompt should reference the path or file
        assert "main.py" in prompt or "/calculate" in prompt or "calculate" in prompt


class TestBuildUnknownErrorPrompt:
    """Tests for build_unknown_error_prompt."""

    def test_build_unknown_error_prompt(self):
        macroscope_ctx = "Some codebase context."
        prompt = build_unknown_error_prompt(FIXTURE_INCIDENT, macroscope_ctx)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should contain guardrail language indicating caution / unknown error handling
        # Check for at least one of several reasonable guardrail terms
        prompt_lower = prompt.lower()
        guardrail_terms = [
            "unknown",
            "uncertain",
            "caution",
            "careful",
            "not enough information",
            "confidence",
            "unsure",
            "cannot determine",
            "limited",
            "best effort",
        ]
        assert any(
            term in prompt_lower for term in guardrail_terms
        ), f"Prompt should contain guardrail language, got: {prompt[:200]}"
