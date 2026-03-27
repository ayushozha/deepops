from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from server.services.approval_policy import ApprovalPolicyDecision


class Auth0Error(Exception):
    """Base exception for Auth0 wrapper failures."""


class Auth0ConfigError(Auth0Error):
    """Raised when required Auth0 configuration is missing."""


class Auth0APIError(Auth0Error):
    """Raised when Auth0 responds with an error."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Auth0 API error {status_code}: {detail}")


def _normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme and parsed.netloc:
        return parsed.netloc.rstrip("/")
    return value.strip().rstrip("/")


def _encode_state(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii")
    return encoded.rstrip("=")


def decode_state(token: str) -> dict[str, Any]:
    padding = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode((token + padding).encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise Auth0Error("Decoded Auth0 state must be a JSON object")
    return payload


@dataclass(frozen=True)
class Auth0Config:
    domain: str
    client_id: str
    client_secret: str
    audience: str = ""
    redirect_uri: str = ""
    scope: str = "openid profile email"
    organization_id: str | None = None
    approval_connection: str | None = None
    approval_prompt: str = "login"
    management_audience: str = ""
    timeout_seconds: int = 30

    def validate(self) -> None:
        missing: list[str] = []
        if not self.domain.strip():
            missing.append("AUTH0_DOMAIN")
        if not self.client_id.strip():
            missing.append("AUTH0_CLIENT_ID")
        if not self.client_secret.strip():
            missing.append("AUTH0_CLIENT_SECRET")
        if missing:
            raise Auth0ConfigError("Missing Auth0 configuration: " + ", ".join(missing))

    @property
    def base_url(self) -> str:
        return f"https://{self.domain.strip().rstrip('/')}"

    @property
    def effective_management_audience(self) -> str:
        if self.management_audience.strip():
            return self.management_audience.strip()
        return f"{self.base_url}/api/v2/"

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        include_os_env: bool = True,
    ) -> "Auth0Config":
        values: dict[str, str] = {}
        if include_os_env:
            values.update(os.environ)
        if env:
            values.update(env)

        config = cls(
            domain=_normalize_url(values.get("AUTH0_DOMAIN", "")),
            client_id=values.get("AUTH0_CLIENT_ID", "").strip(),
            client_secret=values.get("AUTH0_CLIENT_SECRET", "").strip(),
            audience=values.get("AUTH0_AUDIENCE", "").strip(),
            redirect_uri=values.get("AUTH0_REDIRECT_URI", values.get("AUTH0_CALLBACK_URL", "")).strip(),
            scope=values.get("AUTH0_SCOPE", "openid profile email").strip() or "openid profile email",
            organization_id=values.get("AUTH0_ORGANIZATION_ID", "").strip() or None,
            approval_connection=values.get("AUTH0_APPROVAL_CONNECTION", values.get("AUTH0_CONNECTION", "")).strip() or None,
            approval_prompt=values.get("AUTH0_APPROVAL_PROMPT", "login").strip() or "login",
            management_audience=values.get("AUTH0_MANAGEMENT_AUDIENCE", "").strip(),
            timeout_seconds=int(values.get("AUTH0_TIMEOUT_SECONDS", "30")),
        )
        config.validate()
        return config


class Auth0Client:
    def __init__(
        self,
        config: Auth0Config | None = None,
        *,
        env: Mapping[str, str] | None = None,
        include_os_env: bool = True,
    ) -> None:
        self._config = config or Auth0Config.from_env(env=env, include_os_env=include_os_env)
        self._config.validate()

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        include_os_env: bool = True,
    ) -> "Auth0Client":
        return cls(env=env, include_os_env=include_os_env)

    @property
    def config(self) -> Auth0Config:
        return self._config

    def build_authorize_url(
        self,
        *,
        state: Mapping[str, Any] | str | None = None,
        redirect_uri: str | None = None,
        audience: str | None = None,
        scope: str | None = None,
        prompt: str | None = None,
        connection: str | None = None,
        login_hint: str | None = None,
        screen_hint: str | None = None,
        organization_id: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
    ) -> str:
        actual_redirect_uri = (redirect_uri or self._config.redirect_uri).strip()
        if not actual_redirect_uri:
            raise Auth0ConfigError("AUTH0_REDIRECT_URI or redirect_uri is required to build an authorize URL")

        if isinstance(state, Mapping):
            state_value = _encode_state(state)
        elif isinstance(state, str):
            state_value = state
        else:
            state_value = ""

        params: dict[str, Any] = {
            "client_id": self._config.client_id,
            "response_type": "code",
            "redirect_uri": actual_redirect_uri,
            "scope": scope or self._config.scope,
        }
        if state_value:
            params["state"] = state_value
        if audience or self._config.audience:
            params["audience"] = audience or self._config.audience
        if prompt or self._config.approval_prompt:
            params["prompt"] = prompt or self._config.approval_prompt
        if connection or self._config.approval_connection:
            params["connection"] = connection or self._config.approval_connection
        if login_hint:
            params["login_hint"] = login_hint
        if screen_hint:
            params["screen_hint"] = screen_hint
        if organization_id or self._config.organization_id:
            params["organization"] = organization_id or self._config.organization_id
        if extra_params:
            for key, value in extra_params.items():
                if value is not None:
                    params[key] = value

        return f"{self._config.base_url}/authorize?{urlencode(params, doseq=True)}"

    def build_approval_request(
        self,
        incident: Mapping[str, Any],
        decision: ApprovalPolicyDecision,
        *,
        redirect_uri: str | None = None,
        return_to: str | None = None,
        login_hint: str | None = None,
        extra_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        incident_id = incident.get("incident_id") if isinstance(incident.get("incident_id"), str) else None
        state_payload: dict[str, Any] = {
            "incident_id": incident_id,
            "severity": decision.severity,
            "route": decision.route,
            "next_action": decision.next_action,
            "required": decision.required,
            "mode": decision.mode,
            "status": decision.status,
            "requires_phone_escalation": decision.requires_phone_escalation,
        }
        if return_to:
            state_payload["return_to"] = return_to
        if extra_state:
            state_payload.update(extra_state)

        authorization_url = self.build_authorize_url(
            state=state_payload,
            redirect_uri=redirect_uri,
            audience=self._config.audience or None,
            scope=self._config.scope,
            prompt=self._config.approval_prompt,
            connection=self._config.approval_connection,
            login_hint=login_hint,
            organization_id=self._config.organization_id,
        )

        return {
            "authorization_url": authorization_url,
            "state": state_payload,
            "state_token": _encode_state(state_payload),
            "channel": decision.channel,
            "decider": decision.decider,
            "mode": decision.mode,
            "status": decision.status,
            "required": decision.required,
            "requires_phone_escalation": decision.requires_phone_escalation,
            "auth0_kind": decision.approval_kind,
        }

    def build_decision_id(self, incident: Mapping[str, Any], decision: ApprovalPolicyDecision) -> str:
        incident_id = incident.get("incident_id") if isinstance(incident.get("incident_id"), str) else "incident"
        severity = decision.severity or "pending"
        return f"auth0-{incident_id}-{severity}-{decision.route}"

    def fetch_management_token(
        self,
        *,
        audience: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "audience": audience or self._config.effective_management_audience,
        }
        if scope:
            payload["scope"] = scope
        return self._request_json("POST", "/oauth/token", payload)

    def build_gate_context(
        self,
        incident: Mapping[str, Any],
        decision: ApprovalPolicyDecision,
        *,
        redirect_uri: str | None = None,
        return_to: str | None = None,
        login_hint: str | None = None,
    ) -> dict[str, Any]:
        approval_request = self.build_approval_request(
            incident,
            decision,
            redirect_uri=redirect_uri,
            return_to=return_to,
            login_hint=login_hint,
        )
        return {
            "incident_id": incident.get("incident_id"),
            "severity": decision.severity,
            "approval": approval_request,
            "auth0_decision_id": self.build_decision_id(incident, decision),
            "requires_phone_escalation": decision.requires_phone_escalation,
            "next_action": decision.next_action,
        }

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _request_json(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._config.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise Auth0APIError(exc.code, detail) from exc
        except URLError as exc:
            raise Auth0Error(f"Auth0 request failed: {exc.reason}") from exc

        if status >= 300:
            raise Auth0APIError(status, payload)
        if not payload:
            return {}
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise Auth0Error("Auth0 responses must be JSON objects")
        return result
