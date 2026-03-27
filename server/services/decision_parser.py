"""Decision parser — turns free-form human input into structured decisions."""

from __future__ import annotations

import re
from typing import Any

DECISION_TYPES = [
    "approve",
    "reject",
    "revise",
    "suggest",
    "defer",
    "ask_context",
    "no_answer",
    "retry",
]

# ---------------------------------------------------------------------------
# Keyword / pattern banks
# ---------------------------------------------------------------------------

_APPROVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(yes|yep|yeah|yup|approved?|go\s*ahead|ship\s*it|lgtm|deploy|proceed|do\s*it|sounds\s*good|looks\s*good|green\s*light|confirmed?|absolutely|affirmative)\b", re.I),
    re.compile(r"\bjust\s+(do|fix|deploy|ship)\b", re.I),
    re.compile(r"\b(push|send|roll)\s*(it)?\s*(out|forward|live|to\s*prod)\b", re.I),
    re.compile(r"\bhotfix\b", re.I),  # "just do a hotfix" implies approval
]

_REJECT_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(no|nope|nah|reject(ed)?|denied?|stop|abort|halt|cancel|block|don'?t\s+deploy|do\s+not\s+deploy|hold\s+off|back\s+off|stand\s+down|revert)\b", re.I),
    re.compile(r"\b(not\s+now|absolutely\s+not|no\s+way)\b", re.I),
]

_REVISE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(different\s+approach|try\s+(again|another|something\s+else)|redo|rework|rethink|re-?do|re-?write|start\s+over|alternative)\b", re.I),
    re.compile(r"\bcan\s+you\s+(try|find|come\s+up\s+with)\b", re.I),
]

_SUGGEST_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(try\s+fixing|instead\s+(try|use|do)|what\s+if|have\s+you\s+(tried|considered)|maybe\s+(try|use|fix|change)|suggest|I\s+would|you\s+should|consider)\b", re.I),
    re.compile(r"\b(use\s+\w+\s+instead)\b", re.I),
]

_DEFER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(later|tomorrow|next\s+week|get\s+back|call\s+(you\s+)?back|check\s+(and|then)|hold\s+on|postpone|defer|not\s+right\s+now|wait|let\s+me\s+(think|check|look|review))\b", re.I),
    re.compile(r"\b(ask\s+\w+\s+instead|escalate|talk\s+to)\b", re.I),
]

