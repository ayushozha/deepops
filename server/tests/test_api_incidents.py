from __future__ import annotations

from fastapi.testclient import TestClient

from agent.contracts import load_incident_from_path
from agent.store_adapter import InMemoryIncidentStore
from config import Settings
from server.app import create_app


def _build_client() -> TestClient:
    store = InMemoryIncidentStore()
    incident = load_incident_from_path("docs/incident-example.json")
    store.create_incident(incident)
    app = create_app(
        settings=Settings(allow_in_memory_store=True),
        store=store,
        diagnose=lambda _: {
            "root_cause": "mock root cause",
            "suggested_fix": "mock fix",
            "affected_components": ["demo-app/main.py"],
            "confidence": 0.9,
        },
        generate_fix=lambda *_: {
            "spec_markdown": "# mock",
            "diff_preview": "--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@\n+pass\n",
            "files_changed": ["demo-app/main.py"],
            "test_plan": ["run tests"],
        },
    )
    return TestClient(app)


def test_list_incidents_returns_payload():
    client = _build_client()
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["incident_id"]


def test_get_incident_returns_detail():
    client = _build_client()
    incidents = client.get("/api/incidents").json()
    response = client.get(f"/api/incidents/{incidents[0]['incident_id']}")
    assert response.status_code == 200
    assert response.json()["incident_id"] == incidents[0]["incident_id"]


def test_create_incident_appends_first_timeline_event():
    client = _build_client()
    payload = {
        "incident": {
            "source": {
                "provider": "demo-app",
                "path": "GET /calculate/0",
                "error_type": "ZeroDivisionError",
                "error_message": "division by zero",
                "source_file": "demo-app/main.py",
                "timestamp_ms": 1711540800000,
            }
        }
    }
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 200
    created = response.json()
    assert created["timeline"]
    assert created["timeline"][0]["actor"] == "backend-api"
