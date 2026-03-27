from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from server.services.incident_service import IncidentService

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _service(request: Request) -> IncidentService:
    return request.app.state.context.incidents


class CreateIncidentBody(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_incidents(
    request: Request,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return _service(request).list_incidents(status=status, limit=limit)


@router.get("/{incident_id}")
async def get_incident(request: Request, incident_id: str) -> dict[str, Any]:
    incident = _service(request).get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("")
async def create_incident(request: Request, body: CreateIncidentBody) -> dict[str, Any]:
    return _service(request).create_incident(body.incident)
