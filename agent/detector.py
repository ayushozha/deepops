from __future__ import annotations

from typing import Iterable

from agent.contracts import IncidentRecord, STATUS_STORED, normalize_incident
from agent.store_adapter import IncidentStore


def detect_ready_incidents(
    store: IncidentStore,
    *,
    limit: int = 10,
    allowed_statuses: Iterable[str] = (STATUS_STORED,),
) -> list[IncidentRecord]:
    allowed = set(allowed_statuses)
    incidents = store.list_incidents(limit=limit)
    return [normalize_incident(incident) for incident in incidents if incident.get("status") in allowed]
