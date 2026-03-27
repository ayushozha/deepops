"""Tests for server/integrations/truefoundry_client.py"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from server.integrations.truefoundry_client import (
    TrueFoundryClient,
    MockTrueFoundryClient,
    DeploymentResult,
)
from server.services.fix_artifact_service import FixArtifact


def _artifact() -> FixArtifact:
    return FixArtifact(
        incident_id="inc-test-1",
        source_path="demo-app/main.py",
        error_type="ZeroDivisionError",
        kiro_mode="fallback",
    )


def test_missing_api_key_raises():
    with pytest.raises(RuntimeError, match="TRUEFOUNDRY_API_KEY"):
        TrueFoundryClient(api_key="")


def test_submit_deployment_http_error():
    client = TrueFoundryClient(api_key="test-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("server.integrations.truefoundry_client._http_lib") as mock_lib:
        mock_lib.post.return_value = mock_resp
        result = client.submit_deployment(_artifact())

    assert result.status == "failed"
    assert result.failure_reason is not None


def test_submit_deployment_connection_error():
    client = TrueFoundryClient(api_key="test-key")

    with patch("server.integrations.truefoundry_client._http_lib") as mock_lib:
        mock_lib.post.side_effect = Exception("connection refused")
        result = client.submit_deployment(_artifact())

    assert result.status == "failed"


def test_mock_client_submit_returns_succeeded():
    client = MockTrueFoundryClient()
    result = client.submit_deployment(_artifact())
    assert result.status == "succeeded"


def test_mock_client_get_status_returns_succeeded():
    client = MockTrueFoundryClient()
    result = client.get_deployment_status("any-id")
    assert result.status == "succeeded"


def test_deployment_result_has_required_fields():
    client = MockTrueFoundryClient()
    result = client.submit_deployment(_artifact())
    assert result.deploy_id
    assert result.status
    assert result.service_name
    assert result.environment
