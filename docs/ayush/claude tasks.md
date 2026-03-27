# Claude Tasks: Person A Diagnosis and Codebase Reasoning

## Mission

Own the parts of Person A that require codebase understanding and structured diagnosis. Claude should make the agent look intelligent without changing the lifecycle or store contract that Codex owns.

This file is only for **Person A** scope.

## Overclaw Requirement

Claude's work now needs to be legible to Overclaw's setup and optimization loop, not just to the live demo runtime.

The official Overclaw guide changes the diagnosis task in four important ways:

1. Diagnosis prompts and outputs need to be stable enough for scoring and regression checks.
2. Policies are first-class inputs to diagnosis, scoring, synthetic data generation, and code generation constraints.
3. Training data should be explicit and diverse, usually 10 to 50 cases.
4. LLM calls should go through `call_llm` so Overclaw sees token usage, latency, and tool metadata with full detail.

## Files Claude Should Own

- `agent/diagnoser.py`
- `agent/prompts.py` or equivalent prompt template module
- `agent/macroscope_client.py` or equivalent API wrapper
- `docs/ayush/person-a-policy.md`
- `data/person_a_dataset.json` or equivalent Overclaw seed dataset
- `tests/test_diagnoser.py`
- `tests/test_prompt_parsing.py`
- `tests/test_macroscope_client.py`

Claude should avoid editing:

- `agent/orchestrator.py`
- `agent/detector.py`
- `agent/severity.py`
- `agent/fixer.py`
- `agent/kiro_client.py`
- `config.py`
- Codex-owned store adapters and lifecycle helpers

## Primary Goal For Today

By the end of today, Claude should make it possible for Person A to take one incident and produce:

1. a structured diagnosis,
2. a deterministic root-cause explanation,
3. a suggested fix approach that Kiro can consume,
4. affected component lists and confidence scores,
5. enough metadata for Codex to move the incident cleanly into `fixing`.

By the end of today, Claude should also make it possible for Overclaw to score diagnosis quality against explicit policies and expected outputs.

## Shared Contracts Claude Must Respect

- Use the incident contract defined by Codex and the canonical schema in `docs/incident.schema.json`.
- Return only Person A-owned outputs:
  - `diagnosis.*`
  - optional Person A `observability` metadata
- Do not write `approval` or `deployment`.
- Do not invent alternate stage names. Codex owns lifecycle transitions.

## P0 Tasks

### 1. Build the Macroscope adapter

**Deliverable**

- A focused client wrapper around Macroscope that the agent can call safely.

**What to build**

- A function or class that:
  - sends one question to Macroscope
  - takes repo identifier and incident context
  - applies timeout and retry behavior
  - returns clean text context for downstream reasoning
- Error handling for:
  - missing API key
  - non-200 responses
  - empty or partial answers
- A local fallback mode that returns deterministic fixture context if the real API is unavailable during development.

**Important**

- Keep the wrapper narrow. The goal is not full SDK coverage.
- The output should be stable enough to feed into a structured prompt.
- If this wrapper is invoked during an Overclaw evaluation run, Codex should be able to wrap it with `call_tool`.

**Done when**

- `diagnoser.py` can ask questions like:
  - what does the failing function do
  - what calls it
  - what dependencies it touches
- Failures are surfaced clearly instead of breaking the whole run invisibly.

### 2. Design the diagnosis prompt and response contract

**Deliverable**

- A prompt template that reliably converts incident plus code context into structured diagnosis output.

**What to build**

- A prompt that includes:
  - raw error message
  - source file
  - route or path
  - Macroscope context
  - explicit JSON output requirements
- A strict response shape that maps cleanly into:
  - `root_cause`
  - `suggested_fix`
  - `affected_components`
  - `confidence`
  - optional severity reasoning text
- A parser that:
  - strips markdown fences
  - validates required fields
  - normalizes types
  - fails loudly if the response is not usable
- Prompt text that is compatible with Overclaw scoring:
  - stable keys
  - low ambiguity in field semantics
  - minimal free-form variation when the same bug appears twice

**Done when**

- The three planned demo bugs all produce valid structured diagnosis objects with minimal cleanup.

### 3. Draft the Overclaw policy document

**Deliverable**

- A policy doc that Overclaw can ingest during `overclaw setup`.

**What to build**

- `docs/ayush/person-a-policy.md` with:
  - purpose
  - decision rules
  - constraints
  - priority order
  - edge cases
- Policy rules specific to DeepOps Person A, for example:
  - diagnosis must cite the failing file or route
  - suggested fix must address the actual root cause, not only the symptom
  - severity reasoning must stay consistent with the known bug mappings
  - fix suggestions must avoid inventing unrelated architectural changes

**Important**

- Overclaw uses policies during diagnosis, scoring, synthetic data generation, and candidate generation, so this file matters more than a normal notes doc.

**Done when**

- The team can run `overclaw setup deepops-person-a --policy docs/ayush/person-a-policy.md` with a meaningful starting policy.

### 4. Build the Overclaw seed dataset

**Deliverable**

- A small but diverse seed dataset for Overclaw setup and optimization.

**What to build**

- `data/person_a_dataset.json` or equivalent JSON array where each item has:
  - `input`
  - `expected_output`
