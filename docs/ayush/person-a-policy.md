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

---

## Ingestion Policy

### Normalization requirements

All raw payloads entering the system -- whether from the demo app trigger endpoints, raw error reports, or Airbyte syncs -- must be normalized into the canonical incident source shape before storage:

```json
{
  "path": "string",
  "error_type": "string",
  "error_message": "string",
  "source_file": "string"
}
```

### Default handling for missing fields

Missing fields must be set to sensible defaults, never left as `null`:

| Field | Default |
|---|---|
| `error_type` | `"UnknownError"` |
| `error_message` | `"No error message provided"` |
| `source_file` | `"unknown"` |
| `path` | `"/"` |

### Fingerprinting

Fingerprints must be deterministic. The fingerprint is computed as a hash of `error_type + path`. Two incidents with the same error type on the same path must produce identical fingerprints, enabling deduplication.

### Timeline requirements

After normalization, the incident record must contain at least one timeline event recording the ingestion itself:

```json
{
  "stage": "ingestion",
  "status": "stored",
  "timestamp": "<ISO 8601>"
}
```

### Provider constraints

The `provider` field on normalized incidents must be one of:

- `"demo-app"` -- for errors originating from demo trigger endpoints or raw demo app errors
- `"airbyte"` -- for records forwarded by Airbyte syncs

No other provider values are permitted. Records with unrecognized providers must be rejected with a validation error.

---

## Bland AI Escalation Policy

### Eligibility

Only incidents with **high** or **critical** severity may trigger a Bland AI approval call. Medium and low severity incidents are auto-deployed or handled without human-in-the-loop approval. Attempting to escalate a medium or low severity incident to Bland AI is a policy violation.

### Call script requirements

Every Bland AI call script must include all of the following fields, presented clearly to the approver:

1. **Incident ID** -- the unique identifier (e.g., INC-018)
2. **Severity** -- the assessed severity level with brief justification
3. **Error summary** -- the error type and message in plain language
4. **Root cause** -- the diagnosis agent's root cause finding
5. **Suggested fix** -- the proposed remediation

Omitting any of these fields from the call script is a policy violation.

### Transcript-based decision extraction

Approval decisions are extracted from the Bland AI call transcript using keyword matching:

| Keywords detected | Decision |
|---|---|
| "approve", "yes", "go ahead", "deploy" | `approved` |
| "reject", "no", "deny", "do not deploy" | `rejected` |
| None of the above, or contradictory signals | `pending` |

### Ambiguity fail-safe

If the transcript is ambiguous (no clear approval or rejection keywords, contradictory statements, or the approver expressed uncertainty), the decision **must default to `pending`**. The system must never auto-approve based on transcript parsing when confidence in the extracted decision is low. A `pending` decision requires manual review.

### Webhook data mapping

Bland AI webhook payloads must map cleanly into the incident's `approval.*` fields:

| Webhook field | Incident field |
|---|---|
| `call_id` | `approval.call_id` |
| `decision` / transcript parse | `approval.status` |
| `answered_by` | `approval.answered_by` |
| `call_length` | `approval.call_length` |
| `transcript` | `approval.transcript` |

### Safety constraint

The system must **never auto-approve** based solely on transcript parsing if the parsing confidence is below a reliable threshold. When in doubt, default to `pending` and flag for manual review.

---

## Full-System Integration Rules

### Timeline event invariant

Every state change across the incident lifecycle must append a timeline event to the incident record. This includes ingestion, diagnosis, escalation, approval, and deployment stages. Skipping a timeline event for any state transition is a system invariant violation.

### Subsystem field ownership

Each subsystem owns its designated slice of the incident record and must not write to fields owned by other subsystems:

| Subsystem | Owned fields | Must NOT write |
|---|---|---|
| **Ingestion** | `source`, `fingerprint`, `provider`, `observability`, `status` (initial), `timeline` (ingestion event) | `diagnosis.*`, `approval.*`, `deployment.*` |
| **Diagnosis** | `diagnosis.root_cause`, `diagnosis.suggested_fix`, `diagnosis.affected_components`, `diagnosis.confidence`, `diagnosis.severity_reasoning`, `severity`, `timeline` (diagnosis event) | `approval.*`, `deployment.*`, `source.*` (read-only) |
| **Approval** | `approval.status`, `approval.call_id`, `approval.transcript`, `approval.answered_by`, `approval.call_length`, `timeline` (approval event) | `diagnosis.*`, `source.*`, `deployment.*` |
| **Deployment** | `deployment.*`, `status` (final), `timeline` (deployment event) | `diagnosis.*`, `source.*`, `approval.*` (read-only) |

### Cross-subsystem reads

All subsystems may **read** any field on the incident record. The ownership rules above govern **writes** only. For example, the approval subsystem reads `diagnosis.severity` to determine whether Bland AI escalation is warranted, but it must not modify the severity value.

### Record integrity

An incident record is considered valid only if each subsystem has written exclusively to its owned fields. Any field written by a non-owning subsystem indicates a bug in the pipeline and must be flagged as a system integrity violation.
