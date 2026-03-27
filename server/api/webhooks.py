from __future__ import annotations

from typing import Any, Mapping

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from server.integrations.truefoundry_client import DeploymentResult
from server.normalizers.bland_normalizer import parse_bland_transcript_full
from server.services.decision_parser import parse_transcript_to_actions
from server.services.suggestion_extractor import build_replan_packet

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class TrueFoundryWebhookBody(BaseModel):
    incident_id: str
    status: str
    deploy_url: str | None = None
    commit_sha: str | None = None
    failure_reason: str | None = None
    provider: str = "truefoundry"
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = "truefoundry-webhook"


def _extract_incident_id(payload: Mapping[str, Any]) -> str | None:
    incident_id = payload.get("incident_id")
    if isinstance(incident_id, str) and incident_id:
        return incident_id
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        nested = metadata.get("incident_id")
        if isinstance(nested, str) and nested:
            return nested
    return None


def _flatten_transcript(transcript: Any) -> str:
    if isinstance(transcript, str):
        return transcript.strip()
    if isinstance(transcript, list):
        parts: list[str] = []
        for item in transcript:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return " ".join(part for part in parts if part).strip()
    return ""


def _constraint_strings(extracted: Mapping[str, Any]) -> list[str]:
    items: list[str] = []
    for value in extracted.get("files_to_avoid") or []:
        items.append(f"avoid {value}")
    for value in extracted.get("files_to_target") or []:
        items.append(f"target {value}")
    for value in extracted.get("scope_limits") or []:
        if value == "hotfix":
            items.append("hotfix only")
        elif value == "minimal":
            items.append("minimal change")
        elif value == "strict_scope":
            items.append("strict scope")
        elif str(value).startswith("scope:"):
            items.append(f"scope to {str(value)[6:]}")
        else:
            items.append(str(value))
    if extracted.get("rollback_expectations"):
        items.append(str(extracted["rollback_expectations"]))
    for value in extracted.get("deployment_constraints") or []:
        items.append(str(value))
    for value in extracted.get("safety_requirements") or []:
        items.append(f"preserve {value}")
    deduped: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


@router.post("/bland")
async def bland_webhook(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    context = request.app.state.context

    legacy_incident_id = _extract_incident_id(payload)
    if "approved" in payload and legacy_incident_id:
        try:
            return await context.workflow.apply_human_decision(
                legacy_incident_id,
                decision_text="approve" if payload.get("approved") else "reject",
                actor=str(payload.get("actor") or "bland-webhook"),
                sponsor="Bland AI",
                notes=payload.get("notes"),
                channel=str(payload.get("channel") or "voice_call"),
                decider=payload.get("decider"),
                bland_call_id=payload.get("bland_call_id"),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    incident_id = _extract_incident_id(payload)
    if incident_id is None:
        raise HTTPException(status_code=400, detail="Bland webhook is missing incident_id metadata.")

    incident = context.incidents.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    parsed_webhook = parse_bland_transcript_full(payload)
    transcript = payload.get("transcripts") or payload.get("transcript") or ""
    transcript_text = _flatten_transcript(transcript)
    transcript_actions = parse_transcript_to_actions(transcript)

    decision_type = str(parsed_webhook.get("decision_type") or "").lower()
    approval = dict(parsed_webhook.get("approval") or {})
    if decision_type in {"suggest", "follow_up"} or transcript_actions["primary_action"] in {"suggest", "revise"}:
        decision_text = "suggest"
    elif approval.get("status") == "approved" or transcript_actions["primary_action"] == "approve":
        decision_text = "approve"
    elif approval.get("status") == "rejected" or transcript_actions["primary_action"] == "reject":
        decision_text = "reject"
    else:
        decision_text = "clarify"

    suggested_steps: list[str] = []
    constraints: list[str] = []
    replan_packet: dict[str, Any] | None = None
    if decision_text == "suggest":
        replan_packet = build_replan_packet(
            transcript_text or transcript_actions["summary"],
            incident,
            current_diagnosis=dict(incident.get("diagnosis") or {}),
            current_fix=dict(incident.get("fix") or {}),
        )
        suggested_steps = list(replan_packet.get("plan_notes") or [])
        constraints = _constraint_strings(replan_packet.get("extracted_constraints") or {})

    try:
        result = await context.workflow.apply_human_decision(
            incident_id,
            decision_text=decision_text,
            actor="bland-webhook",
            sponsor="Bland AI",
            notes=transcript_text or transcript_actions["summary"],
            channel="voice_call",
            decider=approval.get("decider"),
            suggested_steps=suggested_steps,
            constraints=constraints,
            bland_call_id=approval.get("bland_call_id"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        **result,
        "webhook": {
            "incident_id": incident_id,
            "parsed_approval": approval,
            "decision_type": decision_type,
            "transcript_actions": transcript_actions,
            "replan_packet": replan_packet,
        },
    }


@router.post("/truefoundry")
async def truefoundry_webhook(request: Request, body: TrueFoundryWebhookBody) -> dict[str, Any]:
    context = request.app.state.context
    incident = context.incidents.get_incident(body.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    result = DeploymentResult(
        deploy_id=str(body.metadata.get("deploy_id") or ""),
        status=body.status,
        service_name=incident.get("service") or context.settings.truefoundry_service_name,
        environment=incident.get("environment") or context.settings.truefoundry_environment,
        deploy_url=body.deploy_url,
        commit_sha=body.commit_sha,
        failure_reason=body.failure_reason,
        completed_at_ms=body.metadata.get("completed_at_ms"),
        started_at_ms=body.metadata.get("started_at_ms"),
    )

    context.deployment.handle_deployment_result(dict(incident), result)
    updated = context.incidents.get_incident(body.incident_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Deployment callback was processed but the incident could not be reloaded.")

    return {
        "incident": updated,
        "provider": body.provider,
        "status": body.status,
    }
