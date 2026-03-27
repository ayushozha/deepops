from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Mapping

from agent.contracts import now_ms


@dataclass(frozen=True)
class RealtimeMessage:
    event: str
    data: dict[str, Any]


def build_realtime_payload(
    event: str,
    incident: Mapping[str, Any] | None = None,
    *,
    timeline_event: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> RealtimeMessage:
    incident_payload = dict(incident) if incident is not None else None
    payload: dict[str, Any] = {
        "event": event,
        "sent_at_ms": now_ms(),
        "incident_id": incident_payload.get("incident_id") if incident_payload else None,
        "status": incident_payload.get("status") if incident_payload else None,
        "severity": incident_payload.get("severity") if incident_payload else None,
        "updated_at_ms": incident_payload.get("updated_at_ms") if incident_payload else None,
        "timeline_event": dict(timeline_event) if timeline_event is not None else None,
        "incident": incident_payload,
    }
    if extra:
        payload.update(dict(extra))
    return RealtimeMessage(event=event, data=payload)


def encode_sse(message: RealtimeMessage) -> bytes:
    return (
        f"event: {message.event}\n"
        f"data: {json.dumps(message.data, separators=(',', ':'))}\n\n"
    ).encode("utf-8")


class RealtimeHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[RealtimeMessage]] = set()

    def subscribe(self) -> asyncio.Queue[RealtimeMessage]:
        queue: asyncio.Queue[RealtimeMessage] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RealtimeMessage]) -> None:
        self._subscribers.discard(queue)

    def publish(
        self,
        event: str,
        incident: Mapping[str, Any] | None = None,
        *,
        timeline_event: Mapping[str, Any] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> RealtimeMessage:
        message = build_realtime_payload(event, incident, timeline_event=timeline_event, extra=extra)
        for queue in list(self._subscribers):
            queue.put_nowait(message)
        return message

    def heartbeat(self) -> RealtimeMessage:
        return build_realtime_payload("pipeline.heartbeat", None, extra={"ok": True})
