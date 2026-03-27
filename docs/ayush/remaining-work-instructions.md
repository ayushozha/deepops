# Remaining Work Instructions

## Purpose

This document is the consolidated source of truth for the unfinished work in the repo.

It is written for the current state of the codebase, not the original plan. The goal is to let Codex, Claude, Kiro, and the human team finish the remaining work without re-reading every earlier task file and without guessing which items are already done.

## Source Documents Reviewed

These documents were used to build this remaining-work pack:

- `README.md`
- `docs/deepops-guide.md`
- `docs/implementation-alignment.md`
- `docs/incident.schema.json`
- `docs/ayush/full-system-backend-alignment.md`
- `docs/ayush/demo-flow-alignment.md`
- `docs/ayush/codex full-system tasks.md`
- `docs/ayush/claude full-system tasks.md`
- `docs/ayush/kiro full-system tasks.md`
- `docs/ayush/codex demo tasks.md`
- `docs/ayush/claude demo tasks.md`
- `docs/ayush/kiro demo tasks.md`
- `docs/hackathon-context/event.md`
- `docs/hackathon-context/bland-docs.md`
- `docs/hackathon-context/truefoundry-ai-gateway-quickstart.md`

## Current Reality

The backend and demo flow are mostly implemented.

The repo already has:

- a FastAPI backend
- live incident routes
- SSE streaming
- run-once agent execution
- approval and escalation routes
- webhook routes
- Auth0, Bland, and TrueFoundry wrappers
- execution-plan persistence
- explanation, decision parsing, and suggestion extraction helpers
- execution-package and hotfix-package helpers
- a green test suite

The current gap is not "build the system from scratch." The gap is:

- finish the true live integrations
- route a few helpers into the real backend path
- remove remaining schema and tracing mismatches
- run real rehearsals with sponsor credentials

## What Is Already Done

Do not spend time rebuilding these:

- `server/app.py`, `server/main.py`, and the main backend shell
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
- `server/services/approval_policy.py`
- `server/integrations/auth0_client.py`
- `server/integrations/bland_client.py`
- `server/integrations/truefoundry_client.py`
- `server/services/explanation_service.py`
- `server/services/decision_parser.py`
- `server/services/suggestion_extractor.py`
- `agent/execution_package.py`

Tests currently pass:

- `python -m pytest -q tests server/tests`

## Remaining Work By Priority

### P0: Must Finish Before Demo Rehearsal

These are blocking items for a believable live demo.

#### 1. Shared tracing and Overclaw live-path wiring

Why this is still open:

- `.overclaw/` does not exist yet.
- `agent/diagnoser.py` still defines a local `call_llm`.
- `agent/kiro_client.py` still defines a local `call_tool`.
- The live backend path is not yet proven through the shared tracing wrappers.

Required changes:

- replace local `call_llm` usage in `agent/diagnoser.py` with the shared tracing wrapper from `agent/tracing.py`
- replace local `call_tool` usage in `agent/kiro_client.py` with the shared tracing wrapper from `agent/tracing.py`
- confirm the backend-triggered flow populates `observability.overmind_trace_id`
- run:
  - `overclaw init`
  - `overclaw agent register deepops-person-a agents.person_a_agent:run`
  - `overclaw setup deepops-person-a --policy docs/ayush/person-a-policy.md`
  - `overclaw optimize deepops-person-a`

Done when:

- `.overclaw/` exists
- no local tracing shim remains in the diagnoser or Kiro client
- one backend-triggered run can be inspected in Overmind

Owner:

- Codex for the backend/live path
- Claude for the diagnosis-side wrapper migration
- Kiro for the tool-call wrapper migration

#### 2. Real demo-app and Airbyte ingestion clients

Why this is still open:

- `server/services/ingestion_service.py` exists
- `server/integrations/demo_app_client.py` and `server/integrations/airbyte_client.py` exist
- `server/app.py` currently creates `IngestionService()` without real clients
- `/api/ingest/airbyte-sync` is therefore not live

Required changes:

- instantiate the real demo-app client in `server/app.py`
- instantiate the real Airbyte client in `server/app.py`
- pass both into `IngestionService`
- add config/env loading for the endpoints and credentials those clients need
- verify:
  - demo trigger path
  - demo-app error ingestion path
  - Airbyte sync path

Done when:

- a real external input creates a canonical `stored` incident without manual inserts

Owner:

- Claude for client correctness and normalization
- Codex for app wiring

#### 3. Raw Bland transcript webhook path

Why this is still open:

- transcript parsing helpers exist
- the webhook route still expects a clean boolean approval body
- the phone call flow should be able to consume actual transcript payloads

Required changes:

- route the raw Bland webhook through `server/normalizers/bland_normalizer.py`
- use `server/services/decision_parser.py` and `server/services/suggestion_extractor.py` for natural language interpretation where needed
- support these outcomes:
  - approve
  - reject
  - suggest changes
  - defer / wait
  - no answer
  - follow-up required
