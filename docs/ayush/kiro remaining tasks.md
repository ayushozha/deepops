# Kiro Remaining Tasks

## Purpose

This is the Kiro-only handoff for the unfinished work.

Use this together with:

- `docs/ayush/remaining-work-instructions.md`
- `docs/implementation-alignment.md`
- `docs/incident.schema.json`

Kiro owns fix payload correctness, tool execution reliability, deployment service behavior, and execution artifact packaging.

## Do Not Rebuild

These Kiro-owned pieces already exist and should be fixed or integrated, not replaced from scratch:

- `agent/fixer.py`
- `agent/kiro_client.py`
- `agent/fix_specs.py`
- `agent/execution_package.py`
- `server/services/deployment_service.py`
- `server/integrations/truefoundry_client.py`
- `server/services/fix_artifact_service.py`

## Kiro Scope

Kiro owns:

- schema-clean `fix` persistence
- Kiro tool-call reliability
- deployment service behavior
- execution package and hotfix package generation
- verification that a Kiro run produced usable artifacts

Kiro does not own:

- approval semantics
- transcript meaning
- FastAPI route registration
- backend orchestration

## Remaining Tasks

### 1. Remove non-schema metadata from the stored `fix` payload

Current gap:

- `agent/fixer.py` still emits `_metadata`
- the canonical schema does not allow extra keys inside `fix`

What Kiro must do:

- keep the stored `fix` object limited to:
  - `status`
  - `spec_markdown`
  - `diff_preview`
  - `files_changed`
  - `test_plan`
  - timestamps
- move Kiro-specific metadata such as:
  - mode
  - fix summary
  - regression warning
  out of the stored `fix` object
- use:
  - timeline metadata
  - observability fields
  - response-only fields
  where appropriate

Done when:

- no incident written to storage contains non-schema keys in `fix`

### 2. Migrate Kiro tool calls to the shared tracing wrapper

Current gap:

- `agent/kiro_client.py` still defines a local `call_tool`

What Kiro must do:

- replace the local tool-call shim with the shared tracing wrapper from `agent/tracing.py`
- preserve current behavior and test coverage
- verify the backend-triggered fix path remains traceable

Done when:

- no local `call_tool` shim remains in the Kiro client path

### 3. Unify the live deployment path through `server/services/deployment_service.py`

Current gap:

- `server/services/deployment_service.py` exists
- the orchestration layer still has direct deploy logic

What Kiro must do:

- make `server/services/deployment_service.py` the authoritative deployment implementation
- keep the service responsible for:
  - starting deployment
  - normalizing result state
  - building canonical deployment patches
  - appending deployment timeline events
- coordinate with Codex so orchestration calls the service instead of duplicating deploy logic

Done when:

- all deploy transitions flow through the deployment service only

### 4. Hook execution-package and hotfix-package outputs into the live flow

Current gap:

- `agent/execution_package.py` exists
- execution packages are not yet part of the live backend flow

What Kiro must do:

- generate a normal execution package for approved plans
- generate a hotfix package for constrained or emergency paths
- make sure constraints already parsed by Claude and routed by Codex can shape:
  - files changed
  - execution steps
  - verification checklist
  - narration summary

Done when:

- every approved execution path can produce a clean execution artifact for the demo

### 5. Enforce usable Kiro output, not just successful exit codes

Current gap:

- the Kiro lane still needs stronger validation that output is actually deployable

What Kiro must do:

- reject runs that exit successfully but produce:
  - no diff preview
  - no meaningful file list
  - empty or malformed artifacts
- return clear failure signals for:
  - missing CLI
  - timeout
  - malformed output
  - empty artifact result

Done when:

- the backend can trust that a "successful" Kiro run produced a usable fix artifact

## Ordered Execution Sequence

Follow this order:

1. Clean the stored `fix` payload
2. Migrate tool tracing to the shared wrapper
3. Harden output validation
4. Unify deployment behavior through `server/services/deployment_service.py`
5. Integrate execution-package and hotfix-package outputs into the live path

## Test And Verification Requirements

Before calling the Kiro lane done, run:

- fixer tests
- Kiro client tests
- fix spec tests
- execution package tests
- deployment service tests
- TrueFoundry client tests

Also verify:

- one stored incident validates against `docs/incident.schema.json`
- one approved path yields a normal execution package
- one constrained path yields a hotfix package

## Final Done Criteria

Kiro is done when:

- the stored `fix` payload is schema-clean
- Kiro tool calls use the shared tracing wrapper
- deploy behavior is implemented in the deployment service
- the backend can trust Kiro output quality
- execution and hotfix packages are available for the live demo path
