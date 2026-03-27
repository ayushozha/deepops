from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/run-once")
async def run_agent_once(request: Request, incident_id: str | None = None) -> JSONResponse:
    context = request.app.state.context
    try:
        result = await context.workflow.run_once(incident_id=incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse({"ok": True, **result})
