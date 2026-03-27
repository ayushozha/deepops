from __future__ import annotations

import unittest

from agent.contracts import normalize_incident
from agent.severity import assess_severity


class SeverityTests(unittest.TestCase):
    def test_divide_by_zero_maps_to_medium(self) -> None:
        incident = normalize_incident(
            {
                "source": {
                    "path": "/calculate/0",
                    "error_type": "ZeroDivisionError",
                    "error_message": "division by zero",
                    "source_file": "demo-app/main.py",
                }
            }
        )
        decision = assess_severity(incident, {"root_cause": "Missing zero guard on calculate."})
        self.assertEqual(decision.severity, "medium")

    def test_missing_user_maps_to_high(self) -> None:
        incident = normalize_incident(
            {
                "source": {
                    "path": "/user/unknown",
                    "error_type": "KeyError",
                    "error_message": "missing user",
                    "source_file": "demo-app/main.py",
                }
            }
        )
        decision = assess_severity(incident, {"root_cause": "Null handling is missing for absent users."})
        self.assertEqual(decision.severity, "high")

    def test_timeout_maps_to_critical(self) -> None:
        incident = normalize_incident(
            {
                "source": {
                    "path": "/search",
                    "error_type": "TimeoutError",
                    "error_message": "blocking sleep caused timeout",
                    "source_file": "demo-app/main.py",
                }
            }
        )
        decision = assess_severity(incident, {"root_cause": "Blocking sleep causes cascading timeout behavior."})
        self.assertEqual(decision.severity, "critical")


if __name__ == "__main__":
    unittest.main()
