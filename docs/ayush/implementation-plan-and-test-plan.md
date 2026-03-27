# DeepOps Live Implementation Plan and Test Plan

## Purpose

This document is the single go-live checklist for DeepOps.

It is not another task brainstorm. It is the execution document to take the current repo from "demo-ready codebase" to "live, end-to-end system that behaves the way we originally planned":

1. autonomous self-healing for low-risk incidents,
2. approval and human steering for medium/high-risk incidents,
3. phone escalation for critical incidents with executable guidance.

Use this document when wiring the live environment, fixing the remaining backend gaps, and running the final rehearsal.

## Target Product Behavior

DeepOps should behave as one closed-loop incident system:

- ingest a live failure from the demo app or Airbyte,
- persist one canonical incident record,
- diagnose root cause,
- generate a constrained fix,
- decide whether the fix can auto-deploy or must wait for a human,
- escalate by phone when risk is too high,
- deploy through TrueFoundry,
- write the final outcome back into the same incident,
- capture traces for optimization.

The source of truth remains:

- canonical schema: `docs/incident.schema.json`
- lifecycle contract: `docs/implementation-alignment.md`
- full backend alignment: `docs/ayush/full-system-backend-alignment.md`
- demo flow alignment: `docs/ayush/demo-flow-alignment.md`

## Current State

As of the current `main` branch, the repo already has:

- FastAPI backend and main API routes
- landing page, dashboard, metrics page, and settings page
- incident list/detail API
- SSE stream
- run-once agent endpoint
- approval and escalation endpoints
- Bland and TrueFoundry webhook routes
- settings overview endpoint
- Auth0, Bland, TrueFoundry, Airbyte, and demo-app client wrappers
- local Aerospike infrastructure
- Overclaw workspace and registered agent config

The system is not fully live yet. The remaining work is integration hardening, one persistence fix, and full rehearsal.

## Critical Live Blockers

### 1. Aerospike write path is not currently safe for the canonical incident object

Observed failure during live ingest:

`exception.BinNameError: A bin name should not exceed 15 characters limit`

Cause:

- `agent/store_adapter.py` writes the full normalized incident object directly as Aerospike bins
- the canonical schema has field names longer than 15 characters
- Aerospike rejects those writes in live mode

Impact:

- `POST /api/ingest/demo-trigger` fails
- the live backend cannot create incidents in Aerospike
- the UI can render, but the live data loop is blocked

Required fix:

- change Aerospike persistence to a storage representation that respects bin limits

Recommended approach:

1. Store the full canonical incident JSON in a single bin such as `payload`
2. Keep only a few short index bins for fast filtering and scans:
   - `iid`
   - `st`
   - `sev`
   - `cat`
   - `crt_ms`
   - `upd_ms`
3. On read:
   - load `payload`
   - run `normalize_incident(payload)`
4. On patch:
   - read `payload`
   - apply merge
   - rewrite `payload`
   - refresh the short index bins
5. On list:
   - scan records
   - filter with short bins where possible
   - fall back to normalized `payload` if needed

Files to update:

- `agent/store_adapter.py`
- `server/integrations/aerospike_repo.py` if needed
- any tests that assume the current full-bin write behavior

Done when:

- `POST /api/ingest/demo-trigger` works against real Aerospike
- `GET /api/incidents` returns stored live incidents
- no Aerospike bin-name error remains in logs

### 2. Bland is only partially live until a public webhook URL is configured

Current status:

- `BLAND_API_KEY` present
- `BLAND_PHONE_NUMBER` present
- local settings UI currently falls back to `http://localhost:8000/api/webhooks/bland`

What is still required:

- set a real public `BLAND_WEBHOOK_URL`
- verify Bland can reach it from outside localhost

Done when:

- a real Bland callback hits `POST /api/webhooks/bland`
- the incident approval/escalation state updates from the actual callback payload

### 3. Overclaw setup is only partially complete until the CLI sees model credentials directly

Current status:

- `.overclaw/` exists
- agent is registered
- repo `.env` contains model/tracing keys locally

What is still required:

- make the keys visible to the Overclaw process itself
- run:
  - `overclaw setup deepops-person-a --fast --policy docs/ayush/person-a-policy.md`
  - `overclaw optimize deepops-person-a`

Done when:

- setup completes without auth failure
- optimize completes successfully

### 4. Kiro CLI is not yet available in the runtime

Current settings state shows:

- `command=kiro`
- `available=False`

Impact:

- fix generation can only use fallback behavior
- the real Kiro execution path is not proven

Done when:

