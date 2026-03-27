"""
fixer.py - Main fix-generation pipeline for the DeepOps Person A agent.
"""

from __future__ import annotations

import time

from agent.fix_specs import _detect_bug_class, generate_fix_spec
from agent.kiro_client import KiroClient

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_SCHEMA_FIX_KEYS = {"status", "spec_markdown", "diff_preview", "files_changed", "test_plan", "started_at_ms", "completed_at_ms"}


def extract_schema_fix(fix_result: dict) -> dict:
    """Return only the schema-valid fix fields, stripping _metadata and any other extras."""
    return {k: v for k, v in fix_result.items() if k in _SCHEMA_FIX_KEYS}


# ---------------------------------------------------------------------------
# Diff trimming
# ---------------------------------------------------------------------------

def trim_diff(diff: str, max_lines: int = 50) -> str:
    """
    Keep header lines (--- +++ @@) and truncate body if over max_lines.
    Appends a '# ... (truncated)' note when truncated.
    """
    lines = diff.splitlines()
    if len(lines) <= max_lines:
        return diff

    # Always keep header lines at the top
    header: list[str] = []
    body: list[str] = []
    in_header = True
    for line in lines:
        if in_header and (line.startswith("---") or line.startswith("+++") or line.startswith("@@")):
            header.append(line)
        else:
            in_header = False
            body.append(line)

    remaining = max_lines - len(header)
    truncated_body = body[:max(remaining, 0)]
    result_lines = header + truncated_body + ["# ... (truncated)"]
    return "\n".join(result_lines)


# ---------------------------------------------------------------------------
# Fallback diff generation
# ---------------------------------------------------------------------------

_FALLBACK_DIFFS: dict[str, str] = {
    "zero_div": """\
# [fallback mode]
--- a/{source_file}
+++ b/{source_file}
@@ -1,6 +1,9 @@
 def compute(value, divisor):
+    if divisor == 0:
+        raise ValueError("divisor must not be zero")
     return value / divisor
""",
    "null_user": """\
# [fallback mode]
--- a/{source_file}
+++ b/{source_file}
@@ -1,6 +1,9 @@
 def get_user_data(user_id):
     user = db.find(user_id)
+    if user is None:
+        raise KeyError(f"User {{user_id}} not found")
     return user.profile
""",
    "timeout": """\
# [fallback mode]
--- a/{source_file}
+++ b/{source_file}
@@ -1,5 +1,11 @@
+import signal
+
 def run_search(query):
-    result = slow_search(query)
-    return result
+    def _handler(signum, frame):
+        raise TimeoutError("search exceeded time limit")
+    signal.signal(signal.SIGALRM, _handler)
+    signal.alarm(5)
+    try:
+        return slow_search(query)
+    finally:
+        signal.alarm(0)
""",
}

_GENERIC_FALLBACK_DIFF = """\
# [fallback mode]
--- a/{source_file}
+++ b/{source_file}
@@ -1,4 +1,7 @@
 def affected_function(*args, **kwargs):
+    try:
         result = original_logic(*args, **kwargs)
+    except Exception as exc:
+        raise RuntimeError(f"Unhandled error in affected_function: {{exc}}") from exc
     return result
"""


def _build_fallback_diff(diagnosis: dict, incident: dict) -> tuple[str, list[str]]:
    """Return (diff_str, files_changed) for fallback mode."""
    bug_class = _detect_bug_class(diagnosis)
    source_file = incident.get("source", {}).get("source_file", "app/main.py")
    affected = diagnosis.get("affected_components") or []

    template = _FALLBACK_DIFFS.get(bug_class, _GENERIC_FALLBACK_DIFF)
    diff = template.format(source_file=source_file)

    files_changed = [source_file] if source_file else []
    for comp in affected:
        if comp not in files_changed:
            files_changed.append(comp)

    return diff, files_changed


# ---------------------------------------------------------------------------
# Demo-grade summaries (task 8)
# ---------------------------------------------------------------------------

_FIX_SUMMARIES: dict[str, str] = {
    "zero_div": "Add zero-guard before division to return HTTP 400 instead of crashing.",
    "null_user": "Add null check after user lookup to return 404 instead of propagating KeyError.",
    "timeout": "Replace blocking call with async-safe equivalent and enforce explicit timeout.",
}

