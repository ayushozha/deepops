# Kiro Demo Tasks: Execution Plan Formatting, Hotfix Packaging, and Smallest Safe Action Layer

## Mission

Own the simplest slice of the demo:

- take an already-approved plan,
- turn it into a clean execution package,
- keep hotfix execution artifacts structured,
- avoid owning complex branching or human interpretation.

Kiro should stay focused on execution-ready output, not orchestration.

## Core Demo Responsibility

Kiro owns the smallest safe action layer after intent is already clear.

That means Kiro owns:

- execution plan formatting,
- fix spec cleanup,
- hotfix package generation,
- deployable artifact summaries,
- constrained execution outputs after a human suggestion has already been parsed.

## What Kiro Must Build

### 1. Approved Plan To Execution Package

When Codex and Claude have already settled on the plan, Kiro should convert it into:

- concise execution steps,
- final fix spec,
- diff preview,
- files changed,
- test plan,
- deployment package inputs.

### 2. Suggestion-Aware Fix Packaging

If the human says:

- "do not touch auth",
- "only patch the endpoint",
- "ship a hotfix now and clean later",

Kiro should apply those already-parsed constraints to the fix packaging step, not reinterpret the human language itself.

### 3. Hotfix Mode

For the phone-guided emergency path, Kiro should produce:

- a compact hotfix plan,
- limited-scope fix artifact,
- fast verification checklist,
- deployable package metadata.

### 4. Execution Summary For Demo Narration

Keep producing short outputs that are easy to show:

- what is being changed,
- where it is being changed,
- what to verify after deploy.

This should be useful in the UI and during the live explanation.

## Files Kiro Should Own

- fix artifact builders
- deployment packaging helpers
- constrained hotfix output logic
- tests for fix packaging under approved and suggested-plan scenarios

## Demo Checkpoints Kiro Must Deliver

### Checkpoint 1

- normal approved plan becomes a clean execution package

### Checkpoint 2

- constrained suggested plan still produces a valid fix package

### Checkpoint 3

- emergency hotfix path produces a smaller, faster execution package

### Checkpoint 4

- package output is simple enough to narrate live

## What Kiro Should Not Own

- approval logic
- phone transcript understanding
- state transitions
- escalation rules
- backend routing

## Success Criteria

If Kiro finishes well, every approved path ends with a clean, believable execution package and hotfix artifact without Kiro needing to reason about the full system flow.