_ASK_CONTEXT_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(show\s+me|can\s+I\s+see|let\s+me\s+see|send\s+me|what('?s| is| are)\s+(the\s+)?(diff|change|log|error|stack|trace|impact|risk|details?))\b", re.I),
    re.compile(r"\b(more\s+(info|information|context|details?)|explain|what\s+happened|what\s+broke|walk\s+me\s+through)\b", re.I),
    re.compile(r"\b(I\s+need\s+to\s+see|before\s+I\s+decide)\b", re.I),
]

_RETRY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(try\s+calling\s+(again|back|later)|couldn'?t\s+reach|no\s+answer|voice\s*mail|retry|call\s+(again|back))\b", re.I),
]

# Constraint extraction patterns
_CONSTRAINT_DONT_TOUCH: re.Pattern = re.compile(
    r"(?:don'?t|do\s+not|avoid|stay\s+away\s+from|leave)\s+(?:touch(?:ing)?|change|modify|edit|alter|mess\s+with)?\s*(.+?)(?:,|$)",
    re.I,
)
_CONSTRAINT_ONLY: re.Pattern = re.compile(
    r"(?:only|just)\s+(?:fix|change|touch|modify|update|deploy|patch|do)\s+(.+?)(?:,|$)",
    re.I,
)
_CONSTRAINT_HOTFIX: re.Pattern = re.compile(r"\bhotfix\s+only\b", re.I)
_CONSTRAINT_ROLLBACK: re.Pattern = re.compile(
    r"\b(?:roll\s*back|revert)\s+(?:if|when|on)\s+(.+?)(?:,|$)", re.I
)
_CONSTRAINT_STAGING: re.Pattern = re.compile(
    r"\b(?:staging|stage)\s+(?:first|before|then)\b", re.I
)
_CONSTRAINT_SCOPE_HOTFIX: re.Pattern = re.compile(
    r"\bjust\s+(?:a\s+)?hotfix\b", re.I
)
_CONSTRAINT_AVOID: re.Pattern = re.compile(
    r"\bavoid\s+(?:the\s+)?(.+?)(?:,|$)", re.I
)
_CONSTRAINT_DONT_STANDALONE: re.Pattern = re.compile(
    r"(?:don'?t|do\s+not)\s+touch\s+(.+?)(?:,|$)", re.I
)

# File reference pattern (paths like foo.py, src/bar.js, etc.)
_FILE_REF: re.Pattern = re.compile(
    r"\b([\w./-]*\w+\.(?:py|js|ts|tsx|jsx|java|go|rs|rb|css|html|json|yaml|yml|toml|cfg|sql|sh|md))\b",
    re.I,
)

# Module / package names often referenced without extension
_MODULE_REF: re.Pattern = re.compile(
    r"\b(?:the\s+)?(\w+)\s+(?:module|package|service|component|class|file)\b", re.I
)

# People references ("ask Sarah", "tell Bob", "check with Alice")
# Uses a two-step approach: case-insensitive verb match, then explicitly
# uppercase-first-letter name capture via a conditional check in the
# extraction function.  The regex itself is kept simple.
_PEOPLE_VERBS: re.Pattern = re.compile(
    r"\b(?:ask|tell|check\s+with|call|contact|ping|notify|escalate\s+to|talk\s+to|let|cc|loop\s+in)\s+(\w+(?:\s+\w+)?)",
    re.I,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_human_decision(text: str, source: str = "ui") -> dict:
    """Parse free-form human input into a structured decision.

    Args:
        text: The human's input (typed text, transcript, or note).
        source: Where the input came from ("ui", "phone", "note").

    Returns:
        Dictionary with keys: decision, confidence, raw_input, source,
        reasoning, suggestions, constraints.
    """
    if not text or not text.strip():
        return {
            "decision": "no_answer",
            "confidence": 1.0,
            "raw_input": text or "",
            "source": source,
            "reasoning": "Input was empty or whitespace-only.",
            "suggestions": [],
            "constraints": [],
        }

    decision, confidence = _classify_decision(text)
    constraints = _extract_constraints(text)
    suggestions = _extract_suggestions(text)

    # Build human-readable reasoning
    reasoning = _build_reasoning(text, decision, confidence)

    return {
        "decision": decision,
        "confidence": confidence,
        "raw_input": text,
        "source": source,
        "reasoning": reasoning,
        "suggestions": suggestions,
        "constraints": constraints,
    }


def parse_transcript_to_actions(transcript: str | list[dict]) -> dict:
    """Parse a phone call transcript into structured actions.

    Handles complex inputs including approvals with constraints, deferrals
    with escalation targets, requests for more context, and empty/no-answer
    transcripts.

    Args:
        transcript: Raw transcript string or list of utterance dicts
                    (each with at least a ``text`` key).

    Returns:
        Dictionary with keys: primary_action, confidence, actions,
        constraints, mentioned_files, mentioned_people, urgency, summary.
    """
    text = _normalize_transcript(transcript)

    if not text or not text.strip():
        return {
            "primary_action": "no_answer",
            "confidence": 1.0,
            "actions": [{"action": "no_answer", "detail": "No transcript content.", "confidence": 1.0}],
            "constraints": [],
            "mentioned_files": [],
            "mentioned_people": [],
            "urgency": "normal",
            "summary": "No answer or empty transcript.",
        }

    decision, confidence = _classify_decision(text)
    constraints = _extract_constraints(text)
    files = _extract_file_references(text)
    people = _extract_people_references(text)
    urgency = _infer_urgency(text)
    summary = _build_summary(text, decision)

    # Build action list — primary action + secondary actions detected
    actions: list[dict] = [
        {"action": decision, "detail": summary, "confidence": confidence}
    ]

    # If we have constraints alongside an approval, note them as secondary actions
    if decision == "approve" and constraints:
        actions.append({
            "action": "constrain",
            "detail": f"Constraints: {'; '.join(constraints)}",
            "confidence": confidence,
        })

    # If people are mentioned, might indicate escalation
    if people and decision == "defer":
        actions.append({
            "action": "escalate",
            "detail": f"Escalate to {', '.join(people)}.",
            "confidence": min(confidence + 0.1, 1.0),
        })

    return {
        "primary_action": decision,
        "confidence": confidence,
        "actions": actions,
        "constraints": constraints,
        "mentioned_files": files,
        "mentioned_people": people,
        "urgency": urgency,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_transcript(transcript: str | list[dict]) -> str:
    """Flatten transcript to plain text."""
    if isinstance(transcript, str):
        return transcript.strip()
    if isinstance(transcript, list):
        parts: list[str] = []
        for entry in transcript:
            if isinstance(entry, dict):
                parts.append(entry.get("text", entry.get("content", "")))
            elif isinstance(entry, str):
                parts.append(entry)
        return " ".join(parts).strip()
    return str(transcript).strip()


def _extract_keywords(text: str) -> dict[str, list[str]]:
    """Extract decision-relevant keywords and their surrounding context."""
    results: dict[str, list[str]] = {dt: [] for dt in DECISION_TYPES}
    lower = text.lower()

    pattern_map: dict[str, list[re.Pattern]] = {
        "approve": _APPROVE_PATTERNS,
        "reject": _REJECT_PATTERNS,
        "revise": _REVISE_PATTERNS,
        "suggest": _SUGGEST_PATTERNS,
        "defer": _DEFER_PATTERNS,
        "ask_context": _ASK_CONTEXT_PATTERNS,
        "retry": _RETRY_PATTERNS,
    }

    for decision_type, patterns in pattern_map.items():
        for pattern in patterns:
            for m in pattern.finditer(text):
                # Capture match + a few surrounding words for context
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 30)
                snippet = text[start:end].strip()
                results[decision_type].append(snippet)

    return results


def _classify_decision(text: str) -> tuple[str, float]:
    """Classify the primary decision type from text.

    Returns (decision_type, confidence).

    Priority order for ambiguous inputs:
    1. Explicit rejection beats everything
    2. Explicit approval with constraints = approve
    3. Questions or "let me check" = ask_context or defer
    4. Suggestions without clear yes/no = suggest
    5. Unclear = defer with low confidence
    """
    keywords = _extract_keywords(text)
    scores: dict[str, float] = {}

    # Weighted scoring: each keyword match adds to the category score
    weights: dict[str, float] = {
        "approve": 1.0,
        "reject": 1.3,   # rejection is weighted higher (safety)
        "revise": 1.1,
        "suggest": 0.9,
        "defer": 0.95,
        "ask_context": 1.0,
        "retry": 1.1,
        "no_answer": 0.0,
    }

    for dt in DECISION_TYPES:
        count = len(keywords.get(dt, []))
        scores[dt] = count * weights.get(dt, 1.0)

    total = sum(scores.values())

    if total == 0:
        return ("defer", 0.3)

    # Pick highest-scoring category
    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]

    # Confidence = proportion of signal going to the winning category,
    # clamped and scaled for human-readable range
    raw_confidence = best_score / total if total > 0 else 0.0

    # Boost confidence when there are many keyword matches
    match_count = len(keywords.get(best, []))
    if match_count >= 3:
        raw_confidence = min(raw_confidence + 0.15, 1.0)
    elif match_count == 0:
        raw_confidence = max(raw_confidence - 0.2, 0.1)

    # Scale into a useful range: single clear keyword -> ~0.85,
    # ambiguous -> 0.3-0.5
    confidence = round(min(max(raw_confidence, 0.2), 1.0), 2)

    # --- Priority rules for ambiguous cases ---

    # 1. Explicit rejection beats everything
    if scores["reject"] > 0 and scores["reject"] >= scores["approve"]:
        return ("reject", confidence)

    # 2. Approve with possible constraints
    if scores["approve"] > 0 and scores["approve"] > scores["reject"]:
        return ("approve", confidence)

    return (best, confidence)


def _extract_constraints(text: str) -> list[str]:
    """Extract deployment/fix constraints from human text.

    Looks for patterns like:
    - "don't touch X" / "avoid X" -> constraint: avoid file/module X
    - "only fix X" / "just the X" -> constraint: scope to X only
    - "hotfix only" -> constraint: minimal change
    - "roll back if it fails" -> constraint: rollback on failure
    - "deploy to staging first" -> constraint: staging before prod
    """
    constraints: list[str] = []

    # "don't touch / don't change ..."
    for m in _CONSTRAINT_DONT_TOUCH.finditer(text):
        target = _clean_constraint_target(m.group(1))
        if target:
            constraints.append(f"avoid {target}")

    # "don't touch X" (standalone, simpler pattern)
    for m in _CONSTRAINT_DONT_STANDALONE.finditer(text):
        target = _clean_constraint_target(m.group(1))
        candidate = f"avoid {target}"
        if target and candidate not in constraints:
            constraints.append(candidate)

    # "avoid X"
    for m in _CONSTRAINT_AVOID.finditer(text):
        target = _clean_constraint_target(m.group(1))
        candidate = f"avoid {target}"
        if target and candidate not in constraints:
            constraints.append(candidate)

    # "only fix X" / "just fix X"
    for m in _CONSTRAINT_ONLY.finditer(text):
        target = _clean_constraint_target(m.group(1))
        if target:
            constraints.append(f"scope to {target} only")

    # "hotfix only"
    if _CONSTRAINT_HOTFIX.search(text):
        constraints.append("hotfix only")

    # "just do a hotfix" (without the word "only")
    if _CONSTRAINT_SCOPE_HOTFIX.search(text) and "hotfix only" not in constraints:
        constraints.append("hotfix only")

    # "roll back if ..."
    for m in _CONSTRAINT_ROLLBACK.finditer(text):
        condition = _clean_constraint_target(m.group(1))
        if condition:
            constraints.append(f"rollback if {condition}")

    # "staging first"
    if _CONSTRAINT_STAGING.search(text):
        constraints.append("staging before prod")

    return constraints


def _clean_constraint_target(raw: str) -> str:
    """Clean a captured constraint target, preserving file extensions."""
    target = raw.strip()
    # Strip trailing period only if it is NOT part of a file extension
    # (e.g., "auth.py" should keep the dot, but "the auth module." should lose it)
    if target.endswith("."):
        # Check if it looks like a file extension (dot + 1-4 alpha chars + dot)
        if not re.search(r"\.\w{1,4}$", target[:-1]):
            target = target.rstrip(".")
    return target.strip()


def _extract_file_references(text: str) -> list[str]:
    """Extract file paths or module names from text."""
    files: list[str] = []
    for m in _FILE_REF.finditer(text):
        path = m.group(1)
        if path not in files:
            files.append(path)
    for m in _MODULE_REF.finditer(text):
        module = m.group(1)
        if module not in files:
            files.append(module)
    return files


def _extract_people_references(text: str) -> list[str]:
    """Extract names of people mentioned (for escalation)."""
    # Common non-name words that can follow the verb phrase
    _NON_NAMES = {
        "about", "the", "this", "that", "them", "their", "it", "if",
        "me", "my", "our", "us", "we", "you", "your", "him", "her",
        "instead", "again", "before", "after", "when", "first",
    }
    people: list[str] = []
    for m in _PEOPLE_VERBS.finditer(text):
        raw = m.group(1).strip()
        # Take only the first word as the name candidate
        words = raw.split()
        candidate = words[0]
        # Must start with uppercase and not be a common non-name word
        if candidate[0].isupper() and candidate.lower() not in _NON_NAMES:
            # Check for two-word proper name
            if len(words) > 1 and words[1][0].isupper() and words[1].lower() not in _NON_NAMES:
                candidate = f"{words[0]} {words[1]}"
            if candidate not in people:
                people.append(candidate)
    return people


def _extract_suggestions(text: str) -> list[str]:
    """Extract actionable suggestions from human input."""
    suggestions: list[str] = []

    # "try fixing X", "use X instead", "maybe try X"
    suggestion_patterns = [
        re.compile(r"\b(?:try|maybe)\s+(?:fixing|using|changing|updating)\s+(.+?)(?:\.|,|$)", re.I),
        re.compile(r"\b(?:use|switch\s+to)\s+(.+?)\s+instead\b", re.I),
        re.compile(r"\b(?:you\s+should|I\s+would|consider)\s+(.+?)(?:\.|,|$)", re.I),
        re.compile(r"\b(?:what\s+if\s+(?:you|we))\s+(.+?)(?:\.|,|\?|$)", re.I),
    ]

    for pattern in suggestion_patterns:
        for m in pattern.finditer(text):
            suggestion = m.group(1).strip().rstrip(".")
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)

    return suggestions


