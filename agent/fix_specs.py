"""
fix_specs.py - Deterministic markdown spec generator for DeepOps fix payloads.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Demo-bug detection helpers
# ---------------------------------------------------------------------------

_ZERO_DIV_SIGNALS = {"zerodivisionerror", "divide-by-zero", "division by zero", "divisionbyzero"}
_NULL_USER_SIGNALS = {"keyerror", "attributeerror", "missing user", "nonetype", "none has no attribute"}
_TIMEOUT_SIGNALS = {"timeouterror", "timeout", "blocking sleep", "blocking", "search timeout"}


def _detect_bug_class(diagnosis: dict) -> str | None:
    """Return 'zero_div', 'null_user', 'timeout', or None."""
    haystack = " ".join([
        (diagnosis.get("root_cause") or ""),
        (diagnosis.get("suggested_fix") or ""),
        " ".join(diagnosis.get("affected_components") or []),
    ]).lower()

    if any(s in haystack for s in _ZERO_DIV_SIGNALS):
        return "zero_div"
    if any(s in haystack for s in _NULL_USER_SIGNALS):
        return "null_user"
    if any(s in haystack for s in _TIMEOUT_SIGNALS):
        return "timeout"
    return None


# ---------------------------------------------------------------------------
# Per-bug-class spec fragments
# ---------------------------------------------------------------------------

_FRAGMENTS: dict[str, dict] = {
    "zero_div": {
        "title": "Zero-Division Guard",
        "requirements": [
            "Prevent unhandled ZeroDivisionError when the divisor is zero",
            "Return a safe, descriptive error response instead of a 500",
        ],
        "criteria": [
            "Endpoint returns a handled error (e.g. HTTP 400) when value is 0",
            "Non-zero inputs continue to return the correct result",
            "No unhandled exception propagates to the caller",
        ],
        "approach": (
            "Add a guard clause before the division operation that checks for zero "
            "and raises/returns a validation error immediately."
        ),
        "risks": [
            "Other callers of the same helper may rely on the raw exception — verify usages",
            "Edge case: negative divisors that produce unexpected results",
        ],
    },
    "null_user": {
        "title": "Missing-User Null Handling",
        "requirements": [
            "Handle the case where a user lookup returns None or a missing key",
            "Return a meaningful error instead of propagating KeyError / AttributeError",
        ],
        "criteria": [
            "Request with an unknown user ID returns a handled 404 or equivalent",
            "Existing valid-user paths are unaffected",
            "No AttributeError or KeyError surfaces to the caller",
        ],
        "approach": (
            "Add a null/existence check after the user lookup and return an appropriate "
            "error response before accessing any attributes on the result."
        ),
        "risks": [
            "Downstream code that assumes a user object is always present may need updating",
            "Caching layers may serve stale None values — check cache invalidation",
        ],
    },
    "timeout": {
        "title": "Timeout / Blocking-Call Fix",
        "requirements": [
            "Prevent the service from hanging on a slow or blocking operation",
            "Enforce an explicit timeout and surface a clear error on expiry",
        ],
        "criteria": [
            "Operation completes or fails within the configured timeout window",
            "Caller receives a timeout error response rather than an indefinite hang",
            "Non-blocking path (fast inputs) is unaffected",
        ],
        "approach": (
            "Replace the blocking call with an async-safe or timeout-bounded equivalent, "
            "and catch the timeout exception to return a structured error."
        ),
        "risks": [
            "Partial state may be left behind if the operation is interrupted mid-way",
            "Downstream retries could amplify load — consider backoff strategy",
        ],
    },
}

_GENERIC_FRAGMENT = {
    "title": "Bug Fix",
    "requirements": [
        "Resolve the identified root cause without breaking existing behaviour",
        "Ensure the fix is isolated to the affected component(s)",
    ],
    "criteria": [
        "The error no longer occurs under the conditions described in the diagnosis",
        "Existing functionality remains intact",
    ],
    "approach": "Apply the suggested fix to the affected component(s) with appropriate error handling.",
    "risks": [
        "Unintended side-effects in callers that depend on the current (broken) behaviour",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_fix_spec(diagnosis: dict, incident: dict) -> str:
    """
    Generate a deterministic markdown fix specification.

    Args:
        diagnosis: dict with keys root_cause, suggested_fix, affected_components,
                   confidence, severity_reasoning (optional)
        incident:  full incident dict (used for service name, error_type, etc.)

    Returns:
        Markdown string.
    """
    bug_class = _detect_bug_class(diagnosis)
    frag = _FRAGMENTS.get(bug_class, _GENERIC_FRAGMENT) if bug_class else _GENERIC_FRAGMENT

    source = incident.get("source", {})
    service = incident.get("service", "unknown-service")
    error_type = source.get("error_type", "")
    source_file = source.get("source_file", "")
    affected = diagnosis.get("affected_components") or []
    confidence = diagnosis.get("confidence", 0.0)
    root_cause = diagnosis.get("root_cause") or "Unknown root cause."
    suggested_fix = diagnosis.get("suggested_fix") or frag["approach"]
    severity_note = diagnosis.get("severity_reasoning") or ""

    # Build files-to-inspect list (deduplicated, source file first)
    files_to_inspect: list[str] = []
    if source_file:
        files_to_inspect.append(source_file)
    for comp in affected:
        if comp not in files_to_inspect:
            files_to_inspect.append(comp)
    if not files_to_inspect:
        files_to_inspect = ["(see affected_components in diagnosis)"]

    title = f"{frag['title']} — {service}"
    if error_type:
        title += f" ({error_type})"

    lines: list[str] = [
        f"# Fix Specification: {title}",
        "",
        "## Requirements",
    ]
    for req in frag["requirements"]:
        lines.append(f"- {req}")

    lines += ["", "## Acceptance Criteria"]
    for crit in frag["criteria"]:
        lines.append(f"- {crit}")

    lines += [
        "",
        "## Root Cause",
        root_cause,
        "",
        "## Implementation Approach",
        suggested_fix,
    ]

    if severity_note:
        lines += ["", f"_Severity note: {severity_note}_"]

    lines += ["", f"_Diagnosis confidence: {confidence:.0%}_", "", "## Files to Inspect"]
    for f in files_to_inspect:
        lines.append(f"- `{f}`")

    lines += ["", "## Regression Risks"]
    for risk in frag["risks"]:
        lines.append(f"- {risk}")

    return "\n".join(lines) + "\n"
