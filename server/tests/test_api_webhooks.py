from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from agent.store_adapter import InMemoryIncidentStore
from config import Settings
from server.app import create_app


def _fixture(index: int) -> dict:
    incidents = json.loads(Path("tests/fixtures/incidents.json").read_text(encoding="utf-8"))
    return deepcopy(incidents[index])


def _ready_for_approval(index: int = 2) -> dict:
    incident = _fixture(index)
    incident["status"] = "awaiting_approval"
    incident["diagnosis"] = {
        "status": "complete",
        "root_cause": "search path blocks on a slow dependency",
        "suggested_fix": "add timeout handling and fallback",
        "affected_components": ["demo-app/main.py"],
        "confidence": 0.95,
        "severity_reasoning": "customer impact is high",
        "macroscope_context": None,
        "started_at_ms": 1,
        "completed_at_ms": 2,
    }
    incident["fix"] = {
        "status": "complete",
        "spec_markdown": "# Fix\nAdd a timeout guard and fallback.",
        "diff_preview": "--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@\n+return fallback_response\n",
        "files_changed": ["demo-app/main.py"],
        "test_plan": ["pytest demo-app", "curl /search?q=test"],
        "started_at_ms": 3,
        "completed_at_ms": 4,
    }
    incident["approval"] = {
        "required": True,
        "mode": "manual",
        "status": "pending",
        "channel": "voice_call",
        "decider": None,
        "bland_call_id": "call-123",
        "notes": None,
        "decision_at_ms": None,
    }
    return incident


def _build_client(incident: dict) -> TestClient:
    app = create_app(
        settings=Settings(allow_in_memory_store=True),
        store=InMemoryIncidentStore([incident]),
        diagnose=lambda _: {
            "root_cause": "unused in webhook tests",
            "suggested_fix": "unused",
            "affected_components": ["demo-app/main.py"],
            "confidence": 0.8,
        },
        generate_fix=lambda *_: {
            "spec_markdown": "# mock",
            "diff_preview": "--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@\n+pass\n",
            "files_changed": ["demo-app/main.py"],
            "test_plan": ["run tests"],
        },
    )
    return TestClient(app)


def test_raw_bland_webhook_approved_deploys() -> None:
    incident = _ready_for_approval()
    client = _build_client(incident)
    response = client.post(
        "/api/webhooks/bland",
        json={
            "call_id": "call-raw-1",
            "status": "completed",
            "metadata": {"incident_id": incident["incident_id"]},
            "transcripts": [{"speaker": "human", "text": "Yes, go ahead and deploy it."}],
            "answered_by": "eng-jane",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["status"] == "resolved"
    assert body["incident"]["approval"]["status"] == "approved"
    assert body["incident"]["approval"]["bland_call_id"] == "call-raw-1"
    assert body["webhook"]["decision_type"] == "approve"


def test_raw_bland_webhook_suggestion_replans() -> None:
    incident = _ready_for_approval()
    client = _build_client(incident)
    response = client.post(
        "/api/webhooks/bland",
        json={
            "call_id": "call-raw-2",
            "status": "completed",
            "metadata": {"incident_id": incident["incident_id"]},
            "transcripts": [
                {
                    "speaker": "human",
                    "text": "Try a hotfix only and don't touch auth.py. Patch the endpoint first.",
                }
            ],
            "answered_by": "eng-jane",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["status"] == "gating"
    assert body["incident"]["approval"]["mode"] == "manual"
    assert body["webhook"]["replan_packet"] is not None
    assert body["hotfix_package"]["scope_note"]
