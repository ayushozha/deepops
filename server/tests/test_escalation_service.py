from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.store_adapter import InMemoryIncidentStore
from server.api.escalation import router as escalation_router
from server.integrations.bland_client import MockBlandClient
from server.services.escalation_service import EscalationService
from server.services.incident_service import IncidentService
from server.services.realtime_hub import RealtimeHub


def _load_incident(index: int = 2) -> dict:
    incidents = json.loads(Path("tests/fixtures/incidents.json").read_text(encoding="utf-8"))
    return incidents[index]


def _build_service(*, bland_client=None):
    store = InMemoryIncidentStore([_load_incident()])
    incidents = IncidentService(store=store, realtime_hub=RealtimeHub())
    service = EscalationService(incidents=incidents, bland_client=bland_client)
    incident = store.list_incidents(limit=1)[0]
    return service, store, incident


def test_requires_phone_escalation_for_high_severity() -> None:
    service, _, incident = _build_service()
    assert service.requires_phone_escalation(incident) is True


def test_rejects_low_severity_without_force() -> None:
    store = InMemoryIncidentStore([_load_incident(index=0)])
    incidents = IncidentService(store=store, realtime_hub=RealtimeHub())
    service = EscalationService(incidents=incidents)
    incident = store.list_incidents(limit=1)[0]
    assert service.requires_phone_escalation(incident) is False


def test_build_escalation_request_includes_metadata() -> None:
    service, _, incident = _build_service(bland_client=MockBlandClient())
    payload = service.build_escalation_request(
        incident,
        phone_number="+15555550100",
        webhook_url="https://example.com/webhooks/bland",
        reason="Critical outage",
    )
    assert payload["phone_number"] == "+15555550100"
    assert payload["metadata"]["incident_id"] == incident["incident_id"]
    assert payload["metadata"]["severity"] == incident["severity"]
    assert payload["metadata"]["escalation_reason"] == "Critical outage"
    assert payload["webhook"] == "https://example.com/webhooks/bland"


def test_trigger_escalation_dry_run_marks_incident() -> None:
    service, store, incident = _build_service()
    result = asyncio.run(
        service.trigger_escalation(
            incident["incident_id"],
            phone_number="+15555550100",
            reason="Critical user impact",
            dry_run=True,
        )
    )
    updated = store.get_incident(incident["incident_id"])
    assert result.call_result["status"] == "dry_run"
    assert updated["status"] == "awaiting_approval"
    assert updated["approval"]["required"] is True
    assert updated["approval"]["mode"] == "manual"
    assert updated["approval"]["status"] == "pending"
    assert updated["approval"]["channel"] == "voice_call"
    assert updated["timeline"]


def test_trigger_escalation_with_mock_client_sets_call_id() -> None:
    service, store, incident = _build_service(bland_client=MockBlandClient())
    result = asyncio.run(
        service.trigger_escalation(
            incident["incident_id"],
            phone_number="+15555550100",
            webhook_url="https://example.com/webhooks/bland",
            reason="Critical user impact",
        )
    )
    updated = store.get_incident(incident["incident_id"])
    assert result.call_result["status"] == "queued"
    assert result.call_result["call_id"]
    assert updated["approval"]["bland_call_id"] == result.call_result["call_id"]
    assert updated["status"] == "awaiting_approval"


def test_trigger_escalation_rejects_low_severity_without_force() -> None:
    store = InMemoryIncidentStore([_load_incident(index=0)])
    incidents = IncidentService(store=store, realtime_hub=RealtimeHub())
    service = EscalationService(incidents=incidents)
    incident = store.list_incidents(limit=1)[0]
    try:
        asyncio.run(
            service.trigger_escalation(
                incident["incident_id"],
                phone_number="+15555550100",
            )
        )
    except ValueError as exc:
        assert "phone-escalation threshold" in str(exc)
    else:
        raise AssertionError("Expected phone escalation to reject low severity")


def test_escalation_route_returns_clean_payload() -> None:
    service, _, incident = _build_service()
    app = FastAPI()
    app.state.context = SimpleNamespace(escalation=service)
    app.include_router(escalation_router)
    client = TestClient(app)

    response = client.post(
        f"/api/escalation/{incident['incident_id']}/trigger",
        json={
            "phone_number": "+15555550100",
            "reason": "Critical outage with user impact",
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert body["call_result"]["status"] == "dry_run"
    assert body["incident"]["status"] == "awaiting_approval"
    assert body["request_payload"]["metadata"]["incident_id"] == incident["incident_id"]
