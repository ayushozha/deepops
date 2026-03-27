from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from agent.contracts import (
    APPROVAL_PENDING,
    STATUS_AWAITING_APPROVAL,
    STATUS_BLOCKED,
    STATUS_DEPLOYING,
    STATUS_FAILED,
    STATUS_GATING,
    STATUS_RESOLVED,
    STATUS_STORED,
    deep_merge_dict,
    make_timeline_event,
    now_ms,
)
from agent.execution_package import format_execution_package
from agent.orchestrator import AgentRuntime, process_incident, process_next_incident
from agent.store_adapter import IncidentStore
from agent.tracing import TracerLike
from config import Settings
from server.integrations.auth0_client import Auth0Client
from server.integrations.truefoundry_client import MockTrueFoundryClient, TrueFoundryClient
from server.services.approval_policy import ApprovalPolicyDecision, evaluate_approval_policy
from server.services.decision_parser import parse_human_decision
from server.services.deployment_service import DeploymentService
from server.services.escalation_service import EscalationService
from server.services.explanation_service import (
    build_approval_explanation,
    build_call_script,
    build_follow_up_questions,
    build_phone_explanation,
    build_short_explanation,
)
from server.services.fix_artifact_service import package_fix_artifact, package_hotfix
from server.services.flow_router import FlowDecision, route_incident
from server.services.incident_service import IncidentService
from server.services.plan_state_service import (
    build_plan_state_mutation,
    create_execution_plan,
    extract_latest_plan_snapshot,
    revise_execution_plan,
)
from server.services.suggestion_extractor import build_replan_packet, extract_suggestions

REPLAN_MODES = {"suggested", "revision_requested", "replan", "suggestion"}


