from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent.contracts import IncidentRecord, make_timeline_event, normalize_incident
from agent.store_adapter import IncidentStore
from server.services.realtime_hub import RealtimeHub


@dataclass
class IncidentService:
    store: IncidentStore
    realtime_hub: RealtimeHub

    def list_incidents(self, *, status: str | None = None, limit: int = 50) -> list[IncidentRecord]:
        return self.store.list_incidents(status=status, limit=limit)

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        return self.store.get_incident(incident_id)

    def create_incident(
        self,
        payload: Mapping[str, Any],
        *,
        actor: str = "backend-api",
        sponsor: str = "FastAPI",
        message: str = "Incident created via backend API.",
    ) -> IncidentRecord:
        incident = normalize_incident(payload)
        created = self.store.create_incident(incident)
        timeline_event = None
        if not created.get("timeline"):
            timeline_event = make_timeline_event(
                status=created["status"],
                actor=actor,
                message=message,
                sponsor=sponsor,
            )
            created = self.store.append_timeline_event(created["incident_id"], timeline_event)
        self.realtime_hub.publish("incident.created", created, timeline_event=timeline_event)
        return created

    def patch_incident(
        self,
        incident_id: str,
        patch: Mapping[str, Any],
        *,
        event_type: str = "incident.updated",
        timeline_event: Mapping[str, Any] | None = None,
    ) -> IncidentRecord:
        updated = self.store.patch_incident(incident_id, dict(patch))
        if timeline_event is not None:
            updated = self.store.append_timeline_event(incident_id, dict(timeline_event))
        self.realtime_hub.publish(event_type, updated, timeline_event=timeline_event)
        return updated

    def append_timeline_event(self, incident_id: str, event: Mapping[str, Any]) -> IncidentRecord:
        updated = self.store.append_timeline_event(incident_id, dict(event))
        self.realtime_hub.publish("incident.updated", updated, timeline_event=event)
        return updated
