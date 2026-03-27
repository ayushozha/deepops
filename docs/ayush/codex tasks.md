# Codex Tasks: Person A Runtime, State Machine, and Agent Skeleton

## Mission

Own the parts of Person A that define how the agent runs, how it consumes incidents from the shared store, how it moves incidents through the canonical lifecycle, and how it exposes a stable runtime skeleton that Claude and Kiro can plug their work into.

This file is only for **Person A** scope.

## Files Codex Should Own

- `config.py`
- `agent/__init__.py`
- `agent/orchestrator.py`
- `agent/detector.py`
- `agent/severity.py`
- `agent/types.py` or `agent/contracts.py`
- `agent/store_adapter.py` or equivalent Person A read/patch wrapper
- `agent/runner.py` or equivalent local entrypoint
- `tests/test_orchestrator.py`
- `tests/test_severity.py`
- `tests/test_detector.py`

Claude should avoid editing these unless you both explicitly re-assign ownership.

## Primary Goal For Today

By the end of today, Codex should make it possible to start one agent process that:

1. Reads incidents from Aerospike using the shared schema.
2. Claims only incidents that are ready for Person A work.
3. Moves incidents through `diagnosing`, `fixing`, and `gating`.
4. Calls into Claude-owned diagnosis functions and Kiro-owned fix functions through clean interfaces.
5. Writes back severity, status, and timeline events in the exact shape expected by the dashboard and Person B.

## Shared Contracts Codex Must Respect

- Source of truth for schema: `docs/incident.schema.json`
- Source of truth for status model: `docs/implementation-alignment.md`
- Person A must only own:
  - `diagnosis`
  - `fix`
  - `severity`
  - transitions into `diagnosing`, `fixing`, and `gating`
  - Person A side `observability` fields
- Person A must not overwrite:
  - `source`
  - `approval`
  - `deployment`
- Store updates must behave like patch operations, not whole-record replacement.

## P0 Tasks

### 1. Create the Person A runtime scaffold

**Deliverable**

- A working Python package structure for the agent.
- One import path that all modules can rely on.

**What to build**

- `agent/` package with clear module boundaries.
- `config.py` that loads:
  - Aerospike host and namespace config
  - Overmind API key
  - Anthropic or LLM configuration placeholders
  - Macroscope and Kiro config placeholders, even if Claude fills usage later
- A small runtime settings object or dataclass so the rest of the code does not read environment variables directly.

**Done when**

- `python -m agent.runner` or an equivalent command starts without import errors.
- All config usage is centralized and not scattered across modules.

### 2. Define the incident contract helpers for Person A

**Deliverable**

- A typed contract layer that mirrors the canonical incident shape enough for safe reads and patches.

**What to build**

- `TypedDict`, dataclass, or Pydantic models for:
  - incident record
  - diagnosis payload
  - fix payload
  - timeline event
  - patch payloads for Person A updates
- Helper functions that generate valid timeline events and Person A patch objects.
- A small set of status constants so no one hardcodes lifecycle strings in five places.

**Important**

- This does not need full JSON-schema validation on every request.
- It does need enough structure that Codex and Claude use the same field names.

**Done when**

- Orchestrator code can read and write incidents without stringly-typed chaos.
- Claude and Kiro can import the same contract helpers for diagnosis and fix results.

### 3. Implement the Aerospike-facing detector and store adapter

**Deliverable**

- A Person A wrapper that can fetch candidate incidents and patch only Person A-owned fields.

**What to build**

- A read path that fetches incidents whose `status` is `stored`.
- A claim or guard strategy so the same incident is not processed repeatedly in a tight loop.
- Patch helpers for:
  - moving to `diagnosing`
  - writing `diagnosis`
  - moving to `fixing`
  - writing `fix`
  - moving to `gating`
  - appending timeline events
- Graceful handling for empty store results, malformed incidents, and Aerospike connection failures.

**Assumption**

- Person B may still be implementing the real Aerospike store. If so, Codex should support a local mock or JSON fixture mode so work can continue.

**Done when**

- Codex can run the detector against `docs/incident-example.json` or a mock incident and receive a valid in-memory incident object.
- Patch operations are isolated to Person A-owned fields.

### 4. Build the orchestrator state machine

