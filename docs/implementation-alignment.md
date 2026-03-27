# DeepOps Implementation Alignment

This is the canonical build contract for the hackathon build. It is distilled from:

- `README.md`
- `docs/deepops-guide.md`
- `docs/deepops-dashboard.jsx`
- `docs/deepops-architecture.svg`

The existing docs are strong on the concept and demo story. The missing piece was a stricter shared runtime contract so two people can work in parallel without guessing at status names, payload shape, or who owns which fields.

## What We Are Freezing

1. Aerospike is still the only shared runtime boundary between Person A and Person B.
2. The dashboard reads the same incident record the agent writes. No second view model unless we need one later.
3. We will use one canonical incident object with nested sections instead of a flat record.
4. We will append timeline events and patch owned fields. We will not replace the full incident record on each update.
5. Top-level `status` is the pipeline stage. Approval and deployment get their own nested status fields.

## Canonical Lifecycle

| Status | Owner | Meaning | Required write before leaving stage |
|---|---|---|---|
| `detected` | Person B | Error exists in raw source stream | `source.*`, `incident_id`, `created_at_ms` |
| `stored` | Person B | Incident normalized and written to Aerospike | `updated_at_ms`, first `timeline` event |
| `diagnosing` | Person A | Agent is querying Macroscope and reasoning | `diagnosis.status=running` |
| `fixing` | Person A | Agent is generating a fix spec and diff | `diagnosis.*`, `fix.status=running` |
| `gating` | Person A | Severity is finalized and routing decision is ready | `severity`, `fix.*`, `approval.required` |
| `awaiting_approval` | Person B | Manual approval path via Bland AI is in progress | `approval.mode=manual`, `approval.channel=voice_call` |
| `deploying` | Person B | Fix is approved and deployment started | `approval.status=approved`, `deployment.status=running` |
| `resolved` | Person B | Fix deployed successfully | `deployment.*`, `resolution_time_ms` |
| `blocked` | Person B | Human rejected or deferred deploy | `approval.status=rejected` or note in `timeline` |
| `failed` | Either | Something in diagnosis, fix, or deploy failed | `timeline` event with failure reason |

## Severity Rules For The Demo

Use fixed mappings for the three planned demo bugs so the demo is predictable:

| Trigger | Error | Severity | Approval path |
|---|---|---|---|
| `/calculate/0` | divide by zero | `medium` | auto-deploy |
| `/user/unknown` | null or key access on missing user | `high` | Bland AI approval |
| `/search` | timeout or blocking sleep | `critical` | Bland AI approval |

This gives one clean auto path and one escalation path during the demo.

## Canonical Incident Record

The runtime contract lives in [docs/incident.schema.json](C:/Users/ayush/Desktop/Hackathons/Deep%20Agents%20Hackathon%20March%2027/docs/incident.schema.json).

High-level shape:

- `source`: normalized raw error from demo app or Airbyte
- `diagnosis`: Macroscope and LLM output
- `fix`: Kiro spec, diff, files changed, test plan
- `approval`: Auth0 decision plus Bland AI escalation metadata when needed
- `deployment`: TrueFoundry deploy state
- `observability`: Overmind trace ids and external linkage
- `timeline`: append-only status history for the dashboard and debugging

## Mutation Rules

Person B owns these writes:

- incident creation from demo app or Airbyte
- `source`
- `approval`
- `deployment`
- dashboard polling API
- Bland webhook handling
- final `resolved` or `blocked` state

Person A owns these writes:

- `diagnosis`
- `fix`
- `severity`
- transition into `diagnosing`, `fixing`, and `gating`
- Overmind trace metadata from the agent side

Shared rules:

- Both sides may append `timeline` events.
- Both sides may update `updated_at_ms`.
- No one should overwrite sections owned by the other side.
- Aerospike writes should behave like partial patch operations, not full document replacement.

## Minimal Functions Both Sides Should Agree On

These are the only shared store operations both sides should code against:

```python
def create_incident(incident: dict) -> None: ...
def get_incident(incident_id: str) -> dict: ...
def list_incidents(limit: int = 50) -> list[dict]: ...
def patch_incident(incident_id: str, patch: dict) -> None: ...
def append_timeline_event(incident_id: str, event: dict) -> None: ...
```

If Person B ships these first, Person A can build the agent loop without waiting on any other infra.

## Dashboard Contract

The dashboard should poll one backend endpoint:

```http
GET /api/incidents
```

Response:

```json
{
  "incidents": [IncidentRecord]
}
```

The dashboard derives UI directly from:

- `status`
- `severity`
- `source.error_message`
- `source.source_file`
- `diagnosis.root_cause`
- `fix.diff_preview`
- `approval.status`
- `deployment.status`
- `observability.overmind_trace_id`
- `timeline`

There is no need for a second dashboard-only schema.

## Integration Sequence

1. Freeze the schema and example record in this repo.
2. Person B builds `create_incident`, `patch_incident`, and `list_incidents` against Aerospike.
3. Person B builds the dashboard using `docs/incident-example.json` as mocked data before the backend is ready.
4. Person A builds the orchestrator against one incident already stored in Aerospike.
5. Person A wires `diagnosis`, `fix`, and severity classification.
6. Person B wires Auth0 gating, Bland webhook, and deployment updates.
7. Run the full pipeline with the three known demo bugs.
8. Record a backup video once the loop works end to end.

## Folder Ownership

Recommended project layout once implementation starts:

```text
deepops/
  agent/                  # Person A
    orchestrator.py
    detector.py
    diagnoser.py
    fixer.py
    severity.py
  infra/                  # Person B
    aerospike_store.py
    airbyte_pipeline.py
    auth_gate.py
    bland_caller.py
    truefoundry_deploy.py
  demo-app/               # Person B
    main.py
  dashboard/              # Person B
    app/ or src/
  docs/                   # Shared source of truth
```

## Sync Points

Do these syncs even if you are moving fast:

1. Before coding: both agree the schema file is the source of truth.
2. After Aerospike write works: Person A reads a real incident produced by Person B.
3. After diagnosis and fix generation work: dashboard renders those fields without custom transforms.
4. Before demo rehearsal: verify one medium incident auto-deploys and one high or critical incident triggers a call.

## Definition Of Done

- A new demo-app error becomes a valid incident record in Aerospike.
- The agent can move an incident from `stored` to `gating`.
- Low and medium incidents route straight to `deploying`.
- High and critical incidents route to `awaiting_approval`.
- Bland webhook can move a manual approval incident to `deploying` or `blocked`.
- Dashboard shows status, root cause, fix preview, and trace metadata from the same record.
- One full end-to-end incident reaches `resolved` on camera.

## Important Gap From The Original Docs

The original guide used different stage names in different places:

- the flat Aerospike schema used `escalated`
- the dashboard used `stored` and `gating`
- the deployment path implied approval state but did not model it explicitly

This alignment doc resolves that by separating:

- top-level pipeline `status`
- nested `approval.status`
- nested `deployment.status`

That separation is what will keep the two workstreams aligned.
