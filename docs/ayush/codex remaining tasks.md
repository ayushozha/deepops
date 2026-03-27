# Codex Remaining Tasks

## Purpose

This is the Codex-only handoff for the unfinished work.

Use this together with:

- `docs/ayush/remaining-work-instructions.md`
- `docs/implementation-alignment.md`
- `docs/incident.schema.json`

Codex owns orchestration, backend wiring, lifecycle control, and the live API contract.

## Do Not Rebuild

These are already implemented and should be extended, not replaced:

- `server/app.py`
- `server/main.py`
- `server/api/incidents.py`
- `server/api/stream.py`
- `server/api/agent.py`
- `server/api/approval.py`
- `server/api/escalation.py`
- `server/api/webhooks.py`
- `server/api/ingest.py`
- `server/services/demo_flow_service.py`
- `server/services/flow_router.py`
- `server/services/plan_state_service.py`
- `server/services/escalation_service.py`

## Codex Scope

Codex owns:

- backend orchestration
- app wiring
- route integration
- execution-path branching
- deployment-path consolidation
- response shape for the frontend
- Overclaw and live backend tracing setup

Codex does not own:

- transcript interpretation internals Claude already wrote
- fix artifact semantics Kiro already wrote
- frontend visual design

## Remaining Tasks

### 1. Finish shared tracing and Overclaw on the live path

Current gap:

- `.overclaw/` does not exist
- the live backend run is not yet proven through shared tracing wrappers

What Codex must do:

- verify the backend-triggered agent path uses the shared tracing flow end-to-end
- coordinate wrapper migration with Claude and Kiro so the live path no longer depends on local shims
- ensure `observability.overmind_trace_id` is written for a real backend-triggered run
- run:
  - `overclaw init`
  - `overclaw agent register deepops-person-a agents.person_a_agent:run`
  - `overclaw setup deepops-person-a --policy docs/ayush/person-a-policy.md`
  - `overclaw optimize deepops-person-a`

Done when:

- `.overclaw/` exists
- the backend-triggered path is traceable
- one real backend run appears in Overmind

### 2. Wire real demo-app and Airbyte clients into app startup

Current gap:

- `server/services/ingestion_service.py` exists
- `server/integrations/demo_app_client.py` and `server/integrations/airbyte_client.py` exist
- `server/app.py` still creates `IngestionService()` without those clients

What Codex must do:

- instantiate the real demo-app client in `server/app.py`
- instantiate the real Airbyte client in `server/app.py`
- pass both into `IngestionService`
- add any missing settings/env reads needed by those clients
- verify:
  - `/api/ingest/demo-trigger`
  - `/api/ingest/demo-app`
  - `/api/ingest/airbyte-sync`

Done when:

- the backend can create incidents from live inputs without manual inserts

Dependency:

- Claude owns client correctness
- Codex owns the app wiring

### 3. Integrate raw Bland transcript webhooks into the workflow path

Current gap:

- transcript and suggestion parsing helpers exist
- `server/api/webhooks.py` still expects a simplified approval payload

What Codex must do:

- route raw Bland payloads through the live workflow path
- consume normalized decision output from Claude-owned helpers
- make sure the phone-call branch can end in:
  - deploy
  - block
  - replan
  - pending follow-up
- keep all mutations canonical:
  - `approval.*`
  - top-level `status`
  - `timeline`

Done when:

- the webhook route can process a real call result payload and move the incident correctly

Dependency:

- Claude must provide the interpretation layer

### 4. Unify all deploy starts through `server/services/deployment_service.py`

Current gap:

- `server/services/deployment_service.py` exists
- `server/services/demo_flow_service.py` still performs direct deploy submission logic

What Codex must do:

- remove direct deploy logic from the orchestration layer
- call the deployment service as the single deployment path
- keep `demo_flow_service.py` focused on routing and lifecycle only
- ensure both:
  - auto-deploy flow
  - manual approval flow
  use the same deployment path

Done when:

- deployment behavior is implemented in one place only

Dependency:

- Kiro owns deployment service behavior
- Codex owns orchestration integration

### 5. Surface explanation and execution artifacts in live backend responses

Current gap:

- explanation helpers exist
- execution-package helpers exist
- the live backend responses do not yet expose them consistently

What Codex must do:

- add explanation payloads to approval and escalation responses
- add execution package or hotfix package payloads where an approved plan is returned
- keep response shape frontend-friendly without inventing a second state model
- prefer response-only fields or timeline metadata for UI helpers rather than polluting the stored canonical record

Done when:

- the frontend can narrate the approval and deployment story directly from backend responses

Dependency:

- Claude owns explanation content
- Kiro owns execution package generation

## Ordered Execution Sequence

Follow this order:

1. Wire real clients in `server/app.py`
2. Integrate raw Bland webhook handling
3. Consolidate deployment through the deployment service
4. Add explanation and execution-package response payloads
5. Run Overclaw and trace one real backend-triggered incident

## Test And Verification Requirements

Before calling the Codex lane done, run:

- route/API regression tests
- one end-to-end backend flow for low-risk auto-deploy
- one end-to-end backend flow for approval/replan
- one end-to-end backend flow for phone escalation
- one live traced run with Overmind

## Final Done Criteria

Codex is done when:

- the backend wiring no longer has placeholder integration gaps
- deployment is unified through one service
- webhook and approval flows use the same orchestration path
- explanation and execution artifacts are available to the frontend
- Overclaw and Overmind are active on the live backend path
