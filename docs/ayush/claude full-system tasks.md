# Claude Tasks: Ingestion, Normalization, Diagnosis, and Sponsor Payload Reasoning

## Mission

Own the backend work that turns raw external signals into clean incident records and makes the live integrations speak the same language as the canonical schema.

Claude should make the system intelligent and integration-friendly without owning the API server or the deployment pipeline.

This file is for the full-system backend scope, not only Person A.

## Primary Goal

By the end of this workstream, Claude should make it possible to:

1. ingest raw error events from the demo app or Airbyte,
2. normalize them into the canonical incident shape,
3. produce high-quality diagnosis output in the live backend path,
4. prepare Bland AI escalation payloads that sound real,
5. parse incoming approval and transcript data into structured state updates,
6. keep the backend outputs stable enough for Overclaw evaluation.

## Files Claude Should Own

- `server/services/ingestion_service.py`
- `server/integrations/airbyte_client.py`
- `server/integrations/demo_app_client.py`
- `server/integrations/bland_client.py`
- `server/normalizers/incident_normalizer.py`
- `server/normalizers/bland_normalizer.py`
- `agent/diagnoser.py`
- `agent/prompts.py`
- `agent/macroscope_client.py`
- `docs/ayush/person-a-policy.md`
- `data/person_a_dataset.json`
- `server/tests/test_ingestion_service.py`
- `server/tests/test_bland_normalizer.py`
- `tests/test_diagnoser.py`
- `tests/test_prompt_parsing.py`
- `tests/test_macroscope_client.py`

Claude should avoid editing:

- backend API route wiring
- Aerospike repository code
- SSE hub
- TrueFoundry deployment code
- Kiro fix-generation modules

## Shared Contracts Claude Must Respect

- incident schema: `docs/incident.schema.json`
- lifecycle: `docs/implementation-alignment.md`
- incident normalization must populate `source`, not bypass it
- diagnosis output must stay within `diagnosis.*`
- Bland parsing must update `approval.*`, not invent a parallel transcript model
- external payload mappers must fail visibly, not silently drop data

## P0 Tasks

### 1. Build the real ingestion normalization path

**Deliverable**

- One reusable normalization layer that converts raw demo-app or Airbyte payloads into canonical incidents.

**What to build**

- normalization from raw event into:
  - `incident_id`
  - `status=stored`
  - `source.*`
  - default `diagnosis`, `fix`, `approval`, `deployment`, `observability`
  - first `timeline` event
- support both:
  - demo trigger payloads
  - polled error payloads from the demo app
  - Airbyte-delivered records if they differ slightly

**Important**

- Do not let frontend-specific convenience fields leak into the stored incident.
- The output of normalization should already be ready for Aerospike write.

**Done when**

- Codex can call one ingestion service method and reliably get a schema-valid stored incident payload

### 2. Implement the demo-app and Airbyte-facing clients

**Deliverable**

- A real input path for incident creation.

**What to build**

- a demo-app client that can:
  - poll recent errors
  - trigger known bug scenarios if the backend chooses to expose that route
- an Airbyte client or connector wrapper that can:
  - trigger one sync
  - read sync results or staged records
  - hand normalized payloads to the ingestion service

**Important**

- If Airbyte is not fully available yet, keep the wrapper real but allow a development-mode fallback behind config.
- Do not collapse Airbyte into a hardcoded local JSON file.

**Done when**

- the backend can create real stored incidents from an external source instead of only manual inserts

### 3. Keep live diagnosis quality strong

**Deliverable**

- The same structured diagnosis quality currently present in Person A, but running cleanly in the backend path.

**What to build**

- diagnosis prompt stability
- Macroscope live query quality and fallback behavior
- diagnosis output that stays compact, specific, and dashboard-readable
- diagnosis failure handling that still returns a meaningful failed state

**Important**

- Route all Overclaw-evaluated model calls through the shared `call_llm` path.
- Diagnosis must remain directly consumable by Kiro and Codex.

**Done when**

- one live backend-triggered diagnosis run returns the same shape as the tested local path

### 4. Build Bland AI payload and webhook interpretation helpers

**Deliverable**

- A clean language layer for the manual-approval path.

**What to build**

- outbound Bland call payload builder containing:
  - incident summary
  - severity
  - root cause
  - deployment ask
- inbound Bland webhook parser that extracts:
  - approval decision
  - decision notes
  - call identifier
  - decision timestamp
- normalization rules that convert the webhook result into canonical `approval` updates

**Important**

- Claude owns the content and parsing quality here.
- Codex should only need to call a clean function and patch the returned fields.

**Done when**

- a Bland callback can be interpreted into a structured approval decision without manual string parsing in route handlers

### 5. Expand the policy and dataset for full-system realism

**Deliverable**

- Better Overclaw setup artifacts that reflect live backend behavior, not only isolated diagnosis cases.

**What to build**

- add cases to `data/person_a_dataset.json` that cover:
  - ingestion variants
  - malformed payloads
  - ambiguous severity reasoning
  - approval-worthy incidents
- refine `docs/ayush/person-a-policy.md` so it remains aligned with the live backend flow

**Done when**

- Overclaw setup reflects the incidents the backend will actually see

## P1 Tasks

### 6. Improve unknown-incident normalization and fallback diagnosis

**Deliverable**

- A backend that still behaves sensibly when the error does not match the three rehearsed demo bugs.

**What to build**

- normalization heuristics for incomplete payloads
- safer default source-field mapping
- stronger fallback diagnosis prompts that avoid vague filler
- explicit tagging when fallback mode was used

**Done when**

- new demo inputs still become usable incidents and diagnosis does not degrade into generic noise

### 7. Add tests for ingestion and Bland parsing

**Deliverable**

- A safety net around the most brittle payload transformations.

**What to build**

- tests for:
  - demo-app error normalization
  - Airbyte sync payload normalization
  - Bland request body building
  - Bland webhook result parsing
  - live diagnosis shape invariants

**Done when**

- the payload conversion layer is hard to break accidentally during sponsor integration work

## Integration Checkpoints

### Checkpoint 1

- raw demo error becomes a canonical stored incident

### Checkpoint 2

- live diagnosis works from a backend-triggered run

### Checkpoint 3

- Bland outbound payload sounds credible and complete

### Checkpoint 4

- Bland webhook parsing produces patch-ready approval data

## What Claude Should Not Spend Time On

- FastAPI route registration
- Aerospike repository internals
- SSE implementation
- deployment polling logic
- frontend rendering

## Success Criteria

If Claude finishes well, the backend can ingest real external signals, normalize them correctly, reason about them intelligently, and feed clean, structured sponsor payloads into the rest of the system.
