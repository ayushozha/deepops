# Demo Flow Alignment

## Mission

Design the implementation around the demo, not the other way around.

For the hackathon, the system should be presented through three clear flows that build on each other:

1. autonomous self-healing,
2. human approval and steering,
3. human phone escalation for high-risk incidents.

This document is the source of truth for how the team should divide work between Codex, Claude, and Kiro for the demo-facing backend.

## Demo Flow 1: Autonomous Agent

This is the baseline and should feel magical even before human involvement.

The system should:

- monitor a live app,
- detect an error in real time,
- understand the codebase,
- diagnose the root cause,
- plan a fix,
- write the fix,
- deploy the fix,
- notify the human only if approval is required.

What the audience should see:

- incident appears live on the dashboard,
- agent moves it through diagnosis and fix generation,
- severity is computed,
- low-risk issue deploys without human intervention,
- final state lands in `resolved`.

## Demo Flow 2: Approval and Human Steering

This is the collaborative-control mode.

The system should support:

- approve,
- reject,
- suggest changes,
- ask for another plan,
- ask for another fix,
- approve or reject merge/deploy,
- let the human guide the system when they want more control.

What the audience should see:

- the system pauses at the right time,
- the human can approve or reject specific steps,
- the human can suggest a fix direction,
- the backend turns that into a structured execution plan,
- the agent follows the approved or revised plan.

## Demo Flow 3: Phone Escalation for High-Impact Incidents

This is the showstopper flow.

The system should escalate when the issue is too risky to self-heal silently, for example:

- large financial impact,
- high user impact,
- critical outage,
- security-sensitive behavior,
- anything with broad blast radius.

The system should call the human, explain the issue in plain language, and support two branches:

### Branch A: Human is away from a computer

- the phone call explains the issue,
- the human gives verbal instructions,
- the backend converts the instructions into a structured execution plan,
- the agent executes the hotfix,
- the normal approval and deployment flow continues.

### Branch B: Human can actively guide the system

- the phone call or approval interface gathers intent,
- the human gives constraints or implementation guidance,
- the agent proposes an updated plan,
- the human approves or revises it,
- the agent executes.

## Ownership Philosophy

Codex takes the most complex orchestration and system-state work.

Claude takes the balanced middle layer:

- human-language interpretation,
- approval intent capture,
- call scripts,
- suggestion parsing,
- explanation quality.

Kiro gets the simplest slice:

- turning an already-approved plan into clean execution artifacts,
- packaging fix/deploy inputs,
- keeping implementation steps structured and small.

## Shared Rules

- The canonical incident schema is still `docs/incident.schema.json`.
- The canonical lifecycle is still `docs/implementation-alignment.md`.
- Demo logic must not invent a second state model.
- Every flow must resolve through the same incident record in Aerospike.
- Every user decision must become structured state, not just raw text.
- The phone call flow is not separate from the product. It is another way to drive the same approval and execution pipeline.

## Core Backend Capabilities Required By The Demo

- realtime incident ingest
- live incident list and detail API
- realtime stream to the frontend
- autonomous agent run path
- approval decision path
- suggestion-to-plan conversion path
- outbound Bland AI call trigger
- inbound Bland webhook parsing
- execution-plan persistence
- deployment trigger and status updates

## Success Criteria

If this split is implemented well, the demo can cleanly show:

1. full autonomy when risk is low,
2. precise human control when desired,
3. natural phone escalation and guided hotfixing when risk is high.
