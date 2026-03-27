# DeepOps - Full Project Context for UI Design

This document contains everything needed to design and build the DeepOps dashboard UI. It was compiled from the project's README, build guide, team contract, data schema, example data, existing React dashboard component, and agent source code. If you are an AI design tool or a human designer, this single document should give you complete context.

---

## 1. Project Overview

**DeepOps** is a **self-healing codebase agent** -- an autonomous system that monitors a live application, detects errors in real-time, diagnoses root causes by understanding the codebase, writes and deploys fixes, and calls the on-call engineer (via a real phone call) only when human approval is needed.

It was built for the **Deep Agents Hackathon** (March 27, 2026) by a team of 2 full-stack developers.

**The "wow" moment:** During a 3-minute live demo, the agent detects a production bug, diagnoses it, writes a fix, and -- for high/critical severity bugs -- makes a live phone call to the on-call engineer using Bland AI. The audience hears the AI voice explaining the incident and asking for approval. When the engineer says "yes," the dashboard updates in real-time to show the fix being deployed.

**Tagline:** "Self-healing codebases powered by deep agents"

**Judging criteria:**
- Autonomy: Agent acts on real-time data without manual intervention
- Idea: Solves a meaningful problem (every developer's pain point -- bugs)
- Technical Implementation: LLM orchestration + 8 genuine sponsor integrations
- Tool Use: All 8 sponsor tools have genuine, non-forced roles
- Presentation: 3-minute live demo with the phone call as the showstopper

---

## 2. Architecture

### High-Level Pipeline

```
Error Detected --> Ingested --> Stored --> Diagnosed --> Fixed --> Auth Check --> Deployed --> Resolved
   (Airbyte)    (Aerospike)  (Macroscope)  (Kiro)     (Auth0)  (TrueFoundry)  (Overmind)
```

### ASCII Architecture Diagram

```
[Error Logs / Metrics]
        |
   [ Airbyte ]  -- ingests error signals into pipeline
        |
   [ Aerospike ] -- stores incidents, agent memory, codebase graph
        |
   [ Agent Core (Python + LLM) ]
        |
   +----+----+----+
   |         |         |
[Macroscope]  [Kiro]   [Auth0]
 (understand   (plan &   (RBAC:
  codebase)    write     severity
               fix)      gating)
                |
        +-------+-------+
        |               |
  [TrueFoundry]    [Bland AI]
  (deploy fix)     (voice-call
                    engineer)
        |
   [ Overmind ]  -- traces every decision, optimizes over time
```

### Step-by-Step Flow

1. **Detect** -- Airbyte ingests error signals from logs and metrics
2. **Store** -- Aerospike persists incidents, agent memory, and codebase graph
3. **Diagnose** -- Macroscope analyzes the codebase to understand root cause
4. **Fix** -- Kiro plans and writes the code fix using spec-driven development
5. **Gate** -- Auth0 enforces RBAC severity gating (auto-deploy vs. human approval)
6. **Escalate** -- Bland AI voice-calls the on-call engineer for critical issues
7. **Deploy** -- TrueFoundry deploys the verified fix
8. **Optimize** -- Overmind traces every decision and optimizes over time

An SVG architecture diagram also exists at `docs/deepops-architecture.svg`.

---

## 3. Incident Lifecycle

### Status Flow

The top-level `status` field on every incident record follows this pipeline:

```
detected --> stored --> diagnosing --> fixing --> gating --> awaiting_approval --> deploying --> resolved
                                                     |                                          |
                                                     +-- (auto-approve for low/medium) ---------+
                                                     |
                                                     +-- blocked (if human rejects)
                                                     +-- failed (if something breaks)
```

### Canonical Lifecycle Table

| Status | Owner | Meaning | Required write before leaving stage |
|---|---|---|---|
| `detected` | Person B (Infra) | Error exists in raw source stream | `source.*`, `incident_id`, `created_at_ms` |
| `stored` | Person B | Incident normalized and written to Aerospike | `updated_at_ms`, first `timeline` event |
| `diagnosing` | Person A (Agent) | Agent is querying Macroscope and reasoning | `diagnosis.status=running` |
| `fixing` | Person A | Agent is generating a fix spec and diff | `diagnosis.*`, `fix.status=running` |
| `gating` | Person A | Severity is finalized and routing decision is ready | `severity`, `fix.*`, `approval.required` |
| `awaiting_approval` | Person B | Manual approval path via Bland AI is in progress | `approval.mode=manual`, `approval.channel=voice_call` |
| `deploying` | Person B | Fix is approved and deployment started | `approval.status=approved`, `deployment.status=running` |
| `resolved` | Person B | Fix deployed successfully | `deployment.*`, `resolution_time_ms` |
| `blocked` | Person B | Human rejected or deferred deploy | `approval.status=rejected` or note in `timeline` |
| `failed` | Either | Something in diagnosis, fix, or deploy failed | `timeline` event with failure reason |

### Severity Rules (Fixed for Demo Predictability)

| Trigger Endpoint | Error | Severity | Approval Path |
|---|---|---|---|
| `/calculate/0` | ZeroDivisionError (divide by zero) | `medium` | **auto-deploy** (no phone call) |
| `/user/unknown` | KeyError: 'name' (null reference on missing user) | `high` | **Bland AI voice-call approval** |
| `/search` | TimeoutError (blocking sleep causes cascading timeouts) | `critical` | **Bland AI voice-call approval** |

### Severity Classification Rules (from the agent code)

```python
rules = {
    "critical": ["data loss", "security", "auth bypass", "payment"],
    "high": ["500 error", "service down", "timeout cascade"],
    "medium": ["degraded performance", "non-critical path"],
    "low": ["cosmetic", "logging", "non-user-facing"]
}
```

---

## 4. Data Schema

### Full Incident Record JSON Schema

This is the canonical runtime contract. Both the agent backend and the dashboard read/write this structure. It is stored in Aerospike.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://deepops.local/incident.schema.json",
  "title": "DeepOps Incident Record",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "incident_id",
    "status",
    "severity",
    "service",
    "environment",
    "created_at_ms",
    "updated_at_ms",
    "source",
    "diagnosis",
    "fix",
    "approval",
    "deployment",
    "observability",
    "timeline"
  ],
  "properties": {
    "incident_id": {
      "type": "string",
      "description": "Stable incident identifier. UUID preferred."
    },
    "status": {
      "type": "string",
      "enum": [
        "detected",
        "stored",
        "diagnosing",
        "fixing",
        "gating",
        "awaiting_approval",
        "deploying",
        "resolved",
        "blocked",
        "failed"
      ]
    },
    "severity": {
      "type": "string",
      "enum": [
        "pending",
        "low",
        "medium",
        "high",
        "critical"
      ]
    },
    "service": {
      "type": "string"
    },
    "environment": {
      "type": "string"
    },
    "created_at_ms": {
      "type": "integer",
      "minimum": 0
    },
    "updated_at_ms": {
      "type": "integer",
      "minimum": 0
    },
    "resolution_time_ms": {
      "type": ["integer", "null"],
      "minimum": 0
    },
    "source": {
      "type": "object",
      "required": ["provider", "path", "error_type", "error_message", "source_file", "timestamp_ms"],
      "properties": {
        "provider": { "type": "string", "enum": ["demo-app", "airbyte"] },
        "path": { "type": "string" },
        "error_type": { "type": "string" },
        "error_message": { "type": "string" },
        "source_file": { "type": "string" },
        "timestamp_ms": { "type": "integer", "minimum": 0 },
        "fingerprint": { "type": ["string", "null"] },
        "raw_payload": { "type": ["object", "null"] }
      }
    },
    "diagnosis": {
      "type": "object",
      "required": ["status", "root_cause", "suggested_fix", "affected_components", "confidence"],
      "properties": {
        "status": { "type": "string", "enum": ["pending", "running", "complete", "failed"] },
        "root_cause": { "type": ["string", "null"] },
        "suggested_fix": { "type": ["string", "null"] },
        "affected_components": { "type": "array", "items": { "type": "string" } },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "severity_reasoning": { "type": ["string", "null"] },
        "macroscope_context": { "type": ["string", "null"] },
        "started_at_ms": { "type": ["integer", "null"], "minimum": 0 },
        "completed_at_ms": { "type": ["integer", "null"], "minimum": 0 }
      }
    },
    "fix": {
      "type": "object",
      "required": ["status", "spec_markdown", "diff_preview", "files_changed", "test_plan"],
      "properties": {
        "status": { "type": "string", "enum": ["pending", "running", "complete", "failed"] },
        "spec_markdown": { "type": ["string", "null"] },
        "diff_preview": { "type": ["string", "null"] },
        "files_changed": { "type": "array", "items": { "type": "string" } },
        "test_plan": { "type": "array", "items": { "type": "string" } },
        "started_at_ms": { "type": ["integer", "null"], "minimum": 0 },
        "completed_at_ms": { "type": ["integer", "null"], "minimum": 0 }
      }
    },
    "approval": {
      "type": "object",
      "required": ["required", "mode", "status"],
      "properties": {
        "required": { "type": "boolean" },
        "mode": { "type": "string", "enum": ["auto", "manual"] },
        "status": { "type": "string", "enum": ["pending", "approved", "rejected", "skipped"] },
        "channel": { "type": ["string", "null"] },
        "decider": { "type": ["string", "null"] },
        "bland_call_id": { "type": ["string", "null"] },
        "notes": { "type": ["string", "null"] },
        "decision_at_ms": { "type": ["integer", "null"], "minimum": 0 }
      }
    },
    "deployment": {
      "type": "object",
      "required": ["provider", "status"],
      "properties": {
        "provider": { "type": "string", "enum": ["truefoundry"] },
        "status": { "type": "string", "enum": ["pending", "running", "succeeded", "failed", "skipped"] },
        "service_name": { "type": ["string", "null"] },
        "environment": { "type": ["string", "null"] },
        "commit_sha": { "type": ["string", "null"] },
        "deploy_url": { "type": ["string", "null"] },
        "started_at_ms": { "type": ["integer", "null"], "minimum": 0 },
        "completed_at_ms": { "type": ["integer", "null"], "minimum": 0 },
        "failure_reason": { "type": ["string", "null"] }
      }
    },
    "observability": {
      "type": "object",
      "required": ["overmind_trace_id", "overmind_trace_url", "airbyte_sync_id", "auth0_decision_id"],
      "properties": {
        "overmind_trace_id": { "type": ["string", "null"] },
        "overmind_trace_url": { "type": ["string", "null"] },
        "airbyte_sync_id": { "type": ["string", "null"] },
        "auth0_decision_id": { "type": ["string", "null"] }
      }
    },
    "timeline": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["at_ms", "status", "actor", "message", "sponsor"],
        "properties": {
          "at_ms": { "type": "integer", "minimum": 0 },
          "status": { "type": "string" },
          "actor": { "type": "string" },
          "message": { "type": "string" },
          "sponsor": { "type": "string" },
          "metadata": { "type": ["object", "null"] }
        }
      }
    }
  }
}
```

### Example Incident (Fully Resolved, Medium Severity, Auto-Deploy)

```json
{
  "incident_id": "inc-9d8580b4-27fc-4d3e-b451-2d06a7f3c5ba",
  "status": "resolved",
  "severity": "medium",
  "service": "deepops-demo-app",
  "environment": "hackathon",
  "created_at_ms": 1774647600000,
  "updated_at_ms": 1774647634000,
  "resolution_time_ms": 34000,
  "source": {
    "provider": "airbyte",
    "path": "/calculate/0",
    "error_type": "ZeroDivisionError",
    "error_message": "division by zero",
    "source_file": "demo-app/main.py",
    "timestamp_ms": 1774647600000,
    "fingerprint": "calculate-zero-division",
    "raw_payload": {
      "method": "GET",
      "status_code": 500
    }
  },
  "diagnosis": {
    "status": "complete",
    "root_cause": "The calculate endpoint divides by the raw path parameter without validating zero, so value 0 raises an unhandled ZeroDivisionError.",
    "suggested_fix": "Add a guard clause before division and return a safe validation error when value is 0.",
    "affected_components": [
      "demo-app/main.py",
      "calculate endpoint"
    ],
    "confidence": 0.96,
    "severity_reasoning": "The bug is user-facing but isolated to one endpoint and has a safe deterministic fix.",
    "macroscope_context": "calculate() is only called by the /calculate/{value} route and has no downstream writes.",
    "started_at_ms": 1774647606000,
    "completed_at_ms": 1774647615000
  },
  "fix": {
    "status": "complete",
    "spec_markdown": "# Fix Specification\n\n## Requirements\n- Prevent division by zero in calculate\n- Preserve existing response contract for non-zero input\n\n## Acceptance Criteria\n- /calculate/0 returns a handled error response\n- non-zero values still return result",
    "diff_preview": "@@ -9,5 +9,8 @@\n async def calculate(value: int):\n     logging.info(f\"Calculating for {value}\")\n+    if value == 0:\n+        raise HTTPException(status_code=400, detail=\"Cannot divide by zero\")\n     result = 100 / value\n     return {\"result\": result}\n",
    "files_changed": [
      "demo-app/main.py"
    ],
    "test_plan": [
      "Call /calculate/0 and confirm handled error response",
      "Call /calculate/5 and confirm result is unchanged"
    ],
    "started_at_ms": 1774647615000,
    "completed_at_ms": 1774647624000
  },
  "approval": {
    "required": false,
    "mode": "auto",
    "status": "approved",
    "channel": "auth0-rbac",
    "decider": "auth0:auto-deploy",
    "bland_call_id": null,
    "notes": "Medium severity matched auto-deploy rule.",
    "decision_at_ms": 1774647625000
  },
  "deployment": {
    "provider": "truefoundry",
    "status": "succeeded",
    "service_name": "deepops-demo-app",
    "environment": "hackathon",
    "commit_sha": "abc1234",
    "deploy_url": "https://deepops-demo.truefoundry.app",
    "started_at_ms": 1774647626000,
    "completed_at_ms": 1774647634000,
    "failure_reason": null
  },
  "observability": {
    "overmind_trace_id": "ovr-trace-123",
    "overmind_trace_url": "https://console.overmindlab.ai/traces/ovr-trace-123",
    "airbyte_sync_id": "airbyte-sync-001",
    "auth0_decision_id": "auth0-decision-001"
  },
  "timeline": [
    {
      "at_ms": 1774647600000,
      "status": "detected",
      "actor": "airbyte",
      "message": "Airbyte ingested ZeroDivisionError from /calculate/0",
      "sponsor": "Airbyte",
      "metadata": { "path": "/calculate/0" }
    },
    {
      "at_ms": 1774647603000,
      "status": "stored",
      "actor": "infra",
      "message": "Incident stored in Aerospike",
      "sponsor": "Aerospike",
      "metadata": null
    },
    {
      "at_ms": 1774647606000,
      "status": "diagnosing",
      "actor": "agent-core",
      "message": "Macroscope query started for demo-app/main.py",
      "sponsor": "Macroscope",
      "metadata": null
    },
    {
      "at_ms": 1774647615000,
      "status": "fixing",
      "actor": "agent-core",
      "message": "Kiro generated patch proposal",
      "sponsor": "Kiro",
      "metadata": { "files_changed": 1 }
    },
    {
      "at_ms": 1774647625000,
      "status": "gating",
      "actor": "auth-gate",
      "message": "Auth0 approved medium severity for auto-deploy",
      "sponsor": "Auth0",
      "metadata": { "severity": "medium" }
    },
    {
      "at_ms": 1774647626000,
      "status": "deploying",
      "actor": "deployer",
      "message": "TrueFoundry deployment started",
      "sponsor": "TrueFoundry",
      "metadata": { "service": "deepops-demo-app" }
    },
    {
      "at_ms": 1774647634000,
      "status": "resolved",
      "actor": "deployer",
      "message": "Deployment succeeded and incident resolved",
      "sponsor": "Overmind",
      "metadata": { "trace_id": "ovr-trace-123" }
    }
  ]
}
```

---

## 5. Dashboard Requirements

### What the Dashboard Must Show

Derived from the implementation-alignment contract:

1. **Incident list** -- all active and resolved incidents, sorted by recency
2. **Status pipeline** -- a visual stage-by-stage progress indicator for each incident (detected -> stored -> diagnosing -> fixing -> gating -> awaiting_approval -> deploying -> resolved)
3. **Diagnosis details** -- root cause analysis text, affected components, confidence score
4. **Fix preview** -- the proposed code diff, files changed, test plan
5. **Deployment status** -- whether the fix is being deployed, succeeded, or failed
6. **Severity badge** -- color-coded severity on each incident (low/medium/high/critical)
7. **Sponsor integration indicators** -- which sponsor tool is currently active
8. **Metrics** -- incidents detected, incidents resolved, average resolution time, LLM call count
9. **Agent log** -- real-time scrolling log of agent actions
10. **Overmind traces** -- LLM latency, token usage, and cost per incident
11. **Phone call indicator** -- visible when Bland AI is calling the on-call engineer for high/critical severity

### Fields the Dashboard Reads from the Incident Record

```
status                          -- pipeline stage
severity                        -- color-coded badge
source.error_message            -- what went wrong
source.error_type               -- error class name
source.source_file              -- where the bug is
source.path                     -- the endpoint/route that triggered it
diagnosis.root_cause            -- why it went wrong
diagnosis.confidence            -- how sure the agent is
diagnosis.severity_reasoning    -- why this severity level
fix.diff_preview                -- the proposed code change
fix.files_changed               -- which files the fix touches
fix.test_plan                   -- how to verify the fix
approval.status                 -- pending/approved/rejected
approval.mode                   -- auto or manual
approval.bland_call_id          -- non-null means a phone call happened
deployment.status               -- pending/running/succeeded/failed
deployment.deploy_url           -- link to the deployed service
observability.overmind_trace_id -- link to the Overmind trace
timeline                        -- full event history for the log view
```

### Polling API Contract

```http
GET /api/incidents
```

Response:

```json
{
  "incidents": [IncidentRecord, IncidentRecord, ...]
}
```

The dashboard polls this endpoint every few seconds to get fresh data.

---

## 6. Existing Dashboard Component

This is the **most important section** for UI design. The full React component below defines the current dashboard design, including all visual components, animations, colors, layout, and interaction patterns.

```jsx
import { useState, useEffect, useCallback, useRef } from "react";