- map those outcomes to:
  - `approval.*`
  - execution-plan revision when needed
  - `status`
  - `timeline`

Done when:

- the phone escalation flow can be driven by a real webhook payload instead of a handcrafted boolean

Owner:

- Claude for transcript interpretation
- Codex for webhook integration

#### 4. Schema-clean Kiro fix persistence

Why this is still open:

- `agent/fixer.py` still emits `_metadata`
- the canonical `fix` object in `docs/incident.schema.json` does not allow extra keys

Required changes:

- keep the stored `fix` payload limited to canonical fields only
- move extra fields such as Kiro mode, summary, or regression warning to:
  - timeline metadata
  - observability
  - response-only transient fields
- verify that the stored incident validates against `docs/incident.schema.json`

Done when:

- no stored `fix` object contains `_metadata` or any non-schema key

Owner:

- Kiro

#### 5. Unify deployment through the deployment service

Why this is still open:

- `server/services/deployment_service.py` exists
- `server/services/demo_flow_service.py` currently performs direct TrueFoundry submission logic
- there should be one authoritative deploy path

Required changes:

- move deployment start and result handling in the live backend path to `server/services/deployment_service.py`
- keep `demo_flow_service.py` as orchestration only
- make sure both approval-triggered and auto-deploy flows use the same deploy service
- ensure final write semantics stay canonical:
  - `deployment.*`
  - top-level `status`
  - `resolution_time_ms`
  - timeline event

Done when:

- there is one deployment implementation path for all backend flows

Owner:

- Kiro for deployment service
- Codex for orchestration integration

### P1: Should Finish Before Final Demo Recording

These are not as blocking as P0, but they matter for polish and correctness.

#### 6. Integrate explanation payloads into the live API/UI path

Why this is still open:

- `server/services/explanation_service.py` exists
- approval and escalation responses do not yet surface those explanation payloads

Required changes:

- add explanation payloads to the backend responses the frontend reads for approval and phone flows
- support:
  - short explanation for dashboard
  - approval explanation payload
  - phone-call explanation payload

Done when:

- the frontend can display a clean explanation without reconstructing it itself

Owner:

- Claude
- Codex for response wiring if needed

#### 7. Integrate suggestion extraction into the real approval flow

Why this is still open:

- the approval route currently accepts `constraints` and `suggested_steps`
- the automatic extraction layer is not yet what feeds those fields

Required changes:

- when a human provides free-form suggestion text, run it through `server/services/suggestion_extractor.py`
- persist the structured output into the execution-plan revision path
- make sure extracted constraints affect the downstream execution package

Done when:

- free-form human guidance becomes structured execution constraints automatically

Owner:

- Claude
- Codex for orchestration hookup

#### 8. Integrate execution-package and hotfix-package outputs into the live flow

Why this is still open:

- `agent/execution_package.py` and `tests/test_execution_package.py` exist
- the live backend flow does not yet expose these artifacts as part of the response or deployment handoff

Required changes:

- when a plan is approved, generate an execution package
- when the flow is hotfix-constrained, generate a hotfix package
- surface the artifact in:
  - backend response payload
  - timeline metadata
  - optional frontend detail panel

Done when:

- every approved path has a narratable execution package

Owner:

- Kiro
- Codex for orchestration hookup

#### 9. Unknown-incident fallback quality

Why this is still open:

- the demo bug paths are handled
- unknown live inputs still need better normalization and explanation quality

Required changes:

- improve fallback normalization in `server/normalizers/incident_normalizer.py`
- improve fallback diagnosis behavior
- make fallback mode visible in metadata instead of silently degrading

Done when:

- unknown inputs still become useful incidents and the system does not collapse into vague output

Owner:

- Claude

### P2: Operational Completion Tasks

These are not code-only tasks, but they must be done for a clean demo.

#### 10. Live credential and environment wiring

Required values:

