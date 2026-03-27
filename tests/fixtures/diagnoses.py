"""
Fixture diagnosis and incident payloads for the three known DeepOps demo bugs.
"""

# ---------------------------------------------------------------------------
# Diagnosis fixtures
# ---------------------------------------------------------------------------

DIVIDE_BY_ZERO_DIAGNOSIS = {
    "root_cause": (
        "The calculate endpoint divides by the raw path parameter without validating "
        "zero, so value 0 raises an unhandled ZeroDivisionError."
    ),
    "suggested_fix": (
        "Add a guard clause before division and return a safe validation error "
        "when value is 0."
    ),
    "affected_components": ["demo-app/main.py", "calculate endpoint"],
    "confidence": 0.96,
    "severity_reasoning": (
        "The bug is user-facing but isolated to one endpoint and has a safe "
        "deterministic fix."
    ),
}

MISSING_USER_DIAGNOSIS = {
    "root_cause": (
        "The /user/{user_id} endpoint performs a dict lookup without checking "
        "whether the key exists, raising a KeyError when an unknown user ID is "
        "requested. Downstream attribute access on None also triggers AttributeError."
    ),
    "suggested_fix": (
        "Add a null/existence check after the user lookup and return a 404 "
        "response before accessing any attributes on the result."
    ),
    "affected_components": ["demo-app/main.py", "user endpoint"],
    "confidence": 0.91,
    "severity_reasoning": (
        "Missing-user lookups are a common path; the fix is straightforward and "
        "low-risk."
    ),
}

BLOCKING_TIMEOUT_DIAGNOSIS = {
    "root_cause": (
        "The /search endpoint calls a blocking sleep inside an async handler, "
        "causing the event loop to stall and the request to exceed the timeout "
        "threshold, raising a TimeoutError."
    ),
    "suggested_fix": (
        "Replace the blocking sleep with asyncio.sleep (or equivalent async "
        "primitive) and enforce an explicit timeout, returning a structured "
        "timeout error response on expiry."
    ),
    "affected_components": ["demo-app/main.py", "search endpoint"],
    "confidence": 0.88,
    "severity_reasoning": (
        "Blocking the event loop affects all concurrent requests, not just the "
        "one that triggered the timeout."
    ),
}

# ---------------------------------------------------------------------------
# Incident fixtures  (minimal shape required by fix_specs.generate_fix_spec)
# ---------------------------------------------------------------------------

DIVIDE_BY_ZERO_INCIDENT = {
    "incident_id": "inc-test-zero-div",
    "status": "open",
    "severity": "medium",
    "service": "deepops-demo-app",
    "source": {
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero",
        "source_file": "demo-app/main.py",
        "path": "/calculate/0",
    },
}

MISSING_USER_INCIDENT = {
    "incident_id": "inc-test-missing-user",
    "status": "open",
    "severity": "low",
    "service": "deepops-demo-app",
    "source": {
        "error_type": "KeyError",
        "error_message": "'unknown'",
        "source_file": "demo-app/main.py",
        "path": "/user/unknown",
    },
}

BLOCKING_TIMEOUT_INCIDENT = {
    "incident_id": "inc-test-blocking-timeout",
    "status": "open",
    "severity": "high",
    "service": "deepops-demo-app",
    "source": {
        "error_type": "TimeoutError",
        "error_message": "search timed out",
        "source_file": "demo-app/main.py",
        "path": "/search",
    },
}

# ---------------------------------------------------------------------------
# Expected fix output shapes (for Overclaw eval dataset / regression checks)
# ---------------------------------------------------------------------------

DIVIDE_BY_ZERO_EXPECTED_FIX = {
    "status": "complete",
    "files_changed": ["demo-app/main.py"],
    "test_plan_contains": ["ZeroDivisionError", "calculate"],
    "spec_contains": ["zero", "division", "guard"],
    "_fix_summary": "Add zero-guard before division to return HTTP 400 instead of crashing.",
}

MISSING_USER_EXPECTED_FIX = {
    "status": "complete",
    "files_changed": ["demo-app/main.py"],
    "test_plan_contains": ["KeyError", "user"],
    "spec_contains": ["null", "user", "404"],
    "_fix_summary": "Add null check after user lookup to return 404 instead of propagating KeyError.",
}

BLOCKING_TIMEOUT_EXPECTED_FIX = {
    "status": "complete",
    "files_changed": ["demo-app/main.py"],
    "test_plan_contains": ["TimeoutError", "search"],
    "spec_contains": ["timeout", "blocking", "async"],
    "_fix_summary": "Replace blocking call with async-safe equivalent and enforce explicit timeout.",
}
