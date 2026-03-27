# Codex Demo Tasks: Orchestration, State Machine, and Multi-Flow Backend Control

## Mission

Own the hardest part of the demo:

- one backend that supports all three demo flows,
- one state machine that branches correctly,
- one live system that can move between autonomy, approval, and phone escalation without breaking the incident contract.

Codex owns the most complex work.

## Core Demo Responsibility

Codex owns the runtime that decides which flow the system is in and how it moves to the next stage.

That means Codex owns:

- autonomous end-to-end flow,
- approval checkpoints,
- escalation branching,
- suggestion-driven plan updates,
- deployment handoff state changes,
- the live backend contract the frontend reads.

## What Codex Must Build

### 1. Flow Router For The Three Demo Modes

Build the backend logic that decides:

- can this incident self-heal,
- does this incident require approval,
- does this incident require a phone escalation,
- did the human approve, reject, or suggest,
- should execution continue, pause, or re-plan.

This routing logic should be explicit and auditable in the incident timeline.

### 2. Autonomous Flow State Machine

Own the full path for low-risk incidents:

- `stored`
- `diagnosing`
- `fixing`
- `gating`
- `deploying`
- `resolved`

The autonomous mode should only interrupt the human when the risk threshold or policy requires it.

### 3. Approval-Driven Branching

Own the state transitions for:

- approve current plan,
- reject current plan,
- suggest plan changes,
- approve fix,
- reject fix,
- approve merge/deploy,
- block execution.

Codex should define the structured state updates and timeline entries for all of these decisions.

### 4. Suggestion-To-Plan Execution Backbone

When the human says:

- "do it this way",
- "do not change that file",
- "roll back after hotfix",
- "use a feature flag",
- "patch only the endpoint",

Codex should own the execution backbone that:

- stores the suggestion,
- marks the incident as needing re-plan,
- hands the suggestion to Claude and Kiro outputs,
- resumes the execution flow after approval.

### 5. Escalation Trigger Logic

Codex owns the rules for when the system escalates to a call.

Examples:

- critical severity,
- financial risk,
- broad blast radius,
- explicit policy trigger,
- repeated deployment failure.

Codex should also own the post-call branching:

- approved,
- rejected,
- suggested alternative,
- no answer,
- follow-up required.

### 6. Live Backend Surface

Codex should keep owning the backend routes and state APIs that make the demo visible:

- incident list/detail
- realtime stream
- agent run
- approval decision
- escalation trigger
- Bland webhook receive
- deployment webhook receive

### 7. Execution Plan Persistence

Codex should introduce a structured place in backend state for:

- current execution plan,
- current approval request,
- suggested revision from human,
- source of instruction: UI or phone,
- whether the plan is pending, approved, superseded, or executed.

If a new top-level field is not acceptable in the canonical schema, Codex should store this in approved metadata locations without breaking the contract.

## Files Codex Should Own

- backend flow router and orchestrator files
- API routes for approval and escalation triggers
- realtime and state services
- any plan-state persistence layer
- integration tests that prove the three demo flows actually work

## Demo Checkpoints Codex Must Deliver

### Checkpoint 1

- low-risk incident resolves without human interruption

### Checkpoint 2

- medium or high-risk incident pauses for approval

### Checkpoint 3

- human suggestion causes re-plan instead of dead-end rejection

### Checkpoint 4

- critical incident triggers phone escalation path

### Checkpoint 5

- phone-guided execution resumes and reaches deployment or block state cleanly

## What Codex Should Not Offload

- branching logic
- lifecycle ownership
- approval semantics
- escalation state machine
- live backend API contract

## Success Criteria

If Codex finishes well, the system can move naturally between all three demo flows without special-case hacks and the frontend can narrate the entire story from one live incident record.
