# Kiro Tasks: Person A Spec-Driven Fix Generation

## Mission

Own the parts of Person A that turn a structured diagnosis into a believable, spec-driven fix proposal. Kiro should make the "agent writes the fix" portion of the demo feel real without touching deployment or Person B-owned systems.

This file is only for **Person A** scope.

## Files Kiro Should Own

- `agent/fixer.py`
- `agent/kiro_client.py` or equivalent CLI wrapper
- `agent/fix_specs.py` or equivalent spec builder
- `tests/test_fixer.py`
- `tests/test_kiro_client.py`
- `tests/test_fix_specs.py`

Kiro should avoid editing:

- `agent/orchestrator.py`
- `agent/detector.py`
- `agent/severity.py`
- `agent/diagnoser.py`
- `config.py`
- store adapters

## Primary Goal For Today

By the end of today, Kiro should make it possible for Person A to take a structured diagnosis and produce:

1. a Kiro-style markdown spec,
2. a fix proposal or diff preview,
3. likely files changed,
4. a short test plan,
5. a clean `fix` payload that Codex can write back into the incident record.

## Shared Contracts Kiro Must Respect

- Input comes from Claude's structured diagnosis output plus the original incident.
- Output must fit the `fix` section described in `docs/incident.schema.json`.
- Kiro owns only:
  - `fix.spec_markdown`
  - `fix.diff_preview`
  - `fix.files_changed`
  - `fix.test_plan`
  - optional fix-generation metadata for Person A observability
- Kiro must not:
  - move lifecycle states directly
  - write `approval`
  - write `deployment`
  - apply patches to the repo as part of Person A work

## P0 Tasks

### 1. Build the Kiro spec generator

**Deliverable**

- A deterministic markdown spec generator that converts diagnosis into implementation-ready instructions.

**What to build**

- A function that creates a spec with:
  - requirements
  - acceptance criteria
  - implementation approach
  - likely files to inspect
  - regression risks
- Spec text that is:
  - structured enough to showcase Kiro
  - short enough to generate quickly during the demo
  - specific to the diagnosis instead of generic boilerplate

**Done when**

- Each of the three demo bugs produces a useful spec that looks intentional on screen.

### 2. Implement the Kiro CLI wrapper

**Deliverable**

- A wrapper that runs the Kiro CLI safely and predictably.

**What to build**

- A function or class that:
  - writes the spec to a temp file
  - invokes Kiro with repo path and timeout
  - captures stdout and stderr
  - returns exit status and raw output
- Clear handling for:
  - CLI not installed
  - timeout
  - empty output
  - malformed diff output

**Important**

- Keep the wrapper narrow and practical.
- Do not build a full general-purpose Kiro abstraction.

**Done when**

- The fix pipeline can run Kiro from one function call and get back structured output or a clear failure.

### 3. Implement `agent/fixer.py`

**Deliverable**

- One production path from diagnosis to `fix` payload.

**What to build**

- `run_fix_generation(incident, diagnosis)` or whatever interface Codex defines.
- A flow that:
  - receives diagnosis from Claude
  - generates the Kiro spec
  - runs the Kiro CLI
  - extracts a diff preview
  - extracts or infers files changed
  - produces a small test plan
- Output formatting that is dashboard-friendly and not too long.

**Done when**

- Codex can call one function and get a complete `fix` object back.

### 4. Add fallback behavior if Kiro is unavailable

**Deliverable**

- A backup mode so Person A work does not stall if the CLI misbehaves.

**What to build**

- A fallback path that still returns:
  - spec markdown
  - a plausible diff preview
  - files changed
  - test plan
- Clear labeling that fallback mode was used.
- A simple rule that prefers real Kiro output whenever available.

**Important**

- The fallback should preserve the spec-driven feel of the demo.
- It should not block the rest of the agent loop.

**Done when**

- Person A can still demo fix generation even if Kiro setup is flaky.

### 5. Add diff extraction and summarization

**Deliverable**

- A clean diff preview suitable for the dashboard and incident record.

**What to build**

- Logic to:
  - trim oversized output
  - keep only relevant hunks
  - extract changed file paths
  - produce a readable preview without flooding the incident record

**Done when**

- The fix preview is short enough to display but concrete enough to be believable.

## P1 Tasks

### 6. Add fixtures for the three known demo bugs

**Deliverable**

- Reusable fix-generation fixtures tied to Claude diagnosis outputs.

**What to build**

- Example diagnosis payloads for:
  - divide-by-zero
  - missing-user null handling
  - blocking timeout search
- Expected spec shapes and expected file change lists for each.

**Done when**

- Kiro can test fix generation locally without the live diagnosis service.

### 7. Add tests around fix payload generation

**Deliverable**

- A small suite that protects the fix pipeline from regressions.

**What to build**

- Tests for:
  - spec markdown generation
  - CLI wrapper timeout handling
  - fallback mode
  - diff preview trimming
  - files changed extraction
  - final `fix` payload completeness

**Done when**

- Refactors do not silently break the `fix` contract.

### 8. Add demo-grade test plans and fix summaries

**Deliverable**

- Fix output that is easy to narrate live.

**What to build**

- For each incident, generate:
  - one-line fix summary
  - one-line regression warning if relevant
  - compact test plan steps that Ayush can say out loud during the demo

**Done when**

- The proposed fix can be shown in the dashboard without extra rewriting.

## Handoff Points To Codex

Kiro should hand Codex these exact stable artifacts:

- final `fix` payload shape
- Kiro success versus fallback mode indicator
- error contract for Kiro timeout or CLI failure
- example fix payload for each of the three demo bugs

Codex should not need to guess how to consume Kiro output.

## Dependency On Claude

Kiro depends on Claude to provide a stable diagnosis payload with:

- `root_cause`
- `suggested_fix`
- `affected_components`
- `confidence`
- optional severity reasoning

If that payload changes shape, Kiro work will slow down immediately, so this contract should be frozen early.

## Integration Checkpoints For Today

### Checkpoint 1

- Kiro spec generation works from a fixture diagnosis.

### Checkpoint 2

- Real Kiro CLI output is captured successfully or fallback mode is triggered cleanly.

### Checkpoint 3

- `run_fix_generation()` returns a valid `fix` payload for one demo incident.

### Checkpoint 4

- Codex can write Kiro's `fix` payload into the incident and move the incident to `gating`.

## What Kiro Should Not Spend Time On Today

- Aerospike integration
- Macroscope queries
- diagnosis prompt engineering
- lifecycle state machine logic
- deployment or approval flows
- dashboard UI

## Success Criteria

If Kiro finishes well, the demo will have a credible "agent wrote the fix" step with a clean spec, a readable patch preview, and a reliable payload that Codex can hand off to Person B.
