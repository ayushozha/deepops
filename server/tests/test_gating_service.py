from __future__ import annotations

import json
from pathlib import Path

from agent.contracts import STATUS_BLOCKED, STATUS_DEPLOYING
from agent.store_adapter import InMemoryIncidentStore
from server.services.gating_service import GatingService
from server.services.incident_service import IncidentService
from server.services.realtime_hub import RealtimeHub


def _build_service():
    incident = json.loads(Path("tests/fixtures/incidents.json").read_text(encoding="utf-8"))[0]
    store = InMemoryIncidentStore()
    created = store.create_incident(incident)
    incidents = IncidentService(store=store, realtime_hub=RealtimeHub())
    return created, GatingService(incidents=incidents)


def test_apply_decision_approved_moves_to_deploying():
    incident, gating = _build_service()
    updated = gating.apply_decision(
        incident["incident_id"],
        approved=True,
        actor="test",
        sponsor="Auth0",
        mode="manual",
    )
    assert updated["status"] == STATUS_DEPLOYING
    assert updated["approval"]["status"] == "approved"


def test_apply_decision_denied_moves_to_blocked():
    incident, gating = _build_service()
    updated = gating.apply_decision(
        incident["incident_id"],
        approved=False,
        actor="test",
        sponsor="Auth0",
        mode="manual",
    )
    assert updated["status"] == STATUS_BLOCKED
    assert updated["approval"]["status"] == "denied"
