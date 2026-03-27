"""Client for the DeepOps demo application."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_FIXTURE_ERRORS = [
    {
        "path": "/calculate/0",
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero",
        "source_file": "demo-app/main.py",
        "method": "GET",
        "status_code": 500,
    },
    {
        "path": "/user/unknown",
        "error_type": "KeyError",
        "error_message": "'name'",
        "source_file": "demo-app/main.py",
        "method": "GET",
        "status_code": 500,
    },
    {
        "path": "/search",
        "error_type": "TimeoutError",
        "error_message": "search endpoint timed out",
        "source_file": "demo-app/main.py",
        "method": "GET",
        "status_code": 504,
    },
]


class DemoAppClient:
    """Client for polling errors and triggering bugs on the demo app."""

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        fallback_mode: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.fallback_mode = fallback_mode
        self._timeout = 10.0

    @classmethod
    def from_settings(cls, settings) -> "DemoAppClient":
        """Create client from Settings object."""
        base = getattr(settings, "demo_app_base_url", None) or getattr(settings, "demo_app_url", "http://localhost:8001")
        fallback = getattr(settings, "demo_app_fallback_mode", True)
        return cls(base_url=base, fallback_mode=fallback)

    async def poll_recent_errors(self, since_ms: int | None = None) -> list[dict]:
        """Poll the demo app for recent errors."""
        if self.fallback_mode:
            logger.debug("Fallback mode: returning fixture errors")
            return list(_FIXTURE_ERRORS)

        params = {}
        if since_ms is not None:
            params["since"] = since_ms

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self.base_url}/errors", params=params)
            resp.raise_for_status()
            return resp.json().get("errors", [])

    async def trigger_bug(self, bug_key: str) -> dict:
        """Trigger a known bug scenario on the demo app."""
        route_map = {
            "calculate_zero": "/calculate/0",
            "user_missing": "/user/unknown",
            "search_timeout": "/search",
        }

        if self.fallback_mode:
            for err in _FIXTURE_ERRORS:
                if err["path"] == route_map.get(bug_key):
                    return err
            return _FIXTURE_ERRORS[0]

        route = route_map.get(bug_key)
        if not route:
            raise ValueError(f"Unknown bug_key: {bug_key}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(f"{self.base_url}{route}")
                return {
                    "path": route,
                    "status_code": resp.status_code,
                    "body": resp.text[:500],
                }
            except httpx.HTTPError as e:
                return {"path": route, "error": str(e)}

    async def health_check(self) -> bool:
        """Check if the demo app is reachable."""
        if self.fallback_mode:
            return True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
