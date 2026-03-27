from __future__ import annotations

import unittest

from agent.contracts import STATUS_GATING, STATUS_STORED, load_incident_from_path
from agent.detector import detect_ready_incidents
from agent.store_adapter import InMemoryIncidentStore


class DetectorTests(unittest.TestCase):
    def test_detect_ready_incidents_filters_for_stored_status(self) -> None:
        ready = load_incident_from_path("docs/incident-example.json")
        ready["status"] = STATUS_STORED

        blocked = load_incident_from_path("docs/incident-example.json")
        blocked["incident_id"] = "inc-blocked"
        blocked["status"] = STATUS_GATING

        store = InMemoryIncidentStore([ready, blocked])
        incidents = detect_ready_incidents(store)

        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["incident_id"], ready["incident_id"])


if __name__ == "__main__":
    unittest.main()
