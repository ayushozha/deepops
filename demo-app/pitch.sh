#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_APP_BASE_URL="${DEEPOPS_DEMO_APP_BASE_URL:-http://127.0.0.1:8001}"
BACKEND_BASE_URL="${DEEPOPS_BACKEND_BASE_URL:-http://127.0.0.1:8000}"
DASHBOARD_URL="${DEEPOPS_DASHBOARD_URL:-http://127.0.0.1:3000/dashboard}"
PYTHON_BIN="${PYTHON:-python}"

bold="$(printf '\033[1m')"
cyan="$(printf '\033[36m')"
green="$(printf '\033[32m')"
yellow="$(printf '\033[33m')"
red="$(printf '\033[31m')"
dim="$(printf '\033[2m')"
reset="$(printf '\033[0m')"

print_header() {
  printf "\n%s%sDeepOps 60-second pitch%s\n" "$bold" "$cyan" "$reset"
}

print_usage() {
  cat <<EOF
Usage:
  ./pitch.sh               Print the 60-second demo talk track
  ./pitch.sh script        Print the talk track
  ./pitch.sh run           Execute the 60-second auto-heal demo flow
  ./pitch.sh check         Check required local services

Environment overrides:
  DEEPOPS_DEMO_APP_BASE_URL   default: ${DEMO_APP_BASE_URL}
  DEEPOPS_BACKEND_BASE_URL    default: ${BACKEND_BASE_URL}
  DEEPOPS_DASHBOARD_URL       default: ${DASHBOARD_URL}
  PYTHON                      default: ${PYTHON_BIN}
EOF
}

print_script() {
  print_header
  cat <<EOF
${bold}[0-08s] Problem${reset}
Say: "Production bugs do not wait for office hours. DeepOps detects them, diagnoses the root cause, drafts the fix, and routes deployment automatically."
Show: ${DASHBOARD_URL}

${bold}[08-18s] Trigger${reset}
Say: "I will break the demo app on port 8001 with a real divide-by-zero."
Do:  ./pitch.sh run

${bold}[18-32s] Ingest${reset}
Say: "The error is ingested into DeepOps on port 8000 and becomes a live incident record."
Show: incident appears in the left log with severity and status

${bold}[32-46s] Diagnose + Fix${reset}
Say: "The agent moves the incident from stored to diagnosing to fixing, produces a root cause, and drafts a patch diff."
Show: root cause, confidence, and diff preview in /dashboard

${bold}[46-55s] Resolve${reset}
Say: "Because this bug is medium severity, policy auto-approves it and the incident resolves without human interruption."
Show: status transitions to resolved

${bold}[55-60s] Close${reset}
Say: "For high and critical bugs, the same pipeline pauses for approval. DeepOps is the control plane for self-healing codebases."
EOF
}

require_service() {
  local name="$1"
  local url="$2"

  if ! curl -fsS "$url" >/dev/null; then
    printf "%s%s not reachable%s: %s\n" "$red" "$name" "$reset" "$url" >&2
    return 1
  fi

  printf "%s%s reachable%s: %s\n" "$green" "$name" "$reset" "$url"
}

check_services() {
  print_header
  require_service "demo-app" "${DEMO_APP_BASE_URL}/health"
  require_service "backend" "${BACKEND_BASE_URL}/api/health"
  printf "%sdashboard%s: %s\n" "$yellow" "$reset" "$DASHBOARD_URL"
}

trigger_incident() {
  printf "\n%s[08-18s] Triggering calculate_zero on demo-app%s\n" "$yellow" "$reset"
  "$PYTHON_BIN" "${SCRIPT_DIR}/trigger_error.py" calculate_zero --ingest \
    --demo-app-base-url "${DEMO_APP_BASE_URL}" \
    --backend-base-url "${BACKEND_BASE_URL}"
}

run_agent_once() {
  printf "\n%s[18-46s] Running DeepOps agent once%s\n" "$yellow" "$reset"
  curl -fsS -X POST "${BACKEND_BASE_URL}/api/agent/run-once"
}

latest_incident_json() {
  curl -fsS "${BACKEND_BASE_URL}/api/incidents" | "$PYTHON_BIN" -c \
    'import json,sys; items=json.load(sys.stdin); items=sorted(items,key=lambda x: x.get("updated_at_ms",0), reverse=True); print(json.dumps(items[0] if items else {}))'
}

summarize_latest_incident() {
  local incident_json
  incident_json="$(latest_incident_json)"

  if [[ "$incident_json" == "{}" ]]; then
    printf "%sNo incidents returned from backend.%s\n" "$red" "$reset" >&2
    return 1
  fi

  printf "\n%s[46-60s] Latest incident summary%s\n" "$yellow" "$reset"
  printf "%s\n" "$incident_json" | "$PYTHON_BIN" -c '
import json,sys
incident=json.load(sys.stdin)
summary={
  "incident_id": incident.get("incident_id"),
  "status": incident.get("status"),
  "severity": incident.get("severity"),
  "diagnosis_status": (incident.get("diagnosis") or {}).get("status"),
  "root_cause": (incident.get("diagnosis") or {}).get("root_cause"),
  "fix_status": (incident.get("fix") or {}).get("status"),
  "files_changed": (incident.get("fix") or {}).get("files_changed"),
  "approval_status": (incident.get("approval") or {}).get("status"),
  "deployment_status": (incident.get("deployment") or {}).get("status"),
}
print(json.dumps(summary, indent=2))
'
}

run_demo() {
  check_services

  printf "\n%s%sStart on screen%s\n" "$bold" "$cyan" "$reset"
  printf "%sOpen dashboard:%s %s\n" "$dim" "$reset" "$DASHBOARD_URL"
  printf "%sNarration:%s Bugs do not wait for office hours. DeepOps closes the loop.\n" "$dim" "$reset"

  trigger_incident
  run_agent_once
  summarize_latest_incident

  cat <<EOF

${bold}${green}Pitch closeout${reset}
- "A real error hit the app on 8001."
- "DeepOps on 8000 ingested it, diagnosed it, drafted the patch, and resolved it."
- "The same incident record powers the dashboard, approval flow, and deployment story."
EOF
}

main() {
  local mode="${1:-script}"

  case "$mode" in
    script)
      print_script
      ;;
    run)
      run_demo
      ;;
    check)
      check_services
      ;;
    -h|--help|help)
      print_usage
      ;;
    *)
      print_usage
      return 1
      ;;
  esac
}

main "$@"