const SPONSORS = [
  { name: "Airbyte", icon: "\u{1F504}", color: "#634BFF", role: "Ingest" },
  { name: "Aerospike", icon: "\u26A1", color: "#C4302B", role: "Store" },
  { name: "Macroscope", icon: "\u{1F50D}", color: "#00B4D8", role: "Understand" },
  { name: "Kiro", icon: "\u{1F47B}", color: "#FF9900", role: "Fix" },
  { name: "Auth0", icon: "\u{1F510}", color: "#EB5424", role: "Gate" },
  { name: "Bland AI", icon: "\u{1F399}\uFE0F", color: "#6366F1", role: "Escalate" },
  { name: "TrueFoundry", icon: "\u{1F680}", color: "#10B981", role: "Deploy" },
  { name: "Overmind", icon: "\u2699\uFE0F", color: "#A855F7", role: "Optimize" },
];

const STAGES = [
  { key: "detected", label: "DETECTED", color: "#F87171", sponsor: "Airbyte" },
  { key: "stored", label: "STORED", color: "#C4302B", sponsor: "Aerospike" },
  { key: "diagnosing", label: "DIAGNOSING", color: "#00B4D8", sponsor: "Macroscope" },
  { key: "fixing", label: "FIXING", color: "#FF9900", sponsor: "Kiro" },
  { key: "gating", label: "AUTH CHECK", color: "#EB5424", sponsor: "Auth0" },
  { key: "escalated", label: "CALLING...", color: "#6366F1", sponsor: "Bland AI" },
  { key: "deploying", label: "DEPLOYING", color: "#10B981", sponsor: "TrueFoundry" },
  { key: "resolved", label: "RESOLVED", color: "#22C55E", sponsor: "Overmind" },
];

