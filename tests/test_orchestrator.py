from __future__ import annotations

import unittest

from agent.contracts import STATUS_FAILED, STATUS_GATING, STATUS_STORED, load_incident_from_path
from agent.orchestrator import AgentRuntime, process_next_incident
from agent.store_adapter import InMemoryIncidentStore


class OrchestratorTests(unittest.TestCase):
    def test_process_next_incident_moves_record_to_gating(self) -> None:
        incident = load_incident_from_path("docs/incident-example.json")
        incident["status"] = STATUS_STORED
        incident["severity"] = "pending"
        incident["diagnosis"] = {
            "status": "pending",
            "root_cause": None,
            "suggested_fix": None,
            "affected_components": [],
            "confidence": 0.0,
            "severity_reasoning": None,
            "macroscope_context": None,
            "started_at_ms": None,
            "completed_at_ms": None,
        }
        incident["fix"] = {
            "status": "pending",
            "spec_markdown": None,
            "diff_preview": None,
            "files_changed": [],
            "test_plan": [],
            "started_at_ms": None,
            "completed_at_ms": None,
        }

        store = InMemoryIncidentStore([incident])
        runtime = AgentRuntime(
            store=store,
            diagnose=lambda _: {
                "root_cause": "The calculate endpoint divides by zero with no guard.",
                "suggested_fix": "Add an early zero check.",
                "affected_components": ["demo-app/main.py"],
                "confidence": 0.97,
            },
            generate_fix=lambda _, __: {
                "spec_markdown": "# Fix Specification",
                "diff_preview": "@@ + if value == 0: raise HTTPException(...)",
                "files_changed": ["demo-app/main.py"],
                "test_plan": ["Call /calculate/0", "Call /calculate/5"],
            },
        )

        result = process_next_incident(runtime)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["status"], STATUS_GATING)
        self.assertEqual(result["severity"], "medium")
        self.assertEqual(result["diagnosis"]["status"], "complete")
        self.assertEqual(result["fix"]["status"], "complete")
        self.assertGreaterEqual(len(result["timeline"]), 3)

    def test_process_next_incident_marks_failure(self) -> None:
        incident = load_incident_from_path("docs/incident-example.json")
        incident["status"] = STATUS_STORED
        store = InMemoryIncidentStore([incident])
        runtime = AgentRuntime(
            store=store,
            diagnose=lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
            generate_fix=lambda _, __: {},
        )

        with self.assertRaises(RuntimeError):
            process_next_incident(runtime)

        stored = store.get_incident(incident["incident_id"])
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["status"], STATUS_FAILED)


if __name__ == "__main__":
    unittest.main()
