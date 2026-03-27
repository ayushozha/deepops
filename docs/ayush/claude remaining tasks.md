# Claude Remaining Tasks

## Purpose

This is the Claude-only handoff for the unfinished work.

Use this together with:

- `docs/ayush/remaining-work-instructions.md`
- `docs/implementation-alignment.md`
- `docs/incident.schema.json`

Claude owns ingestion quality, transcript interpretation, human-language explanations, suggestion extraction, and diagnosis-side tracing cleanup.

## Do Not Rebuild

These Claude-owned pieces already exist and should be integrated or refined, not rewritten from scratch:

- `server/services/ingestion_service.py`
- `server/integrations/airbyte_client.py`
- `server/integrations/demo_app_client.py`
- `server/integrations/bland_client.py`
- `server/normalizers/incident_normalizer.py`
- `server/normalizers/bland_normalizer.py`
- `server/services/explanation_service.py`
- `server/services/decision_parser.py`
- `server/services/suggestion_extractor.py`

## Claude Scope

Claude owns:

- input normalization quality
- live demo-app and Airbyte client correctness
- approval explanation content
- phone script and transcript meaning
- suggestion extraction from human language
- diagnosis-side tracing migration

Claude does not own:

- FastAPI route registration
- backend orchestration state machine
- deployment execution
- Aerospike patch semantics

## Remaining Tasks

### 1. Make the demo-app and Airbyte clients fully live and config-driven

Current gap:

- the clients exist
- the backend is not yet running those clients as real integration sources

What Claude must do:

- verify the request/response contract of `server/integrations/demo_app_client.py`
- verify the request/response contract of `server/integrations/airbyte_client.py`
- make the clients fully config-driven
- make failures explicit and backend-usable
- confirm output is stable for `server/services/ingestion_service.py`

Done when:

- Codex can wire these clients into app startup and create incidents from real input sources

### 2. Route raw Bland transcripts into a structured approval outcome

Current gap:

- transcript helpers exist
- the live webhook path is not yet consuming a real transcript payload

What Claude must do:

- harden `server/normalizers/bland_normalizer.py` for real webhook payload shapes
- make transcript handling cover:
  - approve
  - reject
  - suggest changes
  - defer / wait
  - no answer
  - ask another person
  - follow-up required
- ensure the output is patch-ready for:
  - `approval.*`
  - execution-plan revision triggers
  - timeline notes

Done when:

- Codex can feed a raw Bland webhook payload into Claude-owned helpers and get a structured decision back

### 3. Feed explanation, decision parsing, and suggestion extraction into the live backend path

Current gap:

- helper services exist
- they are not yet the default source for the live approval and phone flows

What Claude must do:

- make `server/services/explanation_service.py` the canonical builder for:
  - short dashboard explanation
  - approval explanation payload
  - phone-call explanation payload
- make `server/services/decision_parser.py` and `server/services/suggestion_extractor.py` produce machine-usable outputs for the live path
- keep these outputs compact, explicit, and demo-safe

Done when:

- human language no longer has to be pre-structured before entering the approval flow

### 4. Improve unknown-input fallback behavior

Current gap:

- rehearsed bug paths work
- non-demo inputs still need safer fallback handling

What Claude must do:

- improve fallback normalization in `server/normalizers/incident_normalizer.py`
- strengthen fallback diagnosis behavior
- ensure fallback mode is visible in metadata and not silent
- avoid vague filler output in diagnosis and explanation layers

Done when:

- unknown or malformed live inputs still become useful incidents and remain explainable

### 5. Migrate diagnosis calls to the shared tracing wrapper

Current gap:

- `agent/diagnoser.py` still defines a local `call_llm`

What Claude must do:

- replace local `call_llm` usage with the shared tracing wrapper from `agent/tracing.py`
- make sure the diagnosis path still returns the same shape expected by the backend and tests
- verify one backend-triggered diagnosis run can be traced

Done when:

- diagnosis no longer depends on a local tracing shim

## Ordered Execution Sequence

Follow this order:

1. Finish client correctness for demo-app and Airbyte
2. Harden Bland transcript normalization
3. Connect decision parsing and suggestion extraction to real approval text
4. Improve unknown-input fallback behavior
5. Migrate diagnosis-side tracing to the shared wrapper

## Test And Verification Requirements

Before calling the Claude lane done, run:

- ingestion tests
- Bland normalizer tests
- decision parser tests
- suggestion extractor tests
- explanation service tests
- diagnosis-side tests after tracing migration

Also verify:

- one real transcript example routes to a structured decision
- one free-form suggestion becomes structured constraints

## Final Done Criteria

Claude is done when:

- live inputs normalize cleanly
- raw call transcripts become structured approval outcomes
- human guidance becomes machine-usable plan constraints
- explanations are good enough to show directly in the demo
- the diagnosis path uses the shared tracing wrapper
