# Full-System Backend Alignment

## Mission

Build the real backend for DeepOps, not a mock adapter. The frontend should read live incident state from one backend API, that backend should read and write the canonical incident schema in Aerospike, and every sponsor integration should update the same incident record in real time.

This plan replaces the old "Person A only" mindset for execution order. The older task files still describe the agent internals, but the files in this pack are the source of truth for the full backend build.

## Non-Negotiables

- One canonical incident schema: `docs/incident.schema.json`
- One canonical lifecycle: `docs/implementation-alignment.md`
- One shared state store: Aerospike
- One backend API surface for the frontend
- Real integrations first, fixture mode only behind explicit flags
- No second dashboard-only data model
- Every state change must append a timeline event

## What "Complete System" Means Here

The backend is only complete when all of these are true:

1. Demo app or Airbyte ingestion creates a real incident in Aerospike.
2. Person A reads that stored incident and writes diagnosis, fix, severity, and gating state back to Aerospike.
3. Auth0-style gating logic decides whether the incident can auto-deploy or must wait for approval.
4. High and critical incidents can trigger Bland AI escalation and consume the webhook result.
5. TrueFoundry deployment status is written back into the same incident record.
6. The frontend can read the incident list and detail view from one FastAPI backend.
7. The frontend can receive live updates through one realtime feed instead of manual refresh.

## Backend Surface

The backend should expose these endpoints as the minimum real API:

- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `GET /api/incidents/stream`
- `POST /api/incidents`
- `POST /api/ingest/demo/{bug_key}`
- `POST /api/ingest/airbyte/sync`
- `POST /api/agent/run-once`
- `POST /api/approval/{incident_id}/decision`
- `POST /api/webhooks/bland`
- `POST /api/webhooks/truefoundry`
- `GET /api/health`

## Realtime Contract

Use SSE first, not WebSocket, unless the frontend proves it needs bidirectional messaging.

Target event types:

- `incident.created`
- `incident.updated`
- `incident.deleted` only if deletion becomes necessary later
- `pipeline.heartbeat`

Each SSE event should include:

- `incident_id`
- `status`
- `severity`
- `updated_at_ms`
- `timeline_event` when available
- full `incident` payload for simple frontend consumption

## Proposed Backend Layout

- `server/app.py`
- `server/main.py`
- `server/api/incidents.py`
- `server/api/stream.py`
- `server/api/ingest.py`
- `server/api/agent.py`
- `server/api/approval.py`
- `server/api/webhooks.py`
- `server/services/incident_service.py`
- `server/services/realtime_hub.py`
- `server/services/ingestion_service.py`
- `server/services/gating_service.py`
- `server/services/deployment_service.py`
- `server/integrations/aerospike_repo.py`
- `server/integrations/auth0_client.py`
- `server/integrations/bland_client.py`
- `server/integrations/truefoundry_client.py`
- `server/integrations/airbyte_client.py`

Reuse the existing shared contract and agent modules where possible:

- `agent/contracts.py`
- `agent/orchestrator.py`
- `agent/diagnoser.py`
- `agent/fixer.py`

## Ownership Split

Codex owns platform backend and shared state boundaries:

- FastAPI app structure
- API routes
- Aerospike repository and patch semantics
- SSE / realtime streaming
- service orchestration
- Auth0 gating flow and backend transitions
- end-to-end backend tests

Claude owns ingestion, normalization, and reasoning-heavy integration payloads:

- Airbyte or demo-app ingestion normalization
- incident creation payload shaping
- Macroscope live query quality
- Bland AI request copy and webhook transcript parsing
- diagnosis quality in the live backend path
- policy and dataset quality for Overclaw

Kiro owns fix and deployment execution surfaces:

- Kiro fix generation hardening
- deployable patch packaging and fix artifacts
- TrueFoundry client wrapper
- deployment status polling and result mapping
- deployment-specific regression checks

## Execution Order

1. FastAPI app + Aerospike repository + `GET /api/incidents`
2. `GET /api/incidents/{incident_id}` + SSE stream
3. `POST /api/incidents` + `POST /api/ingest/demo/{bug_key}`
4. `POST /api/agent/run-once` backed by the real Person A agent
5. `POST /api/approval/{incident_id}/decision`
6. `POST /api/webhooks/bland`
7. `POST /api/webhooks/truefoundry`
8. `POST /api/ingest/airbyte/sync`
9. one full end-to-end demo run with live state transitions

## Checkpoints

### Checkpoint 1

- Backend starts.
- Aerospike read and write work.
- Frontend can load `GET /api/incidents`.

### Checkpoint 2

- SSE feed pushes incident updates without page refresh.
- Demo trigger creates new stored incidents.

### Checkpoint 3

- Agent can process one stored incident from the live backend.
- Incident moves to `gating`.

### Checkpoint 4

- Auth0 gating and Bland escalation update the same incident.

### Checkpoint 5

- TrueFoundry deployment status updates the same incident.
- Frontend shows the full lifecycle from one backend source.

## What To Avoid

- building a fake API that only mirrors local JSON files
- inventing a second schema for the frontend
- stuffing dashboard-only computed fields into Aerospike
- hiding sponsor failures behind silent fallbacks
- making realtime depend on polling-only code paths

## Success Criteria

If this split is executed well, the frontend becomes a thin client over one live backend, every sponsor integration updates the same incident record, and the hackathon demo can show a real end-to-end system instead of stitched-together mock screens.
