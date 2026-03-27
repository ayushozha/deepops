"""Tests for the main diagnosis orchestrator."""

import json
import os

import pytest

from agent.diagnoser import run_diagnosis, get_diagnosis_metadata


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------

def _make_llm_response(
    root_cause="Division by zero when b is 0",
    suggested_fix="Add guard clause for b == 0",
    affected_components=None,
    confidence=0.9,
    severity_reasoning="Medium severity",
):
    """Build a JSON string that parse_diagnosis_response can handle."""
    if affected_components is None:
        affected_components = ["demo-app/main.py"]
    return json.dumps({
        "root_cause": root_cause,
        "suggested_fix": suggested_fix,
        "affected_components": affected_components,
        "confidence": confidence,
        "severity_reasoning": severity_reasoning,
    })


_DEMO_LLM_RESPONSES = {
    "ZeroDivisionError": _make_llm_response(
        root_cause="Division by zero when b parameter is 0",
        suggested_fix="Add a guard clause to check b != 0 before dividing",
        affected_components=["demo-app/main.py", "/calculate endpoint"],
        confidence=0.92,
        severity_reasoning="Medium: only the calculate endpoint is affected",
    ),
    "KeyError": _make_llm_response(
        root_cause="KeyError 'name' because users.get() returns None for unknown usernames",
        suggested_fix="Check for None before accessing ['name'] and return 404",
        affected_components=["demo-app/main.py", "/user endpoint"],
        confidence=0.95,
        severity_reasoning="High: any caller can trigger a 500 error",
    ),
    "TimeoutError": _make_llm_response(
        root_cause="Blocking time.sleep(5) in async handler causes event loop stall",
        suggested_fix="Replace time.sleep with await asyncio.sleep or remove the delay",
        affected_components=["demo-app/main.py", "/search endpoint"],
        confidence=0.88,
        severity_reasoning="Critical: blocks the entire event loop",
    ),
}

# Inline fallback incidents in case the fixtures file doesn't exist yet
_FALLBACK_INCIDENTS = [
    {
        "id": "inc-001",
        "trigger": {
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "file": "demo-app/main.py",
            "function": "calculate",
            "path": "/calculate/0",
        },
        "severity": "medium",
    },
    {
        "id": "inc-002",
        "trigger": {
            "error_type": "KeyError",
            "error_message": "'name'",
            "file": "demo-app/main.py",
            "function": "get_user",
            "path": "/user/unknown",
        },
        "severity": "high",
    },
    {
        "id": "inc-003",
        "trigger": {
            "error_type": "TimeoutError",
            "error_message": "search endpoint timed out",
            "file": "demo-app/main.py",
            "function": "search",
            "path": "/search",
        },
        "severity": "critical",
    },
]


def _load_incidents():
    """Load incidents from fixtures file, falling back to inline data."""
    try:
        return load_fixture("incidents.json")
    except (FileNotFoundError, json.JSONDecodeError):
        return _FALLBACK_INCIDENTS


# Schema fields that every diagnosis result must contain
SCHEMA_FIELDS = {
    "status",
    "root_cause",
    "suggested_fix",
    "affected_components",
    "confidence",
    "severity_reasoning",
    "macroscope_context",
    "started_at_ms",
    "completed_at_ms",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunDiagnosisWithMockLLM:
    """Core integration test: mock LLM returns valid JSON."""

    def test_run_diagnosis_with_mock_llm(self):
        incident = _FALLBACK_INCIDENTS[0]

        def mock_llm(prompt):
            return _DEMO_LLM_RESPONSES["ZeroDivisionError"]

        result = run_diagnosis(incident, llm_caller=mock_llm)

        assert result["status"] == "complete"
        assert result["root_cause"] is not None
        assert result["suggested_fix"] is not None
        assert isinstance(result["affected_components"], list)
        assert isinstance(result["confidence"], float)
        assert result["started_at_ms"] is not None
        assert result["completed_at_ms"] is not None
        assert result["completed_at_ms"] >= result["started_at_ms"]


class TestSchemaFields:
    """Verify the returned dict has exactly the expected schema fields."""

    def test_run_diagnosis_returns_schema_fields(self):
        incident = _FALLBACK_INCIDENTS[0]

        def mock_llm(prompt):
            return _DEMO_LLM_RESPONSES["ZeroDivisionError"]

        result = run_diagnosis(incident, llm_caller=mock_llm)
        assert set(result.keys()) == SCHEMA_FIELDS


class TestDiagnosisFailure:
    """Verify graceful failure when the LLM call raises."""

    def test_run_diagnosis_failure_returns_failed(self):
        incident = _FALLBACK_INCIDENTS[0]

        def exploding_llm(prompt):
            raise RuntimeError("LLM service unavailable")

        result = run_diagnosis(incident, llm_caller=exploding_llm)

        assert result["status"] == "failed"
        assert result["root_cause"] is None
        assert result["suggested_fix"] is None
        assert result["affected_components"] == []
        assert result["confidence"] == 0.0
        assert "Diagnosis failed" in result["severity_reasoning"]
        assert result["started_at_ms"] is not None
        assert result["completed_at_ms"] is not None


class TestDemoBugs:
    """Parametrized test over all 3 demo bug incidents."""

    @pytest.mark.parametrize(
        "incident_idx",
        [0, 1, 2],
        ids=["ZeroDivisionError", "KeyError", "TimeoutError"],
    )
    def test_run_diagnosis_for_each_demo_bug(self, incident_idx):
        incidents = _load_incidents()
        incident = incidents[incident_idx]
        error_type = incident.get("trigger", incident).get("error_type", "ZeroDivisionError")

        def mock_llm(prompt):
            return _DEMO_LLM_RESPONSES.get(error_type, _DEMO_LLM_RESPONSES["ZeroDivisionError"])

        result = run_diagnosis(incident, llm_caller=mock_llm)

        assert result["status"] == "complete"
        assert set(result.keys()) == SCHEMA_FIELDS
        assert result["root_cause"] is not None
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0


class TestGetDiagnosisMetadata:
    """Verify metadata helper returns expected keys."""

    def test_get_diagnosis_metadata(self):
        incident = _FALLBACK_INCIDENTS[0]

        def mock_llm(prompt):
            return _DEMO_LLM_RESPONSES["ZeroDivisionError"]

        diagnosis = run_diagnosis(incident, llm_caller=mock_llm)
        metadata = get_diagnosis_metadata(diagnosis)

        expected_keys = {"token_count", "prompt_type", "fallback_used", "macroscope_mode", "duration_ms"}
        assert set(metadata.keys()) == expected_keys

        assert metadata["token_count"] is None  # placeholder
        assert metadata["prompt_type"] in ("standard", "unknown_error")
        assert isinstance(metadata["fallback_used"], bool)
        assert metadata["macroscope_mode"] in ("live", "fallback")
        assert isinstance(metadata["duration_ms"], int)
        assert metadata["duration_ms"] >= 0
