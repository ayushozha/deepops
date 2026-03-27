from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Keyword sets used for decision extraction
# ---------------------------------------------------------------------------

_APPROVED_PHRASES: list[str] = sorted(
    [
        "approved", "approve", "yes", "go ahead", "deploy it",
        "ship it", "confirmed", "confirm", "do it", "proceed", "agreed",
        "absolutely", "affirmative", "go for it", "let's do it",
    ],
    key=len, reverse=True,  # longest first
)

_REJECTED_PHRASES: list[str] = sorted(
    [
        "rejected", "reject", "no", "deny", "denied", "stop", "hold",
        "wait", "do not deploy", "don't deploy", "rollback", "cancel",
        "abort", "negative", "hold off", "not now", "stand down",
        "cancel the deployment",
    ],
    key=len, reverse=True,
)

# Pre-compile regex patterns: word-boundary anchored, longest first
_DECISION_PATTERNS: list[tuple[re.Pattern[str], str]] = []
for _phrase in _REJECTED_PHRASES:
    _DECISION_PATTERNS.append((re.compile(r"(?<!\w)" + re.escape(_phrase) + r"(?!\w)"), "rejected"))
for _phrase in _APPROVED_PHRASES:
    _DECISION_PATTERNS.append((re.compile(r"(?<!\w)" + re.escape(_phrase) + r"(?!\w)"), "approved"))


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def extract_approval_decision(transcripts: list[dict] | str) -> str:
    """Extract approval decision from call transcript.

    Returns ``"approved"``, ``"rejected"``, or ``"pending"``.

    Strategy: find every occurrence of every keyword/phrase, track the
    rightmost (latest in the conversation) match.  Longer phrases are
    checked first so "do not deploy" beats a bare "deploy" at the same
    position.  Rejected spans suppress any approved keyword that falls
    entirely inside the rejected phrase.
    """
    text = _flatten_transcripts(transcripts).lower()

    if not text.strip():
        return "pending"

    # Collect all matches: (start_pos, end_pos, decision)
    matches: list[tuple[int, int, str]] = []
    for pattern, decision in _DECISION_PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), decision))

    if not matches:
        return "pending"

    # Remove approved matches that are fully contained within a rejected
    # match (e.g. "deploy" inside "do not deploy").
    rejected_spans = [(s, e) for s, e, d in matches if d == "rejected"]
    filtered: list[tuple[int, int, str]] = []
    for start, end, decision in matches:
        if decision == "approved":
            suppressed = any(rs <= start and end <= re_ for rs, re_ in rejected_spans)
            if suppressed:
                continue
        filtered.append((start, end, decision))

    if not filtered:
        return "pending"

    # Honour the *last* decisive keyword in the conversation.
    filtered.sort(key=lambda t: t[0])
    return filtered[-1][2]


def summarize_transcript(transcripts: list[dict] | str) -> str:
    """Create a one-line summary of the call for the ``notes`` field."""
    text = _flatten_transcripts(transcripts)
    if not text:
        return "No transcript available."
    # Collapse whitespace and trim to a reasonable length.
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 280:
        text = text[:277] + "..."
    return text


