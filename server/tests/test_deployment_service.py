"""Tests for server/services/deployment_service.py"""
from __future__ import annotations

from unittest.mock import MagicMock

from server.services.deployment_service import DeploymentService, run_deployment
from server.integrations.truefoundry_client import DeploymentResult
from server.services.fix_artifact_service import FixArtifact


def _incident() -> dict:
    return {"incident_id": "inc-test-1", "created_at_ms": 1_000_000}


def _artifact() -> FixArtifact:
    return FixArtifact(
        incident_id="inc-test-1",
        source_path="demo-app/main.py",
        error_type="ZeroDivisionError",
        kiro_mode="fallback",
    )


def _succeeded_result() -> DeploymentResult:
    return DeploymentResult(
        deploy_id="dep-1", status="succeeded",
        service_name="svc", environment="hackathon",
        deploy_url="https://example.com",
    )


def _failed_result() -> DeploymentResult:
    return DeploymentResult(
        deploy_id="dep-2", status="failed",
        service_name="svc", environment="hackathon",
        failure_reason="timeout",
    )


def _make_svc(result: DeploymentResult | None = None):
    store = MagicMock()
    tfy = MagicMock()
    tfy.submit_deployment.return_value = result or _succeeded_result()
    return DeploymentService(store, tfy), store, tfy


def test_start_deployment_patches_incident():
    svc, store, _ = _make_svc()
    svc.start_deployment(_incident(), _artifact())
    patch = store.patch_incident.call_args[0][1]
    assert patch["status"] == "deploying"
    assert patch["deployment"]["status"] == "running"


def test_start_deployment_appends_timeline():
    svc, store, _ = _make_svc()
    svc.start_deployment(_incident(), _artifact())
    store.append_timeline_event.assert_called_once()


def test_handle_deployment_result_success():
    svc, store, _ = _make_svc()
    svc.handle_deployment_result(_incident(), _succeeded_result())
    patch = store.patch_incident.call_args[0][1]
    assert patch["status"] == "resolved"
    assert patch["deployment"]["status"] == "succeeded"


def test_handle_deployment_result_failure():
    svc, store, _ = _make_svc()
    svc.handle_deployment_result(_incident(), _failed_result())
    patch = store.patch_incident.call_args[0][1]
    assert patch["status"] == "failed"
    assert patch["deployment"]["failure_reason"] == "timeout"


def test_build_deployment_patch_resolved_has_resolution_time():
    svc, _, _ = _make_svc()
    patch = svc.build_deployment_patch(_succeeded_result(), _incident())
    assert "resolution_time_ms" in patch


def test_run_deployment_convenience():
    store = MagicMock()
    tfy = MagicMock()
    tfy.submit_deployment.return_value = _succeeded_result()
    patch = run_deployment(_incident(), _artifact(), store, tfy)
    assert "status" in patch
    tfy.submit_deployment.assert_called_once()


def test_deploy_incident_uses_deployment_service():
    """DemoFlowService._deploy_incident delegates to DeploymentService."""
    from unittest.mock import MagicMock
    import types
    import server.services.demo_flow_service as dfs_mod

    incident = {
        "incident_id": "inc-demo-1",
        "created_at_ms": 1_000_000,
        "fix": {
            "diff_preview": "--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@\n+pass\n",
            "files_changed": ["demo-app/main.py"],
            "test_plan": ["pytest demo-app"],
        },
        "source": {"path": "demo-app/main.py", "error_type": "ZeroDivisionError"},
    }

    store = MagicMock()
    tfy = MagicMock()
    tfy.submit_deployment.return_value = _succeeded_result()

    incidents_svc = MagicMock()
    incidents_svc.get_incident.return_value = {**incident, "status": "resolved"}

    # Spy on the real DeploymentService methods
    real_ds = DeploymentService(incidents_svc, tfy)
    real_ds.deploy = MagicMock(wraps=real_ds.deploy)
    real_ds.start_deployment = MagicMock(wraps=real_ds.start_deployment)
    real_ds.handle_deployment_result = MagicMock(wraps=real_ds.handle_deployment_result)

    # Build a minimal stand-in with the attributes _deploy_incident needs
    obj = types.SimpleNamespace(
        deployment=real_ds,
        truefoundry=tfy,
        incidents=incidents_svc,
    )
    obj._build_execution_package_dict = MagicMock(return_value=None)
    obj._build_hotfix_package_dict = MagicMock(return_value=None)

    result_tuple = dfs_mod.DemoFlowService._deploy_incident(
        obj, incident, actor="test", sponsor="test"
    )

    real_ds.deploy.assert_called_once()
    updated, exec_pkg, hotfix_pkg = result_tuple
    assert updated["status"] == "resolved"
    assert exec_pkg is None
    assert hotfix_pkg is None
