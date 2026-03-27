from __future__ import annotations

import json
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
    """Stores incidents in Aerospike using a single JSON payload bin.

    Aerospike has a 15-character bin name limit. The canonical incident schema
    has field names exceeding that (e.g. resolution_time_ms, affected_components).
    To work around this, we store the full incident as a JSON string in a single
    ``payload`` bin and keep a few short index bins for fast scan filtering.
    """

    # Short index bins (all <=6 chars) used for scan-time filtering
    _BIN_PAYLOAD = "payload"
    _BIN_ID = "iid"
    _BIN_STATUS = "st"
    _BIN_SEVERITY = "sev"
    _BIN_CREATED = "crt_ms"
    _BIN_UPDATED = "upd_ms"

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

    def _to_bins(self, incident: IncidentRecord) -> dict[str, Any]:
        return {
            self._BIN_PAYLOAD: json.dumps(incident),
            self._BIN_ID: incident.get("incident_id", ""),
            self._BIN_STATUS: incident.get("status", ""),
            self._BIN_SEVERITY: incident.get("severity", ""),
            self._BIN_CREATED: incident.get("created_at_ms", 0),
            self._BIN_UPDATED: incident.get("updated_at_ms", 0),
        }

    @staticmethod
    def _from_bins(bins: dict[str, Any]) -> IncidentRecord:
        raw = bins.get("payload")
        if raw is None:
            return normalize_incident(bins)
        return normalize_incident(json.loads(raw))

    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        normalized = normalize_incident(incident)
        self._client.put(self._key(normalized["incident_id"]), self._to_bins(normalized))
        return normalized

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        try:
            _, _, bins = self._client.get(self._key(incident_id))
        except self._aerospike.exception.RecordNotFound:
            return None
        return self._from_bins(bins)

    def list_incidents(self, *, status: str | None = None, limit: int = 50) -> list[IncidentRecord]:
        incidents: list[IncidentRecord] = []

        def _collector(record: tuple[object, object, dict[str, Any]]) -> None:
            if len(incidents) >= limit:
                return
            bins = record[2]
            if status is not None and bins.get("st") != status:
                return
            incidents.append(self._from_bins(bins))

        scan = self._client.scan(self._namespace, self._set_name)
        scan.foreach(_collector)
        incidents.sort(key=lambda incident: incident.get("created_at_ms", 0))
        return incidents[:limit]

    def patch_incident(self, incident_id: str, patch: dict[str, Any]) -> IncidentRecord:
        existing = self.get_incident(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        merged = normalize_incident(deep_merge_dict(existing, patch))
        self._client.put(self._key(incident_id), self._to_bins(merged))
        return merged

    def append_timeline_event(self, incident_id: str, event: TimelineEvent) -> IncidentRecord:
        existing = self.get_incident(incident_id)
        if existing is None:
            raise KeyError(f"Incident not found: {incident_id}")
        updated_timeline = [*existing.get("timeline", []), deepcopy(event)]
        return self.patch_incident(incident_id, {"timeline": updated_timeline})
