# Kiro Tasks: Fix Execution, Deployment Integration, and Post-Fix Verification

## Mission

Own the backend work that turns a structured diagnosis into a deployable fix path and keeps deployment state real.

Kiro should make the "agent wrote the fix and we shipped it" part of the demo credible, but must do so through the real backend and canonical incident schema.

This file is for the full-system backend scope, not only Person A.

## Primary Goal

By the end of this workstream, Kiro should make it possible to:

1. generate a real or fallback fix artifact from diagnosis,
2. package the fix output into a deployment-ready unit,
3. invoke TrueFoundry through a narrow backend wrapper,
4. capture deployment progress and final result,
5. feed deployment status back into the same incident record,
6. keep the fix and deployment path stable enough for Overclaw analysis.

## Files Kiro Should Own

- `agent/fixer.py`
- `agent/kiro_client.py`
- `agent/fix_specs.py`
- `server/services/deployment_service.py`
- `server/integrations/truefoundry_client.py`
- `server/services/fix_artifact_service.py`
- `server/tests/test_deployment_service.py`
- `server/tests/test_truefoundry_client.py`
- `tests/test_fixer.py`
- `tests/test_kiro_client.py`
- `tests/test_fix_specs.py`

Kiro should avoid editing:

- FastAPI route definitions
- Aerospike repository code
- Auth0 gating logic
- ingestion normalization logic
- Claude-owned diagnosis modules

## Shared Contracts Kiro Must Respect

- `fix` output must match the canonical schema exactly
- deployment updates must write only `deployment.*`, top-level `status`, and `timeline`
- Kiro must not invent new top-level incident fields for summaries or mode flags
- all tool invocations should be compatible with the shared Overclaw tracing wrappers

## P0 Tasks

### 1. Finish the `fix` payload so it is schema-clean

**Deliverable**

- A `fix` object that is both useful for the demo and valid against the canonical schema.

**What to build**

- keep:
  - `status`
  - `spec_markdown`
  - `diff_preview`
  - `files_changed`
  - `test_plan`
  - timestamps
- move any extra display or debug metadata out of the stored `fix` object and into:
  - timeline metadata
  - observability metadata
  - transient response-only fields if Codex explicitly asks for them

**Done when**

- the fix payload can be validated against `docs/incident.schema.json` without special casing

### 2. Harden real Kiro execution

**Deliverable**

- A Kiro execution path that is safe to call from the live backend.

**What to build**

- validate that a successful Kiro run actually produced:
  - a diff preview
  - meaningful file paths
- clear error results for:
  - CLI missing
  - timeout
  - malformed output
  - zero exit code with empty artifact output
- traceable tool boundaries compatible with the shared `call_tool` wrapper

**Important**

- A zero exit code is not enough. The output must be usable.

**Done when**

- the backend can distinguish "Kiro executed" from "Kiro produced a fix we can trust"

### 3. Build the fix artifact packaging service

**Deliverable**

- One service that turns the diagnosis and Kiro output into something deployment code can consume.

**What to build**

- package:
  - spec markdown
  - diff preview
  - files changed
  - test plan
  - source incident metadata
- create a stable representation the deployment service can consume without re-parsing the raw Kiro output

**Done when**

- the deploy path no longer depends directly on Kiro stdout format

### 4. Implement the TrueFoundry client wrapper

**Deliverable**

- A narrow deployment wrapper around the real platform.

**What to build**

- methods for:
  - submit deployment
  - fetch deployment status
  - fetch deploy URL or failure reason
- config-driven auth and environment selection
- response normalization into canonical `deployment` fields

**Important**

- Keep the wrapper small and backend-oriented.
- The rest of the code should not know TrueFoundry response shape details.

**Done when**

- Codex can call one deployment client method and get a patch-ready deployment result object

### 5. Build the deployment service

**Deliverable**

- One backend service that moves incidents through `deploying` and `resolved` or `failed`.

**What to build**

- deployment start logic from an approved or auto-approved incident
- deployment status polling or webhook reconciliation
- patch helpers for:
  - `deployment.status`
  - `deployment.started_at_ms`
  - `deployment.completed_at_ms`
  - `deployment.deploy_url`
  - `deployment.failure_reason`
  - top-level `status`
  - `resolution_time_ms`
  - timeline events

**Done when**

- an incident can move from approval success to `deploying` and then to `resolved` through one real backend path

## P1 Tasks

### 6. Add deployment verification and regression checks

**Deliverable**

- A believable post-fix verification step instead of a blind deploy flag.

**What to build**

- post-deploy verification hooks such as:
  - health endpoint check
  - targeted route check for the fixed bug
  - deployment failure interpretation
- compact verification summaries that can be surfaced in timeline metadata

**Done when**

- the system can justify why an incident became `resolved`

### 7. Add deployment and fix tests

**Deliverable**

- Confidence that the fix and deploy path works under both real and fallback conditions.

**What to build**

- tests for:
  - schema-valid fix payloads
  - zero-exit-but-empty Kiro output rejection
  - fix artifact packaging
  - TrueFoundry client response normalization
  - deployment success path
  - deployment failure path

**Done when**

- the fix-to-deploy path can be refactored without silently breaking the hackathon flow

## Integration Checkpoints

### Checkpoint 1

- fix payload is schema-valid

### Checkpoint 2

- real Kiro output is accepted only when it contains usable artifacts

### Checkpoint 3

- TrueFoundry deployment wrapper returns normalized status

### Checkpoint 4

- deployment service updates the live incident record correctly

## What Kiro Should Not Spend Time On

- API route wiring
- SSE mechanics
- Airbyte ingestion
- Auth0 decision logic
- frontend rendering

## Success Criteria

If Kiro finishes well, the system can show a believable path from structured diagnosis to generated fix to real deployment state, all inside the same live backend and incident record.