- `AEROSPIKE_HOST`
- `AEROSPIKE_PORT`
- `AEROSPIKE_NAMESPACE`
- `AEROSPIKE_SET`
- `BLAND_API_KEY`
- `BLAND_PHONE_NUMBER`
- `BLAND_WEBHOOK_URL`
- `TRUEFOUNDRY_API_KEY`
- `TRUEFOUNDRY_BASE_URL`
- `TRUEFOUNDRY_SERVICE_NAME`
- `TRUEFOUNDRY_ENVIRONMENT`
- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_AUDIENCE`
- `AUTH0_REDIRECT_URI`
- `AUTH0_ORGANIZATION_ID`
- `AUTH0_APPROVAL_CONNECTION`
- `OVERMIND_API_KEY`
- `MACROSCOPE_API_KEY`
- any demo-app and Airbyte endpoint settings

Done when:

- the backend boots against real sponsor services without local fallbacks

#### 11. Frontend hookup to the real backend

Required routes the frontend should use:

- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `GET /api/incidents/stream`
- `POST /api/agent/run-once`
- `POST /api/approval/{incident_id}/decision`
- `POST /api/escalation/{incident_id}/trigger`

Done when:

- the UI is no longer reading mock JSON as its primary source

#### 12. End-to-end rehearsal for all three flows

The three flows to rehearse:

- low or medium incident auto-resolves
- approval/suggestion flow revises plan and then deploys or blocks
- critical incident triggers a real phone escalation path

Done when:

- each flow works on demand
- each flow produces sensible timeline entries
- each flow can be narrated from one incident record

## Owner-Specific Remaining Instructions

### Codex Remaining Lane

Codex should focus only on orchestration and backend wiring.

Remaining Codex tasks:

1. Finish Overclaw and shared tracing integration on the live path.
2. Wire real demo-app and Airbyte clients into `server/app.py`.
3. Route raw Bland transcript webhooks into the shared workflow path.
4. Consolidate all deploy starts through `server/services/deployment_service.py`.
5. Hook explanation and execution-package payloads into the live backend responses where useful.

Codex should not spend more time on:

- rewriting transcript parsing logic Claude already owns
- rewriting fix artifact packaging Kiro already owns
- frontend visual work

### Claude Remaining Lane

Claude should focus on the human-language and ingestion side.

Remaining Claude tasks:

1. Make the demo-app and Airbyte clients fully live and config-driven.
2. Hook raw Bland transcripts into the live webhook path.
3. Feed `explanation_service`, `decision_parser`, and `suggestion_extractor` into the approval and phone paths.
4. Improve unknown-input fallback normalization and diagnosis quality.
5. Migrate diagnosis calls to the shared tracing wrapper.

Claude should not spend more time on:

- API router registration
- deploy orchestration
- Aerospike patch semantics

### Kiro Remaining Lane

Kiro should focus on fix, deployment, and execution artifacts.

Remaining Kiro tasks:

1. Remove non-schema metadata from the stored `fix` payload.
2. Migrate Kiro tool calls to the shared tracing wrapper.
3. Route the live deploy path through `server/services/deployment_service.py`.
4. Hook `agent/execution_package.py` into the real backend flow.
5. Verify real Kiro output requires a usable diff and file list.

Kiro should not spend more time on:

- approval semantics
- transcript interpretation
- route registration

## Ordered Finish Sequence

Follow this order to avoid stepping on each other:

1. Codex: wire real clients and raw webhook integration points.
2. Claude: connect transcript and suggestion parsing to those integration points.
3. Kiro: clean fix payload and unify the deploy path.
4. Codex: finish execution-package response wiring.
5. Shared: enable live credentials and run full rehearsal.
6. Shared: run Overclaw setup and one traced backend-triggered incident.

## Acceptance Criteria For Final Demo Readiness

The system is demo-ready when all of the following are true:

- low-risk incident:
  - appears in the dashboard
  - moves through `stored -> diagnosing -> fixing -> gating -> deploying -> resolved`
  - does not require a human

- approval incident:
  - pauses correctly
  - accepts approve / reject / suggest
  - stores a structured execution plan revision
  - deploys or blocks cleanly

- phone escalation incident:
  - triggers a real outbound call request
  - consumes a real callback payload
  - supports approve, reject, suggest, and no-answer branches

- canonical data contract:
  - incident validates against `docs/incident.schema.json`
  - no extra keys are written into `fix`
  - approval and deployment remain nested contracts

- observability:
  - one backend-triggered run shows up in Overmind
  - `.overclaw` exists and the agent is registered

## Demo-Day Scheduled Tasks

These are not engineering backlog items. They are scheduled operational tasks pulled from the build guide and should be treated as required.

### Before Final Demo Rehearsal

- populate all sponsor credentials
- verify the demo app is running
- verify Aerospike is reachable
- verify Bland webhook URL is reachable
- verify TrueFoundry workspace and deploy target are reachable
- verify Overmind key works
- verify Macroscope key works

### Before Recording The Backup Video

- rehearse all three flows without code changes
- make sure one phone call path succeeds cleanly
- keep browser tabs ready:
  - dashboard
  - Overmind
  - TrueFoundry
  - optional Auth0 and Airbyte views

### Before Devpost Submission

- record the backup 3-minute video
- make sure the architecture diagram and sponsor list match the actual repo
- make sure the story used in the demo matches the real implemented flow
- make sure all team members are listed

## Post-Demo / Not Blocking

These are good later, but do not block the hackathon demo:

- stronger production auth and RBAC UI
- continuous agent background loop instead of only run-once
- richer deployment polling and retry strategy
- stronger unknown-incident heuristics
- production hardening for secrets, retries, and telemetry retention