@dataclass
class DemoFlowService:
    settings: Settings
    store: IncidentStore
    incidents: IncidentService
    tracer: TracerLike
    diagnose: Any
    generate_fix: Any
    escalation: EscalationService
    truefoundry: TrueFoundryClient | MockTrueFoundryClient
    deployment: DeploymentService | None = None
    auth0: Auth0Client | None = None

    async def run_once(self, *, incident_id: str | None = None) -> dict[str, Any]:
        runtime = AgentRuntime(
            store=self.store,
            diagnose=self.diagnose,
            generate_fix=self.generate_fix,
            tracer=self.tracer,
        )

        if incident_id:
            incident = self.incidents.get_incident(incident_id)
            if incident is None:
                raise KeyError(f"Incident not found: {incident_id}")
            if not self._can_rerun(incident):
                raise ValueError(
                    f"Incident {incident_id} is not eligible for rerun from status '{incident.get('status')}'."
                )
            processed = process_incident(runtime, incident, persist=True)
        else:
            processed = process_next_incident(runtime, persist=True)

        if processed is None:
            return {"processed": False, "reason": "no stored incidents"}
        return await self._route_processed_incident(processed)

    async def apply_human_decision(
        self,
        incident_id: str,
        *,
        decision_text: str,
        notes: str | None = None,
        channel: str | None = None,
        decider: str | None = None,
        actor: str,
        sponsor: str,
        suggested_steps: Sequence[str] | None = None,
        constraints: Sequence[str] | None = None,
        bland_call_id: str | None = None,
    ) -> dict[str, Any]:
        incident = self.incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(f"Incident not found: {incident_id}")

        human_input = self._prepare_human_input(
            incident,
            decision_text=decision_text,
            notes=notes,
            channel=channel,
            suggested_steps=suggested_steps,
            constraints=constraints,
        )

        policy = evaluate_approval_policy(incident, human_input["decision_text"])
        auth0_context = self._build_auth0_context(incident, policy)

        if policy.next_action == "replan":
            updated = self._record_replan_request(
                incident,
                policy=policy,
                auth0_context=auth0_context,
                notes=human_input["notes"],
                channel=channel,
                decider=decider,
                actor=actor,
                sponsor=sponsor,
                suggested_steps=human_input["suggested_steps"],
                constraints=human_input["constraints"],
                bland_call_id=bland_call_id,
            )
            hotfix_pkg_dict = self._build_hotfix_package_dict(updated, human_input["constraints"])
            return self._build_result(
                updated,
                flow=route_incident(updated),
                policy=policy,
                auth0_context=auth0_context,
                hotfix_pkg_dict=hotfix_pkg_dict,
                human_input=human_input,
            )

        if policy.next_action == "block":
            updated = self._record_terminal_decision(
                incident,
                target_status=STATUS_BLOCKED,
                policy=policy,
                auth0_context=auth0_context,
                actor=actor,
                sponsor=sponsor,
                notes=human_input["notes"],
                channel=channel,
                decider=decider,
                message="Human rejected the proposed fix.",
                bland_call_id=bland_call_id,
            )
            return self._build_result(
                updated,
                flow=route_incident(updated),
                policy=policy,
                auth0_context=auth0_context,
                human_input=human_input,
            )

        if policy.next_action == "deploy":
            gated = self._record_terminal_decision(
                incident,
                target_status=STATUS_DEPLOYING,
                policy=policy,
                auth0_context=auth0_context,
                actor=actor,
                sponsor=sponsor,
                notes=human_input["notes"],
                channel=channel,
                decider=decider,
                message="Approval recorded. Deployment started.",
                bland_call_id=bland_call_id,
            )
            deployed = self._deploy_incident(
                gated,
                actor=actor,
                sponsor=sponsor,
                constraints=human_input["constraints"],
            )
            return self._build_result(
                deployed[0],
                flow=route_incident(deployed[0]),
                policy=policy,
                auth0_context=auth0_context,
                exec_pkg_dict=deployed[1],
                hotfix_pkg_dict=deployed[2],
                human_input=human_input,
            )

        updated = self._record_pending_review(
            incident,
            policy=policy,
            auth0_context=auth0_context,
            actor=actor,
            sponsor=sponsor,
            notes=human_input["notes"],
            channel=channel,
            decider=decider,
            status=STATUS_AWAITING_APPROVAL,
            message="Human asked for more context before a deployment decision.",
            bland_call_id=bland_call_id,
        )
        return self._build_result(
            updated,
            flow=route_incident(updated),
            policy=policy,
            auth0_context=auth0_context,
            human_input=human_input,
        )

    async def _route_processed_incident(self, incident: Mapping[str, Any]) -> dict[str, Any]:
        flow = route_incident(incident)
        policy = evaluate_approval_policy(incident)
        auth0_context = self._build_auth0_context(incident, policy)

        if policy.next_action == "deploy":
            gated = self._record_terminal_decision(
                incident,
                target_status=STATUS_DEPLOYING,
                policy=policy,
                auth0_context=auth0_context,
                actor="approval-policy",
                sponsor="Auth0",
                notes="Auto-approved by policy.",
                channel=policy.channel,
                decider=policy.decider,
                message="Policy auto-approved deployment.",
            )
            deployed = self._deploy_incident(gated, actor="deployment-service", sponsor="TrueFoundry")
            return self._build_result(
                deployed[0],
                flow=route_incident(deployed[0]),
                policy=policy,
                auth0_context=auth0_context,
                exec_pkg_dict=deployed[1],
                hotfix_pkg_dict=deployed[2],
            )

        if policy.next_action == "call_human":
            escalated = await self._trigger_phone_escalation(
                incident,
                policy=policy,
                auth0_context=auth0_context,
            )
            return self._build_result(
                escalated["incident"],
                flow=route_incident(escalated["incident"]),
                policy=policy,
                auth0_context=auth0_context,
                escalation=escalated,
            )

        pending = self._record_pending_review(
            incident,
            policy=policy,
            auth0_context=auth0_context,
            actor="approval-policy",
            sponsor="Auth0",
            notes=policy.reason,
            channel=policy.channel,
            decider=policy.decider,
            status=STATUS_AWAITING_APPROVAL,
            message="Awaiting human approval before deployment.",
        )
        return self._build_result(
            pending,
            flow=route_incident(pending),
            policy=policy,
            auth0_context=auth0_context,
        )

    async def _trigger_phone_escalation(
        self,
        incident: Mapping[str, Any],
        *,
        policy: ApprovalPolicyDecision,
        auth0_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        phone_number = self.settings.bland_phone_number
        if not phone_number:
            pending = self._record_pending_review(
                incident,
                policy=policy,
                auth0_context=auth0_context,
                actor="approval-policy",
                sponsor="Auth0",
                notes="Phone escalation requested but BLAND_PHONE_NUMBER is not configured.",
                channel="voice_call",
                decider="auth0:phone-escalation",
                status=STATUS_AWAITING_APPROVAL,
                message="Phone escalation required, but no phone number is configured.",
            )
            return {
                "incident": pending,
                "request_payload": None,
                "call_result": {"status": "not_configured"},
                "timeline_event": None,
                "escalated": False,
            }

        result = await self.escalation.trigger_escalation(
            incident["incident_id"],
            phone_number=phone_number,
            webhook_url=self.settings.bland_webhook_url,
            reason=policy.reason,
        )
        updated = self._record_pending_review(
            result.incident,
            policy=policy,
            auth0_context=auth0_context,
            actor="approval-policy",
            sponsor="Auth0",
            notes=policy.reason,
            channel="voice_call",
            decider="auth0:phone-escalation",
            status=STATUS_AWAITING_APPROVAL,
            message="Phone escalation is in progress and waiting for a decision.",
            bland_call_id=result.call_result.get("call_id"),
        )
        return {
            "incident": updated,
            "request_payload": result.request_payload,
            "call_result": result.call_result,
            "timeline_event": result.timeline_event,
            "escalated": result.escalated,
        }

    def _record_pending_review(
        self,
        incident: Mapping[str, Any],
        *,
        policy: ApprovalPolicyDecision,
        auth0_context: Mapping[str, Any],
        actor: str,
        sponsor: str,
        notes: str | None,
        channel: str | None,
        decider: str | None,
        status: str,
        message: str,
        bland_call_id: str | None = None,
    ) -> dict[str, Any]:
        plan = self._build_or_reuse_plan(
            incident,
            source="autonomous",
            requested_by="codex",
            requested_via="backend",
            instruction_text=notes,
        )
        approval_patch = policy.to_approval_patch(
            notes=None,
            bland_call_id=bland_call_id,
            decision_at_ms=None,
        )
        approval_patch.pop("notes", None)
        approval_patch["status"] = APPROVAL_PENDING
        approval_patch["mode"] = "manual"
        approval_patch["channel"] = channel or approval_patch.get("channel")
        approval_patch["decider"] = decider or approval_patch.get("decider")

        mutation = build_plan_state_mutation(
            plan,
            actor=actor,
            sponsor=sponsor,
            incident_status=status,
            message=message,
            approval_patch=approval_patch,
            extra_metadata={"auth0_context": dict(auth0_context)},
        )
        patch = deep_merge_dict(
            mutation.patch,
            {
                "status": status,
                "observability": {
                    "auth0_decision_id": auth0_context.get("auth0_decision_id"),
                },
            },
        )
        return self.incidents.patch_incident(
            incident["incident_id"],
            patch,
            timeline_event=mutation.timeline_event,
        )

    def _record_replan_request(
        self,
        incident: Mapping[str, Any],
        *,
        policy: ApprovalPolicyDecision,
        auth0_context: Mapping[str, Any],
        notes: str,
        channel: str | None,
        decider: str | None,
        actor: str,
        sponsor: str,
        suggested_steps: Sequence[str] | None,
        constraints: Sequence[str] | None,
        bland_call_id: str | None = None,
    ) -> dict[str, Any]:
        existing = self._build_or_reuse_plan(
            incident,
            source="ui" if channel != "voice_call" else "phone",
            requested_by=decider or "human",
            requested_via="ui" if channel != "voice_call" else "phone",
            instruction_text=notes,
        )
        revised = revise_execution_plan(
            existing,
            summary=notes or existing.summary,
            source="ui" if channel != "voice_call" else "phone",
            requested_by=decider or existing.requested_by,
            requested_via="ui" if channel != "voice_call" else "phone",
            steps=suggested_steps,
            constraints=constraints,
            instruction_text=notes,
        )
        approval_patch = policy.to_approval_patch(
            notes=None,
            bland_call_id=bland_call_id,
            decision_at_ms=now_ms(),
        )
        approval_patch.pop("notes", None)
        approval_patch["mode"] = "manual"
        approval_patch["status"] = APPROVAL_PENDING
        approval_patch["channel"] = channel or "ui"
        approval_patch["decider"] = decider or "human"

        mutation = build_plan_state_mutation(
            revised,
            actor=actor,
            sponsor=sponsor,
            incident_status=STATUS_GATING,
            message="Human requested a revised execution plan.",
            approval_patch=approval_patch,
            extra_metadata={"auth0_context": dict(auth0_context)},
        )

        hotfix_pkg_dict = self._build_hotfix_package_dict(incident, constraints)
        patch = deep_merge_dict(
            mutation.patch,
            {
                "status": STATUS_GATING,
                "observability": {
                    "auth0_decision_id": auth0_context.get("auth0_decision_id"),
                },
            },
        )
        if hotfix_pkg_dict and mutation.timeline_event:
            mutation.timeline_event["metadata"].update(
                {
                    "hotfix_scope_note": hotfix_pkg_dict.get("scope_note"),
                    "hotfix_plan": hotfix_pkg_dict.get("hotfix_plan"),
                }
            )
        return self.incidents.patch_incident(
            incident["incident_id"],
            patch,
            timeline_event=mutation.timeline_event,
        )

    def _record_terminal_decision(
        self,
        incident: Mapping[str, Any],
        *,
        target_status: str,
        policy: ApprovalPolicyDecision,
        auth0_context: Mapping[str, Any],
        actor: str,
        sponsor: str,
        notes: str | None,
        channel: str | None,
        decider: str | None,
        message: str,
        bland_call_id: str | None = None,
    ) -> dict[str, Any]:
        approval_patch = policy.to_approval_patch(
            notes=notes,
            bland_call_id=bland_call_id or (incident.get("approval") or {}).get("bland_call_id"),
            decision_at_ms=now_ms(),
        )
        approval_patch["channel"] = channel or approval_patch.get("channel")
        approval_patch["decider"] = decider or approval_patch.get("decider")
        timeline_event = make_timeline_event(
            status=target_status,
            actor=actor,
            message=message,
            sponsor=sponsor,
            metadata={
                "approval": dict(approval_patch),
                "auth0_context": dict(auth0_context),
            },
        )
        patch = {
            "status": target_status,
            "approval": approval_patch,
            "observability": {
                "auth0_decision_id": auth0_context.get("auth0_decision_id"),
            },
        }
        return self.incidents.patch_incident(
            incident["incident_id"],
            patch,
            timeline_event=timeline_event,
        )

    def _deploy_incident(
        self,
        incident: Mapping[str, Any],
        *,
        actor: str,
        sponsor: str,
        constraints: Sequence[str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        artifact = package_fix_artifact(dict(incident), dict(incident.get("fix") or {}))
        exec_pkg_dict = self._build_execution_package_dict(artifact, constraints)
        hotfix_pkg_dict = self._build_hotfix_package_dict(incident, constraints)

        svc = self.deployment or DeploymentService(
            store_adapter=self.incidents,
            truefoundry_client=self.truefoundry,
        )
        svc.deploy(dict(incident), artifact)
        updated = self.incidents.get_incident(incident["incident_id"]) or dict(incident)
        return updated, exec_pkg_dict, hotfix_pkg_dict

    def _build_or_reuse_plan(
        self,
        incident: Mapping[str, Any],
        *,
        source: str,
        requested_by: str,
        requested_via: str,
        instruction_text: str | None,
    ):
        snapshot = extract_latest_plan_snapshot(incident)
        if snapshot:
            return create_execution_plan(
                title=str(snapshot.get("title") or "Incident execution plan"),
                summary=str(snapshot.get("summary") or "Execute the prepared fix safely."),
                source=str(snapshot.get("source") or source),
                requested_by=str(snapshot.get("requested_by") or requested_by),
                requested_via=str(snapshot.get("requested_via") or requested_via),
                target_stage=str(snapshot.get("target_stage") or "deploying"),
                steps=snapshot.get("steps") or (),
                constraints=snapshot.get("constraints") or (),
                state=str(snapshot.get("state") or "pending"),
                plan_id=str(snapshot.get("plan_id") or ""),
                revision=int(snapshot.get("revision") or 1),
                parent_plan_id=snapshot.get("parent_plan_id"),
                created_at_ms=int(snapshot.get("created_at_ms") or now_ms()),
                updated_at_ms=int(snapshot.get("updated_at_ms") or now_ms()),
                instruction_text=str(snapshot.get("instruction_text") or instruction_text or ""),
            )

        title = str(incident.get("title") or f"Resolve incident {incident.get('incident_id')}")
        diagnosis = incident.get("diagnosis") or {}
        fix = incident.get("fix") or {}
        summary = str(
            diagnosis.get("suggested_fix")
            or diagnosis.get("root_cause")
            or "Apply the generated fix and verify the affected endpoint."
        )
        files_changed = fix.get("files_changed") or []
        steps = list(fix.get("test_plan") or [])
        if files_changed:
            steps.insert(0, f"Apply the patch to {files_changed[0]}")
        if not steps:
            steps = [
                "Apply the generated patch",
                "Deploy the service",
                "Verify the failing endpoint recovers",
            ]
        defaults = [
            "Keep the fix scoped to the failing path",
            "Preserve the public API contract",
        ]
        return create_execution_plan(
            title=title,
            summary=summary,
            source=source,
            requested_by=requested_by,
            requested_via=requested_via,
            target_stage="deploying",
            steps=steps,
            constraints=defaults,
            instruction_text=instruction_text,
        )

    def _build_auth0_context(
        self,
        incident: Mapping[str, Any],
        policy: ApprovalPolicyDecision,
    ) -> dict[str, Any]:
        if self.auth0 is not None:
            return self.auth0.build_gate_context(incident, policy)
        incident_id = str(incident.get("incident_id") or "incident")
        return {
            "incident_id": incident.get("incident_id"),
            "severity": policy.severity,
            "approval": {
                "required": policy.required,
                "mode": policy.mode,
                "status": policy.status,
                "channel": policy.channel,
                "decider": policy.decider,
            },
            "auth0_decision_id": f"auth0-{incident_id}-{policy.severity}-{policy.route}",
            "requires_phone_escalation": policy.requires_phone_escalation,
            "next_action": policy.next_action,
        }

    def _build_result(
        self,
        incident: Mapping[str, Any],
        *,
        flow: FlowDecision,
        policy: ApprovalPolicyDecision,
        auth0_context: Mapping[str, Any],
        escalation: Mapping[str, Any] | None = None,
        exec_pkg_dict: dict[str, Any] | None = None,
        hotfix_pkg_dict: dict[str, Any] | None = None,
        human_input: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        explanations = self._build_explanations(incident)
        return {
            "processed": True,
            "incident": dict(incident),
            "flow": {
                "action": flow.action,
                "mode": flow.mode,
                "reason": flow.reason,
                "next_status": flow.next_status,
                "requires_human": flow.requires_human,
                "should_call_human": flow.should_call_human,
            },
            "policy": {
                "severity": policy.severity,
                "required": policy.required,
                "mode": policy.mode,
                "status": policy.status,
                "route": policy.route,
                "next_action": policy.next_action,
                "channel": policy.channel,
                "decider": policy.decider,
                "reason": policy.reason,
                "requires_phone_escalation": policy.requires_phone_escalation,
            },
            "auth0_context": dict(auth0_context),
            "explanations": explanations,
            "escalation": dict(escalation) if escalation else None,
            "execution_package": exec_pkg_dict,
            "hotfix_package": hotfix_pkg_dict,
            "human_input": dict(human_input) if human_input else None,
        }

    def _prepare_human_input(
        self,
        incident: Mapping[str, Any],
        *,
        decision_text: str,
        notes: str | None,
        channel: str | None,
        suggested_steps: Sequence[str] | None,
        constraints: Sequence[str] | None,
    ) -> dict[str, Any]:
        source = (notes or decision_text or "").strip()
        parsed = parse_human_decision(source, source=channel or "ui") if source else {
            "decision": "no_answer",
            "confidence": 1.0,
            "raw_input": "",
            "source": channel or "ui",
            "reasoning": "No human input provided.",
            "suggestions": [],
            "constraints": [],
        }

        normalized_decision = (decision_text or parsed["decision"] or "clarify").strip().lower()
        if normalized_decision in {"revise", "suggestion"}:
            normalized_decision = "suggest"
        if normalized_decision in {"defer", "ask_context", "retry", "no_answer", "pending"}:
            normalized_decision = "clarify"

        normalized_notes = notes or parsed.get("raw_input") or decision_text
        normalized_steps = list(suggested_steps or [])
        normalized_constraints = list(constraints or [])

        if normalized_decision == "suggest" and normalized_notes:
            replan_packet = build_replan_packet(
                normalized_notes,
                dict(incident),
                current_diagnosis=dict(incident.get("diagnosis") or {}),
                current_fix=dict(incident.get("fix") or {}),
            )
            if not normalized_steps:
                normalized_steps = list(replan_packet.get("plan_notes") or [])
            if not normalized_constraints:
                normalized_constraints = self._constraint_strings_from_extracted(
                    replan_packet.get("extracted_constraints") or {}
                )
        elif normalized_notes and not normalized_constraints:
            normalized_constraints = self._constraint_strings_from_extracted(
                extract_suggestions(normalized_notes, dict(incident))
            )

        return {
            "decision_text": normalized_decision,
            "notes": normalized_notes,
            "suggested_steps": normalized_steps,
            "constraints": normalized_constraints,
            "parsed": parsed,
        }

    @staticmethod
    def _constraint_strings_from_extracted(extracted: Mapping[str, Any]) -> list[str]:
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

    @staticmethod
    def _constraint_flags(constraints: Sequence[str] | None) -> dict[str, bool]:
        flags = {
            "skip_auth": False,
            "endpoint_only": False,
            "hotfix_only": False,
        }
        for raw in constraints or ():
            text = str(raw).lower()
            if "auth" in text and any(token in text for token in ("avoid", "skip", "don't touch", "untouched")):
                flags["skip_auth"] = True
            if any(token in text for token in ("endpoint", "route", "path only", "scope to /")):
                flags["endpoint_only"] = True
            if "hotfix" in text or "minimal" in text:
                flags["hotfix_only"] = True
        return flags

    def _build_execution_package_dict(
        self,
        artifact: Any,
        constraints: Sequence[str] | None = None,
    ) -> dict[str, Any] | None:
        try:
            exec_pkg = format_execution_package(artifact, constraints=self._constraint_flags(constraints))
            return asdict(exec_pkg)
        except Exception as exc:  # noqa: BLE001
            self._safe_log(f"[demo_flow] execution_package generation failed: {exc}")
            return None

    def _build_hotfix_package_dict(
        self,
        incident: Mapping[str, Any],
        constraints: Sequence[str] | None = None,
    ) -> dict[str, Any] | None:
        if not any("hotfix" in str(item).lower() for item in (constraints or ())):
            return None

        excluded_files = [
            str(item).split(" ", 1)[1]
            for item in (constraints or ())
            if str(item).lower().startswith("avoid ")
        ]
        try:
            hotfix_pkg = package_hotfix(
                dict(incident),
                dict(incident.get("fix") or {}),
                excluded_files=excluded_files or None,
            )
            return asdict(hotfix_pkg)
        except Exception as exc:  # noqa: BLE001
            self._safe_log(f"[demo_flow] hotfix_package generation failed: {exc}")
            return None

    @staticmethod
    def _build_explanations(incident: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(incident)
        return {
            "approval": build_approval_explanation(payload),
            "short": build_short_explanation(payload),
            "phone": build_phone_explanation(payload),
            "call_script": build_call_script(payload),
            "follow_up_questions": build_follow_up_questions(payload),
        }

    def _safe_log(self, message: str) -> None:
        logger = getattr(self.tracer, "log", None)
        if callable(logger):
            logger(message)

    @staticmethod
    def _can_rerun(incident: Mapping[str, Any]) -> bool:
        status = str(incident.get("status") or "")
        if status == STATUS_STORED:
            return True
        if status in {STATUS_RESOLVED, STATUS_BLOCKED, STATUS_FAILED, STATUS_DEPLOYING}:
            return False
        approval = incident.get("approval") or {}
        mode = str(approval.get("mode") or "").lower()
        return mode in REPLAN_MODES
