"""Unified facade for human-language processing in the live backend.

Codex routes should call these functions instead of using the individual
services directly. This ensures consistent behavior across UI, phone,
and webhook surfaces.
"""

from __future__ import annotations

import time

from server.services.explanation_service import (
    build_approval_explanation,
    build_call_script,
    build_follow_up_questions,
    build_phone_explanation,
    build_short_explanation,
)
from server.services.decision_parser import (
    parse_human_decision,
    parse_transcript_to_actions,
)
from server.services.suggestion_extractor import (
    build_replan_packet,
    extract_suggestions,
)


def explain_for_approval(incident: dict) -> dict:
    """Build all explanation variants for an incident needing approval."""
    return {
        "short": build_short_explanation(incident),
        "detailed": build_approval_explanation(incident),
        "phone": build_phone_explanation(incident),
        "call_script": build_call_script(incident),
        "follow_up_questions": build_follow_up_questions(incident),
    }


def process_human_input(text: str, incident: dict, source: str = "ui") -> dict:
    """Process any human input and return structured action + explanation."""
    decision = parse_human_decision(text, source=source)
    decision_type = decision.get("decision", "defer")

    suggestions = {}
    replan_packet = None
    approval_patch = None

    if decision_type in ("suggest", "revise"):
        suggestions = extract_suggestions(text, incident)
        replan_packet = build_replan_packet(
            human_input=text,
            incident=incident,
            current_diagnosis=incident.get("diagnosis"),
            current_fix=incident.get("fix"),
        )

    if decision_type == "approve":
        approval_patch = {
            "approval": {
                "status": "approved",
                "mode": "manual",
                "channel": source,
                "decider": "human",
                "notes": text[:280] if text else None,
                "decision_at_ms": int(time.time() * 1000),
            },
            "updated_at_ms": int(time.time() * 1000),
        }
    elif decision_type == "reject":
        approval_patch = {
            "approval": {
                "status": "rejected",
                "mode": "manual",
                "channel": source,
                "decider": "human",
                "notes": text[:280] if text else None,
                "decision_at_ms": int(time.time() * 1000),
            },
            "updated_at_ms": int(time.time() * 1000),
        }

    response_text = _build_response_text(decision_type, incident)

    return {
        "decision": decision,
        "suggestions": suggestions,
        "replan_packet": replan_packet,
        "approval_patch": approval_patch,
        "response_text": response_text,
    }


def process_phone_transcript(transcript, incident: dict) -> dict:
    """Process a phone call transcript and return structured outcome."""
    actions = parse_transcript_to_actions(transcript)
    primary = actions.get("primary_action", "defer")

    suggestions = {}
    replan_packet = None
    approval_patch = None

    if primary in ("suggest", "revise"):
        summary = actions.get("summary", "")
        suggestions = extract_suggestions(summary, incident)
        replan_packet = build_replan_packet(
            human_input=summary,
            incident=incident,
            current_diagnosis=incident.get("diagnosis"),
            current_fix=incident.get("fix"),
        )

    if primary == "approve":
        approval_patch = build_approval_patch_from_decision(
            {"decision": "approve"}, incident
        )
    elif primary == "reject":
        approval_patch = build_approval_patch_from_decision(
            {"decision": "reject"}, incident
        )

    needs_follow_up = primary in ("ask_context", "defer", "no_answer")

    return {
        "actions": actions,
        "suggestions": suggestions,
        "approval_patch": approval_patch,
        "replan_packet": replan_packet,
        "needs_follow_up": needs_follow_up,
        "follow_up_questions": build_follow_up_questions(incident) if needs_follow_up else [],
    }


def build_approval_patch_from_decision(decision: dict, incident: dict) -> dict | None:
    """Convert a parsed decision into an Aerospike-ready approval patch."""
    dtype = decision.get("decision", "")
    now_ms = int(time.time() * 1000)

    if dtype == "approve":
        return {
            "approval": {
                "required": True,
                "mode": "manual",
                "status": "approved",
                "channel": decision.get("source", "unknown"),
                "decider": "human",
                "notes": decision.get("raw_input", "")[:280] or None,
                "decision_at_ms": now_ms,
            },
            "updated_at_ms": now_ms,
        }
    elif dtype == "reject":
        return {
            "approval": {
                "required": True,
                "mode": "manual",
                "status": "rejected",
                "channel": decision.get("source", "unknown"),
                "decider": "human",
                "notes": decision.get("raw_input", "")[:280] or None,
                "decision_at_ms": now_ms,
            },
            "updated_at_ms": now_ms,
        }
    return None


def _build_response_text(decision_type: str, incident: dict) -> str:
    """Build confirmation text for the human."""
    iid = incident.get("incident_id", "unknown")
    responses = {
        "approve": f"Approved. Deploying fix for {iid} now.",
        "reject": f"Rejected. Fix for {iid} will not be deployed.",
        "revise": f"Understood. Revising the fix approach for {iid}.",
        "suggest": f"Got it. Incorporating your guidance for {iid}.",
        "defer": f"Acknowledged. Holding {iid} for later review.",
        "ask_context": f"Let me get more details on {iid} for you.",
        "no_answer": f"No response received for {iid}. Will retry.",
    }
    return responses.get(decision_type, f"Processing your input for {iid}.")
