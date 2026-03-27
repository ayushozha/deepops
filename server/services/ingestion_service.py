"""Ingestion service — turns raw external signals into canonical incidents."""

from __future__ import annotations

import logging
from typing import Any

from server.normalizers.incident_normalizer import (
    normalize_airbyte_record,
    normalize_demo_app_error,
    normalize_demo_trigger,
)

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates ingestion from demo app, Airbyte, or manual triggers.

    This service normalizes raw payloads into schema-valid incidents.
    It does NOT write to Aerospike — that is the caller's responsibility.
    """

    def __init__(self, demo_client=None, airbyte_client=None) -> None:
        self.demo_client = demo_client
        self.airbyte_client = airbyte_client

    async def ingest_demo_trigger(self, bug_key: str) -> dict:
        """Create a stored incident from a demo trigger key."""
        logger.info("Ingesting demo trigger: %s", bug_key)

        raw_payload = None
        if self.demo_client:
            try:
                raw_payload = await self.demo_client.trigger_bug(bug_key)
            except Exception as e:
                logger.warning("Demo app trigger failed: %s. Continuing with fixture.", e)

        incident = normalize_demo_trigger(bug_key, raw_payload)
        logger.info("Demo trigger ingested: %s -> %s", bug_key, incident["incident_id"])
        return incident

    async def ingest_demo_app_error(self, raw_error: dict) -> dict:
        """Create a stored incident from a raw demo app error event."""
        logger.info("Ingesting demo app error: %s", raw_error.get("error_type", "unknown"))
        incident = normalize_demo_app_error(raw_error)
        logger.info("Demo app error ingested: %s", incident["incident_id"])
        return incident

    async def ingest_airbyte_sync(self, connection_id: str) -> list[dict]:
        """Trigger Airbyte sync, read results, normalize into incidents."""
        if not self.airbyte_client:
            raise RuntimeError("AirbyteClient not configured")

        logger.info("Triggering Airbyte sync for connection: %s", connection_id)
        sync_result = await self.airbyte_client.trigger_sync(connection_id)
        job_id = sync_result.get("job_id", "unknown")

        status = await self.airbyte_client.get_sync_status(job_id)
        logger.info("Airbyte sync %s status: %s", job_id, status.get("status"))

        records = await self.airbyte_client.read_synced_records(connection_id)
        logger.info("Airbyte returned %d records", len(records))

        incidents = []
        for record in records:
            incident = normalize_airbyte_record(record, sync_id=job_id)
            incidents.append(incident)

        logger.info("Normalized %d Airbyte records into incidents", len(incidents))
        return incidents

    async def ingest_raw_payload(self, payload: dict, provider: str = "demo-app") -> dict:
        """Generic ingestion entry point for arbitrary payloads."""
        logger.info("Ingesting raw payload from provider: %s", provider)
        if provider == "airbyte":
            return normalize_airbyte_record(payload)
        return normalize_demo_app_error(payload)