def parse_bland_webhook(webhook_payload: dict) -> dict:
    """Parse a Bland webhook callback into structured approval data.

    Parameters
    ----------
    webhook_payload:
        Raw JSON body delivered by Bland's webhook.  Expected keys include
        ``call_id``, ``status``, ``transcripts``, ``completed_at``,
        ``answered_by``, and optionally ``analysis``.

    Returns
    -------
    dict
        A dict matching the canonical approval schema, ready to be
        patched into ``incident.approval``.
    """
    call_id: str = webhook_payload.get("call_id", "")
    call_status: str = (webhook_payload.get("status") or "").lower()
    transcripts = webhook_payload.get("transcripts") or webhook_payload.get("transcript", [])
    completed_at = webhook_payload.get("completed_at")
    answered_by: str | None = webhook_payload.get("answered_by") or webhook_payload.get("to")
    analysis: dict = webhook_payload.get("analysis") or {}

    # Determine decision timestamp ------------------------------------------
    decision_at_ms = _parse_timestamp_ms(completed_at)

    # Determine approval status ---------------------------------------------
    if call_status in ("failed", "no-answer", "busy", "error"):
        # Call did not connect -- decision is still pending.
        decision = "pending"
    elif analysis.get("decision"):
        # If Bland returned a structured analysis, trust it first.
        raw = str(analysis["decision"]).lower().strip()
        if raw in ("approved", "approve", "yes"):
            decision = "approved"
        elif raw in ("rejected", "reject", "no"):
            decision = "rejected"
        else:
            decision = extract_approval_decision(transcripts)
    else:
        decision = extract_approval_decision(transcripts)

    notes = analysis.get("notes") or summarize_transcript(transcripts)

    return {
        "required": True,
        "mode": "manual",
        "status": decision,
        "channel": "voice_call",
        "decider": answered_by,
        "bland_call_id": call_id,
        "notes": notes,
        "decision_at_ms": decision_at_ms,
    }


def build_approval_patch(webhook_payload: dict) -> dict:
    """Build an Aerospike-ready patch dict from a Bland webhook.

    Combines the parsed approval block with a timeline event suitable
    for appending to the incident's ``timeline`` list.
    """
    approval = parse_bland_webhook(webhook_payload)
    now_ms = int(time.time() * 1000)

    status_label = "gating" if approval["status"] == "pending" else "awaiting_approval"
    message = _build_timeline_message(approval)

    return {
        "approval": approval,
        "updated_at_ms": now_ms,
        "timeline_event": {
            "at_ms": approval["decision_at_ms"] or now_ms,
            "status": status_label,
            "actor": "bland-ai",
            "message": message,
            "sponsor": "Bland AI",
            "metadata": {
                "call_id": approval["bland_call_id"],
                "decision": approval["status"],
            },
        },
    }