def _infer_urgency(text: str) -> str:
    """Infer urgency from the human's language."""
    # Check deferred FIRST -- phrases like "no rush" should not be
    # overridden by the word "rush" matching an urgent pattern.
    deferred_patterns = [
        re.compile(r"\b(no\s+rush|not\s+urgent|low\s+priority|when\s+you\s+can|no\s+hurry)\b", re.I),
        re.compile(r"\b(later|tomorrow|next\s+week)\b", re.I),
    ]
    urgent_patterns = [
        re.compile(r"\b(now|immediately|asap|urgent|right\s+away|critical|emergency|hurry|rush)\b", re.I),
    ]

    for p in deferred_patterns:
        if p.search(text):
            return "deferred"
    for p in urgent_patterns:
        if p.search(text):
            return "immediate"
    return "normal"


def _build_reasoning(text: str, decision: str, confidence: float) -> str:
    """Build a human-readable reasoning string."""
    keywords = _extract_keywords(text)
    matched = keywords.get(decision, [])
    if matched:
        samples = matched[:3]
        keyword_str = ", ".join(f'"{s}"' for s in samples)
        return (
            f"Classified as '{decision}' (confidence {confidence}) "
            f"based on matching signals: {keyword_str}."
        )
    return (
        f"Classified as '{decision}' (confidence {confidence}) "
        f"as the best-fit interpretation of the input."
    )


def _build_summary(text: str, decision: str) -> str:
    """Build a one-line summary of what the human communicated."""
    # Truncate long text for summary
    clean = " ".join(text.split())
    if len(clean) > 120:
        clean = clean[:117] + "..."
    label_map = {
        "approve": "Approved",
        "reject": "Rejected",
        "revise": "Requested revision",
        "suggest": "Provided suggestion",
        "defer": "Deferred decision",
        "ask_context": "Requested more context",
        "no_answer": "No answer",
        "retry": "Requested retry",
    }
    label = label_map.get(decision, decision.capitalize())
    return f"{label}: {clean}"