- Start with 10 to 15 cases if time is tight, but cover:
  - divide-by-zero variants
  - missing-user and null-handling variants
  - timeout and slow-path variants
  - malformed input cases
  - ambiguous cases where severity reasoning matters

**Important**

- The expected output should score diagnosis quality, not deployment behavior.
- Use compact, stable expected outputs so Overclaw can compare results mechanically where possible.

**Done when**

- The dataset is good enough that Overclaw setup does not need to start from a blank slate.

### 5. Implement `agent/diagnoser.py`

**Deliverable**

- One production path from incident to structured diagnosis result.

**What to build**

- `run_diagnosis(incident)` or the interface Codex defines.
- LLM calls wrapped through `call_llm` in any Overclaw-evaluated path.
- Overmind-friendly instrumentation hooks or attributes if Codex exposes them.
- A flow that:
  - queries Macroscope
  - calls the LLM
  - parses the response
  - returns only structured diagnosis data
- Reasoning tuned for the demo app's known bugs and plausible unknown failures.

**Important**

- Diagnosis should be concise, specific, and easy for the dashboard to display.
- Root cause text should sound like a senior engineer, not a vague model summary.

**Done when**

- For `/calculate/0`, diagnosis explicitly mentions missing zero guard.
- For `/user/unknown`, diagnosis explicitly mentions missing null handling on absent user.
- For `/search`, diagnosis explicitly mentions blocking sleep or timeout cause.

### 6. Add fixtures for the three known demo bugs

**Deliverable**

- Reusable local fixtures that let diagnosis be tested without the full live system.

**What to build**

- Fixture incidents or prompt snapshots for:
  - divide-by-zero endpoint
  - missing-user endpoint
  - slow search endpoint
- Optional fixture Macroscope responses for each.

**Done when**

- Claude can run diagnosis deterministically during development and rehearsal.

### 7. Add tests around parsing and output quality

**Deliverable**

- A small suite of tests that protects the structured diagnosis outputs from breaking.

**What to build**

- Tests for:
  - prompt output parser
  - Macroscope response fallback behavior
  - diagnosis object completeness for the three main bugs
  - required field validation
  - parsing when the model returns JSON inside markdown fences

**Important**

- Diagnosis output must map cleanly into the `diagnosis` section Codex expects.
- Claude should not own fix generation anymore. Kiro owns the spec-driven fix path.

**Done when**

- Claude can refactor prompts without constantly breaking the orchestrator contract.

## P1 Tasks

### 8. Add demo-grade language and observability metadata

**Deliverable**

- Outputs that look strong in the dashboard and in Overmind traces.

**What to build**

- Root cause summaries that are short enough for cards.
- Suggested fix text that is clear enough for Kiro to consume without rewriting.
- Optional extra metadata for spans, such as:
  - token count
  - prompt type
  - fallback path used
  - Macroscope success or fallback mode
- Any Overclaw-facing tags that help interpret evaluation failures later.

**Done when**

- The dashboard can show diagnosis text without manual rewriting during the demo.

### 9. Improve diagnosis prompts for unknown errors

**Deliverable**

- A better fallback prompt for incidents beyond the three rehearsed bugs.

**What to build**

- Prompt phrasing that still produces:
  - one concrete root cause
  - one practical fix direction
  - one compact affected component list
- Guardrails against vague responses like "check the logs" or "investigate further."

**Done when**

- Unknown incidents still produce usable diagnosis output instead of generic filler.

### 10. Prepare the handoff payload for Kiro

**Deliverable**

- A diagnosis output that Kiro can consume without custom translation.

**What to build**

- Make sure diagnosis includes:
  - `root_cause`
  - `suggested_fix`
  - `affected_components`
  - `confidence`
  - `severity_reasoning`
- Coordinate exact field names with Codex and Kiro so the fix worker can start immediately from diagnosis output.

**Done when**

- Kiro can accept Claude diagnosis output as input without another normalization layer.

## Handoff Points To Codex And Kiro

Claude should hand Codex and Kiro these exact stable artifacts:

- final diagnosis return shape
- policy document path
- seed dataset path
- any new prompt module imports
- a clear error contract for:
  - diagnosis failure
  - Macroscope unavailability
- fixture incidents and fixture external responses for local testing
- one example diagnosis payload for each of the three demo bugs

Codex and Kiro should not need to guess how to consume Claude's modules.

## Integration Checkpoints For Today

### Checkpoint 1

- Macroscope wrapper returns either real or fixture context.

### Checkpoint 2

- Diagnosis prompt returns parseable JSON for all three demo bugs.

### Checkpoint 3

- Diagnosis payload is stable enough that Kiro can start fix generation immediately.

### Checkpoint 4

- `docs/ayush/person-a-policy.md` exists and matches the DeepOps bug domain.
- `data/person_a_dataset.json` exists or is ready to generate during `overclaw setup`.

## What Claude Should Not Spend Time On Today

- Aerospike read or patch implementation
- lifecycle state machine design
- deployment logic
- Auth0 approval flow
- dashboard UI
- Kiro CLI integration
- live production-hardening beyond simple retries and fallbacks

## Success Criteria

If Claude finishes well, the agent will be able to explain what broke in a structured way and hand a high-quality diagnosis directly to Kiro and Codex without translation work.
