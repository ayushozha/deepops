"""
Tests for agent/fix_specs.py — deterministic markdown spec generator.
"""

import pytest

from agent.fix_specs import generate_fix_spec
from tests.fixtures.diagnoses import (
    BLOCKING_TIMEOUT_DIAGNOSIS,
    BLOCKING_TIMEOUT_INCIDENT,
    DIVIDE_BY_ZERO_DIAGNOSIS,
    DIVIDE_BY_ZERO_INCIDENT,
    MISSING_USER_DIAGNOSIS,
    MISSING_USER_INCIDENT,
)

REQUIRED_SECTIONS = [
    "## Requirements",
    "## Acceptance Criteria",
    "## Implementation Approach",
    "## Files to Inspect",
    "## Regression Risks",
]


# ---------------------------------------------------------------------------
# Content tests
# ---------------------------------------------------------------------------

def test_generate_spec_divide_by_zero():
    spec = generate_fix_spec(DIVIDE_BY_ZERO_DIAGNOSIS, DIVIDE_BY_ZERO_INCIDENT)
    lower = spec.lower()
    assert "zero" in lower or "division" in lower


def test_generate_spec_missing_user():
    spec = generate_fix_spec(MISSING_USER_DIAGNOSIS, MISSING_USER_INCIDENT)
    lower = spec.lower()
    assert "null" in lower or "user" in lower


def test_generate_spec_timeout():
    spec = generate_fix_spec(BLOCKING_TIMEOUT_DIAGNOSIS, BLOCKING_TIMEOUT_INCIDENT)
    lower = spec.lower()
    assert "timeout" in lower or "blocking" in lower


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_generate_spec_has_required_sections():
    spec = generate_fix_spec(DIVIDE_BY_ZERO_DIAGNOSIS, DIVIDE_BY_ZERO_INCIDENT)
    for section in REQUIRED_SECTIONS:
        assert section in spec, f"Missing section: {section}"


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

def test_generate_spec_unknown_bug():
    unknown_diagnosis = {
        "root_cause": "Something completely unexpected happened in the flux capacitor.",
        "suggested_fix": "Recalibrate the flux capacitor.",
        "affected_components": ["flux/capacitor.py"],
        "confidence": 0.5,
        "severity_reasoning": None,
    }
    unknown_incident = {
        "incident_id": "inc-test-unknown",
        "status": "open",
        "severity": "low",
        "service": "deepops-demo-app",
        "source": {
            "error_type": "FluxError",
            "source_file": "flux/capacitor.py",
            "path": "/flux",
        },
    }
    # Should not raise
    spec = generate_fix_spec(unknown_diagnosis, unknown_incident)
    assert isinstance(spec, str)
    assert len(spec) > 0
    for section in REQUIRED_SECTIONS:
        assert section in spec, f"Missing section in unknown-bug spec: {section}"