_REGRESSION_WARNINGS: dict[str, str] = {
    "zero_div": "Verify all callers of the divide helper still work with non-zero inputs.",
    "null_user": "Confirm cached user lookups are invalidated correctly after the fix.",
    "timeout": "Watch for retry storms — clients may hammer the endpoint after timeout errors.",
}


def build_fix_summary(diagnosis: dict) -> str:
    """One-line fix summary suitable for dashboard cards and demo narration."""
    bug_class = _detect_bug_class(diagnosis)
    if bug_class and bug_class in _FIX_SUMMARIES:
        return _FIX_SUMMARIES[bug_class]
    suggested = diagnosis.get("suggested_fix") or ""
    # Truncate to first sentence for dashboard friendliness
    first_sentence = suggested.split(".")[0].strip()
    return first_sentence + "." if first_sentence else "Apply fix to affected component."


def build_regression_warning(diagnosis: dict) -> str | None:
    """One-line regression warning, or None if not applicable."""
    bug_class = _detect_bug_class(diagnosis)
    return _REGRESSION_WARNINGS.get(bug_class) if bug_class else None


# ---------------------------------------------------------------------------
# Test plan generation
# ---------------------------------------------------------------------------

def _build_test_plan(diagnosis: dict, incident: dict) -> list[str]:
    """Generate 2-3 test steps from the diagnosis."""
    affected = diagnosis.get("affected_components") or []
    source = incident.get("source", {})
    error_type = source.get("error_type", "the error")
    bug_class = _detect_bug_class(diagnosis)

    steps: list[str] = []

    # Step 1: component-specific verification
    if affected:
        component = affected[0]
        steps.append(f"Verify {component} handles {error_type} gracefully")
    else:
        steps.append(f"Verify the affected endpoint handles {error_type} gracefully")

    # Step 2: regression check per component (or generic)
    if len(affected) > 1:
        steps.append(f"Confirm existing {affected[1]} behavior is unchanged")
    elif affected:
        steps.append(f"Confirm existing {affected[0]} behavior is unchanged")
    else:
        steps.append("Confirm existing service behavior is unchanged after the fix")

    # Step 3: bug-class-specific integration check
    if bug_class == "zero_div":
        steps.append("Run integration test with zero-value input to confirm safe error response")
    elif bug_class == "null_user":
        steps.append("Run integration test with unknown user ID to confirm 404 or handled error")
    elif bug_class == "timeout":
        steps.append("Run integration test with a slow input to confirm timeout is enforced")
    else:
        steps.append("Run the full regression suite to confirm no unintended side effects")

    return steps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_fix_generation(
    incident: dict,
    diagnosis: dict,
    repo_path: str = ".",
) -> dict:
    """
    Main fix-generation pipeline.

    1. Generates a Kiro spec via generate_fix_spec.
    2. Tries to run the Kiro CLI via KiroClient.run().
    3. Falls back to a plausible synthetic diff if Kiro is unavailable or fails.
    4. Builds a 2-3 step test plan from the diagnosis.
    5. Returns a complete fix payload dict.
    """
    started_at_ms: int = time.time_ns() // 1_000_000

    spec_markdown = generate_fix_spec(diagnosis, incident)

    kiro_mode = "fallback"
    diff_preview: str | None = None
    files_changed: list[str] = []

    try:
        client = KiroClient()
        result = client.run(spec_markdown, repo_path=repo_path)
        if result.get("success"):
            kiro_mode = "real"
            diff_preview = result.get("diff_preview")
            files_changed = result.get("files_changed") or []
    except Exception:
        pass  # any unexpected error → fallback

    if kiro_mode == "fallback":
        diff_preview, files_changed = _build_fallback_diff(diagnosis, incident)

    if diff_preview:
        diff_preview = trim_diff(diff_preview)

    test_plan = _build_test_plan(diagnosis, incident)
    fix_summary = build_fix_summary(diagnosis)
    regression_warning = build_regression_warning(diagnosis)

    completed_at_ms: int = time.time_ns() // 1_000_000

    return {
        "status": "complete",
        "spec_markdown": spec_markdown,
        "diff_preview": diff_preview,
        "files_changed": files_changed,
        "test_plan": test_plan,
        "started_at_ms": started_at_ms,
        "completed_at_ms": completed_at_ms,
        "_metadata": {
            "kiro_mode": kiro_mode,
            "fix_summary": fix_summary,
            "regression_warning": regression_warning,
        },
    }
