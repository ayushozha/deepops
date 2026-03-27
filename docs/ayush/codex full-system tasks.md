# Codex Tasks: Full Backend, State, API, and Realtime

## Mission

Own the platform backend. Codex should make DeepOps feel like one coherent system instead of a set of scripts.

Codex owns the API server, shared state boundaries, realtime feed, Aerospike patch semantics, and the backend coordination that lets the frontend, Person A agent, and sponsor integrations all operate on the same incident records.

This file is for the full-system backend scope, not only Person A.

## Primary Goal

By the end of this workstream, Codex should make it possible to:

1. run one FastAPI backend,
2. read and write incidents from Aerospike,
3. expose live incident APIs to the frontend,
4. push realtime updates as incidents change,
5. invoke the Person A agent against real stored incidents,
6. route approval and deployment state changes through one backend,
7. keep every transition aligned with the canonical schema.

## Files Codex Should Own

- `server/app.py`
- `server/main.py`
- `server/api/incidents.py`
- `server/api/stream.py`
- `server/api/agent.py`
- `server/api/approval.py`
- `server/api/webhooks.py`
- `server/services/incident_service.py`
- `server/services/realtime_hub.py`
- `server/services/gating_service.py`
- `server/integrations/aerospike_repo.py`
- `server/tests/test_api_incidents.py`
- `server/tests/test_stream.py`
- `server/tests/test_gating_service.py`

Continue owning the existing shared-runtime files:

- `config.py`
- `agent/contracts.py`
- `agent/orchestrator.py`
- `agent/store_adapter.py`
- `agents/person_a_agent.py`

Claude and Kiro should not edit these unless ownership changes explicitly.

## Shared Contracts Codex Must Enforce

- incident schema: `docs/incident.schema.json`
- lifecycle: `docs/implementation-alignment.md`
- no full-document overwrite writes to Aerospike
- timeline is append-only
- realtime payloads must serialize directly from the canonical incident record
- frontend APIs must not invent alternate field names

## P0 Tasks

### 1. Create the real FastAPI backend shell

**Deliverable**

- One backend app that starts cleanly and mounts the incident, stream, agent, approval, and webhook routes.

**What to build**

- `server/app.py` returning a configured FastAPI app
- `server/main.py` for local `uvicorn` startup
- dependency wiring for config, Aerospike repo, realtime hub, and service layer
- a `GET /api/health` route that checks process readiness and store connectivity

**Done when**

- `uvicorn server.main:app --reload` is a plausible dev command
- the backend imports cleanly without requiring the frontend

### 2. Build the Aerospike repository and incident service

**Deliverable**

- One shared backend repository that the API layer and agent runtime both trust.

**What to build**

- Aerospike read methods:
  - `list_incidents`
  - `get_incident`
  - `create_incident`
- Aerospike patch methods:
  - `patch_incident`
  - `append_timeline_event`
- service-layer methods that:
  - validate patch ownership
  - normalize incidents through `agent/contracts.py`
  - emit realtime events after successful writes

**Important**

- Patch operations must preserve Claude and Kiro output fields without clobbering unrelated sponsor state.
- The API server and the agent loop must share the same write rules.

**Done when**

- `GET /api/incidents` and `GET /api/incidents/{id}` can read live Aerospike records
- `POST /api/incidents` can store a normalized record and publish an update event

### 3. Expose the frontend incident API

**Deliverable**

- A real backend surface for the dashboard.

**What to build**

- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- optional filters for:
  - `status`
  - `severity`
  - `limit`
- responses that serialize directly from the canonical record with no dashboard-only remapping

**Done when**

- frontend work can stop relying on `docs/incident-example.json`
- the incident list and detail page can both consume real API responses

### 4. Add realtime streaming for live dashboard updates

**Deliverable**

- A real-time feed that pushes incident updates without frontend polling being the only mechanism.

**What to build**

- `GET /api/incidents/stream` using SSE
- a small in-process realtime hub that publishes:
  - `incident.created`
  - `incident.updated`
  - `pipeline.heartbeat`
