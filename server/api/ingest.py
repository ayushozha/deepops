from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _context(request: Request):
    return request.app.state.context


class DemoTriggerBody(BaseModel):
    bug_key: str


class DemoAppErrorBody(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class AirbyteSyncBody(BaseModel):
    connection_id: str


@router.post("/demo-trigger")
async def ingest_demo_trigger(request: Request, body: DemoTriggerBody) -> dict[str, Any]:
    context = _context(request)
    try:
        incident = await context.ingestion.ingest_demo_trigger(body.bug_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    created = context.incidents.create_incident(
        incident,
        actor="ingest-api",
        sponsor="Demo App",
        message=f"Demo trigger '{body.bug_key}' ingested.",
    )
    return {"incident": created, "provider": "demo-trigger", "bug_key": body.bug_key}


@router.post("/demo-app")
async def ingest_demo_app_error(request: Request, body: DemoAppErrorBody) -> dict[str, Any]:
    context = _context(request)
    incident = await context.ingestion.ingest_demo_app_error(body.payload)
    created = context.incidents.create_incident(
        incident,
        actor="ingest-api",
        sponsor="Demo App",
        message="Demo app error ingested.",
    )
    return {"incident": created, "provider": "demo-app"}


@router.post("/airbyte-sync")
async def ingest_airbyte_sync(request: Request, body: AirbyteSyncBody) -> dict[str, Any]:
    context = _context(request)
    try:
        incidents = await context.ingestion.ingest_airbyte_sync(body.connection_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    created: list[dict[str, Any]] = []
    for incident in incidents:
        created.append(
            context.incidents.create_incident(
                incident,
                actor="ingest-api",
                sponsor="Airbyte",
                message=f"Airbyte sync '{body.connection_id}' generated an incident.",
            )
        )
    return {"incidents": created, "provider": "airbyte", "connection_id": body.connection_id}
