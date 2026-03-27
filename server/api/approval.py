from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/approval", tags=["approval"])


class ApprovalDecisionBody(BaseModel):
    approved: bool | None = None
    decision: str | None = None
    notes: str | None = None
    channel: str | None = None
    decider: str | None = None
    actor: str = "approval-api"
    sponsor: str = "Auth0"
    mode: str = "manual"
    suggested_steps: list[str] = []
    constraints: list[str] = []


def _decision_text(body: ApprovalDecisionBody) -> str:
    if body.decision:
        return body.decision
    if body.approved is True:
        return "approve"
    if body.approved is False:
        return "reject"
    return body.notes or "clarify"


@router.post("/{incident_id}/decision")
async def apply_approval_decision(
    request: Request,
    incident_id: str,
    body: ApprovalDecisionBody,
) -> dict:
    try:
        return await request.app.state.context.workflow.apply_human_decision(
            incident_id,
            decision_text=_decision_text(body),
            actor=body.actor,
            sponsor=body.sponsor,
            notes=body.notes,
            channel=body.channel,
            decider=body.decider,
            suggested_steps=body.suggested_steps,
            constraints=body.constraints,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
