from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from config import Settings
from agent.contracts import IncidentRecord, TimelineEvent, deep_merge_dict, normalize_incident


class IncidentStore(Protocol):
    def create_incident(self, incident: IncidentRecord) -> IncidentRecord: ...

    def get_incident(self, incident_id: str) -> IncidentRecord | None: ...

    def list_incidents(self, *, status: str | None = None, limit: int = 50) -> list[IncidentRecord]: ...

    def patch_incident(self, incident_id: str, patch: dict[str, Any]) -> IncidentRecord: ...

    def append_timeline_event(self, incident_id: str, event: TimelineEvent) -> IncidentRecord: ...


class InMemoryIncidentStore:
    def __init__(self, incidents: list[IncidentRecord] | None = None) -> None:
        self._incidents: dict[str, IncidentRecord] = {}
        for incident in incidents or []:
            self.create_incident(incident)

    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        normalized = normalize_incident(incident)
        self._incidents[normalized["incident_id"]] = deepcopy(normalized)
        return deepcopy(normalized)

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        incident = self._incidents.get(incident_id)
        return deepcopy(incident) if incident is not None else None

    def list_incidents(self, *, status: str | None = None, limit: int = 50) -> list[IncidentRecord]:
        incidents = list(self._incidents.values())
        incidents.sort(key=lambda incident: incident.get("created_at_ms", 0))
        if status is not None:
            incidents = [incident for incident in incidents if incident.get("status") == status]
        return [deepcopy(incident) for incident in incidents[:limit]]

    def patch_incident(self, incident_id: str, patch: dict[str, Any]) -> IncidentRecord:
        existing = self._incidents.get(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        merged = normalize_incident(deep_merge_dict(existing, patch))
        self._incidents[incident_id] = merged
        return deepcopy(merged)

    def append_timeline_event(self, incident_id: str, event: TimelineEvent) -> IncidentRecord:
        existing = self._incidents.get(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        updated_timeline = [*existing.get("timeline", []), deepcopy(event)]
        return self.patch_incident(incident_id, {"timeline": updated_timeline})


class AerospikeIncidentStore:
    def __init__(self, settings: Settings) -> None:
        try:
            import aerospike  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Aerospike client is not installed.") from exc

        self._aerospike = aerospike
        self._namespace = settings.aerospike_namespace
        self._set_name = settings.aerospike_set
        self._client = aerospike.client({"hosts": [(settings.aerospike_host, settings.aerospike_port)]}).connect()

    def _key(self, incident_id: str) -> tuple[str, str, str]:
        return (self._namespace, self._set_name, incident_id)

    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        normalized = normalize_incident(incident)
        self._client.put(self._key(normalized["incident_id"]), normalized)
        return normalized

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        try:
            _, _, bins = self._client.get(self._key(incident_id))
        except self._aerospike.exception.RecordNotFound:
            return None
        return normalize_incident(bins)

    def list_incidents(self, *, status: str | None = None, limit: int = 50) -> list[IncidentRecord]:
        incidents: list[IncidentRecord] = []

        def _collector(record: tuple[object, object, dict[str, Any]]) -> None:
            if len(incidents) >= limit:
                return
            normalized = normalize_incident(record[2])
            if status is None or normalized.get("status") == status:
                incidents.append(normalized)

        scan = self._client.scan(self._namespace, self._set_name)
        scan.foreach(_collector)
        incidents.sort(key=lambda incident: incident.get("created_at_ms", 0))
        return incidents[:limit]

    def patch_incident(self, incident_id: str, patch: dict[str, Any]) -> IncidentRecord:
        existing = self.get_incident(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        merged = normalize_incident(deep_merge_dict(existing, patch))
        self._client.put(self._key(incident_id), merged)
        return merged

    def append_timeline_event(self, incident_id: str, event: TimelineEvent) -> IncidentRecord:
        existing = self.get_incident(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        updated_timeline = [*existing.get("timeline", []), deepcopy(event)]
        return self.patch_incident(incident_id, {"timeline": updated_timeline})
