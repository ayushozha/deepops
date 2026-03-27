"""Deployment service: moves incidents through deploying -> resolved | failed."""

from __future__ import annotations

from typing import Any

from agent.contracts import (
    DeploymentPayload,
    STATUS_DEPLOYING,
    STATUS_FAILED,
    STATUS_RESOLVED,
    make_timeline_event,
    now_ms,
)
from server.integrations.truefoundry_client import DeploymentResult
from server.services.fix_artifact_service import FixArtifact

_ACTOR = "deployment_service"
_SPONSOR = "truefoundry"


class DeploymentService:
    def __init__(self, store_adapter: Any, truefoundry_client: Any) -> None:
        self.store = store_adapter
        self.tfy = truefoundry_client

    def start_deployment(
        self,
        incident: dict,
        artifact: FixArtifact,
        submit_result: DeploymentResult | None = None,
    ) -> dict:
        """Submit deployment and persist the start of the lifecycle."""
        result = submit_result or self.tfy.submit_deployment(artifact)

        ts = now_ms()
        deployment_patch: DeploymentPayload = {
            "provider": "truefoundry",
            "status": "running",
            "service_name": result.service_name,
            "environment": result.environment,
            "commit_sha": result.commit_sha,
            "deploy_url": result.deploy_url,
            "started_at_ms": result.started_at_ms or ts,
        }
        patch: dict[str, Any] = {
            "status": STATUS_DEPLOYING,
            "deployment": deployment_patch,
            "updated_at_ms": ts,
        }

        incident_id: str = incident["incident_id"]
        self.store.patch_incident(incident_id, patch)
        self.store.append_timeline_event(
            incident_id,
            make_timeline_event(
                status=STATUS_DEPLOYING,
                actor=_ACTOR,
                message="Deployment submitted to TrueFoundry.",
                sponsor=_SPONSOR,
                at_ms=ts,
            ),
        )
        return patch

    def handle_deployment_result(self, incident: dict, result: DeploymentResult) -> dict:
        """Process a completed deployment result and return the patch dict."""
        ts = now_ms()
        patch = self.build_deployment_patch(result, incident)
        patch["updated_at_ms"] = ts

        incident_id: str = incident["incident_id"]
        self.store.patch_incident(incident_id, patch)

        top_status: str = patch["status"]
        if top_status == STATUS_RESOLVED:
            msg = f"Deployment succeeded. URL: {result.deploy_url}"
        elif top_status == STATUS_FAILED:
            msg = f"Deployment failed: {result.failure_reason}"
        else:
            msg = f"Deployment status is {result.status}."

        self.store.append_timeline_event(
            incident_id,
            make_timeline_event(
                status=top_status,
                actor=_ACTOR,
                message=msg,
                sponsor=_SPONSOR,
                at_ms=ts,
            ),
        )
        return patch

    def build_deployment_patch(self, result: DeploymentResult, incident: dict) -> dict:
        """Build the raw patch dict for a deployment result."""
        ts = now_ms()
        base: DeploymentPayload = {
            "provider": "truefoundry",
            "service_name": result.service_name,
            "environment": result.environment,
            "commit_sha": result.commit_sha,
            "deploy_url": result.deploy_url,
        }

        if result.status == "succeeded":
            deployment_patch: DeploymentPayload = {
                **base,
                "status": "succeeded",
                "completed_at_ms": result.completed_at_ms or ts,
            }
            patch: dict[str, Any] = {
                "status": STATUS_RESOLVED,
                "deployment": deployment_patch,
                "resolution_time_ms": ts - incident.get("created_at_ms", ts),
            }
        elif result.status == "running":
            deployment_patch = {
                **base,
                "status": "running",
                "started_at_ms": result.started_at_ms or ts,
            }
            patch = {
                "status": STATUS_DEPLOYING,
                "deployment": deployment_patch,
            }
        else:
            deployment_patch = {
                **base,
                "status": "failed",
                "completed_at_ms": result.completed_at_ms or ts,
                "failure_reason": result.failure_reason,
            }
            patch = {
                "status": STATUS_FAILED,
                "deployment": deployment_patch,
            }
        return patch

    def deploy(self, incident: dict, artifact: FixArtifact) -> tuple[dict, DeploymentResult]:
        """Submit a deployment once and persist the resulting lifecycle."""
        result: DeploymentResult = self.tfy.submit_deployment(artifact)
        self.start_deployment(incident, artifact, submit_result=result)
        if result.status in {"succeeded", "failed"}:
            final_patch = self.handle_deployment_result(incident, result)
        else:
            final_patch = self.build_deployment_patch(result, incident)
        return final_patch, result


def run_deployment(
    incident: dict,
    artifact: FixArtifact,
    store_adapter: Any,
    truefoundry_client: Any,
) -> dict:
    """Start a deployment and immediately process its result (sync demo flow)."""
    svc = DeploymentService(store_adapter, truefoundry_client)
    final_patch, _ = svc.deploy(incident, artifact)
    return final_patch
