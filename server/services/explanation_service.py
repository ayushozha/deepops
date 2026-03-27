"""Approval explanation payloads and phone call script generation.

Turns raw incident state into human-readable explanations for
dashboard UI, phone calls, and notification surfaces.
"""

from __future__ import annotations


def _get(d: dict, *keys, default="unknown"):
    """Safely traverse nested dicts."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            return default
    return cur if cur is not None else default


def build_approval_explanation(incident: dict) -> dict:
    """Build a complete approval explanation payload."""
    source = incident.get("source", {})
    diag = incident.get("diagnosis", {})
    fix = incident.get("fix", {})
    severity = incident.get("severity", "unknown")
    error_type = source.get("error_type", "Unknown error")
    path = source.get("path", "unknown route")
    root_cause = diag.get("root_cause") or "Root cause not yet determined."
    suggested_fix = diag.get("suggested_fix") or "No fix proposed yet."
    components = diag.get("affected_components", [])
    confidence = diag.get("confidence", 0.0)
    sev_reasoning = diag.get("severity_reasoning") or ""
    files = fix.get("files_changed", [])

    blast = ", ".join(components) if components else "unknown scope"
    files_str = ", ".join(files) if files else "no files identified yet"

    return {
        "summary": (
            f"A {error_type} on {path} needs approval before deployment. "
            f"Severity: {severity}. Confidence: {confidence:.0%}."
        ),
        "what_broke": (
            f"{error_type} occurred at {path} in {source.get('source_file', 'unknown file')}. "
            f"{root_cause}"
        ),
        "what_we_want_to_do": (
            f"Proposed fix: {suggested_fix} "
            f"Files affected: {files_str}."
        ),
        "why_approval_needed": (
            f"This incident is {severity} severity. {sev_reasoning} "
            f"Human approval is required before deployment."
        ),
        "blast_radius": (
            f"Affected components: {blast}."
        ),
        "if_we_proceed": (
            f"The fix will be deployed via TrueFoundry. "
            f"The {error_type} on {path} should be resolved."
        ),
        "if_we_dont": (
            f"The {error_type} will continue occurring on {path}. "
            f"Users hitting this endpoint will see a server error."
        ),
        "severity": severity,
        "confidence": confidence,
        "incident_id": incident.get("incident_id", "unknown"),
    }


def build_short_explanation(incident: dict) -> str:
    """One-paragraph explanation for dashboard cards."""
    source = incident.get("source", {})
    diag = incident.get("diagnosis", {})
    severity = incident.get("severity", "unknown")
    error_type = source.get("error_type", "An error")
    path = source.get("path", "an endpoint")
    root_cause = diag.get("root_cause") or "Cause under investigation."
    suggested_fix = diag.get("suggested_fix") or ""

    parts = [f"{error_type} hit {path}."]
    if root_cause:
        parts.append(root_cause)
    if suggested_fix:
        parts.append(f"Proposed fix: {suggested_fix}.")
    parts.append(f"Severity: {severity}.")
    return " ".join(parts)[:300]


def build_phone_explanation(incident: dict) -> str:
    """Explanation optimized for spoken delivery."""
    source = incident.get("source", {})
    diag = incident.get("diagnosis", {})
    severity = incident.get("severity", "unknown")
    error_type = source.get("error_type", "an error")
    path = source.get("path", "an endpoint")
    root_cause = diag.get("root_cause") or "We're still determining the root cause."
    suggested_fix = diag.get("suggested_fix") or "We have a proposed fix ready."
    components = diag.get("affected_components", [])

    scope = f"affecting {', '.join(components)}" if components else "with limited scope"

    if severity == "critical":
        opener = f"We have a critical production issue."
    else:
        opener = f"We detected a {severity}-severity issue in production."

    return (
        f"{opener} "
        f"A {error_type} is occurring on the {path} endpoint. "
        f"The root cause is: {root_cause} "
        f"We've prepared a fix: {suggested_fix} "
        f"This is {scope}. Do you approve deployment?"
    )


def build_call_script(incident: dict) -> dict:
    """Build a complete Bland AI call script with follow-up questions."""
    source = incident.get("source", {})
    diag = incident.get("diagnosis", {})
    severity = incident.get("severity", "unknown")
    incident_id = incident.get("incident_id", "unknown")
    error_type = source.get("error_type", "an error")
    path = source.get("path", "an endpoint")
    root_cause = diag.get("root_cause") or "under investigation"
    suggested_fix = diag.get("suggested_fix") or "a proposed fix"
    components = diag.get("affected_components", [])
    scope = ", ".join(components) if components else "limited scope"

    if severity == "critical":
        greeting = (
            f"This is an urgent incident notification from DeepOps. "
            f"We have a critical production issue that requires your immediate attention."
        )
    else:
        greeting = (
            f"This is DeepOps calling about a production incident. "
            f"We have a {severity}-severity issue that needs your approval."
        )

    explanation = (
        f"Incident {incident_id}: a {error_type} is occurring on the {path} endpoint. "
        f"The root cause is {root_cause}."
    )

    proposed = (
        f"Our system has prepared a fix: {suggested_fix}. "
        f"This affects {scope}."
    )

    ask = "Do you approve deploying this fix to production?"

    follow_unclear = (
        "I didn't catch a clear answer. Would you like to approve the deployment, "
        "reject it, or would you prefer to review the details first?"
    )

    follow_away = (
        "If you're away from a computer, you can give me verbal instructions. "
        "For example, you can say 'go ahead and deploy', 'hold off', "
        "or give me specific constraints like 'deploy but avoid touching the auth module'."
    )

    closing = "Thank you. DeepOps will proceed based on your decision."

    full = f"{greeting} {explanation} {proposed} {ask}"

    return {
        "greeting": greeting,
        "incident_explanation": explanation,
        "proposed_action": proposed,
        "ask_for_decision": ask,
        "follow_up_if_unclear": follow_unclear,
        "follow_up_if_away_from_computer": follow_away,
        "closing": closing,
        "full_script": full,
    }


def build_follow_up_questions(incident: dict) -> list[str]:
    """Generate follow-up questions for unclear approval."""
    source = incident.get("source", {})
    diag = incident.get("diagnosis", {})
    path = source.get("path", "the endpoint")

    return [
        "Would you like to proceed with the proposed fix?",
        "Should we hold off and wait for you to review the code?",
        f"Is there a specific area of the codebase you'd like us to avoid when fixing {path}?",
        "Would you prefer we roll back instead of deploying a fix?",
        "Would you like to suggest an alternative approach?",
    ]
