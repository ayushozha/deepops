from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent.contracts import (
    APPROVAL_PENDING,
    STATUS_AWAITING_APPROVAL,
    make_timeline_event,
    now_ms,
)
from server.integrations.bland_client import BlandClient, BlandError
from server.services.explanation_service import build_call_script
from server.services.incident_service import IncidentService

_ACTOR = "escalation-service"
_SPONSOR = "Bland AI"


@dataclass(frozen=True)
class EscalationResult:
    incident: dict[str, Any]
    request_payload: dict[str, Any]
    call_result: dict[str, Any]
    timeline_event: dict[str, Any]
    escalated: bool


class EscalationService:
    """Phone escalation trigger path for high-risk incidents."""

    def __init__(
        self,
        incidents: IncidentService,
        bland_client: BlandClient | None = None,
    ) -> None:
        self.incidents = incidents
        self.bland_client = bland_client

    @staticmethod
    def requires_phone_escalation(incident: Mapping[str, Any], *, force: bool = False) -> bool:
        if force:
            return True

        severity = str(incident.get("severity", "")).lower()
        if severity in {"high", "critical"}:
            return True

        diagnosis = incident.get("diagnosis") or {}
        source = incident.get("source") or {}
        haystack = " ".join(
            str(value or "")
            for value in (
                incident.get("title"),
                source.get("error_message"),
                diagnosis.get("root_cause"),
                diagnosis.get("severity_reasoning"),
            )
        ).lower()
        return any(
            term in haystack
            for term in (
                "financial",
                "blast radius",
                "outage",
                "security",
                "user impact",
                "critical",
            )
        )

    def build_escalation_request(
        self,
        incident: Mapping[str, Any],
        *,
        phone_number: str,
        webhook_url: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        call_script = build_call_script(dict(incident))
        if self.bland_client is not None and hasattr(self.bland_client, "build_call_payload"):
            payload = self.bland_client.build_call_payload(dict(incident), phone_number, webhook_url)
        else:
            payload = self._build_fallback_payload(
                incident,
                phone_number=phone_number,
                webhook_url=webhook_url,
                reason=reason,
            )
        payload["task"] = call_script.get("full_script") or payload.get("task")
        payload["call_script"] = call_script

        metadata = dict(payload.get("metadata") or {})
        metadata["incident_id"] = incident.get("incident_id")
        metadata["severity"] = incident.get("severity")
        metadata["source_file"] = (incident.get("source") or {}).get("source_file")
        metadata["escalation_reason"] = reason or metadata.get("escalation_reason")
        payload["metadata"] = metadata
        if webhook_url:
            payload["webhook"] = webhook_url
        return payload

    async def trigger_escalation(
        self,
        incident_id: str,
        *,
        phone_number: str,
        webhook_url: str | None = None,
        reason: str | None = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> EscalationResult:
        incident = self.incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(f"Incident not found: {incident_id}")

        if not self.requires_phone_escalation(incident, force=force):
            raise ValueError("Incident does not meet the phone-escalation threshold.")

        request_payload = self.build_escalation_request(
            incident,
            phone_number=phone_number,
            webhook_url=webhook_url,
            reason=reason,
        )
        ts = now_ms()
        call_result = self._dry_run_result(ts)

        if not dry_run and self.bland_client is not None:
            try:
                call_result = await self.bland_client.send_escalation_call(
                    dict(incident),
                    phone_number,
                    webhook_url,
                )
            except BlandError as exc:
                call_result = {
                    "call_id": None,
                    "status": "failed",
                    "error": str(exc),
                    "queued_at_ms": ts,
                }
        elif not dry_run and self.bland_client is None:
            call_result = {
                "call_id": None,
                "status": "dry_run",
                "error": "Bland client not configured.",
                "queued_at_ms": ts,
            }

        approval_patch = {
            "required": True,
            "mode": "manual",
            "status": APPROVAL_PENDING,
            "channel": "voice_call",
            "decider": None,
            "bland_call_id": call_result.get("call_id"),
            "notes": reason,
            "decision_at_ms": None,
        }
        timeline_message = self._build_timeline_message(incident_id, call_result)
        timeline_event = make_timeline_event(
            status=STATUS_AWAITING_APPROVAL,
            actor=_ACTOR,
            message=timeline_message,
            sponsor=_SPONSOR,
            metadata={
                "request_payload": request_payload,
                "call_result": call_result,
                "reason": reason,
                "phone_number": phone_number,
                "dry_run": dry_run or self.bland_client is None,
            },
        )
        updated = self.incidents.patch_incident(
            incident_id,
            {
                "status": STATUS_AWAITING_APPROVAL,
                "approval": approval_patch,
            },
            timeline_event=timeline_event,
        )
        return EscalationResult(
            incident=updated,
            request_payload=request_payload,
            call_result=call_result,
            timeline_event=timeline_event,
            escalated=True,
        )

    @staticmethod
    def _build_timeline_message(incident_id: str, call_result: Mapping[str, Any]) -> str:
        call_id = call_result.get("call_id")
        status = str(call_result.get("status") or "").lower()
        if status == "failed":
            return f"Escalation call failed to send for incident {incident_id}."
        if call_id:
            return f"Escalation call initiated for incident {incident_id} (call {call_id})."
        return f"Escalation request prepared for incident {incident_id}."

    @staticmethod
    def _build_fallback_payload(
        incident: Mapping[str, Any],
        *,
        phone_number: str,
        webhook_url: str | None,
        reason: str | None,
    ) -> dict[str, Any]:
        source = incident.get("source") or {}
        diagnosis = incident.get("diagnosis") or {}
        summary = " ".join(
            part
            for part in (
                f"Incident {incident.get('incident_id')}",
                f"Severity: {incident.get('severity') or 'unknown'}",
                f"Error: {source.get('error_message') or 'unknown'}",
                f"Root cause: {diagnosis.get('root_cause') or 'not yet diagnosed'}",
            )
            if part
        )
        payload: dict[str, Any] = {
            "phone_number": phone_number,
            "task": (
                "Call the on-call engineer, explain the incident clearly, and ask for a decision. "
                f"{summary}"
            ),
            "voice": "nat",
            "reduce_latency": True,
            "max_duration": 5,
            "record": True,
            "metadata": {
                "incident_id": incident.get("incident_id"),
                "severity": incident.get("severity"),
                "source_file": source.get("source_file"),
                "escalation_reason": reason,
            },
            "analysis_schema": {
                "decision": "string - approved, rejected, or pending",
                "notes": "string - any additional context from the engineer",
            },
        }
        if webhook_url:
            payload["webhook"] = webhook_url
        return payload

    @staticmethod
    def _dry_run_result(ts: int) -> dict[str, Any]:
        return {
            "call_id": None,
            "status": "dry_run",
            "queued_at_ms": ts,
        }
