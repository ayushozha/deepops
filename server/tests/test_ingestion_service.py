"""Tests for the ingestion normalization layer.

Validates that demo triggers, raw demo-app errors, and Airbyte records
are normalized into the canonical incident shape with correct defaults,
deterministic fingerprints, and timeline events.
"""

import pytest

from server.normalizers.incident_normalizer import (
    normalize_airbyte_record,
    normalize_demo_app_error,
    normalize_demo_trigger,
)

# ---------------------------------------------------------------------------
# Required top-level fields every normalized incident must contain
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = {
    "incident_id",
    "source",
    "status",
    "severity",
    "timeline",
    "diagnosis",
    "fix",
    "approval",
    "deployment",
    "observability",
}


# ---------------------------------------------------------------------------
# Demo trigger tests
# ---------------------------------------------------------------------------
class TestNormalizeDemoTrigger:
    """Tests for normalize_demo_trigger()."""

    def test_normalize_demo_trigger_calculate_zero(self):
        """Trigger 'calculate_zero' produces a valid incident with ZeroDivisionError."""
        incident = normalize_demo_trigger("calculate_zero")
        assert incident["source"]["error_type"] == "ZeroDivisionError"
        assert incident["source"]["path"] == "/calculate/0"
        assert incident["source"]["error_message"] == "division by zero"
        assert incident["source"]["source_file"] == "demo-app/main.py"
        assert incident["source"]["provider"] == "demo-app"

    def test_normalize_demo_trigger_user_missing(self):
        """Trigger 'user_missing' produces a valid incident with KeyError."""
        incident = normalize_demo_trigger("user_missing")
        assert incident["source"]["error_type"] == "KeyError"
        assert "/user" in incident["source"]["path"]
        assert incident["source"]["provider"] == "demo-app"

    def test_normalize_demo_trigger_search_timeout(self):
        """Trigger 'search_timeout' produces a valid incident with TimeoutError."""
        incident = normalize_demo_trigger("search_timeout")
        assert incident["source"]["error_type"] == "TimeoutError"
        assert incident["source"]["path"] == "/search"
        assert incident["source"]["provider"] == "demo-app"

    def test_normalize_demo_trigger_unknown_key(self):
        """An unknown bug_key raises ValueError."""
        with pytest.raises(ValueError):
            normalize_demo_trigger("nonexistent_bug_key")


# ---------------------------------------------------------------------------
# Normalized incident shape tests
# ---------------------------------------------------------------------------
class TestNormalizedIncidentShape:
    """Tests that normalized incidents have the correct structure and defaults."""

    @pytest.fixture()
    def incident(self):
        """Return a normalized incident from a known demo trigger."""
        return normalize_demo_trigger("calculate_zero")

    def test_normalized_incident_has_all_required_fields(self, incident):
        """Every required top-level field must be present."""
        for field in REQUIRED_FIELDS:
            assert field in incident, f"Missing required field: {field}"

    def test_normalized_incident_status_is_stored(self, incident):
        """Freshly ingested incidents must have status 'stored'."""
        assert incident["status"] == "stored"

    def test_normalized_incident_severity_is_pending(self, incident):
        """Severity must be 'pending' immediately after ingestion."""
        assert incident["severity"] == "pending"

    def test_normalized_incident_has_timeline_event(self, incident):
        """Timeline must contain at least one event after normalization."""
        assert isinstance(incident["timeline"], list)
        assert len(incident["timeline"]) >= 1
        first_event = incident["timeline"][0]
        assert first_event["actor"] == "ingestion"
        assert first_event["status"] == "stored"


# ---------------------------------------------------------------------------
# Raw demo-app error normalization
# ---------------------------------------------------------------------------
class TestNormalizeDemoAppError:
    """Tests for normalize_demo_app_error()."""

    def test_normalize_demo_app_error(self):
        """A raw error dict produces a valid incident with all required fields."""
        raw_error = {
            "path": "/calculate/0",
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "source_file": "app.py",
        }
        incident = normalize_demo_app_error(raw_error)

        assert incident["source"]["path"] == "/calculate/0"
        assert incident["source"]["error_type"] == "ZeroDivisionError"
        assert incident["source"]["provider"] == "demo-app"
        for field in REQUIRED_FIELDS:
            assert field in incident, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# Airbyte record normalization
# ---------------------------------------------------------------------------
class TestNormalizeAirbyteRecord:
    """Tests for normalize_airbyte_record()."""

    def test_normalize_airbyte_record(self):
        """An Airbyte record produces a valid incident with sync_id in observability."""
        airbyte_record = {
            "path": "/api/data",
            "error_type": "ValueError",
            "error_message": "invalid literal for int() with base 10: 'N/A'",
            "source_file": "app.py",
            "sync_id": "sync_8a3f2c01",
        }
        incident = normalize_airbyte_record(airbyte_record, sync_id="sync_8a3f2c01")

        assert incident["source"]["provider"] == "airbyte"
        assert incident["source"]["error_type"] == "ValueError"
        assert incident["source"]["path"] == "/api/data"
        for field in REQUIRED_FIELDS:
            assert field in incident, f"Missing required field: {field}"
        assert incident["observability"]["airbyte_sync_id"] == "sync_8a3f2c01"


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------
class TestFingerprinting:
    """Tests for deterministic fingerprint generation."""

    def test_fingerprint_is_deterministic(self):
        """Same error_type + path must always produce the same fingerprint."""
        raw_error = {
            "path": "/calculate/0",
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "source_file": "app.py",
        }
        incident_a = normalize_demo_app_error(raw_error)
        incident_b = normalize_demo_app_error(raw_error)
        assert incident_a["source"]["fingerprint"] == incident_b["source"]["fingerprint"]
        assert isinstance(incident_a["source"]["fingerprint"], str)
        assert len(incident_a["source"]["fingerprint"]) > 0

    def test_fingerprint_differs_for_different_errors(self):
        """Different error_type or path must produce different fingerprints."""
        error_a = {
            "path": "/calculate/0",
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "source_file": "app.py",
        }
        error_b = {
            "path": "/user/unknown",
            "error_type": "KeyError",
            "error_message": "'unknown'",
            "source_file": "app.py",
        }
        incident_a = normalize_demo_app_error(error_a)
        incident_b = normalize_demo_app_error(error_b)
        assert incident_a["source"]["fingerprint"] != incident_b["source"]["fingerprint"]
