"""Tests for Bland AI normalizer and client call-script generation."""
from __future__ import annotations

import pytest

from server.normalizers.bland_normalizer import (
    build_approval_patch,
    extract_approval_decision,
    parse_bland_webhook,
    summarize_transcript,
)
from server.integrations.bland_client import BlandClient, BlandConfigError


# ---------------------------------------------------------------------------
# Fixtures — sample webhook payloads
# ---------------------------------------------------------------------------

def _make_webhook(
    *,
    call_id: str = "call-abc123",
    status: str = "completed",
    transcript_text: str = "",
    completed_at: str = "2026-03-27T10:00:00Z",
    answered_by: str | None = "eng-jane",
    analysis: dict | None = None,
) -> dict:
    transcripts = [{"text": transcript_text, "speaker": "human"}] if transcript_text else []
    payload: dict = {
        "call_id": call_id,
        "status": status,
        "transcripts": transcripts,
        "completed_at": completed_at,
        "answered_by": answered_by,
    }
    if analysis is not None:
        payload["analysis"] = analysis
    return payload


def _make_incident(
    *,
    severity: str = "critical",
    error_message: str = "NullPointerException in PaymentService.charge()",
    root_cause: str = "Null customer object passed due to missing validation",
    suggested_fix: str = "Add null-check guard in PaymentService.charge()",
    affected_components: list[str] | None = None,
    incident_id: str = "INC-42",
) -> dict:
    return {
        "incident_id": incident_id,
        "severity": severity,
        "source": {
            "error_message": error_message,
            "affected_components": affected_components or ["payment-service", "checkout-api"],
        },
        "diagnosis": {
            "root_cause": root_cause,
            "suggested_fix": suggested_fix,
            "affected_components": affected_components or ["payment-service", "checkout-api"],
        },
    }


# ---------------------------------------------------------------------------
# parse_bland_webhook
# ---------------------------------------------------------------------------

class TestParseBlandWebhook:
    def test_parse_approved_webhook(self) -> None:
        payload = _make_webhook(transcript_text="Yes, go ahead and deploy it.")
        result = parse_bland_webhook(payload)
        assert result["status"] == "approved"
        assert result["required"] is True
        assert result["mode"] == "manual"
        assert result["channel"] == "voice_call"
        assert result["bland_call_id"] == "call-abc123"
        assert result["decider"] == "eng-jane"

    def test_parse_rejected_webhook(self) -> None:
        payload = _make_webhook(transcript_text="No, hold off on that deployment.")
        result = parse_bland_webhook(payload)
        assert result["status"] == "rejected"

    def test_parse_ambiguous_webhook(self) -> None:
        payload = _make_webhook(transcript_text="Hmm, I need to think about this more.")
        result = parse_bland_webhook(payload)
        assert result["status"] == "pending"

    def test_parse_failed_call(self) -> None:
        payload = _make_webhook(status="failed", transcript_text="")
        result = parse_bland_webhook(payload)
        assert result["status"] == "pending"

    def test_parse_no_answer_call(self) -> None:
        payload = _make_webhook(status="no-answer", transcript_text="")
        result = parse_bland_webhook(payload)
        assert result["status"] == "pending"

    def test_analysis_overrides_transcript(self) -> None:
        """When Bland returns structured analysis, prefer it over transcript parsing."""
        payload = _make_webhook(
            transcript_text="Maybe deploy later",
            analysis={"decision": "approved", "notes": "Engineer confirmed verbally."},
        )
        result = parse_bland_webhook(payload)
        assert result["status"] == "approved"
        assert result["notes"] == "Engineer confirmed verbally."

    def test_decision_at_ms_parsed(self) -> None:
        payload = _make_webhook(completed_at="2026-03-27T10:00:00Z")
        result = parse_bland_webhook(payload)
        assert isinstance(result["decision_at_ms"], int)
        assert result["decision_at_ms"] > 0


# ---------------------------------------------------------------------------
# build_approval_patch
# ---------------------------------------------------------------------------

class TestBuildApprovalPatch:
    def test_build_approval_patch_has_required_fields(self) -> None:
        payload = _make_webhook(transcript_text="Yes, approved.")
        patch = build_approval_patch(payload)

        # Top-level keys
        assert "approval" in patch
        assert "updated_at_ms" in patch
        assert "timeline_event" in patch

        # Approval sub-dict keys
        approval = patch["approval"]
        for key in ("required", "mode", "status", "channel", "decider",
                     "bland_call_id", "notes", "decision_at_ms"):
            assert key in approval, f"Missing approval key: {key}"

        # Timeline event keys
        event = patch["timeline_event"]
        for key in ("at_ms", "status", "actor", "message", "sponsor", "metadata"):
            assert key in event, f"Missing timeline_event key: {key}"
        assert event["actor"] == "bland-ai"
        assert event["sponsor"] == "Bland AI"

    def test_patch_timeline_status_for_pending(self) -> None:
        payload = _make_webhook(status="failed")
        patch = build_approval_patch(payload)
        assert patch["timeline_event"]["status"] == "gating"

    def test_patch_timeline_status_for_approved(self) -> None:
        payload = _make_webhook(transcript_text="Approved, deploy now.")
        patch = build_approval_patch(payload)
        assert patch["timeline_event"]["status"] == "awaiting_approval"


