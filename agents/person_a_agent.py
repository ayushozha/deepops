from __future__ import annotations

from typing import Any

from config import load_settings
from agent.orchestrator import run_case
from agent.runner import _load_diagnoser, _load_fixer
from agent.tracing import get_tracer


def run(input: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    return run_case(
        input,
        diagnose=_load_diagnoser(),
        generate_fix=_load_fixer(),
        tracer=get_tracer(settings),
    )