const DEMO_ERRORS = [
  {
    id: "INC-001",
    error: "ZeroDivisionError in /calculate/0",
    file: "demo-app/main.py:14",
    severity: "medium",
    rootCause: "Missing input validation on division endpoint. Value 0 causes unhandled ZeroDivisionError.",
    fix: "Add guard clause: if value == 0: return {'error': 'Cannot divide by zero'}",
  },
  {
    id: "INC-002",
    error: "KeyError: 'name' in /user/unknown",
    file: "demo-app/main.py:21",
    severity: "high",
    rootCause: "Null reference when accessing non-existent user. users.get() returns None, then ['name'] fails.",
    fix: "Add null check: if not user: raise HTTPException(404, 'User not found')",
  },
  {
    id: "INC-003",
    error: "TimeoutError in /search endpoint",
    file: "demo-app/main.py:26",
    severity: "critical",
    rootCause: "Blocking sleep(5) in async handler causes cascading timeouts under load.",
    fix: "Replace time.sleep with await asyncio.sleep or remove artificial delay.",
  },
];

function useAnimatedNumber(target, duration = 800) {
  const [val, setVal] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = val;
    let startTime = null;
    const animate = (ts) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      setVal(Math.round(start + (target - start) * progress));
      if (progress < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [target]);
  return val;
}

