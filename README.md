# DeepOps: The Self-Healing Codebase Agent

DeepOps is a hackathon project for a live incident-response workflow:

1. ingest production issues
2. persist a canonical incident record
3. diagnose likely root cause
4. generate a fix
5. gate deployment through policy and human approval
6. escalate by phone when the blast radius is too high
7. deploy and track the result
8. trace the full loop for optimization

The current repo now contains a real FastAPI backend, Aerospike-backed incident storage, sponsor integration wrappers, approval and escalation flows, and the shared incident schema used across backend and frontend work.

![Architecture](docs/deepops-architecture.svg)

## System Overview

Core pipeline:

`ingest -> stored -> diagnosing -> fixing -> gating -> deploying -> resolved`

Primary integrations:

- `Airbyte`: issue ingestion trigger path
- `Aerospike`: incident persistence
- `Macroscope`: diagnosis path
- `Kiro`: fix generation path
- `Auth0`: approval and approval-context routing
- `Bland`: phone escalation for high-risk incidents
- `TrueFoundry`: deployment target
- `Overmind` and `Overclaw`: tracing and optimization

## Repo Layout

- `agent/`: shared contracts, orchestrator, tracing, detector, severity, diagnosis/fix runtime
- `agents/`: Overclaw-facing agent entrypoints
- `server/`: FastAPI backend, API routes, services, sponsor integration wrappers, tests
- `infra/aerospike/`: local Aerospike config and Docker compose
- `docs/`: architecture, guide, schema, alignment docs, task packs
- `data/`: datasets and fixtures used by agent optimization work
- `tests/`: agent-side tests

Important docs:

- `docs/implementation-alignment.md`
- `docs/incident.schema.json`
- `docs/incident-example.json`
- `docs/ayush/person-a-policy.md`
- `docs/ayush/remaining-work-instructions.md`

## Backend API

The FastAPI backend entrypoint is:

- `server/main.py`

Main routes:

- `GET /api/health`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `POST /api/incidents`
- `POST /api/ingest/demo-app`
- `POST /api/ingest/airbyte-sync`
- `GET /api/incidents/stream`
- `POST /api/agent/run-once`
- `POST /api/approval/{incident_id}/decision`
- `POST /api/webhooks/bland`
- `POST /api/webhooks/truefoundry`

## Local Setup

### 1. Python

Use Python 3.14+ in the current workspace environment.

Install the required runtime packages as needed:

```powershell
python -m pip install fastapi uvicorn pytest aerospike
```

### 2. Environment

Create a local `.env` file. The repo already ignores it.

Minimum useful keys for the full live demo path:

```env
OPENAI_API_KEY=
OVERMIND_API_KEY=
TRUEFOUNDRY_API_KEY=
BLAND_API_KEY=
BLAND_PHONE_NUMBER=
BLAND_WEBHOOK_URL=
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_REDIRECT_URI=
AUTH0_MANAGEMENT_AUDIENCE=
AEROSPIKE_HOST=127.0.0.1
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=deepops
AEROSPIKE_SET=incidents
DEEPOPS_ALLOW_IN_MEMORY_STORE=false
```

Optional depending on how live you want the demo:

```env
AUTH0_ORGANIZATION_ID=
AUTH0_APPROVAL_CONNECTION=
AIRBYTE_API_URL=
AIRBYTE_API_KEY=
DEEPOPS_DEMO_APP_BASE_URL=
MACROSCOPE_API_KEY=
ANTHROPIC_API_KEY=
```

### 3. Aerospike

The repo includes a real local Aerospike setup under `infra/aerospike/`.

Start it with:

```powershell
docker compose -f infra/aerospike/docker-compose.yml up -d
```

This config brings up:

- host `127.0.0.1`
- port `3000`
- namespace `deepops`
- set `incidents`

### 4. Run the backend

```powershell
uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/api/health
```

## Testing

Run the full current suite with:

```powershell
python -m pytest -q tests server/tests
```

## Overclaw

The repo includes an Overclaw workspace and registered agent config under `.overclaw/`.

Useful commands:

```powershell
overclaw agent list
overclaw setup deepops-person-a --fast --policy docs/ayush/person-a-policy.md
overclaw optimize deepops-person-a
```

`overclaw setup` and `optimize` require a valid model API key in the environment.

## Current Demo Shape

The demo is designed around three flows:

1. autonomous self-healing
2. human approval and guided replan
3. phone escalation for high-risk incidents

The strongest backend path is already in the repo. The remaining work is mostly final integration hardening, frontend wiring, and live sponsor rehearsal.