- `kiro --help` works in the same environment as the backend
- settings page shows Kiro as active

### 5. Macroscope is not configured yet

Current settings state shows:

- `configured=False`

Impact:

- diagnosis stays in fallback mode
- the demo cannot honestly claim a fully live Macroscope-backed diagnosis path

Done when:

- `MACROSCOPE_API_KEY` is configured
- one live incident writes diagnosis context sourced from the real Macroscope path

## Implementation Plan

## Phase 1: Stabilize Persistence and Bring-Up

Goal: make the backend capable of storing and reading real incidents end to end.

Steps:

1. Fix Aerospike persistence in `agent/store_adapter.py`
2. Verify `GET /api/health` reports a working Aerospike-backed store
3. Verify:
   - `POST /api/ingest/demo-trigger`
   - `POST /api/ingest/demo-app`
   - `GET /api/incidents`
   - `GET /api/incidents/{incident_id}`
4. Confirm the frontend dashboard and metrics page hydrate from the real backend without storage errors

Acceptance criteria:

- at least one incident can be written and read in live Aerospike mode
- incidents survive backend restart
- incident timeline remains intact after patch operations

## Phase 2: Restore the Three Core Demo Flows

Goal: make the original product story real.

### Flow A: Autonomous Self-Heal

Seed incident:

- demo trigger `calculate_zero`

Expected lifecycle:

- `stored`
- `diagnosing`
- `fixing`
- `gating`
- `deploying`
- `resolved`

Implementation focus:

- verify `POST /api/agent/run-once`
- verify deployment path uses `server/services/deployment_service.py`
- verify incident timeline records each state change

Acceptance criteria:

- low-risk incident resolves without human intervention
- deployment result is written back to the same incident

### Flow B: Approval and Human Steering

Seed incident:

- demo trigger `user_missing`

Expected lifecycle:

- `stored`
- `diagnosing`
- `fixing`
- `gating`
- `awaiting_approval`
- then either `deploying`, `blocked`, or revised plan state

Implementation focus:

- verify `POST /api/approval/{incident_id}/decision`
- verify free-form decisions can map to:
  - approve
  - reject
  - suggest/replan
  - ask for more context
- verify execution-plan revision is persisted

Acceptance criteria:

- a human can approve, reject, or suggest changes
- the system persists the revised execution path
- approved flow continues cleanly to deploy

### Flow C: Phone Escalation

Seed incident:

- demo trigger `search_timeout`

Expected lifecycle:

- `stored`
- `diagnosing`
- `fixing`
- `gating`
- `awaiting_approval`
- phone escalation via Bland
- callback-driven decision handling
- deploy or block based on the result

Implementation focus:

- ensure escalation route works
- ensure raw Bland transcript payloads are normalized
- ensure transcript output updates the canonical incident record

Acceptance criteria:

- one real outbound Bland call is triggered
- one real Bland callback is processed
- the system converts that callback into a real decision and next action

## Phase 3: Turn On Live Integrations Completely

Goal: eliminate remaining fallbacks where the hackathon story claims live integration.

Steps:

1. Set a real `BLAND_WEBHOOK_URL`
2. Make Kiro CLI available
3. Configure `MACROSCOPE_API_KEY`
4. Verify Airbyte client against the real instance
5. Verify demo app client against the real demo app base URL
6. Confirm Auth0 redirect/callback config matches the actual frontend/backend runtime
7. Confirm Overmind trace capture works for one backend-triggered incident
8. Finish Overclaw setup and optimize

Acceptance criteria:

- settings page shows all intended integrations as active or intentionally fallback-only
- no critical demo flow depends on a hidden stub

## Phase 4: Rehearsal and Submission Readiness

Goal: prove the system can be run on demand without code changes.

Steps:

1. Start Aerospike
2. Start backend
3. Start frontend
4. Run the three demo flows in order:
   - autonomous
   - approval
   - phone escalation
5. Record evidence:
   - dashboard screenshots
   - one Overmind trace
   - one TrueFoundry deployment result
   - one Bland escalation result
6. Freeze the repo for the final recording

Acceptance criteria:

- all three flows work without editing code between runs
- operators can narrate the whole story from the UI plus one or two sponsor tabs

## Test Plan

## Test Layer 1: Preflight Checks

Run before any live test:

```powershell
docker compose -f infra/aerospike/docker-compose.yml up -d
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:3004
```

Expected:

- Aerospike container healthy
- backend returns `ok: true`
- frontend loads

Additional checks:

```powershell
python -m pytest -q tests server/tests
overclaw agent list
kiro --help
```

Expected:

