# DeepOps: The Self-Healing Codebase Agent
## Deep Agents Hackathon Build Guide | March 27, 2026

**One-liner:** An autonomous agent that monitors a live app, detects errors in real-time, understands the codebase to diagnose root cause, plans and writes a fix, deploys it, and calls the on-call engineer only when human approval is needed.

**Submission deadline:** 4:30 PM on Devpost (https://bit.ly/devpost-mar27)
**Demo:** 3 minutes max
**Team size:** 2 full stack devs

---

## JUDGING CRITERIA (from the slides)

| Criterion | What judges want | How we nail it |
|-----------|-----------------|----------------|
| **Autonomy** | Agent acts on real-time data without manual intervention | Full detect > diagnose > fix > deploy loop with zero human touch for low-severity |
| **Idea** | Solves a meaningful problem or demonstrates real-world value | "What if every bug fixed itself?" Universal pain point |
| **Technical Implementation** | How well was the solution implemented | LLM orchestration + 8 genuine sponsor integrations |
| **Tool Use** | Effectively use at least 3 sponsor tools | We use ALL 8 with genuine, non-forced roles |
| **Presentation (Demo)** | 3-minute live demonstration | Live phone call from the agent is the "wow" moment |

---

## ARCHITECTURE OVERVIEW

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

---

## TEAM SPLIT: PERSON A vs PERSON B

### Design Principle: Minimal Dependencies

The two workstreams share exactly ONE interface: the **Aerospike state store**. Both sides read/write incident records using a shared schema. This means Person A and Person B can work in parallel for most of the day.

### Shared Contract: Aerospike Incident Schema

```python
# Both Person A and Person B agree on this structure upfront (5 min)
INCIDENT_SCHEMA = {
    "namespace": "deepops",
    "set": "incidents",
    "bins": {
        "incident_id": str,          # UUID
        "timestamp": int,            # epoch ms
        "error_type": str,           # e.g. "500_internal", "timeout", "null_ref"
        "error_message": str,        # raw error string
        "severity": str,             # "low", "medium", "high", "critical"
        "status": str,               # "detected", "diagnosing", "fixing", "deploying", "resolved", "escalated"
        "source_file": str,          # file where bug was found
        "root_cause": str,           # LLM diagnosis
        "proposed_fix": str,         # code diff
        "fix_approved": bool,        # True if auto or human approved
        "deployed": bool,            # True once deployed
        "bland_call_id": str,        # Bland AI call ID if escalated
        "overmind_trace_id": str,    # Overmind trace for this run
        "resolution_time_ms": int,   # total time from detection to resolution
    }
}
```

---

## PERSON A: Agent Core + Intelligence Layer

**Owns:** Agent orchestration loop, Macroscope integration, Kiro integration, Overmind tracing, LLM reasoning
**Stack:** Python (FastAPI for internal APIs), LLM calls (Claude/GPT via AWS Bedrock or direct API)

### Phase 1: Scaffold Agent Core (10:30 - 11:30)

#### 1A. Set up the project structure

```
deepops/
  agent/
    __init__.py
    orchestrator.py      # Main agent loop
    detector.py          # Reads from Aerospike, classifies errors
    diagnoser.py         # Uses Macroscope + LLM to find root cause
    fixer.py             # Uses Kiro to plan/write the fix
    severity.py          # Determines severity level
  config.py              # API keys, Aerospike config
  requirements.txt
```

#### 1B. Install dependencies

```bash
pip install aerospike anthropic overmind requests fastapi uvicorn
```

#### 1C. Initialize Overmind tracing (wrap everything from the start)

```python
# config.py
import overmind

overmind.init(
    overmind_api_key="ovr_...",  # Get from Overmind booth
    service_name="deepops-agent",
    environment="hackathon"
)

# Get tracer for custom spans
tracer = overmind.get_tracer()
```

**WHY THIS MATTERS:** Overmind auto-instruments all LLM calls. Every Claude/GPT call your agent makes is automatically traced. You get a dashboard showing latency, token usage, and decision quality for free. The judges from Overmind (Tyler Edwards, Akhat Rakishev) will see their tool being used meaningfully.

#### 1D. Set up Aerospike connection

```python
# config.py
import aerospike

aero_config = {
    'hosts': [('127.0.0.1', 3000)],  # Or use Aerospike cloud endpoint from booth
    'policies': {'read': {'total_timeout': 1000}}
}
aero_client = aerospike.client(aero_config)
```

**Talk to the Aerospike booth** (Harin Avvari, Lucas Beeler, Jagrut Nemade) early to get:
- A cloud instance or Docker container credentials
- Best practices for key-value patterns they want to see

### Phase 2: Build the Agent Loop (11:30 - 1:30)

#### 2A. The Orchestrator (core agent loop)

```python
# agent/orchestrator.py
import time
from config import tracer, aero_client
from agent.detector import detect_new_errors
from agent.diagnoser import diagnose_error
from agent.fixer import generate_fix
from agent.severity import classify_severity

async def agent_loop():
    """Main autonomous loop. Runs continuously."""
    while True:
        with tracer.start_as_current_span("agent-cycle") as span:
            # Step 1: Check for new errors
            errors = detect_new_errors()
            
            for error in errors:
                span.set_attribute("error_type", error["error_type"])
                
                # Step 2: Diagnose with Macroscope + LLM
                diagnosis = await diagnose_error(error)
                
                # Step 3: Classify severity
                severity = classify_severity(diagnosis)
                
                # Step 4: Generate fix with Kiro
                fix = await generate_fix(diagnosis)
                
                # Step 5: Write decision to Aerospike
                update_incident(error["incident_id"], {
                    "status": "fixing",
                    "root_cause": diagnosis["root_cause"],
                    "proposed_fix": fix["diff"],
                    "severity": severity
                })
                
                # Step 6: Route based on severity (Person B handles execution)
                if severity in ["low", "medium"]:
                    update_incident(error["incident_id"], {
                        "fix_approved": True,
                        "status": "deploying"
                    })
                else:
                    update_incident(error["incident_id"], {
                        "status": "escalated"
                    })
        
        time.sleep(5)  # Poll every 5 seconds for demo
```

#### 2B. The Diagnoser (Macroscope integration)

**How Macroscope works for us:** Macroscope connects to your GitHub repo and builds an AST-based understanding graph. For the hackathon, we connect it to our demo app's repo, and the agent queries Macroscope's API to understand code relationships.

```python
# agent/diagnoser.py
import requests
from anthropic import Anthropic
from config import tracer

MACROSCOPE_API_KEY = "..."  # Get from Macroscope booth (Ikshita Puri, Zhuolun Li)
MACROSCOPE_BASE_URL = "https://api.macroscope.com/v1"

async def diagnose_error(error: dict) -> dict:
    with tracer.start_as_current_span("diagnose") as span:
        # Query Macroscope for codebase context around the error
        # Macroscope provides natural language Q&A about your codebase
        macroscope_context = query_macroscope(
            f"What does the function in {error['source_file']} do? "
            f"What are its dependencies and callers?"
        )
        
        # Use LLM to reason about root cause with codebase context
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""You are a senior engineer diagnosing a production error.

ERROR: {error['error_message']}
FILE: {error['source_file']}

CODEBASE CONTEXT FROM MACROSCOPE:
{macroscope_context}

Provide:
1. Root cause (1-2 sentences)
2. Affected components
3. Suggested fix approach
4. Severity assessment (low/medium/high/critical)

Respond in JSON."""
            }]
        )
        
        span.set_attribute("diagnosis_tokens", response.usage.input_tokens + response.usage.output_tokens)
        return parse_diagnosis(response.content[0].text)

def query_macroscope(question: str) -> str:
    """Query Macroscope's codebase understanding API."""
    # Macroscope offers Slack integration and API
    # For hackathon: use their GitHub app + API endpoint
    resp = requests.post(
        f"{MACROSCOPE_BASE_URL}/ask",
        headers={"Authorization": f"Bearer {MACROSCOPE_API_KEY}"},
        json={"question": question, "repo": "your-org/demo-app"}
    )
    return resp.json().get("answer", "No context available")
```

**TALK TO MACROSCOPE BOOTH EARLY** (Rob Bishop is a co-founder and judge): Ask for API access and what integration pattern they recommend for hackathons.

#### 2C. The Fixer (Kiro integration)

**How Kiro works for us:** Kiro is an IDE/CLI that does spec-driven development. Our agent uses Kiro CLI to plan a fix from a spec, then generates the code change.

```python
# agent/fixer.py
import subprocess
import json
from config import tracer

async def generate_fix(diagnosis: dict) -> dict:
    with tracer.start_as_current_span("generate-fix") as span:
        # Option A: Use Kiro CLI to generate a spec-driven fix
        # Kiro CLI can be invoked programmatically
        spec = create_fix_spec(diagnosis)
        
        # Write spec to file for Kiro to process
        with open("/tmp/fix-spec.md", "w") as f:
            f.write(spec)
        
        # Invoke Kiro CLI (spec-driven mode)
        result = subprocess.run(
            ["kiro", "implement", "--spec", "/tmp/fix-spec.md", "--repo", "./demo-app"],
            capture_output=True, text=True, timeout=60
        )
        
        # Option B: If CLI isn't available, use Kiro IDE API or
        # simulate spec-driven development by generating fix code via LLM
        # with Kiro's spec-driven methodology (requirements > design > implementation)
        
        fix_diff = result.stdout
        span.set_attribute("fix_lines_changed", fix_diff.count('\n'))
        
        return {
            "diff": fix_diff,
            "files_changed": extract_files_from_diff(fix_diff),
            "spec": spec
        }

def create_fix_spec(diagnosis: dict) -> str:
    """Create a Kiro-style spec for the fix."""
    return f"""# Fix Specification

## Requirements
- Fix the {diagnosis['error_type']} error in {diagnosis['source_file']}
- Root cause: {diagnosis['root_cause']}

## Acceptance Criteria
- The error no longer occurs when the triggering condition is met
- Existing tests continue to pass
- No regressions in dependent modules: {', '.join(diagnosis.get('affected_components', []))}

## Implementation Approach
{diagnosis['suggested_fix']}
"""
```

**IMPORTANT:** Download Kiro from kiro.dev before the hackathon. It's a VS Code fork. The CLI tool (`kiro`) is what we invoke programmatically. If CLI access is limited, you can demonstrate Kiro's spec-driven approach by showing the spec generation + code fix pipeline.

### Phase 3: Polish Agent Intelligence (1:30 - 2:30)

#### 3A. Connect Overmind's optimization loop

```python
# After several agent cycles, Overmind has traces
# Use Overmind's dashboard to show:
# 1. Every LLM call traced with latency + tokens
# 2. Agent decision patterns (which errors it fixes correctly)
# 3. Cost analysis per fix

# The Overmind Python client auto-instruments all LLM providers:
# - anthropic (Claude calls)
# - openai (if used)
# - google-genai (if used)
# No additional code needed beyond overmind.init()

# For the demo: show the Overmind dashboard with real traces
# Tyler Edwards (CEO) and Akhat Rakishev (CTO) are both judges
```

#### 3B. Enhance severity classification

```python
# agent/severity.py
def classify_severity(diagnosis: dict) -> str:
    """Classify based on impact analysis."""
    rules = {
        "critical": ["data loss", "security", "auth bypass", "payment"],
        "high": ["500 error", "service down", "timeout cascade"],
        "medium": ["degraded performance", "non-critical path"],
        "low": ["cosmetic", "logging", "non-user-facing"]
    }
    
    root_cause_lower = diagnosis["root_cause"].lower()
    for severity, keywords in rules.items():
        if any(kw in root_cause_lower for kw in keywords):
            return severity
    return "medium"  # Default
```

---

## PERSON B: Infra, Actions, Dashboard & Voice

**Owns:** Demo app (with intentional bugs), Airbyte pipeline, Aerospike setup, Auth0 auth, Bland AI voice calls, TrueFoundry deployment, dashboard UI
**Stack:** Python (FastAPI) + Next.js/React (dashboard) + Docker

### Phase 1: Scaffold Infrastructure (10:30 - 11:30)

#### 1A. The Demo App (deliberately buggy)

Create a simple FastAPI service with bugs that can be triggered on demand:

```python
# demo-app/main.py
from fastapi import FastAPI, HTTPException
import logging
import json
import time

app = FastAPI(title="DeepOps Demo App")

# Bug 1: Division by zero on specific input
@app.get("/calculate/{value}")
async def calculate(value: int):
    logging.info(f"Calculating for {value}")
    result = 100 / value  # BUG: crashes on value=0
    return {"result": result}

# Bug 2: Null reference
@app.get("/user/{user_id}")
async def get_user(user_id: str):
    users = {"alice": {"name": "Alice", "email": "alice@example.com"}}
    user = users.get(user_id)
    return {"name": user["name"]}  # BUG: KeyError on unknown user

# Bug 3: Memory leak / slow endpoint
@app.get("/search")
async def search(query: str = ""):
    time.sleep(5)  # BUG: simulates timeout
    return {"results": []}

# Health check endpoint (Airbyte will poll this)
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

# Error log endpoint (Airbyte source)
@app.get("/errors")
async def get_errors():
    """Returns recent errors for Airbyte to ingest."""
    # In production, this reads from a log file or error tracking service
    return {"errors": ERROR_BUFFER}

ERROR_BUFFER = []

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_record = {
        "timestamp": time.time(),
        "path": str(request.url),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "source_file": "demo-app/main.py"
    }
    ERROR_BUFFER.append(error_record)
    logging.error(json.dumps(error_record))
    raise HTTPException(status_code=500, detail=str(exc))
```

Push this to a GitHub repo so Macroscope can index it.

#### 1B. Set up Aerospike

```bash
# Option 1: Docker (fastest for hackathon)
docker run -d --name aerospike -p 3000:3000 aerospike/aerospike-server

# Option 2: Get cloud credentials from Aerospike booth
# Talk to Lucas Beeler / Harin Avvari / Jagrut Nemade
```

```python
# Initialize Aerospike with the shared schema
import aerospike

client = aerospike.client({'hosts': [('127.0.0.1', 3000)]})

def write_incident(incident: dict):
    key = ('deepops', 'incidents', incident['incident_id'])
    client.put(key, incident)

def read_incident(incident_id: str) -> dict:
    key = ('deepops', 'incidents', incident_id)
    _, _, bins = client.get(key)
    return bins

def get_all_incidents() -> list:
    """Scan all incidents for dashboard."""
    records = []
    scan = client.scan('deepops', 'incidents')
    scan.foreach(lambda record: records.append(record[2]))
    return records
```

#### 1C. Set up Auth0

```bash
# 1. Create free Auth0 account at auth0.com
# 2. Create a new Application (Regular Web App)
# 3. Create an API (DeepOps API)
# 4. Set up roles: "auto-deploy" (low severity) and "manual-approve" (high severity)
```

```python
# auth0_config.py
from authlib.integrations.requests_client import OAuth2Session

AUTH0_DOMAIN = "your-tenant.auth0.com"
AUTH0_CLIENT_ID = "..."
AUTH0_CLIENT_SECRET = "..."
AUTH0_AUDIENCE = "https://deepops-api"

# RBAC: Define permissions
PERMISSIONS = {
    "auto-deploy": ["deploy:low", "deploy:medium"],
    "manual-approve": ["deploy:high", "deploy:critical"]
}

def check_deploy_permission(severity: str, user_role: str) -> bool:
    """Auth0 RBAC gating for deployment decisions."""
    if severity in ["low", "medium"]:
        return True  # Auto-deploy
    return user_role == "admin"  # Require human for high/critical
```

**Talk to Fred Patton (Auth0 Senior Developer Advocate)** at the booth to get:
- Quick-start credentials for hackathon
- Recommended RBAC pattern they want to see

### Phase 2: Build the Action Layer (11:30 - 1:30)

#### 2A. Airbyte Data Pipeline

Airbyte ingests error signals from the demo app into our pipeline. For the hackathon, use PyAirbyte or Airbyte's Agent Connectors.

```python
# airbyte_pipeline.py
# Option A: Use Airbyte Agent Connectors (newest, recommended for hackathon)
# pip install airbyte-agent-connectors

# Option B: Use PyAirbyte
# pip install airbyte

# Option C: Use Airbyte Cloud (free 30-day trial)
# Set up a connection: Source = Custom HTTP API (demo app /errors endpoint)
#                       Destination = Write to Aerospike or a staging area

# Simplest approach for hackathon:
import requests
import time

def airbyte_ingest_loop():
    """
    Simulates Airbyte pipeline: polls demo app errors endpoint
    and writes to Aerospike.
    
    For the demo, show this running as an Airbyte connection in the UI
    OR use PyAirbyte programmatically.
    """
    while True:
        # Fetch errors from demo app
        resp = requests.get("http://localhost:8000/errors")
        errors = resp.json().get("errors", [])
        
        for error in errors:
            incident_id = f"inc-{int(error['timestamp'] * 1000)}"
            write_incident({
                "incident_id": incident_id,
                "timestamp": int(error["timestamp"] * 1000),
                "error_type": error["error_type"],
                "error_message": error["error_message"],
                "source_file": error.get("source_file", "unknown"),
                "severity": "pending",
                "status": "detected",
                "fix_approved": False,
                "deployed": False,
            })
        
        time.sleep(3)
```

**Talk to Pedro Lopez and Patrick Nilan from Airbyte** at the booth. They can help you set up a real Airbyte connection in minutes. Having the Airbyte UI showing a live sync is much more impressive for the demo than a polling script.

#### 2B. Bland AI Voice Escalation

This is the **demo showstopper**. When severity is high/critical, the agent calls the "on-call engineer" using Bland AI.

```python
# bland_caller.py
import requests

BLAND_API_KEY = "..."  # Get from Bland booth (Spencer Small, Lucca Psaila)
BLAND_API_URL = "https://api.bland.ai/v1/calls"

def escalate_via_voice(incident: dict, phone_number: str):
    """
    Call the on-call engineer using Bland AI to explain the issue
    and get verbal approval for the fix.
    """
    task_prompt = f"""You are DeepOps, an autonomous code repair agent. 
You are calling the on-call engineer about a production incident.

INCIDENT: {incident['incident_id']}
SEVERITY: {incident['severity']}
ERROR: {incident['error_message']}
ROOT CAUSE: {incident['root_cause']}
PROPOSED FIX: {incident['proposed_fix'][:200]}

Your job:
1. Greet the engineer professionally
2. Explain the incident concisely
3. Describe the proposed fix
4. Ask if they approve deploying the fix
5. If they say yes, say "Fix approved. Deploying now."
6. If they say no, say "Understood. The fix is queued for manual review."
"""

    payload = {
        "phone_number": phone_number,
        "task": task_prompt,
        "voice": "mason",  # Professional male voice
        "first_sentence": f"Hi, this is DeepOps, your automated incident response system. I'm calling about a {incident['severity']} severity incident.",
        "model": "enhanced",
        "max_duration": 120,  # 2 min max
        "record": True,
        "webhook": "https://your-ngrok-url.ngrok.io/bland-webhook",
        "temperature": 0.3,  # Low creativity for accuracy
        "wait_for_greeting": True,
    }

    response = requests.post(
        BLAND_API_URL,
        headers={
            "Authorization": f"Bearer {BLAND_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    call_data = response.json()
    return call_data.get("call_id")


def handle_bland_webhook(webhook_data: dict):
    """
    Bland sends webhook after call completes.
    Parse transcript to determine if fix was approved.
    """
    transcript = webhook_data.get("transcript", "")
    
    # Simple approval detection
    approved = any(word in transcript.lower() for word in ["yes", "approve", "go ahead", "deploy it"])
    
    incident_id = webhook_data.get("metadata", {}).get("incident_id")
    if incident_id:
        update_incident(incident_id, {
            "fix_approved": approved,
            "status": "deploying" if approved else "blocked",
            "bland_call_id": webhook_data.get("call_id")
        })
```

**CRITICAL FOR DEMO:** Test the Bland AI call BEFORE the demo. Have your teammate's phone number ready. The moment the phone rings live on stage, you win the crowd.

#### 2C. TrueFoundry Deployment

TrueFoundry deploys both the demo app AND the agent itself. When the agent generates a fix, TrueFoundry redeploys the patched version.

```python
# truefoundry_deploy.py
# pip install truefoundry

# Option A: Use TrueFoundry Python SDK
from truefoundry import TrueFoundryClient

tf_client = TrueFoundryClient(api_key="...")

def deploy_fix(incident: dict):
    """Deploy the fixed version of the demo app via TrueFoundry."""
    # 1. Apply the fix to the codebase
    apply_patch(incident["proposed_fix"])
    
    # 2. Push to git (TrueFoundry watches the repo)
    subprocess.run(["git", "add", "."], cwd="./demo-app")
    subprocess.run(["git", "commit", "-m", f"fix: {incident['incident_id']} - auto-fix by DeepOps"], cwd="./demo-app")
    subprocess.run(["git", "push"], cwd="./demo-app")
    
    # 3. TrueFoundry auto-deploys on push (or trigger manually)
    # Show the TrueFoundry dashboard with deployment logs
    
    # 4. Update incident status
    update_incident(incident["incident_id"], {
        "deployed": True,
        "status": "resolved",
        "resolution_time_ms": int((time.time() - incident["timestamp"]/1000) * 1000)
    })

# Option B: Use TrueFoundry CLI
# tfy deploy --project deepops --service demo-app
```

**Talk to Sai Krishna (TrueFoundry DevRel)** at the booth to get:
- Free hackathon workspace
- Quickest deployment pattern (they have a ~15 min setup)
- They have Helm charts and Docker-based deployment

### Phase 3: Build the Dashboard (1:30 - 2:30)

#### 3A. Real-time Dashboard (Next.js or simple HTML)

```jsx
// For speed: use a simple React app or even just an HTML page
// that polls the FastAPI backend

// Dashboard shows:
// 1. Live incident feed (status, severity, timestamps)
// 2. Agent state (idle / detecting / diagnosing / fixing / deploying / calling)
// 3. Per-sponsor integration status (green checkmarks)
// 4. Resolution metrics (avg time, success rate)
// 5. Overmind trace link for each incident
```

For hackathon speed, a simple HTML + Tailwind page with fetch() polling is fine:

```html
<!-- dashboard/index.html -->
<!-- Polls /api/incidents every 2 seconds -->
<!-- Shows a card per incident with live status updates -->
<!-- Color-coded by severity -->
<!-- Shows which sponsors were involved in each resolution -->
```

### Phase 4: Integration Testing & Demo Polish (2:30 - 4:15)

#### 4A. End-to-End Demo Script

```
SETUP: Demo app is running on TrueFoundry. Dashboard is open.
       Agent is running. Overmind dashboard is in a tab.

[0:00 - 0:30] HOOK
  "Bugs don't wait for office hours. What if your codebase could heal itself?"
  Show the dashboard: clean, all green.
  "This is DeepOps. Let me show you what happens when things break."

[0:30 - 0:50] TRIGGER THE BUG
  Hit: curl http://demo-app/calculate/0
  Dashboard immediately shows: NEW INCIDENT DETECTED (red)
  "Airbyte just ingested that error. Aerospike stored the context."

[0:50 - 1:20] AGENT DIAGNOSES
  Dashboard updates: DIAGNOSING...
  "Macroscope analyzed the codebase and found this function lacks input validation."
  Show the LLM reasoning (optional: show Overmind trace)

[1:20 - 1:50] AGENT FIXES
  Dashboard updates: GENERATING FIX...
  "Kiro planned and wrote the fix using spec-driven development."
  Show the proposed diff on screen.

[1:50 - 2:20] SEVERITY ROUTING
  "This is a low-severity bug. Auth0's RBAC says: auto-deploy."
  Dashboard shows: DEPLOYING VIA TRUEFOUNDRY
  "But watch what happens with a critical bug..."
  
  Trigger a "critical" bug (or simulate one):
  YOUR PHONE RINGS. Bland AI is calling.
  Answer on speakerphone: "Hi, this is DeepOps..."
  Say "yes, deploy it"
  Dashboard updates: FIX APPROVED > DEPLOYING > RESOLVED

[2:20 - 2:45] SHOW THE LOOP
  "Every decision was traced by Overmind."
  Flash the Overmind dashboard: traces, latency, tokens
  "And every cycle makes the agent smarter."

[2:45 - 3:00] CLOSE
  "DeepOps uses ALL 8 sponsor tools in a genuine pipeline:
   Airbyte ingests, Aerospike stores, Macroscope understands,
   Kiro fixes, Auth0 gates, Bland calls, TrueFoundry deploys,
   and Overmind optimizes. Self-healing codebases start here."
```

#### 4B. Backup Plan

Record a 3-minute screen capture of the full flow working. If WiFi dies or an API rate-limits you during demo, play the video. Judges understand. Having a backup shows professionalism.

---

## SPONSOR INTEGRATION SUMMARY

| # | Sponsor | Role in DeepOps | Integration Point | Person |
|---|---------|----------------|-------------------|--------|
| 1 | **Kiro** | Plans and writes code fixes using spec-driven development | Agent generates spec > Kiro CLI implements | A |
| 2 | **Auth0** | RBAC gating: auto-deploy low severity, require approval for high | Middleware on deploy decision | B |
| 3 | **Bland AI** | Voice-calls on-call engineer for high-severity approval | REST API call with incident context | B |
| 4 | **Airbyte** | Ingests error logs from demo app into the pipeline | PyAirbyte or Airbyte Cloud connection | B |
| 5 | **Aerospike** | Real-time state store for incidents, agent memory, context | Python client, key-value operations | B (setup) / Both (use) |
| 6 | **TrueFoundry** | Deploys the demo app and redeploys after fixes | SDK/CLI for deployment + monitoring | B |
| 7 | **Overmind** | Traces every LLM call and agent decision for optimization | Python SDK, auto-instruments LLM calls | A |
| 8 | **Macroscope** | Understands the codebase to enable root cause diagnosis | GitHub app + API for codebase Q&A | A |

---

## TIMELINE SUMMARY

| Time | Person A (Agent Core) | Person B (Infra + Actions) | Sync Point |
|------|----------------------|---------------------------|------------|
| 10:00-10:30 | Attend talks, network with sponsor booths | Attend talks, network with sponsor booths | Agree on Aerospike schema |
| 10:30-11:00 | Project scaffold, Overmind init | Demo app + Aerospike Docker | Push demo app to GitHub |
| 11:00-11:30 | Macroscope API setup | Auth0 + Airbyte setup | Test Aerospike read/write |
| 11:30-12:30 | Agent orchestrator loop | Bland AI integration | -- |
| 12:30-1:00 | Diagnoser (Macroscope + LLM) | TrueFoundry deployment | -- |
| 1:00-1:30 | Fixer (Kiro integration) | Dashboard scaffold | Lunch break (eat while coding) |
| 1:30-2:00 | Severity classifier + routing | Dashboard real-time updates | Test: detect > diagnose works |
| 2:00-2:30 | Overmind dashboard review | Bland AI voice test | Test: full loop end-to-end |
| 2:30-3:00 | Bug fixes, edge cases | Demo polish, backup video | Full integration test |
| 3:00-3:30 | Devpost writeup (Person A writes) | Final demo rehearsal | -- |
| 3:30-4:00 | Review submission together | Review submission together | -- |
| 4:00-4:30 | SUBMIT ON DEVPOST | SUBMIT ON DEVPOST | Done! |

---

## DEVPOST SUBMISSION CHECKLIST

- [ ] Project name: DeepOps
- [ ] Tagline: "Self-healing codebases powered by deep agents"
- [ ] Description: Include architecture diagram, sponsor usage, and demo video link
- [ ] Select ALL sponsor challenges
- [ ] Add GitHub repo link
- [ ] Upload demo video (backup recording)
- [ ] List all team members (everyone registered on Devpost)
- [ ] Publish skills to shipables.dev (mentioned in submission rules)

---

## API KEYS / ACCOUNTS TO SET UP

Get these EARLY (visit booths during first hour):

| Service | What to Get | Who to Ask |
|---------|------------|------------|
| Kiro | Download IDE from kiro.dev, sign in with GitHub | AWS booth |
| Auth0 | Free dev account + API credentials | Fred Patton |
| Bland AI | API key (ask for hackathon credits) | Spencer Small, Lucca Psaila |
| Airbyte | Cloud account (free 30 days) or Docker setup | Pedro Lopez, Patrick Nilan |
| Aerospike | Cloud instance or Docker credentials | Lucas Beeler, Harin Avvari, Jagrut Nemade |
| TrueFoundry | Free workspace + API key | Sai Krishna |
| Overmind | API key from console.overmindlab.ai | Tyler Edwards, Akhat Rakishev |
| Macroscope | GitHub app install + API access | Ikshita Puri, Zhuolun Li |

---

## KEY LINKS

- Devpost: https://bit.ly/devpost-mar27
- Discord: https://bit.ly/discord-march
- AWS Registration: https://events.builder.aws.com/4DGEag
- shipables.dev (publish skills here)

---

Good luck, Ayush. Go get win #6.