# ---------------------------------------------------------------------------
# extract_approval_decision — parametrized keyword tests
# ---------------------------------------------------------------------------

class TestExtractDecisionKeywords:
    @pytest.mark.parametrize(
        "text",
        [
            "Yes, please deploy",
            "Approved",
            "Go ahead",
            "approve it",
            "go for it, deploy",
            "ship it",
            "confirmed",
            "absolutely, proceed",
        ],
    )
    def test_approved_keywords(self, text: str) -> None:
        assert extract_approval_decision(text) == "approved"

    @pytest.mark.parametrize(
        "text",
        [
            "No, do not deploy",
            "Rejected",
            "deny that request",
            "stop everything",
            "hold off",
            "wait, not now",
            "cancel the deployment",
            "abort",
            "stand down",
        ],
    )
    def test_rejected_keywords(self, text: str) -> None:
        assert extract_approval_decision(text) == "rejected"

    @pytest.mark.parametrize(
        "text",
        [
            "I need more information",
            "Let me check the logs first",
            "",
            "   ",
        ],
    )
    def test_pending_keywords(self, text: str) -> None:
        assert extract_approval_decision(text) == "pending"

    def test_last_keyword_wins(self) -> None:
        """If the engineer first says 'no' then 'yes', honour the last one."""
        text = "No wait, actually yes, go ahead and deploy"
        assert extract_approval_decision(text) == "approved"

    def test_transcript_as_list_of_dicts(self) -> None:
        transcripts = [
            {"text": "What is the issue?", "speaker": "agent"},
            {"text": "Okay, approved.", "speaker": "human"},
        ]
        assert extract_approval_decision(transcripts) == "approved"


# ---------------------------------------------------------------------------
# summarize_transcript
# ---------------------------------------------------------------------------

class TestSummarizeTranscript:
    def test_summarize_transcript_non_empty(self) -> None:
        text = "The engineer discussed the incident and approved deployment."
        result = summarize_transcript(text)
        assert len(result) > 0
        assert isinstance(result, str)

    def test_summarize_empty_transcript(self) -> None:
        assert summarize_transcript("") == "No transcript available."
        assert summarize_transcript([]) == "No transcript available."

    def test_summarize_truncates_long_text(self) -> None:
        long_text = "word " * 200
        result = summarize_transcript(long_text)
        assert len(result) <= 280
        assert result.endswith("...")


# ---------------------------------------------------------------------------
# BlandClient.build_call_script
# ---------------------------------------------------------------------------

class TestBuildCallScript:
    def _make_client(self) -> BlandClient:
        """Create a BlandClient with a dummy key (no network calls)."""
        return BlandClient(api_key="test-key-123")

    def test_build_call_script_critical(self) -> None:
        client = self._make_client()
        incident = _make_incident(severity="critical")
        script = client.build_call_script(incident)

        assert "critical" in script.lower()
        assert "DeepOps automated incident response" in script
        assert "INC-42" in script
        assert "NullPointerException" in script
        assert "Do you approve immediate deployment?" in script

    def test_build_call_script_high(self) -> None:
        client = self._make_client()
        incident = _make_incident(severity="high")
        script = client.build_call_script(incident)

        assert "DeepOps incident notification" in script
        assert "high-severity" in script
        assert "Would you like to approve deployment?" in script

    def test_build_call_script_includes_root_cause(self) -> None:
        client = self._make_client()
        incident = _make_incident(root_cause="Memory leak in cache layer")
        script = client.build_call_script(incident)
        assert "Memory leak in cache layer" in script

    def test_build_call_script_includes_suggested_fix(self) -> None:
        client = self._make_client()
        incident = _make_incident(suggested_fix="Increase heap to 4GB")
        script = client.build_call_script(incident)
        assert "Increase heap to 4GB" in script

    def test_build_call_script_includes_affected_components(self) -> None:
        client = self._make_client()
        incident = _make_incident(affected_components=["auth-service", "user-api"])
        script = client.build_call_script(incident)
        assert "auth-service" in script
        assert "user-api" in script


# ---------------------------------------------------------------------------
# BlandClient config error
# ---------------------------------------------------------------------------

class TestBlandClientConfig:
    def test_missing_api_key_raises(self) -> None:
        import os
        env_backup = os.environ.pop("BLAND_API_KEY", None)
        try:
            with pytest.raises(BlandConfigError):
                BlandClient(api_key="")
        finally:
            if env_backup is not None:
                os.environ["BLAND_API_KEY"] = env_backup
