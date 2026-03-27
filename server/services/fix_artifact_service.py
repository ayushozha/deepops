from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.contracts import FixPayload


@dataclass
class FixArtifact:
    """Deployment-ready fix package."""

    incident_id: str
    source_path: str        # e.g. "demo-app/main.py"
    error_type: str         # e.g. "ZeroDivisionError"
    kiro_mode: str          # "real" or "fallback"
    spec_markdown: str | None = None
    diff_preview: str | None = None
    files_changed: list[str] = field(default_factory=list)
    test_plan: list[str] = field(default_factory=list)
    fix_summary: str | None = None
    regression_warning: str | None = None


def package_fix_artifact(incident: dict[str, Any], fix_result: dict[str, Any]) -> FixArtifact:
    """Package raw Kiro fix output into a deployment-ready FixArtifact."""
    source: dict[str, Any] = incident.get("source", {})
    source_path: str = source.get("path", source.get("source_file", ""))
    error_type: str = source.get("error_type", "")

    meta: dict[str, Any] = fix_result.get("_metadata", {})
    kiro_mode: str = meta.get("kiro_mode", "real")
    fix_summary: str | None = meta.get("fix_summary")
    regression_warning: str | None = meta.get("regression_warning")

    return FixArtifact(
        incident_id=incident.get("incident_id", ""),
        source_path=source_path,
        error_type=error_type,
        kiro_mode=kiro_mode,
        spec_markdown=fix_result.get("spec_markdown"),
        diff_preview=fix_result.get("diff_preview"),
        files_changed=fix_result.get("files_changed") or [],
        test_plan=fix_result.get("test_plan") or [],
        fix_summary=fix_summary,
        regression_warning=regression_warning,
    )


def artifact_to_fix_payload(artifact: FixArtifact) -> FixPayload:
    """Return only the schema-valid FixPayload fields (no metadata)."""
    return FixPayload(
        spec_markdown=artifact.spec_markdown,
        diff_preview=artifact.diff_preview,
        files_changed=artifact.files_changed,
        test_plan=artifact.test_plan,
    )


@dataclass
class HotfixPackage:
    incident_id: str
    hotfix_plan: list[str]
    fix_artifact: FixArtifact
    verification_checklist: list[str]
    deployment_metadata: dict
    scope_note: str


def package_hotfix(
    incident: dict[str, Any],
    fix_result: dict[str, Any],
    excluded_files: list[str] | None = None,
) -> HotfixPackage:
    """Create a compact hotfix package from an incident and fix result."""
    source: dict[str, Any] = incident.get("source", {})
    source_file: str = source.get("source_file", source.get("path", "app/main.py"))
    path: str = source.get("path", "/health")
    environment: str = incident.get("environment", "hackathon")

    artifact = package_fix_artifact(incident, fix_result)

    # Filter files_changed to primary source file only
    primary = artifact.files_changed[0] if artifact.files_changed else source_file
    artifact.files_changed = [primary]

    # Trim test_plan to first 2 items
    artifact.test_plan = artifact.test_plan[:2]

    # Exclude any explicitly excluded files
    if excluded_files:
        artifact.files_changed = [f for f in artifact.files_changed if f not in excluded_files]

    hotfix_plan = [
        f"Apply minimal patch to `{source_file}`",
        f"Deploy to `{environment}` immediately",
        f"Verify `{path}` returns expected response",
    ]

    verification_checklist = [
        f"Check `{path}` returns non-500 response",
        "Confirm error no longer appears in logs",
        "Schedule full regression run post-hotfix",
    ]

    deployment_metadata = {
        "service_name": incident.get("service", "deepops-demo-app"),
        "environment": environment,
        "hotfix": True,
        "source_path": source_file,
    }

    scope_note = (
        f"Excluded from hotfix: {', '.join(excluded_files)}"
        if excluded_files
        else "Full fix deferred — hotfix targets primary failure point only"
    )

    return HotfixPackage(
        incident_id=incident.get("incident_id", ""),
        hotfix_plan=hotfix_plan,
        fix_artifact=artifact,
        verification_checklist=verification_checklist,
        deployment_metadata=deployment_metadata,
        scope_note=scope_note,
    )
