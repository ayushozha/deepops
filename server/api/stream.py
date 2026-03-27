from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from server.services.realtime_hub import RealtimeHub, encode_sse

router = APIRouter(tags=["stream"])


def _hub(request: Request) -> RealtimeHub:
    return request.app.state.context.realtime_hub


@router.get("/api/incidents/stream")
async def stream_incidents(request: Request) -> StreamingResponse:
    hub = _hub(request)
    queue = hub.subscribe()
    heartbeat_interval = request.app.state.context.settings.realtime_heartbeat_seconds

    async def event_stream():
        try:
            yield encode_sse(hub.heartbeat())
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                except TimeoutError:
                    message = hub.heartbeat()
                yield encode_sse(message)
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
