"""
execution_package.py - Converts approved FixArtifacts into demo-ready execution packages.

Handles demo tasks 1, 2, and 4:
  - Approved plan → execution package (checkpoint 1)
  - Suggestion-aware fix packaging with constraints (checkpoint 2)
  - Execution summary for demo narration (checkpoint 4)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from server.services.fix_artifact_service import FixArtifact


@dataclass
class ExecutionPackage:
    incident_id: str
    execution_steps: list[str]
    fix_spec: str
    diff_preview: str | None
    files_changed: list[str]
    test_plan: list[str]
    deployment_inputs: dict
    narration_summary: str
    constraints_applied: list[str] = field(default_factory=list)
    mode: str = "normal"


def build_narration_summary(
    artifact: FixArtifact,
    constraints_applied: list[str] | None = None,
) -> str:
    """One-paragraph narration string for live demo use."""
    fix_summary_lower = (artifact.fix_summary or "apply the fix").rstrip(".").lower()
    files_str = ", ".join(artifact.files_changed) if artifact.files_changed else artifact.source_path
    test_first = artifact.test_plan[0] if artifact.test_plan else "run the test suite"

    parts = [
        f"The agent patched `{artifact.source_path}` to {fix_summary_lower}.",
        f"Files changed: {files_str}.",
        f"After deploy, verify: {test_first}.",
    ]

    if constraints_applied:
        parts.append(f"Constraints applied: {', '.join(constraints_applied)}.")

    # Keep under 3 sentences — merge constraint note into last sentence if present
    return " ".join(parts[:3]) if not constraints_applied else " ".join(parts)


def format_execution_package(
    artifact: FixArtifact,
    constraints: dict[str, bool] | None = None,
) -> ExecutionPackage:
    """Convert a FixArtifact into a demo-ready ExecutionPackage."""
    files_changed = list(artifact.files_changed)
    constraints_applied: list[str] = []

    # Apply constraints
    if constraints:
        if constraints.get("skip_auth"):
            files_changed = [f for f in files_changed if "auth" not in f]
            constraints_applied.append("skip_auth")

        if constraints.get("endpoint_only"):
            filtered = [f for f in files_changed if any(k in f for k in ("endpoint", "main", "route"))]
            files_changed = filtered if filtered else files_changed
            constraints_applied.append("endpoint_only")

    # Build execution steps
    first_file = files_changed[0] if files_changed else artifact.source_path
    first_test = artifact.test_plan[0] if artifact.test_plan else "run the test suite"
    execution_steps = [
        f"1. Apply patch to `{first_file}`",
        f"2. Run: `{first_test}`",
        "3. Verify deployment health endpoint",
        f"4. Confirm `{first_file}` behavior is unchanged",
    ]

    if constraints and constraints.get("hotfix_only"):
        execution_steps = execution_steps[:2]
        constraints_applied.append("hotfix_only")

    narration = build_narration_summary(artifact, constraints_applied or None)

    return ExecutionPackage(
        incident_id=artifact.incident_id,
        execution_steps=execution_steps,
        fix_spec=artifact.spec_markdown or "",
        diff_preview=artifact.diff_preview,
        files_changed=files_changed,
        test_plan=artifact.test_plan,
        deployment_inputs={
            "service_name": "deepops-demo-app",
            "environment": "hackathon",
            "source_path": artifact.source_path,
            "error_type": artifact.error_type,
        },
        narration_summary=narration,
        constraints_applied=constraints_applied,
        mode="normal",
    )