- event payloads containing:
  - `incident_id`
  - `status`
  - `severity`
  - `updated_at_ms`
  - `timeline_event`
  - full `incident`

**Important**

- SSE is the default choice for hackathon speed and frontend simplicity.
- If the frontend still polls, the SSE route should still exist as the live-demo path.

**Done when**

- storing or patching an incident emits a backend event the frontend can subscribe to

### 5. Wire the Person A runtime into the backend

**Deliverable**

- A backend entrypoint that runs the real agent against live incidents.

**What to build**

- `POST /api/agent/run-once`
- optional background loop startup hook for continuous processing
- backend service method that:
  - finds one `stored` incident
  - runs the existing Person A orchestrator
  - persists the result
  - publishes realtime updates

**Important**

- The API server must call the same runtime logic already used by the agent package.
- Do not create a second fake orchestration path inside the backend.

**Done when**

- one stored incident in Aerospike can be advanced to `gating` by hitting one backend route

### 6. Implement backend gating and approval transitions

**Deliverable**

- One backend flow that moves incidents through approval-driven states after Person A hands off at `gating`.

**What to build**

- `POST /api/approval/{incident_id}/decision`
- service logic that:
  - auto-approves `medium` and below
  - marks `high` and `critical` incidents for manual approval
  - transitions to `awaiting_approval`, `deploying`, or `blocked`
- timeline events for every decision

**Important**

- Auth0 integration can start as a real wrapper with local decision logic behind it, but the state transitions must be real and schema-valid.

**Done when**

- the backend can advance a `gating` incident to the next lifecycle state without manual Aerospike edits

### 7. Add webhook endpoints for sponsor callbacks

**Deliverable**

- Real callback surfaces the external systems can hit.

**What to build**

- `POST /api/webhooks/bland`
- `POST /api/webhooks/truefoundry`
- request validation and incident lookup
- patch logic that updates:
  - `approval.*`
  - `deployment.*`
  - top-level `status`
  - `timeline`

**Done when**

- a Bland approval callback and a TrueFoundry deployment callback can both update the same incident correctly

## P1 Tasks

### 8. Add end-to-end API tests

**Deliverable**

- Confidence that the live backend surface actually behaves like the docs say it should.

**What to build**

- tests for:
  - incident creation
  - incident list and detail routes
  - SSE event emission
  - run-once agent processing
  - approval transition handling
  - webhook-driven deployment updates

**Done when**

- the backend contract is protected by tests instead of only manual demo rehearsal

### 9. Finish Overclaw and Overmind backend wiring

**Deliverable**

- Traces and optimization hooks that operate on the live backend path, not just isolated unit flows.

**What to build**

- route the agent path through the shared `call_llm` and `call_tool` wrappers
- surface one Overmind trace id in `observability`
- finish:
  - `overclaw init`
  - `overclaw agent register`
  - `overclaw setup`
  - `overclaw optimize`

**Done when**

- one real backend-triggered agent run shows up in Overmind and is compatible with Overclaw

## Integration Checkpoints

### Checkpoint 1

- backend boots
- Aerospike repository works
- `GET /api/incidents` returns real records

### Checkpoint 2

- `GET /api/incidents/stream` emits updates
- demo incident creation updates the frontend

### Checkpoint 3

- `POST /api/agent/run-once` processes a real stored incident

### Checkpoint 4

- `POST /api/approval/{incident_id}/decision` updates lifecycle state correctly

### Checkpoint 5

- Bland and TrueFoundry callbacks update the same live incident record

## What Codex Should Not Spend Time On

- frontend visual polish
- rewriting diagnosis logic Claude already owns
- rewriting fix-generation logic Kiro already owns
- building a custom websocket platform if SSE is sufficient
- inventing a new schema for route responses

## Success Criteria

If Codex finishes well, the frontend has one real backend to talk to, the agent runs through the same backend that the demo uses, and every integration updates live state through one consistent API surface.
