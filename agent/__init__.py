from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["run_diagnosis"]


def __getattr__(name: str) -> Any:
    if name == "run_diagnosis":
        return import_module("agent.diagnoser").run_diagnosis
    raise AttributeError(name)
