from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from server.services.escalation_service import EscalationService

router = APIRouter(prefix="/api/escalation", tags=["escalation"])


def _service(request: Request) -> EscalationService:
    service = getattr(request.app.state.context, "escalation", None)
    if service is None:
        raise RuntimeError("Escalation service is not configured on the app context.")
    return service


class EscalationTriggerBody(BaseModel):
    phone_number: str = Field(min_length=7)
    webhook_url: str | None = None
    reason: str | None = None
    force: bool = False
    dry_run: bool = False


@router.post("/{incident_id}/trigger")
async def trigger_escalation(request: Request, incident_id: str, body: EscalationTriggerBody) -> dict:
    try:
        result = await _service(request).trigger_escalation(
            incident_id,
            phone_number=body.phone_number,
            webhook_url=body.webhook_url,
            reason=body.reason,
            force=body.force,
            dry_run=body.dry_run,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "incident": result.incident,
        "request_payload": result.request_payload,
        "call_result": result.call_result,
        "timeline_event": result.timeline_event,
        "escalated": result.escalated,
    }
