# Overclaw Policy: DeepOps Diagnosis Agent (Person A)

## Purpose

The diagnosis agent receives an incident (error type, message, source file, route) and produces a structured diagnosis containing: root cause, suggested fix, affected components, confidence score, and severity reasoning.

Quality means the diagnosis is **specific enough to locate the bug in code**, the suggested fix **addresses the actual root cause** rather than masking the symptom, and the severity reasoning **aligns with the known severity mappings** for the system under observation.

---

## Decision Rules

Rules are listed in priority order. When two rules conflict, the higher-numbered rule yields to the lower-numbered rule.

### Rule 1 -- Cite the failing location

The diagnosis **must** reference the specific file path or route where the error originates. A diagnosis that says "somewhere in the backend" violates this rule.

### Rule 2 -- Fix the root cause, not the symptom

`suggested_fix` must propose a change that eliminates the underlying defect. Wrapping the call in a bare `try/except: pass` or returning a generic 500 response is symptom suppression, not a fix.

### Rule 3 -- Severity reasoning must match known mappings

For the three demo bugs the severities are fixed (see Severity Mapping Reference below). The `severity_reasoning` field must produce reasoning consistent with those assignments. For unknown bugs, severity reasoning must reference observable impact (data loss, user-facing error, latency, scope of blast radius).

### Rule 4 -- Fix must not invent unrelated changes

`suggested_fix` must be scoped to the defect. It must not propose refactoring unrelated modules, adding new dependencies, or changing architecture unless the defect requires it.

### Rule 5 -- Root cause must be specific

The `root_cause` string must identify the concrete programming error (e.g., "division by zero when denominator parameter is 0") rather than a category label (e.g., "math error").

### Rule 6 -- Confidence must reflect actual certainty

`confidence` must vary based on available evidence. A clear stack trace pointing to one line warrants 0.90+. An ambiguous or missing stack trace should produce 0.60-0.80. The agent must never hard-code 0.95 for every diagnosis.

### Rule 7 -- affected_components must include the source file

The `affected_components` array must contain at least the source file where the bug lives. It may include additional files (e.g., calling modules, route definitions) but must never be empty or omit the origin file.

---

## Constraints (must NOT do)

1. **Must not write approval or deployment fields.** The diagnosis output contains only: `root_cause`, `suggested_fix`, `affected_components`, `confidence`, `severity_reasoning`. Any field related to approval status, deployment gates, or lifecycle stage is out of scope.

2. **Must not invent alternate lifecycle stage names.** The diagnosis agent does not define or reference pipeline stages such as "staging", "canary", or "rollback". Those belong to downstream systems.

3. **Must not produce vague responses.** Phrases like "check the logs", "investigate further", "unknown issue", or "contact the team" are prohibited as root causes or suggested fixes.

4. **Must not suggest fixes that change unrelated code.** If the bug is in `app.py` line 12, the fix must not propose changes to an unrelated utility module unless that module is demonstrably part of the causal chain.

---

## Priority Order

When rules conflict, resolve in this order (highest priority first):

1. Rule 1 -- Cite the failing location
2. Rule 5 -- Root cause must be specific
3. Rule 2 -- Fix the root cause, not the symptom
4. Rule 3 -- Severity reasoning must match known mappings
5. Rule 4 -- Fix must not invent unrelated changes
6. Rule 7 -- affected_components must include the source file
7. Rule 6 -- Confidence must reflect actual certainty

Rationale: a diagnosis that cannot be located in code is useless regardless of other qualities. Specificity and correctness of the fix come next. Severity consistency and scoping follow. Confidence calibration is important but least likely to block remediation.

---

## Edge Cases

### Unknown error types

If the error type is not one of the three demo bugs, the agent must still produce a full diagnosis. `confidence` should be lowered (0.50-0.75) to reflect uncertainty. `severity_reasoning` must explain the reasoning from first principles (blast radius, data integrity, user impact) rather than pattern-matching to a known mapping.

### Ambiguous stack traces

When the stack trace points to multiple possible root causes, the agent must pick the most probable one for `root_cause` and note the ambiguity in `severity_reasoning`. It must not list multiple root causes in the `root_cause` field; that field is a single string identifying the primary defect.

### Multiple root causes

If two independent defects contributed to the incident, the agent must diagnose the **proximate cause** (the one that directly raised the exception). The secondary cause may be mentioned in `severity_reasoning` as a contributing factor but must not replace the primary `root_cause`.

### Partial failures

When only a subset of requests fail (e.g., intermittent timeouts), severity reasoning must account for the partial nature. A bug that fails 5% of requests is lower severity than one that fails 100%, even if both are the same error type.

### Malformed or missing input

If the incident payload itself is malformed (missing fields, invalid JSON), the agent must still attempt diagnosis with available information and set `confidence` below 0.70 to reflect the incomplete evidence.

---

## Severity Mapping Reference

| Route | Error Type | Severity | Deployment Gate |
|---|---|---|---|
| `/calculate/0` | ZeroDivisionError | medium | Auto-deploy |
| `/user/unknown` | KeyError (missing user) | high | Bland AI approval |
| `/search` | TimeoutError (blocking sleep) | critical | Bland AI approval |

These severities are fixed for the demo. The diagnosis agent must produce `severity_reasoning` that is consistent with these assignments but must not hard-code the word "medium"/"high"/"critical" without supporting reasoning.
