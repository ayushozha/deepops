from __future__ import annotations

from fastapi.testclient import TestClient

from agent.store_adapter import InMemoryIncidentStore
from config import Settings
from server.app import create_app


def _build_client() -> TestClient:
    app = create_app(
        settings=Settings(
            allow_in_memory_store=True,
            bland_api_key="demo-key",
            bland_phone_number="+15550001111",
            bland_webhook_url="https://example.com/api/webhooks/bland",
            overmind_api_key="ovr-demo",
            truefoundry_api_key="tf-demo",
            auth0_domain="example.auth0.com",
            auth0_client_id="client-id",
            auth0_client_secret="client-secret",
        ),
        store=InMemoryIncidentStore(),
        diagnose=lambda _: {
            "root_cause": "unused",
            "suggested_fix": "unused",
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


def test_settings_overview_returns_sanitized_configuration() -> None:
    client = _build_client()
    response = client.get("/api/settings/overview")
    assert response.status_code == 200

    payload = response.json()
    assert payload["system"]["service_name"] == "deepops-person-a"
    assert payload["system"]["backend"] == "fastapi"
    assert payload["webhook"]["url"]
    assert all("api_key" not in item for item in payload["integrations"])
    assert any(item["name"] == "Bland AI" for item in payload["integrations"])
