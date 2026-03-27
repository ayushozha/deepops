# Claude Demo Tasks: Human Explanations, Approval Interpretation, and Phone Conversation Intelligence

## Mission

Own the balanced middle layer between raw system state and human communication.

Claude should make the demo feel human:

- explain what happened,
- explain what the plan is,
- interpret approval decisions,
- interpret human suggestions,
- turn phone-call language into structured instructions the backend can act on.

## Core Demo Responsibility

Claude owns the meaning layer for flows 2 and 3.

That means Claude owns:

- approval explanation quality,
- suggestion parsing,
- rejection reasoning capture,
- outbound Bland call content,
- inbound transcript interpretation,
- instruction extraction from natural language.

## What Claude Must Build

### 1. Approval Explanation Payloads

For every approval checkpoint, Claude should produce clear, compact text that answers:

- what broke,
- what the agent wants to do,
- why approval is needed,
- what the blast radius is,
- what happens if we proceed.

This should work for both UI and phone surfaces.

### 2. Human Decision Parsing

Claude should turn human input into structured backend meaning:

- approve,
- reject,
- ask for revision,
- suggest an alternative,
- defer,
- ask for more context.

This applies to:

- frontend approval UI submissions,
- Bland transcripts,
- typed suggestions,
- short human notes.

### 3. Suggestion Extraction

When the human provides guidance, Claude should extract structured constraints such as:

- files to avoid,
- files to target,
- scope limits,
- rollback expectations,
- deployment constraints,
- urgency or safety requirements.

Claude should return these as machine-usable guidance instead of free-form prose.

### 4. Phone Call Scripts and Incident Explanation

Claude should make the call feel real.

Build:

- outbound call summary,
- short explanation for the human,
- follow-up questions when approval is unclear,
- prompts that ask for actionable instructions if the human is away from a computer.

### 5. Transcript-To-Action Parsing

Claude should parse phone-call outcomes into structured responses such as:

- approve now,
- reject now,
- wait,
- hotfix only,
- avoid deployment,
- patch this specific area,
- ask another person,
- no answer / retry later.

### 6. Re-Plan Input Packets

Claude should hand Codex and Kiro a clean packet when the human suggests a new direction:

- revised intent,
- extracted constraints,
- inferred urgency,
- plan notes that can be executed,
- confidence that the suggestion was interpreted correctly.

## Files Claude Should Own

- Bland normalization and transcript parsing
- approval explanation builders
- suggestion extraction helpers
- any structured natural-language interpretation helpers for the approval and phone flows

## Demo Checkpoints Claude Must Deliver

### Checkpoint 1

- approval request text is short, clear, and useful

### Checkpoint 2

- human approve/reject/suggest inputs are parsed correctly

### Checkpoint 3

- outbound phone call script sounds natural

### Checkpoint 4

- transcript parsing returns actionable structured data for Codex

### Checkpoint 5

- away-from-computer instructions can be converted into usable execution guidance

## What Claude Should Not Own

- state machine routing
- deployment execution
- API route registration
- realtime transport
- store patch semantics

## Success Criteria

If Claude finishes well, the demo will feel like the system actually understands the human, not like it is passing around raw strings between services.
