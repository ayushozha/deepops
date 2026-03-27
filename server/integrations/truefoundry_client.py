from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

try:
    import httpx as _http_lib  # type: ignore[import]
    _USE_HTTPX = True
except ImportError:
    import requests as _http_lib  # type: ignore[import]
    _USE_HTTPX = False

from server.services.fix_artifact_service import FixArtifact


@dataclass
class DeploymentResult:
    deploy_id: str
    status: str          # "running" | "succeeded" | "failed" | "skipped"
    service_name: str
    environment: str
    deploy_url: str | None = None
    commit_sha: str | None = None
    failure_reason: str | None = None
    started_at_ms: int | None = None
    completed_at_ms: int | None = None


class TrueFoundryClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.truefoundry.com/v1",
        service_name: str = "deepops-demo-app",
        environment: str = "hackathon",
    ) -> None:
        if not api_key:
            raise RuntimeError("TRUEFOUNDRY_API_KEY not configured")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._service_name = service_name
        self._environment = environment

    @classmethod
    def from_env(cls) -> "TrueFoundryClient":
        return cls(
            api_key=os.environ.get("TRUEFOUNDRY_API_KEY", ""),
            base_url=os.environ.get("TRUEFOUNDRY_BASE_URL", "https://api.truefoundry.com/v1"),
            service_name=os.environ.get("TRUEFOUNDRY_SERVICE_NAME", "deepops-demo-app"),
            environment=os.environ.get("TRUEFOUNDRY_ENVIRONMENT", "hackathon"),
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            fn = getattr(_http_lib, method)
            kwargs: dict[str, Any] = {"headers": self._headers(), "timeout": 30}
            if body is not None:
                kwargs["json"] = body
            resp = fn(url, **kwargs)
            if resp.status_code >= 300:
                return {"_error": f"HTTP {resp.status_code}: {resp.text}"}
            return resp.json()
        except Exception as exc:
            return {"_error": str(exc)}

    def submit_deployment(self, artifact: FixArtifact) -> DeploymentResult:
        body = {
            "service_name": self._service_name,
            "environment": self._environment,
            "incident_id": artifact.incident_id,
            "source_path": artifact.source_path,
            "error_type": artifact.error_type,
            "files_changed": artifact.files_changed,
        }
        data = self._request("post", "/deployments", body)
        if "_error" in data:
            return DeploymentResult(
                deploy_id="",
                status="failed",
                service_name=self._service_name,
                environment=self._environment,
                failure_reason=data["_error"],
                started_at_ms=int(time.time() * 1000),
            )
        return DeploymentResult(
            deploy_id=data.get("deploy_id", ""),
            status=data.get("status", "running"),
            service_name=data.get("service_name", self._service_name),
            environment=data.get("environment", self._environment),
            deploy_url=data.get("deploy_url"),
            commit_sha=data.get("commit_sha"),
            started_at_ms=data.get("started_at_ms"),
            completed_at_ms=data.get("completed_at_ms"),
        )

    def get_deployment_status(self, deploy_id: str) -> DeploymentResult:
        data = self._request("get", f"/deployments/{deploy_id}")
        if "_error" in data:
            return DeploymentResult(
                deploy_id=deploy_id,
                status="failed",
                service_name=self._service_name,
                environment=self._environment,
                failure_reason=data["_error"],
            )
        return DeploymentResult(
            deploy_id=data.get("deploy_id", deploy_id),
            status=data.get("status", "failed"),
            service_name=data.get("service_name", self._service_name),
            environment=data.get("environment", self._environment),
            deploy_url=data.get("deploy_url"),
            commit_sha=data.get("commit_sha"),
            failure_reason=data.get("failure_reason"),
            started_at_ms=data.get("started_at_ms"),
            completed_at_ms=data.get("completed_at_ms"),
        )


class MockTrueFoundryClient(TrueFoundryClient):
    """Returns fake succeeded results without HTTP calls. For local dev/testing."""

    def __init__(self, service_name: str = "deepops-demo-app", environment: str = "hackathon") -> None:
        self._api_key = "mock"
        self._base_url = "https://mock.truefoundry.local/v1"
        self._service_name = service_name
        self._environment = environment

    def _fake_result(self, deploy_id: str) -> DeploymentResult:
        now = int(time.time() * 1000)
        return DeploymentResult(
            deploy_id=deploy_id, status="succeeded",
            service_name=self._service_name, environment=self._environment,
            deploy_url=f"https://{self._service_name}.{self._environment}.mock.truefoundry.local",
            started_at_ms=now, completed_at_ms=now,
        )

    def submit_deployment(self, artifact: FixArtifact) -> DeploymentResult:
        return self._fake_result(f"mock-deploy-{uuid.uuid4().hex[:8]}")

    def get_deployment_status(self, deploy_id: str) -> DeploymentResult:
        return self._fake_result(deploy_id)
