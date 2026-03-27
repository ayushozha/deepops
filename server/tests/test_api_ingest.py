from __future__ import annotations

from fastapi.testclient import TestClient

from agent.store_adapter import InMemoryIncidentStore
from config import Settings
from server.app import create_app


def _build_client() -> TestClient:
    app = create_app(
        settings=Settings(allow_in_memory_store=True),
        store=InMemoryIncidentStore(),
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


def test_ingest_demo_trigger_creates_incident() -> None:
    client = _build_client()
    response = client.post("/api/ingest/demo-trigger", json={"bug_key": "calculate_zero"})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "demo-trigger"
    assert body["incident"]["status"] == "stored"
    assert body["incident"]["source"]["error_type"] == "ZeroDivisionError"


def test_ingest_demo_app_error_creates_incident() -> None:
    client = _build_client()
    response = client.post(
        "/api/ingest/demo-app",
        json={
            "payload": {
                "path": "/search",
                "error_type": "TimeoutError",
                "error_message": "timed out",
                "source_file": "demo-app/main.py",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "demo-app"
    assert body["incident"]["source"]["path"] == "/search"


def test_ingest_airbyte_sync_creates_incidents() -> None:
    client = _build_client()
    response = client.post("/api/ingest/airbyte-sync", json={"connection_id": "conn-demo"})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "airbyte"
    assert body["connection_id"] == "conn-demo"
    assert len(body["incidents"]) >= 1
    assert body["incidents"][0]["source"]["provider"] == "airbyte"
