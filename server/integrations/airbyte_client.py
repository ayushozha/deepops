"""Client for the Airbyte data integration platform."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class AirbyteClient:
    """Wrapper around the Airbyte API for triggering syncs and reading records."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000/api/v1",
        api_key: str | None = None,
        fallback_mode: bool = False,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or os.environ.get("AIRBYTE_API_KEY")
        self.fallback_mode = fallback_mode
        self._timeout = 15.0

    @classmethod
    def from_settings(cls, settings) -> "AirbyteClient":
        """Create client from Settings object."""
        fallback = getattr(settings, "airbyte_fallback_mode", not bool(settings.airbyte_api_key))
        return cls(
            api_url=settings.airbyte_api_url,
            api_key=settings.airbyte_api_key,
            fallback_mode=fallback,
        )

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def trigger_sync(self, connection_id: str) -> dict:
        """Trigger a sync job on an Airbyte connection."""
        if self.fallback_mode:
            return {"job_id": "fallback-job-001", "status": "running", "connection_id": connection_id}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.api_url}/connections/sync",
                json={"connectionId": connection_id},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_sync_status(self, job_id: str) -> dict:
        """Check the status of a sync job."""
        if self.fallback_mode:
            return {"job_id": job_id, "status": "succeeded"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.api_url}/jobs/{job_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def read_synced_records(self, connection_id: str, limit: int = 50) -> list[dict]:
        """Read records from the most recent sync."""
        if self.fallback_mode:
            return [
                {
                    "path": "/calculate/0",
                    "error_type": "ZeroDivisionError",
                    "error_message": "division by zero",
                    "source_file": "demo-app/main.py",
                    "timestamp_ms": 1774647600000,
                },
            ]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.api_url}/connections/{connection_id}/records",
                params={"limit": limit},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("records", [])

    async def health_check(self) -> bool:
        """Check if Airbyte is reachable."""
        if self.fallback_mode:
            return True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/health",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False