- test suite green
- Overclaw agent visible
- Kiro available if live fix path is enabled

## Test Layer 2: API Bring-Up Tests

### Test 2.1 Ingest Demo Trigger

```powershell
curl -X POST http://127.0.0.1:8000/api/ingest/demo-trigger ^
  -H "Content-Type: application/json" ^
  -d "{\"bug_key\":\"calculate_zero\"}"
```

Expected:

- `200 OK`
- response contains `incident`
- incident `status` is `stored`

Failure to watch for:

- Aerospike bin-name error

### Test 2.2 List Incidents

```powershell
curl http://127.0.0.1:8000/api/incidents
```

Expected:

- array includes the stored incident

### Test 2.3 Stream Endpoint

Open:

`GET /api/incidents/stream`

Expected:

- stream stays open
- emits heartbeat or incident updates

## Test Layer 3: Flow-by-Flow Functional Tests

### Test 3.1 Autonomous Flow

Steps:

1. Seed `calculate_zero`
2. Call:

```powershell
curl -X POST "http://127.0.0.1:8000/api/agent/run-once"
```

Expected:

- incident moves through diagnosis and fix
- approval is not required
- deployment starts
- final status becomes `resolved`

Verify:

- incident detail
- timeline events
- deployment block

### Test 3.2 Approval Flow

Steps:

1. Seed `user_missing`
2. Run the agent once
3. Confirm the incident lands in an approval state
4. Submit one decision:

```powershell
curl -X POST "http://127.0.0.1:8000/api/approval/{incident_id}/decision" ^
  -H "Content-Type: application/json" ^
  -d "{\"decision\":\"suggest\",\"notes\":\"Patch only the endpoint and keep auth untouched.\"}"
```

Expected:

- execution plan updates
- timeline records the human input
- a follow-up approve can continue the flow

### Test 3.3 Phone Escalation Flow

Steps:

1. Seed `search_timeout`
2. Run the agent once
3. Confirm escalation is triggered
4. Confirm Bland initiates a call
5. Send or receive the real webhook callback

Expected:

- incident records the call result
- decision is parsed correctly
- resulting state is one of:
  - approved deploy
  - blocked
  - revised plan
  - pending follow-up

## Test Layer 4: Integration-Specific Tests

### Auth0

Verify:

- configured domain/client values are correct
- redirect URI matches the live frontend/backend route
- approval URL can be generated without runtime error

### Bland

Verify:

- outbound call request succeeds
- webhook reaches the backend
- transcript parsing handles real payload shape

### TrueFoundry

Verify:

- deployment request returns a result
- callback or polling updates `deployment.*`
- final incident state is synchronized

### Overmind / Overclaw

Verify:

- one backend-triggered run writes a trace
- trace identifiers are present in incident observability data
- `overclaw setup` and `optimize` complete successfully

### Aerospike

Verify:

- create
- get
- patch
- append timeline event
- survive restart

## Test Layer 5: UI Verification

These are the screens that must be checked live:

- `/`
- `/dashboard`
- `/metrics`
- `/settings`

Verify on the dashboard:

- incident appears after ingest
- status changes are visible
- approval state is visible
- deployment state is visible

Verify on metrics:

- values hydrate from backend data
- service health reflects actual integration readiness

Verify on settings:

- webhook URL is correct
- sponsor status matches reality

## Evidence to Capture

For final confidence and demo backup, collect:

- screenshot of landing page
- screenshot of dashboard during incident activity
- screenshot of metrics page
- screenshot of settings page
- screenshot of one TrueFoundry deployment result
- screenshot of one Overmind trace
- screenshot or transcript proof of one Bland escalation

## Definition of Done

DeepOps is live-ready when all of the following are true:

1. Real Aerospike persistence works with the canonical incident object
2. All three demo flows execute successfully
3. Approval and phone guidance both update the same canonical incident
4. Deployment results are written back through one deployment path
5. Overmind and Overclaw are functional for at least one traced run
6. Frontend surfaces read the backend as the source of truth
7. The final rehearsal can be run without code edits

## Recommended Execution Order

Use this exact order:

1. Fix Aerospike persistence
2. Re-test ingest and list APIs
3. Re-test `run-once`
4. Validate autonomous flow
5. Validate approval flow
6. Configure public Bland webhook URL
7. Validate phone escalation flow
8. Turn on Macroscope and Kiro live paths
9. Finish Overclaw setup and optimize
10. Run final full rehearsal

If a step fails, do not skip ahead. The system is tightly coupled around one incident record, so upstream instability will make downstream sponsor tests misleading.
