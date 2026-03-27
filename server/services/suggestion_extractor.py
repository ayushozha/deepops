"""Suggestion extraction service for DeepOps.

Extracts structured constraints and guidance from human input (UI or phone
transcription) and builds re-plan packets that Codex / Kiro can execute
immediately.
"""

from __future__ import annotations

import re
import time
from typing import Any


# ---------------------------------------------------------------------------
# Pattern banks
# ---------------------------------------------------------------------------

_URGENCY_IMMEDIATE = re.compile(
    r"\b(now|immediately|asap|urgent|right away|critical|drop everything)\b",
    re.IGNORECASE,
)
_URGENCY_LOW = re.compile(
    r"\b(no rush|low priority|when you can|whenever|not urgent|take your time)\b",
    re.IGNORECASE,
)

_FILE_TARGET = re.compile(
    r"(?:focus on|look at|the (?:problem|issue|bug) is in|check|start with|target)\s+"
    r"['\"]?([a-zA-Z0-9_/\\.\-]+\.\w{1,5})['\"]?",
    re.IGNORECASE,
)
_FILE_AVOID = re.compile(
    r"(?:don'?t touch|leave .* alone|stay away from|avoid|don'?t modify|don'?t change|skip)\s+"
    r"['\"]?([a-zA-Z0-9_/\\.\-]+\.\w{1,5})['\"]?",
    re.IGNORECASE,
)

_SCOPE_HOTFIX = re.compile(
    r"\b(hotfix|hot[\s-]?fix)\b",
    re.IGNORECASE,
)
_SCOPE_MINIMAL = re.compile(
    r"\b(keep it simple|minimal change|smallest change|least invasive|simple fix|just fix)\b",
    re.IGNORECASE,
)
_SCOPE_STRICT = re.compile(
    r"\b(don'?t change anything else|only fix|nothing else|just (?:the|this))\b",
    re.IGNORECASE,
)
_SCOPE_ONLY = re.compile(
    r"\bonly (?:fix|change|update|modify|patch)\s+(.+?)(?:\.|$)",
    re.IGNORECASE,
)

_SAFETY_DONT_BREAK = re.compile(
    r"don'?t break (?:the )?(.+?)(?:\.|,|$)",
    re.IGNORECASE,
)
_SAFETY_STILL_WORKS = re.compile(
    r"(?:make sure|ensure) (?:the )?(.+?) still works",
    re.IGNORECASE,
)
_SAFETY_BACKWARD = re.compile(
    r"\b(backward[s]? compatible|backwards? compatibility)\b",
    re.IGNORECASE,
)
_SAFETY_NO_DATA_LOSS = re.compile(
    r"\b(no data loss|preserve data|data integrity)\b",
    re.IGNORECASE,
)
_SAFETY_PRESERVE_API = re.compile(
    r"\b(preserve (?:the )?api|api contract|api compatibility)\b",
    re.IGNORECASE,
)

_ROLLBACK = re.compile(
    r"(roll\s*back|revert|undo).{0,40}?(if .+?)(?:\.|,|$)",
    re.IGNORECASE,
)
_ROLLBACK_SIMPLE = re.compile(
    r"(roll\s*back|revert|undo)\b",
    re.IGNORECASE,
)