function PulsingDot({ color, size = 8 }) {
  return (
    <span style={{ position: "relative", display: "inline-block", width: size, height: size }}>
      <span
        style={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: color,
          animation: "pulse 2s ease-in-out infinite",
        }}
      />
      <span
        style={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: color,
          opacity: 0.4,
          animation: "ping 2s ease-in-out infinite",
        }}
      />
      <style>{`
        @keyframes ping { 0% { transform: scale(1); opacity: 0.4; } 100% { transform: scale(2.5); opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
      `}</style>
    </span>
  );
}

function SeverityBadge({ severity }) {
  const colors = {
    low: { bg: "#064E3B", text: "#6EE7B7", border: "#065F46" },
    medium: { bg: "#78350F", text: "#FDE68A", border: "#92400E" },
    high: { bg: "#7C2D12", text: "#FDBA74", border: "#9A3412" },
    critical: { bg: "#7F1D1D", text: "#FCA5A5", border: "#991B1B" },
  };
  const c = colors[severity] || colors.medium;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 1.2,
        textTransform: "uppercase",
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
      }}
    >
      {severity}
    </span>
  );
}

function PipelineStage({ stage, active, completed, incident }) {
  const isActive = active === stage.key;
  const isDone = completed.includes(stage.key);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        opacity: isDone ? 0.45 : isActive ? 1 : 0.2,
        transition: "all 0.5s ease",
        transform: isActive ? "scale(1.12)" : "scale(1)",
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 18,
          background: isActive ? stage.color + "22" : isDone ? "#22C55E11" : "#1A1A2E",
          border: `2px solid ${isActive ? stage.color : isDone ? "#22C55E55" : "#2A2A3E"}`,
          position: "relative",
          boxShadow: isActive ? `0 0 20px ${stage.color}44` : "none",
        }}
      >
        {isDone ? "\u2713" : isActive ? <PulsingDot color={stage.color} size={10} /> : "\u25CB"}
      </div>
      <span
        style={{
          fontSize: 8,
          fontWeight: 700,
          letterSpacing: 1,
          color: isActive ? stage.color : isDone ? "#22C55E" : "#4A4A6A",
          textAlign: "center",
          maxWidth: 60,
        }}
      >
        {stage.label}
      </span>
      <span style={{ fontSize: 7, color: "#6A6A8A" }}>{stage.sponsor}</span>
    </div>
  );
}

