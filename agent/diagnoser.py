"""
Diagnosis engine for DeepOps incidents.

Takes a structured incident dict, queries Macroscope for codebase context,
calls an LLM to produce a structured diagnosis, and returns a dict that
maps directly into the incident schema's ``diagnosis`` section.

All LLM calls go through ``call_llm`` so Overclaw can observe token usage,
latency, and tool metadata.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from agent.macroscope_client import MacroscopeClient
from agent.prompts import (
    DIAGNOSIS_SYSTEM_PROMPT,
    DIAGNOSIS_USER_PROMPT,
    MACROSCOPE_QUESTION_TEMPLATE,
    build_diagnosis_prompt,
    parse_diagnosis_response,
    DiagnosisParseError,
)
from agent.tracing import call_llm as traced_call_llm, call_tool as traced_call_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM call through shared tracing wrapper
# ---------------------------------------------------------------------------


def _make_llm_call(prompt: str) -> str:
    """Call the LLM through the shared tracing wrapper."""
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "The 'anthropic' package is required for default LLM calls. "
            "Install it with: pip install anthropic"
        ) from e

    client = anthropic.Anthropic()

    def _provider_call(**kwargs):
        response = client.messages.create(**kwargs)
        return response.content[0].text

    return traced_call_llm(
        _provider_call,
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )


# ---------------------------------------------------------------------------
# Macroscope query helper
# ---------------------------------------------------------------------------


def _query_macroscope(
    incident: dict, repo_id: str
) -> tuple[str, bool]:
    """Query Macroscope for codebase context about the incident.

    Returns (context_string, used_fallback).
    """
    source = incident.get("source", {})
    try:
        client = MacroscopeClient(fallback_mode=True)
        used_fallback = True
    except Exception:
        client = MacroscopeClient(fallback_mode=True)
        used_fallback = True

    question = MACROSCOPE_QUESTION_TEMPLATE.format(
        path=source.get("path", "unknown"),
        source_file=source.get("source_file", "unknown"),
        error_type=source.get("error_type", "Unknown"),
        error_message=source.get("error_message", "No message"),
    )

    try:
        context = traced_call_tool(
            "macroscope_query",
            client.query,
            repo_id=repo_id,
            question=question,
            incident_context=source,
        )
        return context, used_fallback
    except Exception as e:
        logger.warning("Macroscope query failed: %s. Using empty context.", e)
        return f"Macroscope unavailable: {e}", True


# ---------------------------------------------------------------------------
# Main diagnosis function
# ---------------------------------------------------------------------------


def run_diagnosis(
    incident: dict,
    llm_caller: Callable[[str], str] | None = None,
    repo_id: str = "deepops-demo-app",
) -> dict:
    """Run full diagnosis pipeline for an incident.

    Parameters
    ----------
    incident:
        Incident dict matching the canonical schema (must have ``source``).
    llm_caller:
        Optional callable ``(prompt) -> raw_text``. If None, uses the
        default Anthropic API.
    repo_id:
        Repository identifier for Macroscope queries.

    Returns
    -------
    dict
        Diagnosis section matching the incident schema.
    """
    started_at_ms = int(time.time() * 1000)
    macroscope_context: str | None = None
    macroscope_fallback = True

    try:
        # Step 1: Query Macroscope
        logger.info("Querying Macroscope for incident context...")
        macroscope_context, macroscope_fallback = _query_macroscope(incident, repo_id)
        logger.info(
            "Macroscope context obtained (%d chars, fallback=%s)",
            len(macroscope_context),
            macroscope_fallback,
        )

        # Step 2: Build prompt
        prompt = build_diagnosis_prompt(incident, macroscope_context)
        logger.info("Diagnosis prompt built (%d chars)", len(prompt))

        # Step 3: Call LLM (through shared tracer or injected caller)
        logger.info("Calling LLM for diagnosis...")
        if llm_caller is not None:
            raw_response = llm_caller(prompt)
        else:
            raw_response = _make_llm_call(prompt)
        logger.info("LLM response received (%d chars)", len(raw_response))

        # Step 4: Parse response
        parsed = parse_diagnosis_response(raw_response)
        logger.info("Diagnosis parsed successfully (confidence=%.2f)", parsed["confidence"])

        completed_at_ms = int(time.time() * 1000)

        return {
            "status": "complete",
            "root_cause": parsed["root_cause"],
            "suggested_fix": parsed["suggested_fix"],
            "affected_components": parsed["affected_components"],
            "confidence": parsed["confidence"],
            "severity_reasoning": parsed.get("severity_reasoning"),
            "macroscope_context": macroscope_context,
            "started_at_ms": started_at_ms,
            "completed_at_ms": completed_at_ms,
        }

    except Exception as e:
        logger.error("Diagnosis failed: %s", e, exc_info=True)
        completed_at_ms = int(time.time() * 1000)
        return {
            "status": "failed",
            "root_cause": None,
            "suggested_fix": None,
            "affected_components": [],
            "confidence": 0.0,
            "severity_reasoning": f"Diagnosis failed: {e}",
            "macroscope_context": macroscope_context,
            "started_at_ms": started_at_ms,
            "completed_at_ms": completed_at_ms,
        }


# ---------------------------------------------------------------------------
# Observability metadata
# ---------------------------------------------------------------------------


def get_diagnosis_metadata(diagnosis_result: dict) -> dict:
    """Extract observability metadata from a diagnosis result.

    Returns a dict suitable for Overmind spans and Overclaw evaluation.
    """
    started = diagnosis_result.get("started_at_ms") or 0
    completed = diagnosis_result.get("completed_at_ms") or 0
    status = diagnosis_result.get("status", "unknown")

    return {
        "token_count": None,  # placeholder for Overclaw
        "prompt_type": "standard" if status == "complete" else "unknown_error",
        "fallback_used": status == "failed",
        "macroscope_mode": (
            "fallback" if diagnosis_result.get("macroscope_context", "").startswith("Macroscope unavailable")
            else "fallback"  # always fallback in demo mode
        ),
        "duration_ms": max(0, completed - started),
    }