def build_timeline_event_for_call_start(incident_id: str, call_id: str) -> dict:
    """Return a timeline event dict for when an escalation call is initiated."""
    now_ms = int(time.time() * 1000)
    return {
        "at_ms": now_ms,
        "status": "awaiting_approval",
        "actor": "bland-ai",
        "message": f"Escalation call initiated for incident {incident_id} (call {call_id}).",
        "sponsor": "Bland AI",
        "metadata": {
            "call_id": call_id,
            "incident_id": incident_id,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _flatten_transcripts(transcripts: list[dict] | str) -> str:
    """Normalise transcripts into a single string."""
    if isinstance(transcripts, str):
        return transcripts
    if isinstance(transcripts, list):
        parts: list[str] = []
        for entry in transcripts:
            if isinstance(entry, dict):
                parts.append(entry.get("text", ""))
            elif isinstance(entry, str):
                parts.append(entry)
        return " ".join(parts)
    return ""


def _parse_timestamp_ms(value: Any) -> int:
    """Convert a timestamp value (ISO string, epoch seconds, or epoch ms) to ms."""
    if value is None:
        return int(time.time() * 1000)
    if isinstance(value, (int, float)):
        # Heuristic: epoch seconds are < 10^12; epoch ms are >= 10^12
        if value < 1e12:
            return int(value * 1000)
        return int(value)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            pass
    return int(time.time() * 1000)


def _build_timeline_message(approval: dict) -> str:
    """Build a human-readable timeline message from parsed approval data."""
    status = approval["status"]
    decider = approval.get("decider") or "unknown engineer"
    call_id = approval.get("bland_call_id") or "unknown"
    if status == "approved":
        return f"Deployment approved by {decider} via voice call (call {call_id})."
    if status == "rejected":
        return f"Deployment rejected by {decider} via voice call (call {call_id})."
    return f"Awaiting manual decision — voice call {call_id} did not yield a clear answer."


# ---------------------------------------------------------------------------
# Extended decision types (suggest, defer, ask_another, follow_up)
# ---------------------------------------------------------------------------

_SUGGEST_PHRASES = [
    "try", "instead", "alternative", "how about", "what if",
    "maybe try", "suggest", "could you", "different approach",
]

_DEFER_PHRASES = [
    "let me check", "call back", "later", "think about it",
    "give me a minute", "not right now", "hold on", "let me look",
]

_ASK_ANOTHER_PATTERNS = [
    re.compile(r"(?:ask|contact|escalate to|get|call|check with)\s+([A-Z][a-z]+)", re.IGNORECASE),
]

_FOLLOW_UP_PHRASES = [
    "what's the blast radius", "show me", "more details", "explain",
    "tell me more", "what exactly", "can you clarify", "walk me through",
]


def _classify_extended_decision(text: str) -> tuple[str, list[str], list[str]]:
    """Classify into extended decision types beyond approve/reject.

    Returns (decision_type, suggestions, mentioned_people).
    """
    lower = text.lower()
    suggestions: list[str] = []
    mentioned_people: list[str] = []

    # Check for people mentions (ask_another)
    for pattern in _ASK_ANOTHER_PATTERNS:
        for m in pattern.finditer(text):
            mentioned_people.append(m.group(1))

    if mentioned_people:
        return "ask_another", suggestions, mentioned_people

    # Check follow_up
    for phrase in _FOLLOW_UP_PHRASES:
        if phrase in lower:
            return "follow_up", suggestions, mentioned_people

    # Check defer
    for phrase in _DEFER_PHRASES:
        if phrase in lower:
            return "defer", suggestions, mentioned_people

    # Check suggest
    for phrase in _SUGGEST_PHRASES:
        if phrase in lower:
            # Extract the suggestion text after the trigger phrase
            idx = lower.index(phrase)
            suggestion_text = text[idx:].strip()
            if suggestion_text:
                suggestions.append(suggestion_text)
            return "suggest", suggestions, mentioned_people

    return "pending", suggestions, mentioned_people


def parse_bland_transcript_full(webhook_payload: dict) -> dict:
    """Extended transcript parsing with all decision types.

    Layers extended classification on top of the canonical approval parsing.
    Supports: approve, reject, suggest, defer, ask_another, follow_up, no_answer.
    """
    approval_patch = build_approval_patch(webhook_payload)
    approval = approval_patch["approval"]

    transcripts = webhook_payload.get("transcripts") or webhook_payload.get("transcript", [])
    text = _flatten_transcripts(transcripts)
    call_status = (webhook_payload.get("status") or "").lower()
    now_ms = int(time.time() * 1000)

    # If call didn't connect, it's no_answer
    if call_status in ("failed", "no-answer", "busy", "error") or not text.strip():
        return {
            "approval": approval,
            "decision_type": "no_answer",
            "suggestions": [],
            "mentioned_people": [],
            "needs_replan": False,
            "timeline_event": approval_patch["timeline_event"],
            "updated_at_ms": now_ms,
        }

    # If we got a clear approve/reject from the base parser, use it
    if approval["status"] == "approved":
        decision_type = "approve"
    elif approval["status"] == "rejected":
        decision_type = "reject"
    else:
        # Try extended classification
        decision_type, suggestions, people = _classify_extended_decision(text)
        if decision_type != "pending":
            return {
                "approval": approval,
                "decision_type": decision_type,
                "suggestions": suggestions,
                "mentioned_people": people,
                "needs_replan": decision_type in ("suggest", "follow_up"),
                "timeline_event": approval_patch["timeline_event"],
                "updated_at_ms": now_ms,
            }
        decision_type = "pending"

    return {
        "approval": approval,
        "decision_type": decision_type,
        "suggestions": [],
        "mentioned_people": [],
        "needs_replan": decision_type in ("suggest", "follow_up"),
        "timeline_event": approval_patch["timeline_event"],
        "updated_at_ms": now_ms,
    }