_DEPLOYMENT = re.compile(
    r"\b(staging first|canary deploy|blue[- ]green|gradual rollout|feature flag|behind a flag)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Individual extractors
# ---------------------------------------------------------------------------


def extract_file_guidance(text: str) -> tuple[list[str], list[str]]:
    """Extract file-level guidance (files to target, files to avoid).

    Returns:
        (target_files, avoid_files)

    Patterns:
    - "focus on main.py" -> target: main.py
    - "don't touch config.py" / "leave config alone" -> avoid: config.py
    - "the problem is in routes.py" -> target: routes.py
    """
    targets = [m.group(1) for m in _FILE_TARGET.finditer(text)]
    avoids = [m.group(1) for m in _FILE_AVOID.finditer(text)]

    # Deduplicate while preserving order
    targets = list(dict.fromkeys(targets))
    avoids = list(dict.fromkeys(avoids))

    return targets, avoids


def extract_scope_limits(text: str) -> list[str]:
    """Extract scope constraints.

    Patterns:
    - "only fix X" / "just X" -> scope to X
    - "hotfix only" -> minimal scope
    - "don't change anything else" -> strict scope
    - "keep it simple" -> minimal change
    """
    limits: list[str] = []

    if _SCOPE_HOTFIX.search(text):
        limits.append("hotfix")
    if _SCOPE_MINIMAL.search(text):
        limits.append("minimal")
    if _SCOPE_STRICT.search(text):
        limits.append("strict_scope")

    only_match = _SCOPE_ONLY.search(text)
    if only_match:
        limits.append(f"scope:{only_match.group(1).strip()}")

    return limits


def extract_urgency(text: str) -> str:
    """Classify urgency from text.

    - "now", "immediately", "ASAP", "urgent" -> "immediate"
    - "when you can", "no rush", "low priority" -> "low"
    - default -> "normal"
    """
    if _URGENCY_IMMEDIATE.search(text):
        return "immediate"
    if _URGENCY_LOW.search(text):
        return "low"
    return "normal"


def extract_safety_requirements(text: str) -> list[str]:
    """Extract safety / preservation constraints.

    Patterns:
    - "don't break X" -> preserve X
    - "make sure Y still works" -> preserve Y
    - "backward compatible" -> preserve API contract
    - "no data loss" -> preserve data integrity
    """
    reqs: list[str] = []

    for m in _SAFETY_DONT_BREAK.finditer(text):
        reqs.append(m.group(1).strip())

    for m in _SAFETY_STILL_WORKS.finditer(text):
        reqs.append(m.group(1).strip())

    if _SAFETY_BACKWARD.search(text):
        reqs.append("backward compatible")

    if _SAFETY_NO_DATA_LOSS.search(text):
        reqs.append("data integrity")

    if _SAFETY_PRESERVE_API.search(text):
        reqs.append("API contract")

    return list(dict.fromkeys(reqs))


def _extract_rollback(text: str) -> str | None:
    """Extract rollback expectation from text."""
    m = _ROLLBACK.search(text)
    if m:
        return m.group(0).strip().rstrip(".,")
    if _ROLLBACK_SIMPLE.search(text):
        return "rollback requested"
    return None


def _extract_deployment_constraints(text: str) -> list[str]:
    """Extract deployment-related constraints."""
    return list(dict.fromkeys(
        m.group(1).strip() for m in _DEPLOYMENT.finditer(text)
    ))


def _extract_raw_suggestions(text: str) -> list[str]:
    """Split human text into individual suggestion phrases.

    Splits on sentence boundaries and common conjunctions so each
    atomic instruction is captured separately.
    """
    if not text.strip():
        return []
    # Split on periods, semicolons, "and also", "but", newlines
    parts = re.split(r'[.;\n]|(?:\band also\b)|(?:\bbut\b)', text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Main extraction entry point
# ---------------------------------------------------------------------------


def extract_suggestions(text: str, incident: dict | None = None) -> dict:
    """Extract structured suggestions from human guidance text.

    Args:
        text: Human's guidance (typed or transcribed).
        incident: Optional incident context for better interpretation.

    Returns:
        Dictionary with extracted constraints, guidance, and confidence.
    """
    text = text.strip() if text else ""

    targets, avoids = extract_file_guidance(text)
    scope = extract_scope_limits(text)
    urgency = extract_urgency(text)
    safety = extract_safety_requirements(text)
    rollback = _extract_rollback(text)
    deployment = _extract_deployment_constraints(text)
    raw = _extract_raw_suggestions(text)

    # If incident provides affected files and the human mentions them
    # without explicit file guidance, boost confidence.
    if incident and not targets:
        affected = incident.get("diagnosis", {}).get("affected_components", [])
        for comp in affected:
            fname = comp.rsplit("/", 1)[-1] if "/" in comp else comp
            if fname.lower() in text.lower():
                targets.append(comp)

    # Confidence heuristic: more structured info -> higher confidence
    signals = sum([
        bool(targets),
        bool(avoids),
        bool(scope),
        urgency != "normal",
        bool(safety),
        bool(rollback),
        bool(deployment),
    ])
    if not text:
        confidence = 0.0
    elif signals == 0:
        confidence = 0.3
    else:
        confidence = min(0.5 + signals * 0.1, 0.98)

    return {
        "files_to_avoid": avoids,
        "files_to_target": targets,
        "scope_limits": scope,
        "rollback_expectations": rollback,
        "deployment_constraints": deployment,
        "urgency": urgency,
        "safety_requirements": safety,
        "raw_suggestions": raw,
        "confidence": round(confidence, 2),
    }


# ---------------------------------------------------------------------------
# Re-plan packet builder
# ---------------------------------------------------------------------------


def _generate_plan_notes(
    constraints: dict,
    human_input: str,
    current_fix: dict | None,
) -> list[str]:
    """Generate concrete, actionable plan notes for Kiro/Codex."""
    notes: list[str] = []

    # File guidance notes
    for f in constraints.get("files_to_avoid", []):
        notes.append(f"Rewrite fix to avoid modifying {f}")
    for f in constraints.get("files_to_target", []):
        notes.append(f"Focus investigation and fix on {f}")

    # Scope notes
    for s in constraints.get("scope_limits", []):
        if s == "hotfix":
            notes.append("Apply hotfix-level change only; no refactoring")
        elif s == "minimal":
            notes.append("Use the smallest possible change")
        elif s == "strict_scope":
            notes.append("Do not modify any files outside the identified scope")
        elif s.startswith("scope:"):
            notes.append(f"Scope fix to only: {s[6:]}")

    # Safety notes
    for req in constraints.get("safety_requirements", []):
        notes.append(f"Ensure {req} is preserved and not broken")

    # Rollback
    if constraints.get("rollback_expectations"):
        notes.append("Add rollback mechanism before deployment")

    # Deployment
    for d in constraints.get("deployment_constraints", []):
        notes.append(f"Deployment strategy: {d}")

    # If we still have no notes, derive a generic one from the input
    if not notes and human_input.strip():
        notes.append(f"Revise approach based on guidance: {human_input.strip()[:120]}")

    return notes


def build_replan_packet(
    human_input: str,
    incident: dict,
    current_diagnosis: dict | None = None,
    current_fix: dict | None = None,
) -> dict:
    """Build a clean re-plan packet for Codex and Kiro.

    Called when the human suggests a new direction. The returned packet
    contains everything the execution agents need to start immediately.

    Args:
        human_input: Raw human guidance text.
        incident: Current incident record (must include incident_id).
        current_diagnosis: The diagnosis we had before the human intervened.
        current_fix: The fix we proposed before the human intervened.

    Returns:
        Re-plan packet dictionary ready for dispatch.
    """
    constraints = extract_suggestions(human_input, incident)

    # Determine source heuristic: phone transcriptions tend to be longer
    # and contain filler words.
    source = "phone" if len(human_input.split()) > 30 else "ui"

    plan_notes = _generate_plan_notes(constraints, human_input, current_fix)

    return {
        "incident_id": incident.get("incident_id", "unknown"),
        "revised_intent": human_input.strip(),
        "original_diagnosis": current_diagnosis,
        "original_fix": current_fix,
        "extracted_constraints": constraints,
        "inferred_urgency": constraints["urgency"],
        "plan_notes": plan_notes,
        "interpretation_confidence": constraints["confidence"],
        "source": source,
        "timestamp_ms": int(time.time() * 1000),
    }
