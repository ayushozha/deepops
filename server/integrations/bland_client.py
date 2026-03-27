from __future__ import annotations

import logging
import os
import time
from typing import Any

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    _HAS_HTTPX = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class BlandError(Exception):
    """Base exception for all Bland AI errors."""


class BlandConfigError(BlandError):
    """Raised when the Bland client is misconfigured (e.g. missing API key)."""


class BlandAPIError(BlandError):
    """Raised when the Bland API returns a non-success response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Bland API error {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class BlandClient:
    """Async client for the Bland AI outbound-call API.

    Uses httpx for async HTTP.  Falls back to a synchronous stub when httpx is
    unavailable so the module can still be imported (useful for tests and dry
    runs).
    """

    DEFAULT_VOICE = "nat"
    DEFAULT_MAX_DURATION = 5  # minutes

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.bland.ai/v1",
    ) -> None:
        self._api_key = api_key or os.environ.get("BLAND_API_KEY", "")
        if not self._api_key:
            raise BlandConfigError(
                "Bland API key not provided and BLAND_API_KEY env var is not set"
            )
        self._base_url = base_url.rstrip("/")

    # -- internal helpers ---------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

    async def _async_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise BlandError("httpx is required for async Bland calls")
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=self._headers())
        if resp.status_code >= 300:
            raise BlandAPIError(resp.status_code, resp.text)
        return resp.json()

    async def _async_get(self, path: str) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise BlandError("httpx is required for async Bland calls")
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())
        if resp.status_code >= 300:
            raise BlandAPIError(resp.status_code, resp.text)
        return resp.json()

    # -- public API ---------------------------------------------------------

    def build_call_script(self, incident: dict) -> str:
        """Generate the voice script text for the Bland AI call.

        Critical incidents get an urgent tone; high-severity incidents use a
        calmer notification style.
        """
        severity = (incident.get("severity") or "high").lower()

        source = incident.get("source") or {}
        error_message = source.get("error_message") or incident.get("error_message", "unknown error")

        diagnosis = incident.get("diagnosis") or {}
        root_cause = diagnosis.get("root_cause") or "undetermined"
        suggested_fix = diagnosis.get("suggested_fix") or "no automated fix available"
        affected = diagnosis.get("affected_components") or source.get("affected_components") or []
        if isinstance(affected, list):
            affected = ", ".join(affected) if affected else "unknown components"

        incident_id = incident.get("incident_id") or incident.get("id") or "unknown"

        if severity == "critical":
            script = (
                f"This is DeepOps automated incident response. "
                f"We have a critical incident, ID {incident_id}. "
                f"The error is: {error_message}. "
                f"Root cause: {root_cause}. "
                f"Our system has prepared a fix: {suggested_fix}. "
                f"This affects {affected}. "
                f"Do you approve immediate deployment?"
            )
        else:
            # high severity (default)
            script = (
                f"This is DeepOps incident notification. "
                f"We detected a high-severity issue, ID {incident_id}. "
                f"The error is: {error_message}. "
                f"The root cause is: {root_cause}. "
                f"A fix has been prepared: {suggested_fix}. "
                f"This affects {affected}. "
                f"Would you like to approve deployment?"
            )

        return script

    def build_call_payload(
        self,
        incident: dict,
        phone_number: str,
        webhook_url: str | None = None,
    ) -> dict:
        """Build the Bland API request body for an escalation call.

        See https://docs.bland.ai/api-v1/post/calls for the expected schema.
        """
        script = self.build_call_script(incident)
        incident_id = incident.get("incident_id") or incident.get("id") or "unknown"

        payload: dict[str, Any] = {
            "phone_number": phone_number,
            "task": script,
            "voice": self.DEFAULT_VOICE,
            "reduce_latency": True,
            "max_duration": self.DEFAULT_MAX_DURATION,
            "record": True,
            "metadata": {
                "incident_id": incident_id,
                "severity": (incident.get("severity") or "high").lower(),
            },
            "analysis_schema": {
                "decision": "string - approved, rejected, or pending",
                "notes": "string - any additional context from the engineer",
            },
        }

        if webhook_url:
            payload["webhook"] = webhook_url

        return payload

    async def send_escalation_call(
        self,
        incident: dict,
        phone_number: str,
        webhook_url: str | None = None,
    ) -> dict:
        """Send a voice call to escalate an incident.

        Returns
        -------
        dict
            ``{ "call_id": str, "status": str, "queued_at_ms": int }``
        """
        payload = self.build_call_payload(incident, phone_number, webhook_url)
        logger.info(
            "Sending Bland escalation call for incident %s to %s",
            payload["metadata"]["incident_id"],
            phone_number,
        )
        try:
            data = await self._async_post("/calls", payload)
        except BlandAPIError:
            raise
        except Exception as exc:
            raise BlandError(f"Failed to send escalation call: {exc}") from exc

        return {
            "call_id": data.get("call_id", ""),
            "status": data.get("status", "queued"),
            "queued_at_ms": int(time.time() * 1000),
        }

    async def get_call_status(self, call_id: str) -> dict:
        """Check the status of an existing call."""
        try:
            data = await self._async_get(f"/calls/{call_id}")
        except BlandAPIError:
            raise
        except Exception as exc:
            raise BlandError(f"Failed to get call status: {exc}") from exc
        return data

    async def health_check(self) -> bool:
        """Check if Bland API is reachable.

        Returns True when the API responds with a 2xx on GET /calls.
        """
        try:
            await self._async_get("/calls")
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Mock for local dev / testing (mirrors MockTrueFoundryClient pattern)
# ---------------------------------------------------------------------------

class MockBlandClient(BlandClient):
    """Returns fake results without making HTTP calls."""

    def __init__(self) -> None:
        # Bypass the real __init__ which requires an API key.
        self._api_key = "mock"
        self._base_url = "https://mock.bland.local/v1"

    async def send_escalation_call(
        self,
        incident: dict,
        phone_number: str,
        webhook_url: str | None = None,
    ) -> dict:
        import uuid
        now = int(time.time() * 1000)
        return {
            "call_id": f"mock-call-{uuid.uuid4().hex[:8]}",
            "status": "queued",
            "queued_at_ms": now,
        }

    async def get_call_status(self, call_id: str) -> dict:
        return {"call_id": call_id, "status": "completed"}

    async def health_check(self) -> bool:
        return True