function IncidentCard({ incident, isActive, stageIdx, onTrigger }) {
  const completedStages = STAGES.slice(0, stageIdx).map((s) => s.key);
  const activeStage = stageIdx < STAGES.length ? STAGES[stageIdx].key : "resolved";
  const resolved = stageIdx >= STAGES.length;

  return (
    <div
      style={{
        background: isActive ? "#0F0F1E" : "#0A0A16",
        border: `1px solid ${isActive ? "#3B3B5C" : "#1A1A2E"}`,
        borderRadius: 12,
        padding: 16,
        transition: "all 0.4s ease",
        boxShadow: isActive ? "0 4px 30px rgba(99,102,241,0.08)" : "none",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: "#E2E8F0" }}>
            {incident.id}
          </span>
          <SeverityBadge severity={incident.severity} />
          {isActive && !resolved && <PulsingDot color={STAGES[stageIdx]?.color || "#22C55E"} />}
        </div>
        {resolved && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "#22C55E",
              background: "#22C55E15",
              padding: "2px 8px",
              borderRadius: 4,
              border: "1px solid #22C55E33",
            }}
          >
            RESOLVED
          </span>
        )}
      </div>

      <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
        {incident.error}
      </div>
      <div style={{ fontSize: 10, color: "#64748B", marginBottom: 12 }}>file: {incident.file}</div>

      {stageIdx >= 3 && (
        <div style={{ background: "#0D0D1A", borderRadius: 8, padding: 10, marginBottom: 12, border: "1px solid #1E1E36" }}>
          <div style={{ fontSize: 9, color: "#00B4D8", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
            ROOT CAUSE
          </div>
          <div style={{ fontSize: 11, color: "#CBD5E1", lineHeight: 1.4 }}>{incident.rootCause}</div>
        </div>
      )}

      {stageIdx >= 4 && (
        <div style={{ background: "#0D0D1A", borderRadius: 8, padding: 10, marginBottom: 12, border: "1px solid #1E1E36" }}>
          <div style={{ fontSize: 9, color: "#FF9900", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
            PROPOSED FIX
          </div>
          <div style={{ fontSize: 11, color: "#CBD5E1", fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.5 }}>
            {incident.fix}
          </div>
        </div>
      )}

      {stageIdx >= 5 && incident.severity === "critical" && !resolved && (
        <div
          style={{
            background: "#6366F111",
            borderRadius: 8,
            padding: 10,
            marginBottom: 12,
            border: "1px solid #6366F133",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ fontSize: 18 }}>phone</span>
          <div>
            <div style={{ fontSize: 10, color: "#6366F1", fontWeight: 700, letterSpacing: 1 }}>BLAND AI VOICE CALL</div>
            <div style={{ fontSize: 11, color: "#A5B4FC" }}>Calling on-call engineer for approval...</div>
          </div>
          <PulsingDot color="#6366F1" size={8} />
        </div>
      )}

      <div style={{ display: "flex", gap: 4, alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 3 }}>
          {STAGES.map((s, i) => (
            <PipelineStage
              key={s.key}
              stage={s}
              active={activeStage}
              completed={completedStages}
              incident={incident}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, unit, color, icon }) {
  const animVal = useAnimatedNumber(value);
  return (
    <div
      style={{
        background: "#0A0A16",
        borderRadius: 10,
        padding: "12px 16px",
        border: "1px solid #1A1A2E",
        flex: 1,
        minWidth: 130,
      }}
    >
      <div style={{ fontSize: 9, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 6 }}>
        {icon} {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>
          {animVal}
        </span>
        {unit && <span style={{ fontSize: 11, color: "#6A6A8A" }}>{unit}</span>}
      </div>
    </div>
  );
}

function SponsorStrip({ activeSponsor }) {
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {SPONSORS.map((s) => (
        <div
          key={s.name}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            borderRadius: 6,
            fontSize: 10,
            fontWeight: 600,
            background: activeSponsor === s.name ? s.color + "22" : "#0A0A16",
            border: `1px solid ${activeSponsor === s.name ? s.color : "#1A1A2E"}`,
            color: activeSponsor === s.name ? s.color : "#4A4A6A",
            transition: "all 0.4s ease",
            boxShadow: activeSponsor === s.name ? `0 0 12px ${s.color}33` : "none",
          }}
        >
          <span style={{ fontSize: 12 }}>{s.icon}</span>
          {s.name}
          {activeSponsor === s.name && <PulsingDot color={s.color} size={5} />}
        </div>
      ))}
    </div>
  );
}

function AgentLog({ entries }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [entries]);
  return (
    <div
      ref={ref}
      style={{
        background: "#060610",
        borderRadius: 10,
        border: "1px solid #1A1A2E",
        padding: 12,
        height: 180,
        overflowY: "auto",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      }}
    >
      {entries.map((e, i) => (
        <div key={i} style={{ marginBottom: 4, display: "flex", gap: 8, opacity: i === entries.length - 1 ? 1 : 0.6 }}>
          <span style={{ color: "#4A4A6A", minWidth: 60 }}>{e.time}</span>
          <span style={{ color: e.color || "#94A3B8" }}>{e.msg}</span>
        </div>
      ))}
      {entries.length === 0 && <div style={{ color: "#2A2A3E" }}>Waiting for incidents...</div>}
    </div>
  );
}

export default function DeepOpsDashboard() {
  const [incidents, setIncidents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState({ detected: 0, resolved: 0, avgTime: 0, llmCalls: 0 });
  const [activeSponsor, setActiveSponsor] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);
  const logRef = useRef([]);

  const addLog = useCallback((msg, color) => {
    const time = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    logRef.current = [...logRef.current, { time, msg, color }];
    setLogs([...logRef.current]);
  }, []);

  const runSimulation = useCallback(() => {
    setIsRunning(true);
    let errorIdx = 0;
    let stageProgress = {};

    const tick = () => {
      setIncidents((prev) => {
        const updated = [...prev];

        // Maybe introduce a new error
        if (errorIdx < DEMO_ERRORS.length && Math.random() > 0.4) {
          const err = DEMO_ERRORS[errorIdx];
          updated.push({ ...err, stageIdx: 0, startTime: Date.now() });
          addLog(`alert ${err.id} ${err.error}`, "#F87171");
          errorIdx++;
          setMetrics((m) => ({ ...m, detected: m.detected + 1 }));
        }

        // Advance existing incidents
        updated.forEach((inc, i) => {
          if (inc.stageIdx < STAGES.length) {
            if (Math.random() > 0.3) {
              inc.stageIdx++;
              const stage = STAGES[Math.min(inc.stageIdx, STAGES.length - 1)];
              if (stage) {
                setActiveSponsor(stage.sponsor);
                const msgs = {
                  1: `bolt ${inc.id} stored in Aerospike`,
                  2: `search ${inc.id} Macroscope analyzing codebase...`,
                  3: `ghost ${inc.id} Kiro generating spec-driven fix`,
                  4: `lock ${inc.id} Auth0 RBAC check: severity=${inc.severity}`,
                  5: inc.severity === "critical"
                    ? `mic ${inc.id} BLAND AI calling on-call engineer!`
                    : `check ${inc.id} Auto-approved for deployment`,
                  6: `rocket ${inc.id} TrueFoundry deploying fix...`,
                  7: `gear ${inc.id} Overmind trace logged. Agent improving.`,
                };
                if (msgs[inc.stageIdx]) addLog(msgs[inc.stageIdx], stage.color);
                setMetrics((m) => ({
                  ...m,
                  llmCalls: m.llmCalls + (inc.stageIdx === 2 || inc.stageIdx === 3 ? 2 : 1),
                  resolved: inc.stageIdx >= STAGES.length ? m.resolved + 1 : m.resolved,
                  avgTime: inc.stageIdx >= STAGES.length
                    ? Math.round(((m.avgTime * m.resolved + (Date.now() - inc.startTime)) / (m.resolved + 1)) / 1000)
                    : m.avgTime,
                }));
              }
            }
          }
        });

        return updated;
      });
    };

    intervalRef.current = setInterval(tick, 1800);
  }, [addLog]);

  const triggerBug = useCallback(() => {
    const err = DEMO_ERRORS[incidents.length % DEMO_ERRORS.length];
    const newInc = { ...err, id: `INC-${String(incidents.length + 1).padStart(3, "0")}`, stageIdx: 0, startTime: Date.now() };
    setIncidents((prev) => [...prev, newInc]);
    addLog(`alert ${newInc.id} ${newInc.error}`, "#F87171");
    setActiveSponsor("Airbyte");
    setMetrics((m) => ({ ...m, detected: m.detected + 1 }));
    if (!isRunning) runSimulation();
  }, [incidents, isRunning, addLog, runSimulation]);

  useEffect(() => () => clearInterval(intervalRef.current), []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#07070F",
        color: "#E2E8F0",
        fontFamily: "'Inter', -apple-system, sans-serif",
        padding: "16px 20px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@400;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0A0A16; }
        ::-webkit-scrollbar-thumb { background: #2A2A3E; border-radius: 4px; }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: -0.5 }}>
              <span style={{ color: "#6366F1" }}>Deep</span>
              <span style={{ color: "#22C55E" }}>Ops</span>
            </span>
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: 2,
                color: isRunning ? "#22C55E" : "#6A6A8A",
                background: isRunning ? "#22C55E11" : "#1A1A2E",
                padding: "3px 8px",
                borderRadius: 4,
                border: `1px solid ${isRunning ? "#22C55E33" : "#2A2A3E"}`,
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              {isRunning && <PulsingDot color="#22C55E" size={5} />}
              {isRunning ? "AGENT ACTIVE" : "STANDBY"}
            </span>
          </div>
          <div style={{ fontSize: 10, color: "#4A4A6A", marginTop: 2 }}>Self-Healing Codebase Agent | Mission Control</div>
        </div>
        <button
          onClick={triggerBug}
          style={{
            background: "linear-gradient(135deg, #DC2626, #991B1B)",
            color: "#FFF",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 12,
            fontWeight: 700,
            cursor: "pointer",
            letterSpacing: 0.5,
            display: "flex",
            alignItems: "center",
            gap: 6,
            boxShadow: "0 4px 15px rgba(220,38,38,0.3)",
            transition: "transform 0.2s",
          }}
        >
          TRIGGER BUG
        </button>
      </div>

      {/* Sponsor strip */}
      <div style={{ marginBottom: 14 }}>
        <SponsorStrip activeSponsor={activeSponsor} />
      </div>

      {/* Metrics row */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <MetricCard label="DETECTED" value={metrics.detected} icon="alert" color="#F87171" />
        <MetricCard label="RESOLVED" value={metrics.resolved} icon="check" color="#22C55E" />
        <MetricCard label="AVG RESOLVE" value={metrics.avgTime} unit="sec" icon="timer" color="#FBBF24" />
        <MetricCard label="LLM CALLS" value={metrics.llmCalls} icon="brain" color="#A855F7" />
      </div>

      {/* Main content: incidents + log */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div>
          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8 }}>
            ACTIVE INCIDENTS
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {incidents.length === 0 && (
              <div
                style={{
                  background: "#0A0A16",
                  borderRadius: 12,
                  padding: 30,
                  textAlign: "center",
                  border: "1px dashed #1A1A2E",
                  color: "#2A2A3E",
                  fontSize: 12,
                }}
              >
                Hit "TRIGGER BUG" to start the demo
              </div>
            )}
            {[...incidents].reverse().map((inc, i) => (
              <IncidentCard
                key={inc.id}
                incident={inc}
                isActive={inc.stageIdx < STAGES.length}
                stageIdx={inc.stageIdx}
              />
            ))}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8 }}>
            AGENT LOG
          </div>
          <AgentLog entries={logs} />

          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8, marginTop: 14 }}>
            PIPELINE ARCHITECTURE
          </div>
          <div
            style={{
              background: "#0A0A16",
              borderRadius: 10,
              border: "1px solid #1A1A2E",
              padding: 16,
            }}
          >
            {[
              { from: "Error", to: "Airbyte", desc: "Ingest error signals", color: "#634BFF" },
              { from: "Airbyte", to: "Aerospike", desc: "Store incident context", color: "#C4302B" },
              { from: "Aerospike", to: "Agent Core", desc: "Read pending incidents", color: "#6366F1" },
              { from: "Agent Core", to: "Macroscope", desc: "Understand codebase", color: "#00B4D8" },
              { from: "Agent Core", to: "Kiro", desc: "Plan + write fix (spec-driven)", color: "#FF9900" },
              { from: "Agent Core", to: "Auth0", desc: "RBAC severity gating", color: "#EB5424" },
              { from: "Auth0 (high)", to: "Bland AI", desc: "Voice-call engineer", color: "#6366F1" },
              { from: "Auth0 (low)", to: "TrueFoundry", desc: "Auto-deploy fix", color: "#10B981" },
              { from: "Everything", to: "Overmind", desc: "Trace + optimize all decisions", color: "#A855F7" },
            ].map((step, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 6,
                  fontSize: 10,
                  opacity: activeSponsor === step.to || !activeSponsor ? 1 : 0.4,
                  transition: "opacity 0.3s",
                }}
              >
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 4,
                    background: step.color + "22",
                    border: `1px solid ${step.color}55`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 8,
                    color: step.color,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ color: "#94A3B8", minWidth: 80, fontWeight: 600 }}>{step.from}</span>
                <span style={{ color: "#2A2A3E" }}>-></span>
                <span style={{ color: step.color, fontWeight: 600, minWidth: 80 }}>{step.to}</span>
                <span style={{ color: "#4A4A6A" }}>{step.desc}</span>
              </div>
            ))}
          </div>

          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8, marginTop: 14 }}>
            OVERMIND TRACES
          </div>
          <div style={{ background: "#0A0A16", borderRadius: 10, border: "1px solid #1A1A2E", padding: 12 }}>
            {incidents.length === 0 ? (
              <div style={{ color: "#2A2A3E", fontSize: 11 }}>No traces yet</div>
            ) : (
              incidents.slice(-3).map((inc) => (
                <div
                  key={inc.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderBottom: "1px solid #1A1A2E",
                    fontSize: 10,
                  }}
                >
                  <span style={{ color: "#A855F7", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                    {inc.id}
                  </span>
                  <div style={{ display: "flex", gap: 12 }}>
                    <span style={{ color: "#6A6A8A" }}>
                      LLM: <span style={{ color: "#FBBF24" }}>{Math.floor(Math.random() * 800 + 200)}ms</span>
                    </span>
                    <span style={{ color: "#6A6A8A" }}>
                      Tokens: <span style={{ color: "#A855F7" }}>{Math.floor(Math.random() * 2000 + 500)}</span>
                    </span>
                    <span style={{ color: "#6A6A8A" }}>
                      Cost: <span style={{ color: "#10B981" }}>${(Math.random() * 0.05 + 0.01).toFixed(3)}</span>
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

### Key Design Patterns from the Existing Component

- **Layout:** Two-column grid. Left column = incident cards (stacked vertically). Right column = agent log + pipeline architecture diagram + Overmind traces.
- **Header:** Logo ("Deep" in indigo, "Ops" in green) + agent status badge + "TRIGGER BUG" button.
- **Sponsor strip:** Horizontal row of all 8 sponsors; the active one glows with its brand color.
- **Metrics row:** 4 metric cards (detected count, resolved count, avg resolve time, LLM calls) with animated number transitions.
- **Incident cards:** Each card shows ID, severity badge, error message, file path, and a horizontal pipeline of 8 stage indicators. Root cause and proposed fix sections appear progressively as the incident advances through stages. A phone call indicator appears for critical severity during the escalation stage.
- **Agent log:** Terminal-style scrolling log with timestamps and color-coded messages per sponsor.
- **Pipeline architecture:** A numbered list showing the data flow between components.
- **Overmind traces:** A small table showing LLM latency, token count, and cost per incident.

---

## 7. Sponsor Integrations

All 8 sponsors have genuine roles in the pipeline. Each has a brand color and icon used throughout the UI:

| # | Sponsor | Icon | Brand Color | Role in Pipeline | Integration Point |
|---|---------|------|-------------|------------------|-------------------|
| 1 | **Airbyte** | Sync arrows | `#634BFF` | **Ingest** -- ingests error signals from the demo app | Source connector polling `/errors` endpoint |
| 2 | **Aerospike** | Lightning bolt | `#C4302B` | **Store** -- persists incidents, agent memory, codebase graph | Key-value store for incident records |
| 3 | **Macroscope** | Magnifying glass | `#00B4D8` | **Understand** -- analyzes codebase to enable root cause diagnosis | GitHub app + API for codebase Q&A |
| 4 | **Kiro** | Ghost | `#FF9900` | **Fix** -- plans and writes code fixes using spec-driven development | CLI invoked by agent to generate patches |
| 5 | **Auth0** | Lock | `#EB5424` | **Gate** -- RBAC severity gating (auto-deploy vs human approval) | Middleware on the deploy decision |
| 6 | **Bland AI** | Microphone | `#6366F1` | **Escalate** -- voice-calls on-call engineer for high/critical issues | REST API to initiate phone calls |
| 7 | **TrueFoundry** | Rocket | `#10B981` | **Deploy** -- deploys the verified fix to production | SDK/CLI for deployment |
| 8 | **Overmind** | Gear | `#A855F7` | **Optimize** -- traces every LLM call and agent decision | Python SDK, auto-instruments LLM calls |

---

## 8. Demo Flow

### The 3 Demo Bugs

**Bug 1: Division by Zero (Medium Severity -- AUTO-DEPLOY)**
- Trigger: `curl http://demo-app/calculate/0`
- Error: `ZeroDivisionError: division by zero`
- File: `demo-app/main.py:14`
- Root cause: Missing input validation on division endpoint. Value 0 causes unhandled ZeroDivisionError.
- Fix: Add guard clause: `if value == 0: return {'error': 'Cannot divide by zero'}`
- Flow: detected -> stored -> diagnosing -> fixing -> gating -> **auto-approved** -> deploying -> resolved
- No phone call. Auth0 RBAC auto-approves medium severity.

**Bug 2: Null Reference (High Severity -- BLAND AI APPROVAL)**
- Trigger: `curl http://demo-app/user/unknown`
- Error: `KeyError: 'name'` (accessing non-existent user)
- File: `demo-app/main.py:21`
- Root cause: `users.get()` returns None, then `['name']` fails.
- Fix: Add null check: `if not user: raise HTTPException(404, 'User not found')`
- Flow: detected -> stored -> diagnosing -> fixing -> gating -> **awaiting_approval** (Bland AI calls engineer) -> deploying -> resolved
- Phone rings. Engineer says "yes" -> fix deploys.

**Bug 3: Timeout / Event Loop Blocking (Critical Severity -- BLAND AI APPROVAL)**
- Trigger: `curl http://demo-app/search`
- Error: `TimeoutError` (blocking `time.sleep(5)` in async handler)
- File: `demo-app/main.py:26`
- Root cause: Blocking sleep in async handler causes cascading timeouts under load.
- Fix: Replace `time.sleep` with `await asyncio.sleep` or remove artificial delay.
- Flow: detected -> stored -> diagnosing -> fixing -> gating -> **awaiting_approval** (Bland AI calls engineer) -> deploying -> resolved
- Phone rings. This is the "wow" moment for the demo audience.

### Demo Script Timeline (3 minutes)

```
[0:00 - 0:30] HOOK
  "Bugs don't wait for office hours. What if your codebase could heal itself?"
  Show the dashboard: clean, all green.

[0:30 - 0:50] TRIGGER THE BUG
  Hit: curl http://demo-app/calculate/0
  Dashboard immediately shows: NEW INCIDENT DETECTED (red)
  "Airbyte just ingested that error. Aerospike stored the context."

[0:50 - 1:20] AGENT DIAGNOSES
  Dashboard updates: DIAGNOSING...
  "Macroscope analyzed the codebase and found this function lacks input validation."

[1:20 - 1:50] AGENT FIXES
  Dashboard updates: GENERATING FIX...
  "Kiro planned and wrote the fix using spec-driven development."
  Show the proposed diff on screen.

[1:50 - 2:20] SEVERITY ROUTING
  "This is a low-severity bug. Auth0's RBAC says: auto-deploy."
  Dashboard shows: DEPLOYING VIA TRUEFOUNDRY
  "But watch what happens with a critical bug..."
  Trigger a "critical" bug:
  YOUR PHONE RINGS. Bland AI is calling.
  Answer on speakerphone: "Hi, this is DeepOps..."
  Say "yes, deploy it"
  Dashboard updates: FIX APPROVED > DEPLOYING > RESOLVED

[2:20 - 2:45] SHOW THE LOOP
  "Every decision was traced by Overmind."
  Flash the Overmind dashboard: traces, latency, tokens

[2:45 - 3:00] CLOSE
  "DeepOps uses ALL 8 sponsor tools in a genuine pipeline."
```

---

## 9. Design Constraints

- **Stack:** React + Tailwind CSS (or inline styles as shown in the existing component)
- **Theme:** Dark theme only. The existing dashboard uses very dark backgrounds (`#07070F`, `#0A0A16`, `#0F0F1E`).
- **Real-time feel:** The dashboard polls the backend every few seconds (the simulation ticks every 1800ms). Incidents should visually progress through stages with smooth transitions.
- **Must show:**
  - Incident list (stacked cards, newest on top)
  - Status pipeline (8-stage horizontal progress indicator per incident)
  - Diagnosis details (root cause text, confidence score)
  - Fix preview (code diff, files changed)
  - Deployment status (running/succeeded/failed)
  - Metrics summary (detected, resolved, avg time, LLM calls)
  - Agent activity log (terminal-style scrolling text)
  - Sponsor strip (which tool is currently active)
  - Overmind trace data (LLM latency, tokens, cost)
- **The "wow" moment:** Seeing an incident flow through all 8 stages automatically, with visual progression and the sponsor strip lighting up for each stage.
- **Phone call indicator:** For high/critical severity incidents, a prominent visual indicator must appear when Bland AI is making a voice call. This should be animated/pulsing to draw attention. The existing component shows a purple-tinted card with "BLAND AI VOICE CALL" text and a pulsing dot.
- **Fonts:**
  - Headers/branding: `Space Grotesk` (sans-serif, geometric)
  - Body text: `Inter` (sans-serif, readable)
  - Code/monospace: `JetBrains Mono` (monospace, for error messages, diffs, IDs)
- **Animations:**
  - PulsingDot: A dot that pulses opacity and has a "ping" ring that expands and fades
  - Animated numbers: Metric values animate smoothly when they change
  - Stage transitions: opacity and scale changes with 0.4-0.5s ease timing
- **Responsive:** The existing component uses a 2-column grid layout that could wrap on smaller screens.
- **"TRIGGER BUG" button:** A red gradient button in the header that the presenter clicks during the demo to inject errors.

---

## 10. Color Palette

### Background Colors (darkest to lightest)

| Token | Hex | Usage |
|---|---|---|
| bg-deepest | `#060610` | Agent log background |
| bg-base | `#07070F` | Page background |
| bg-card | `#0A0A16` | Card backgrounds, metric cards, sponsor strip inactive |
| bg-card-inner | `#0D0D1A` | Inner content blocks (root cause box, fix box) |
| bg-card-active | `#0F0F1E` | Active incident card background |
| bg-muted | `#1A1A2E` | Borders, inactive elements |
| bg-subtle | `#2A2A3E` | Scrollbar thumb, inactive stage borders |

### Text Colors

| Token | Hex | Usage |
|---|---|---|
| text-primary | `#E2E8F0` | Main text, incident IDs |
| text-secondary | `#CBD5E1` | Root cause text, fix text |
| text-muted | `#94A3B8` | Error messages, pipeline "from" labels |
| text-dim | `#64748B` | File paths |
| text-ghost | `#6A6A8A` | Labels, metric labels, trace labels |
| text-faint | `#4A4A6A` | Inactive sponsor names, pipeline descriptions, subtitle |
| text-invisible | `#2A2A3E` | Placeholder text, empty state text |

### Sponsor Brand Colors

| Sponsor | Hex | Usage |
|---|---|---|
| Airbyte | `#634BFF` | Ingest stage, pipeline step 1 |
| Aerospike | `#C4302B` | Store stage, pipeline step 2 |
| Macroscope | `#00B4D8` | Diagnose stage, root cause label |
| Kiro | `#FF9900` | Fix stage, proposed fix label |
| Auth0 | `#EB5424` | Gate stage |
| Bland AI | `#6366F1` | Escalate stage, voice call indicator, also used for "Deep" in logo and active card glow |
| TrueFoundry | `#10B981` | Deploy stage |
| Overmind | `#A855F7` | Optimize stage, trace data |

### Stage Colors (pipeline indicator)

| Stage | Hex |
|---|---|
| detected | `#F87171` (red-400) |
| stored | `#C4302B` (Aerospike red) |
| diagnosing | `#00B4D8` (Macroscope cyan) |
| fixing | `#FF9900` (Kiro orange) |
| gating | `#EB5424` (Auth0 orange-red) |
| escalated/calling | `#6366F1` (Bland AI indigo) |
| deploying | `#10B981` (TrueFoundry emerald) |
| resolved | `#22C55E` (green-500) |

### Severity Badge Colors

| Severity | Background | Text | Border |
|---|---|---|---|
| low | `#064E3B` | `#6EE7B7` | `#065F46` |
| medium | `#78350F` | `#FDE68A` | `#92400E` |
| high | `#7C2D12` | `#FDBA74` | `#9A3412` |
| critical | `#7F1D1D` | `#FCA5A5` | `#991B1B` |

### Accent Colors

| Usage | Hex |
|---|---|
| Logo "Deep" | `#6366F1` (indigo-500) |
| Logo "Ops" | `#22C55E` (green-500) |
| Agent Active indicator | `#22C55E` |
| Trigger Bug button gradient | `#DC2626` to `#991B1B` |
| Avg Resolve metric | `#FBBF24` (amber-400) |
| Completed stage checkmark | `#22C55E` |

---

## 11. Agent Intelligence Details (for context)

### Diagnosis Prompt Structure

The agent uses structured prompts to produce JSON diagnoses. The system prompt instructs the LLM to output exactly 5 fields:

```
root_cause          -- one sentence citing the specific file/route
suggested_fix       -- one sentence describing the minimal code change
affected_components -- array of files/routes affected
confidence          -- number 0-1
severity_reasoning  -- one sentence explaining the severity choice
```

The user prompt includes:
- Service name and environment
- Route/path that triggered the error
- Error type and message
- Source file
- Codebase context from Macroscope

### Diagnosis Prompt Templates (actual code)

**System prompt:**

```
You are a senior backend engineer performing root-cause analysis on a
production incident. You will receive an error report and codebase context.

Your job is to produce a single JSON object with exactly these fields:

  root_cause        (string)  -- one sentence identifying the concrete
                                 programming error, citing the file and line
                                 or route where it occurs.
  suggested_fix     (string)  -- one sentence describing the minimal code
                                 change that eliminates the defect.
  affected_components (array of strings) -- files and/or routes that are
                                 affected.  Must include the source file.
  confidence        (number 0-1) -- your confidence in this diagnosis.
                                 0.90+ for clear stack traces, 0.60-0.80
                                 for ambiguous evidence.
  severity_reasoning (string) -- one sentence explaining why you chose the
                                 implied severity, referencing observable
                                 impact (blast radius, data loss, user-facing
                                 error, latency).

Rules:
- Do NOT wrap the JSON in markdown fences or add any text outside the JSON.
- Do NOT include any fields other than the five listed above.
- root_cause must cite the specific file or route.
- suggested_fix must address the actual root cause, not mask the symptom.
- Output ONLY valid JSON.
```

**User prompt template:**

```
## Incident

- Service:       {service}
- Environment:   {environment}
- Route/Path:    {path}
- Error type:    {error_type}
- Error message: {error_message}
- Source file:   {source_file}

## Codebase Context (from Macroscope)

{macroscope_context}

## Instructions

Produce a JSON diagnosis object with the five required fields.
```

### Macroscope Integration

The Macroscope client queries a codebase understanding API. For the demo, it has fallback fixtures for the 3 known demo bugs:

1. **calculate_zero_division** -- explains the `/calculate` endpoint, its lack of validation, and that it has no downstream writes
2. **user_key_error** -- explains the `/user/{username}` endpoint, the None result from `.get()`, and the subsequent `['name']` access
3. **search_timeout** -- explains the blocking `time.sleep(5)` in the async handler and its cascading effect

These fixtures ensure the demo works reliably even if the Macroscope API is unavailable. The client has retry logic (2 retries with exponential backoff) and falls back to fixtures when all retries are exhausted.

---

## End of Context

This document contains everything needed to design the DeepOps dashboard:
- The full project concept and architecture
- The complete data schema and example data
- The existing React dashboard component (full source code)
- All colors, fonts, animations, and layout patterns
- The demo flow and what the audience sees
- All 8 sponsor integrations with their visual identity
- The agent's diagnosis pipeline and prompt structure

Design a dashboard that makes the self-healing loop feel magical -- incidents appear, flow through stages with sponsor-colored animations, and resolve themselves while the audience watches.
