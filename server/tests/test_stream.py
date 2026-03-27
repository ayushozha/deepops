from __future__ import annotations

import json

from agent.contracts import load_incident_from_path
from server.services.realtime_hub import RealtimeHub, build_realtime_payload, encode_sse


def test_encode_sse_contains_event_and_data():
    incident = load_incident_from_path("docs/incident-example.json")
    message = build_realtime_payload("incident.updated", incident)
    raw = encode_sse(message).decode("utf-8")
    assert "event: incident.updated" in raw
    assert "data:" in raw


def test_hub_publish_to_subscriber_queue():
    incident = load_incident_from_path("docs/incident-example.json")
    hub = RealtimeHub()
    queue = hub.subscribe()
    try:
        hub.publish("incident.updated", incident)
        message = queue.get_nowait()
    finally:
        hub.unsubscribe(queue)
    assert message.event == "incident.updated"
    assert message.data["incident_id"] == incident["incident_id"]
