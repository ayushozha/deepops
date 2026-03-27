from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from agent.contracts import SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM


@dataclass(frozen=True)
class SeverityDecision:
    severity: str
    reason: str


def _joined_text(incident: Mapping[str, object], diagnosis: Mapping[str, object]) -> str:
    source = incident.get("source", {})
    source_mapping = source if isinstance(source, Mapping) else {}
    values = [
        str(source_mapping.get("path", "")),
        str(source_mapping.get("error_type", "")),
        str(source_mapping.get("error_message", "")),
        str(diagnosis.get("root_cause", "")),
        str(diagnosis.get("suggested_fix", "")),
    ]
    return " ".join(values).lower()


def assess_severity(incident: Mapping[str, object], diagnosis: Mapping[str, object]) -> SeverityDecision:
    haystack = _joined_text(incident, diagnosis)

    if "/search" in haystack or "timeout" in haystack or "sleep(5)" in haystack or "blocking sleep" in haystack:
        return SeverityDecision(
            severity=SEVERITY_CRITICAL,
            reason="Timeout or blocking search-path failures are demo-critical and require manual approval.",
        )

    if "/user/" in haystack or "null handling" in haystack or "keyerror" in haystack or "missing user" in haystack:
        return SeverityDecision(
            severity=SEVERITY_HIGH,
            reason="Missing-user access errors are high severity because they break user lookup flows and should route to approval.",
        )

    if "/calculate/0" in haystack or "division by zero" in haystack or "zerodivisionerror" in haystack:
        return SeverityDecision(
            severity=SEVERITY_MEDIUM,
            reason="The divide-by-zero bug is isolated to one route and safe to auto-remediate in the demo.",
        )

    keyword_rules = [
        (SEVERITY_CRITICAL, ("data loss", "security", "auth bypass", "payment", "outage")),
        (SEVERITY_HIGH, ("500 error", "service down", "timeout cascade", "user-facing failure")),
        (SEVERITY_MEDIUM, ("degraded", "isolated endpoint", "validation", "non-critical path")),
    ]
    for severity, keywords in keyword_rules:
        if any(keyword in haystack for keyword in keywords):
            return SeverityDecision(severity=severity, reason=f"Matched fallback severity keywords for {severity}.")

    return SeverityDecision(
        severity=SEVERITY_MEDIUM,
        reason="Defaulting to medium severity until richer routing rules are added.",
    )


def classify_severity(incident: Mapping[str, object], diagnosis: Mapping[str, object]) -> str:
    return assess_severity(incident, diagnosis).severity
