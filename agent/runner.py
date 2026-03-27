from __future__ import annotations

import argparse
import json
import time
from typing import Any, Mapping

from config import load_settings
from agent.contracts import load_incident_from_path
from agent.orchestrator import AgentRuntime, process_next_incident
from agent.store_adapter import AerospikeIncidentStore, InMemoryIncidentStore, IncidentStore
from agent.tracing import get_tracer


def _load_diagnoser():
    from agent.diagnoser import run_diagnosis

    return run_diagnosis


def _load_fixer():
    try:
        from agent.fixer import run_fix_generation  # type: ignore
    except ImportError as exc:
        def _missing(_: Mapping[str, Any], __: Mapping[str, Any]) -> Mapping[str, Any]:
            raise RuntimeError("agent.fixer.run_fix_generation is not available yet.") from exc

        return _missing

    return run_fix_generation


def _build_store(args: argparse.Namespace) -> IncidentStore:
    if args.mock_incident:
        incident = load_incident_from_path(args.mock_incident)
        return InMemoryIncidentStore([incident])

    settings = load_settings()
    return AerospikeIncidentStore(settings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DeepOps Person A agent runtime.")
    parser.add_argument("--once", action="store_true", help="Process a single incident and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting changes to the backing store.")
    parser.add_argument("--mock-incident", help="Path to a local incident fixture.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Polling interval in seconds.")
    args = parser.parse_args()

    settings = load_settings()
    runtime = AgentRuntime(
        store=_build_store(args),
        diagnose=_load_diagnoser(),
        generate_fix=_load_fixer(),
        tracer=get_tracer(settings),
    )

    if args.once:
        result = process_next_incident(runtime, persist=not args.dry_run)
        print(json.dumps(result, indent=2))
        return 0

    while True:
        result = process_next_incident(runtime, persist=not args.dry_run)
        if result is not None:
            print(json.dumps({"incident_id": result["incident_id"], "status": result["status"]}, indent=2))
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
