"""
Prompt templates for the DeepOps diagnosis agent.

Each template is a plain string with {placeholders} for str.format().
The diagnosis prompt produces a strict JSON response that maps directly
into the incident schema's diagnosis section.
"""

import json
import re

# ---------------------------------------------------------------------------
# Diagnosis prompt
# ---------------------------------------------------------------------------

DIAGNOSIS_SYSTEM_PROMPT = """\
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
- root_cause must cite the specific file or route.  "somewhere in the
  backend" is unacceptable.
- suggested_fix must address the actual root cause, not mask the symptom.
  Wrapping in a bare try/except or returning a generic 500 is not a fix.
- Do NOT suggest unrelated refactors, new dependencies, or architecture
  changes.
- Phrases like "check the logs" or "investigate further" are prohibited.
- Output ONLY valid JSON.  No trailing commas, no comments.
"""

DIAGNOSIS_USER_PROMPT = """\
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
"""

# ---------------------------------------------------------------------------
# Macroscope question templates
# ---------------------------------------------------------------------------

MACROSCOPE_QUESTION_TEMPLATE = """\
The route {path} in {source_file} raised {error_type}: {error_message}.
What does the failing function do, what calls it, and what dependencies
does it touch?  Focus on explaining why this error would occur.
"""

UNKNOWN_ERROR_USER_PROMPT = """\
## Incident

- Service:       {service}
- Environment:   {environment}
- Route/Path:    {path}
- Error type:    {error_type}
- Error message: {error_message}
- Source file:   {source_file}

## Codebase Context (from Macroscope)

{macroscope_context}

## Important Constraints

This is an error the team has NOT seen before. You must still produce a
concrete diagnosis. Do NOT fall back to generic advice.

Banned phrases: 'check the logs', 'investigate further', 'needs more context',
'unclear without more information', 'review the configuration'.

You MUST provide:
- One concrete root cause hypothesis based on the error type and code context
- One practical fix direction that a code generation tool can act on
- At least one affected component (the source file at minimum)

## Instructions

Produce a JSON diagnosis object with the five required fields.
"""


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class DiagnosisParseError(Exception):
    """Raised when the LLM response cannot be parsed into a valid diagnosis."""
    pass


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {"root_cause", "suggested_fix", "affected_components", "confidence"}


def build_diagnosis_prompt(incident: dict, macroscope_context: str) -> str:
    """Build a full diagnosis prompt from an incident and Macroscope context."""
    source = incident.get("source", {})
    user_msg = DIAGNOSIS_USER_PROMPT.format(
        service=incident.get("service", "unknown"),
        environment=incident.get("environment", "unknown"),
        path=source.get("path", "unknown"),
        error_type=source.get("error_type", "Unknown"),
        error_message=source.get("error_message", "No message"),
        source_file=source.get("source_file", "unknown"),
        macroscope_context=macroscope_context or "No codebase context available.",
    )
    return f"{DIAGNOSIS_SYSTEM_PROMPT}\n\n{user_msg}"


def build_unknown_error_prompt(incident: dict, macroscope_context: str) -> str:
    """Build a diagnosis prompt for errors not in the rehearsed set."""
    source = incident.get("source", {})
    user_msg = UNKNOWN_ERROR_USER_PROMPT.format(
        service=incident.get("service", "unknown"),
        environment=incident.get("environment", "unknown"),
        path=source.get("path", "unknown"),
        error_type=source.get("error_type", "Unknown"),
        error_message=source.get("error_message", "No message"),
        source_file=source.get("source_file", "unknown"),
        macroscope_context=macroscope_context or "No codebase context available.",
    )
    return f"{DIAGNOSIS_SYSTEM_PROMPT}\n\n{user_msg}"


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def parse_diagnosis_response(raw_text: str) -> dict:
    """Parse and validate an LLM diagnosis response."""
    if not raw_text or not raw_text.strip():
        raise DiagnosisParseError("Empty response from LLM")

    cleaned = _strip_markdown_fences(raw_text.strip())

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise DiagnosisParseError(f"Invalid JSON in LLM response: {e}") from e

    if not isinstance(data, dict):
        raise DiagnosisParseError(f"Expected JSON object, got {type(data).__name__}")

    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise DiagnosisParseError(f"Missing required fields: {sorted(missing)}")

    if not isinstance(data["root_cause"], str) or not data["root_cause"].strip():
        raise DiagnosisParseError("root_cause must be a non-empty string")

    if not isinstance(data["suggested_fix"], str) or not data["suggested_fix"].strip():
        raise DiagnosisParseError("suggested_fix must be a non-empty string")

    if not isinstance(data["affected_components"], list):
        raise DiagnosisParseError("affected_components must be a list")
    data["affected_components"] = [str(c) for c in data["affected_components"]]

    try:
        data["confidence"] = float(data["confidence"])
    except (TypeError, ValueError) as e:
        raise DiagnosisParseError(f"confidence must be a number: {e}") from e
    if not (0.0 <= data["confidence"] <= 1.0):
        raise DiagnosisParseError(
            f"confidence must be between 0.0 and 1.0, got {data['confidence']}"
        )

    if "severity_reasoning" in data and data["severity_reasoning"] is not None:
        data["severity_reasoning"] = str(data["severity_reasoning"])
    else:
        data["severity_reasoning"] = None

    return {
        "root_cause": data["root_cause"],
        "suggested_fix": data["suggested_fix"],
        "affected_components": data["affected_components"],
        "confidence": data["confidence"],
        "severity_reasoning": data["severity_reasoning"],
    }


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON content."""
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
