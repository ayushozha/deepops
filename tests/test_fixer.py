"""
Tests for agent/fixer.py — main fix-generation pipeline.
"""

from unittest.mock import MagicMock, patch

import pytest

from agent.fixer import run_fix_generation, trim_diff, extract_schema_fix
from tests.fixtures.diagnoses import (
    BLOCKING_TIMEOUT_DIAGNOSIS,
    BLOCKING_TIMEOUT_INCIDENT,
    DIVIDE_BY_ZERO_DIAGNOSIS,
    DIVIDE_BY_ZERO_INCIDENT,
    MISSING_USER_DIAGNOSIS,
    MISSING_USER_INCIDENT,
)

REQUIRED_KEYS = {"status", "spec_markdown", "diff_preview", "files_changed", "test_plan"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kiro_failure_result():
    return {
        "success": False,
        "exit_code": -1,
        "stdout": "",
        "stderr": "Kiro CLI not found.",
        "diff_preview": None,
        "files_changed": [],
    }


# ---------------------------------------------------------------------------
# Payload completeness
# ---------------------------------------------------------------------------

def test_fix_payload_completeness():
    result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)
    for key in REQUIRED_KEYS:
        assert key in result, f"Missing key: {key}"


def test_fix_payload_status_is_complete():
    result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)
    assert result["status"] == "complete"


# ---------------------------------------------------------------------------
# Fallback mode
# ---------------------------------------------------------------------------

def test_fallback_mode_when_kiro_unavailable():
    mock_client = MagicMock()
    mock_client.run.return_value = _kiro_failure_result()

    with patch("agent.fixer.KiroClient", return_value=mock_client):
        result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)

    assert result["status"] == "complete"
    for key in REQUIRED_KEYS:
        assert key in result, f"Missing key in fallback result: {key}"
    # fallback diff should still be present
    assert result["diff_preview"] is not None
    assert result["_metadata"]["kiro_mode"] == "fallback"


# ---------------------------------------------------------------------------
# Per-bug-class payloads
# ---------------------------------------------------------------------------

def test_fix_payload_for_divide_by_zero():
    result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)
    assert result["status"] == "complete"
    assert isinstance(result["spec_markdown"], str) and len(result["spec_markdown"]) > 0
    assert isinstance(result["files_changed"], list)
    assert isinstance(result["test_plan"], list) and len(result["test_plan"]) > 0


def test_fix_payload_for_missing_user():
    result = run_fix_generation(MISSING_USER_INCIDENT, MISSING_USER_DIAGNOSIS)
    assert result["status"] == "complete"
    assert isinstance(result["spec_markdown"], str) and len(result["spec_markdown"]) > 0
    assert isinstance(result["files_changed"], list)
    assert isinstance(result["test_plan"], list) and len(result["test_plan"]) > 0


def test_fix_payload_for_timeout():
    result = run_fix_generation(BLOCKING_TIMEOUT_INCIDENT, BLOCKING_TIMEOUT_DIAGNOSIS)
    assert result["status"] == "complete"
    assert isinstance(result["spec_markdown"], str) and len(result["spec_markdown"]) > 0
    assert isinstance(result["files_changed"], list)
    assert isinstance(result["test_plan"], list) and len(result["test_plan"]) > 0


# ---------------------------------------------------------------------------
# trim_diff helper
# ---------------------------------------------------------------------------

def test_trim_diff_short_diff_unchanged():
    diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1,2 +1,3 @@\n line\n+added\n"
    assert trim_diff(diff, max_lines=50) == diff


def test_trim_diff_truncates_long_diff():
    header = "--- a/foo.py\n+++ b/foo.py\n@@ -1,100 +1,101 @@\n"
    body_lines = [f" line {i}" for i in range(100)]
    long_diff = header + "\n".join(body_lines)
    result = trim_diff(long_diff, max_lines=10)
    assert "# ... (truncated)" in result
    assert len(result.splitlines()) <= 12  # header (3) + body (up to 7) + truncation note


def test_fix_payload_is_schema_clean():
    result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)
    for banned in ("_kiro_mode", "_fix_summary", "_regression_warning"):
        assert banned not in result, f"Schema-polluting key found at top level: {banned}"


def test_trim_diff_preserves_header_lines():
    header = "--- a/foo.py\n+++ b/foo.py\n@@ -1,100 +1,101 @@\n"
    body_lines = [f" line {i}" for i in range(100)]
    long_diff = header + "\n".join(body_lines)
    result = trim_diff(long_diff, max_lines=10)
    assert "--- a/foo.py" in result
    assert "+++ b/foo.py" in result
    assert "@@ -1,100 +1,101 @@" in result


# ---------------------------------------------------------------------------
# extract_schema_fix
# ---------------------------------------------------------------------------

def test_extract_schema_fix_strips_metadata():
    fix_result = run_fix_generation(DIVIDE_BY_ZERO_INCIDENT, DIVIDE_BY_ZERO_DIAGNOSIS)
    schema_fix = extract_schema_fix(fix_result)
    assert "_metadata" not in schema_fix
    for key in ("status", "spec_markdown", "diff_preview", "files_changed", "test_plan", "started_at_ms", "completed_at_ms"):
        assert key in schema_fix
