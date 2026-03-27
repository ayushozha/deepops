from __future__ import annotations

from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import pytest

from server.integrations.auth0_client import (
    Auth0Client,
    Auth0Config,
    Auth0ConfigError,
    Auth0Error,
    decode_state,
)
from server.services.approval_policy import evaluate_approval_policy


def _config() -> Auth0Config:
    return Auth0Config(
        domain="tenant.example.auth0.com",
        client_id="client-123",
        client_secret="secret-123",
        audience="https://deepops-api",
        redirect_uri="http://localhost:3000/api/auth/callback",
        organization_id="org_123",
        approval_connection="hackathon",
    )


def _incident() -> dict:
    return {
        "incident_id": "inc-abc",
        "severity": "medium",
        "source": {
            "path": "/calculate/0",
            "error_message": "division by zero",
            "provider": "demo-app",
        },
    }


def test_config_from_env_reads_expected_fields() -> None:
    config = Auth0Config.from_env(
        env={
            "AUTH0_DOMAIN": "tenant.example.auth0.com",
            "AUTH0_CLIENT_ID": "client-123",
            "AUTH0_CLIENT_SECRET": "secret-123",
            "AUTH0_AUDIENCE": "https://deepops-api",
            "AUTH0_REDIRECT_URI": "http://localhost:3000/callback",
            "AUTH0_ORGANIZATION_ID": "org_123",
            "AUTH0_APPROVAL_CONNECTION": "hackathon",
            "AUTH0_MANAGEMENT_AUDIENCE": "https://tenant.example.auth0.com/api/v2/",
            "AUTH0_TIMEOUT_SECONDS": "11",
        },
        include_os_env=False,
    )
    assert config.domain == "tenant.example.auth0.com"
    assert config.client_id == "client-123"
    assert config.client_secret == "secret-123"
    assert config.audience == "https://deepops-api"
    assert config.redirect_uri == "http://localhost:3000/callback"
    assert config.organization_id == "org_123"
    assert config.approval_connection == "hackathon"
    assert config.effective_management_audience == "https://tenant.example.auth0.com/api/v2/"
    assert config.timeout_seconds == 11


def test_config_missing_required_values_raises() -> None:
    with pytest.raises(Auth0ConfigError):
        Auth0Config.from_env(env={}, include_os_env=False)


def test_build_authorize_url_encodes_state_and_standard_params() -> None:
    client = Auth0Client(config=_config())
    url = client.build_authorize_url(
        state={"incident_id": "inc-abc", "route": "auto-deploy", "next_action": "deploy"},
        extra_params={"ui_locales": "en"},
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    assert parsed.netloc == "tenant.example.auth0.com"
    assert qs["client_id"] == ["client-123"]
    assert qs["audience"] == ["https://deepops-api"]
    assert qs["redirect_uri"] == ["http://localhost:3000/api/auth/callback"]
    assert qs["organization"] == ["org_123"]
    assert qs["connection"] == ["hackathon"]
    assert qs["ui_locales"] == ["en"]

    decoded = decode_state(qs["state"][0])
    assert decoded["incident_id"] == "inc-abc"
    assert decoded["route"] == "auto-deploy"
    assert decoded["next_action"] == "deploy"


def test_build_approval_request_uses_policy_context() -> None:
    client = Auth0Client(config=_config())
    decision = evaluate_approval_policy(_incident())
    request = client.build_approval_request(_incident(), decision, return_to="/incidents/inc-abc")

    assert request["mode"] == "auto"
    assert request["status"] == "approved"
    assert request["required"] is False
    assert request["auth0_kind"] == "auth0-rbac"
    assert request["state"]["return_to"] == "/incidents/inc-abc"
    assert request["state"]["incident_id"] == "inc-abc"
    assert request["state"]["route"] == "auto-deploy"


def test_build_gate_context_includes_decision_id() -> None:
    client = Auth0Client(config=_config())
    decision = evaluate_approval_policy(
        {"incident_id": "inc-xyz", "severity": "critical", "source": {"error_message": "outage"}}
    )
    context = client.build_gate_context({"incident_id": "inc-xyz"}, decision)

    assert context["incident_id"] == "inc-xyz"
    assert context["requires_phone_escalation"] is True
    assert context["approval"]["state"]["route"] == "phone-escalation"
    assert context["auth0_decision_id"].startswith("auth0-inc-xyz-critical")


def test_fetch_management_token_builds_client_credentials_payload() -> None:
    client = Auth0Client(config=_config())
    with patch.object(client, "_request_json", return_value={"access_token": "token-123"}) as request_json:
        response = client.fetch_management_token()

    assert response["access_token"] == "token-123"
    method, path, body = request_json.call_args.args
    assert method == "POST"
    assert path == "/oauth/token"
    assert body["grant_type"] == "client_credentials"
    assert body["client_id"] == "client-123"
    assert body["client_secret"] == "secret-123"
    assert body["audience"] == "https://tenant.example.auth0.com/api/v2/"


def test_fetch_management_token_can_override_audience_and_scope() -> None:
    client = Auth0Client(config=_config())
    with patch.object(client, "_request_json", return_value={"access_token": "token-123"}) as request_json:
        client.fetch_management_token(audience="https://custom/api", scope="read:users")

    _, _, body = request_json.call_args.args
    assert body["audience"] == "https://custom/api"
    assert body["scope"] == "read:users"


def test_build_authorize_url_requires_redirect_uri() -> None:
    client = Auth0Client(
        config=Auth0Config(
            domain="tenant.example.auth0.com",
            client_id="client-123",
            client_secret="secret-123",
        )
    )
    with pytest.raises(Auth0ConfigError):
        client.build_authorize_url(state={"incident_id": "inc-1"})


def test_request_json_network_error_is_translated() -> None:
    client = Auth0Client(config=_config())
    with patch("server.integrations.auth0_client.urlopen", side_effect=URLError("boom")):
        with pytest.raises(Auth0Error):
            client.fetch_management_token()
