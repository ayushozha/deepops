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


def _build_client(*, incident: dict, settings: Settings | None = None) -> TestClient:
    store = InMemoryIncidentStore([incident])
    app = create_app(
        settings=settings or Settings(allow_in_memory_store=True),
        store=store,
        diagnose=lambda _: {
            "root_cause": "guard missing in demo-app/main.py",
            "suggested_fix": "add a guard clause before the failing path",
            "affected_components": ["demo-app/main.py"],
            "confidence": 0.91,
        },
        generate_fix=lambda *_: {
            "spec_markdown": "# Fix\nAdd a guard clause.",
            "diff_preview": "--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@\n+if b == 0:\n+    return {\"error\": \"bad input\"}\n",
            "files_changed": ["demo-app/main.py"],
            "test_plan": ["pytest demo-app", "curl /healthz"],
        },
    )
    return TestClient(app)


def test_run_once_autonomous_incident_auto_deploys() -> None:
    client = _build_client(incident=_fixture(0))
    response = client.post("/api/agent/run-once")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["processed"] is True
    assert body["incident"]["status"] == "resolved"
    assert body["policy"]["route"] == "auto-deploy"
    assert body["incident"]["approval"]["status"] == "approved"
    assert body["incident"]["deployment"]["status"] == "succeeded"
    assert body["explanations"]["approval"]["incident_id"] == body["incident"]["incident_id"]


def test_run_once_critical_incident_triggers_phone_escalation() -> None:
    client = _build_client(
        incident=_fixture(2),
        settings=Settings(
            allow_in_memory_store=True,
            bland_phone_number="+15555550100",
            bland_webhook_url="https://example.com/webhooks/bland",
        ),
    )
    response = client.post("/api/agent/run-once")
    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["status"] == "awaiting_approval"
    assert body["policy"]["route"] == "phone-escalation"
    assert body["escalation"]["escalated"] is True
    assert body["incident"]["approval"]["channel"] == "voice_call"
    assert body["incident"]["approval"]["status"] == "pending"
    assert "call_script" in body["explanations"]


def test_deploy_result_includes_execution_package_narration() -> None:
    """Deploy flow should include execution_package narration in the result dict."""
    client = _build_client(incident=_fixture(0))
    response = client.post("/api/agent/run-once")
    assert response.status_code == 200
    body = response.json()

    # Incident must have resolved via auto-deploy
    assert body["processed"] is True
    assert body["incident"]["status"] == "resolved"

    # execution_package should be present and contain narration
    exec_pkg = body.get("execution_package")
    assert exec_pkg is not None, "execution_package missing from result"
    assert "narration_summary" in exec_pkg, "narration_summary missing from execution_package"
    assert isinstance(exec_pkg["narration_summary"], str)
    assert len(exec_pkg["narration_summary"]) > 0

    # execution_steps and files_changed should also be present
    assert "execution_steps" in exec_pkg
    assert isinstance(exec_pkg["execution_steps"], list)
    assert "files_changed" in exec_pkg
    assert exec_pkg["deployment_inputs"]["service_name"] == "deepops-demo-app"
