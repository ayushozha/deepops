from __future__ import annotations

from dataclasses import dataclass

from agent.contracts import (
    APPROVAL_PENDING,
    STATUS_AWAITING_APPROVAL,
    STATUS_BLOCKED,
    STATUS_DEPLOYING,
    make_timeline_event,
    now_ms,
)
from server.services.incident_service import IncidentService


@dataclass
class GatingService:
    incidents: IncidentService

    def apply_decision(
        self,
        incident_id: str,
        *,
        approved: bool,
        actor: str,
        sponsor: str,
        mode: str,
        notes: str | None = None,
        channel: str | None = None,
        decider: str | None = None,
    ) -> dict:
        incident = self.incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(f"Incident not found: {incident_id}")

        severity = incident.get("severity", "medium")
        requires_manual = severity in {"high", "critical"}
        target_status = STATUS_DEPLOYING if approved else STATUS_BLOCKED
        if requires_manual and approved is None:
            target_status = STATUS_AWAITING_APPROVAL

        approval_patch = {
            "required": requires_manual,
            "mode": mode,
            "status": "approved" if approved else "denied",
            "channel": channel,
            "decider": decider,
            "notes": notes,
            "decision_at_ms": now_ms(),
        }
        timeline_message = "Approval granted; deployment can proceed." if approved else "Approval denied; incident blocked."
        event = make_timeline_event(
            status=target_status,
            actor=actor,
            message=timeline_message,
            sponsor=sponsor,
            metadata={"approval": approval_patch},
        )
        return self.incidents.patch_incident(
            incident_id,
            {
                "status": target_status,
                "approval": approval_patch,
            },
            timeline_event=event,
        )

    def mark_pending_manual_review(
        self,
        incident_id: str,
        *,
        actor: str,
        sponsor: str,
        notes: str | None = None,
        channel: str = "voice_call",
    ) -> dict:
        event = make_timeline_event(
            status=STATUS_AWAITING_APPROVAL,
            actor=actor,
            message="Manual approval required before deployment.",
            sponsor=sponsor,
            metadata={"notes": notes, "channel": channel},
        )
        return self.incidents.patch_incident(
            incident_id,
            {
                "status": STATUS_AWAITING_APPROVAL,
                "approval": {
                    "required": True,
                    "mode": "manual",
                    "status": APPROVAL_PENDING,
                    "channel": channel,
                    "notes": notes,
                },
            },
            timeline_event=event,
        )
