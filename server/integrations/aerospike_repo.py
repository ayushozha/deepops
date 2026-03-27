from __future__ import annotations

from pathlib import Path
import json

from agent.contracts import IncidentRecord, normalize_incident
from agent.store_adapter import AerospikeIncidentStore, InMemoryIncidentStore, IncidentStore
from config import Settings


def build_incident_store(settings: Settings) -> IncidentStore:
    try:
        return AerospikeIncidentStore(settings)
    except RuntimeError:
        if not settings.allow_in_memory_store:
            raise
        return InMemoryIncidentStore()


def seed_incidents_from_path(store: IncidentStore, path: str | Path) -> list[IncidentRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]

    created: list[IncidentRecord] = []
    for item in payload:
        incident = normalize_incident(item)
        created.append(store.create_incident(incident))
    return created