**Deliverable**

- `agent/orchestrator.py` that is the canonical Person A loop.

**What to build**

- A loop that:
  - polls for ready incidents
  - starts an Overmind span for each cycle
  - transitions one incident into `diagnosing`
  - calls Claude-owned diagnosis function
  - transitions into `fixing`
  - calls Kiro-owned fix generation function
  - computes severity using Codex-owned severity logic
  - writes final Person A outputs
  - transitions the incident into `gating`
- A narrow interface layer for Claude-owned calls, for example:
  - `run_diagnosis(incident) -> DiagnosisResult`
  - `run_fix_generation(incident, diagnosis) -> FixResult`
- Safe error handling:
  - if diagnosis fails, mark incident `failed`
  - if fix generation fails, mark incident `failed`
  - always append a timeline event

**Important**

- The orchestrator should not decide deployment behavior directly.
- Its final job is to hand off a fully populated incident to Person B by leaving it in `gating`.

**Done when**

- A seeded incident can move from `stored` to `gating` through one command.
- Failures are represented explicitly, not swallowed in logs.

### 5. Implement deterministic severity classification for the demo

**Deliverable**

- `agent/severity.py` with demo-safe classification behavior.

**What to build**

- Severity rules that map the three demo bugs predictably:
  - divide by zero -> `medium`
  - missing user null or key access -> `high`
  - blocking timeout search -> `critical`
- A fallback ruleset for unknown incidents based on diagnosis text.
- A short explanation string that can be written into `diagnosis.severity_reasoning` or timeline metadata.

**Done when**

- The three planned bugs always classify the same way.
- The orchestrator does not depend on free-form LLM severity text alone.

## P1 Tasks

### 6. Add Overmind instrumentation around the whole runtime

**Deliverable**

- Useful tracing instead of just an `init()` call.

**What to build**

- Spans around:
  - agent cycle
  - incident fetch
  - diagnosis call
  - fix generation call
  - store patch/write operations
- Attributes on spans such as:
  - `incident_id`
  - `error_type`
  - `source_file`
  - `severity`
  - `status_before`
  - `status_after`

**Done when**

- Overmind can show one full trace for a single incident lifecycle through Person A.

### 7. Build a local runner and dry-run mode

**Deliverable**

- A way to test Person A before all sponsor services are live.

**What to build**

- CLI or runner flags such as:
  - `--once` to process a single incident and exit
  - `--mock-incident docs/incident-example.json`
  - `--dry-run` to skip real external writes
- Console logging that is demo-readable but not noisy.

**Done when**

- Ayush can test one incident locally without requiring the full live pipeline.

### 8. Add tests around lifecycle behavior

**Deliverable**

- A small but meaningful safety net.

**What to build**

- Tests for:
  - reading a valid incident fixture
  - rejecting malformed status transitions
  - severity mapping for the three known bugs
  - orchestrator progression from `stored` to `gating`
  - failure path to `failed`

**Done when**

- The critical state machine logic is not only manually tested.

## Handoff Points To Claude And Kiro

Codex should hand Claude and Kiro these exact interfaces as early as possible:

- incident contract types
- config access pattern
- diagnosis function signature
- fix generation function signature
- example incident fixture
- expected patch shape for diagnosis and fix payloads

Claude and Kiro should be able to implement internals without changing orchestrator semantics.

## Integration Checkpoints For Today

### Checkpoint 1

- Config loads.
- Runner starts.
- Mock incident loads.

### Checkpoint 2

- Detector returns one `stored` incident.
- Orchestrator can move it to `diagnosing`.

### Checkpoint 3

- Claude diagnosis result plugs in cleanly.
- Incident moves to `fixing`.

### Checkpoint 4

- Kiro fix result plugs in cleanly.
- Severity is computed.
- Incident ends in `gating`.

## What Codex Should Not Spend Time On Today

- Real deployment logic
- Dashboard rendering
- Bland AI integration
- Auth0 integration details
- Full production-grade retry frameworks
- Fancy abstractions that slow down the demo

## Success Criteria

If Codex finishes well, Claude can focus entirely on diagnosis, Kiro can focus entirely on fix generation, and the Person A runtime will already exist with a clean handoff to Person B.
