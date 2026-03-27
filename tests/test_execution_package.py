"""Tests covering all four demo checkpoints from docs/ayush/kiro demo tasks.md."""

import pytest
from agent.execution_package import ExecutionPackage, format_execution_package, build_narration_summary
from server.services.fix_artifact_service import FixArtifact, package_hotfix, HotfixPackage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _artifact() -> FixArtifact:
    return FixArtifact(
        incident_id="inc-demo-1",
        source_path="demo-app/main.py",
        error_type="ZeroDivisionError",
        kiro_mode="fallback",
        spec_markdown="# Fix Spec\n## Requirements\n- Add zero guard",
        diff_preview="--- a/demo-app/main.py\n+++ b/demo-app/main.py\n@@ -1 +1 @@\n+guard",
        files_changed=["demo-app/main.py"],
        test_plan=["Verify /calculate/0 returns 400", "Confirm /calculate/5 still works"],
        fix_summary="Add zero-guard before division.",
        regression_warning="Verify all callers still work.",
    )


def _incident() -> dict:
    return {
        "incident_id": "inc-demo-1",
        "status": "gating",
        "severity": "medium",
        "service": "deepops-demo-app",
        "environment": "hackathon",
        "source": {
            "error_type": "ZeroDivisionError",
            "source_file": "demo-app/main.py",
            "path": "/calculate/0",
        },
    }


def _fix_result() -> dict:
    return {
        "status": "complete",
        "spec_markdown": "# Fix Spec",
        "diff_preview": "...",
        "files_changed": ["demo-app/main.py"],
        "test_plan": ["Verify /calculate/0 returns 400"],
        "_metadata": {
            "kiro_mode": "fallback",
            "fix_summary": "Add zero-guard.",
            "regression_warning": None,
        },
    }


# ---------------------------------------------------------------------------
# Checkpoint 1 — normal approved plan → execution package
# ---------------------------------------------------------------------------

def test_execution_package_has_required_fields():
    pkg = format_execution_package(_artifact())
    for f in ("execution_steps", "fix_spec", "diff_preview", "files_changed",
              "test_plan", "deployment_inputs", "narration_summary"):
        assert hasattr(pkg, f), f"missing field: {f}"


def test_execution_steps_are_numbered():
    pkg = format_execution_package(_artifact())
    for step in pkg.execution_steps:
        assert step[0].isdigit(), f"step not numbered: {step!r}"


def test_deployment_inputs_has_service_and_env():
    pkg = format_execution_package(_artifact())
    assert "service_name" in pkg.deployment_inputs
    assert "environment" in pkg.deployment_inputs


def test_mode_is_normal():
    pkg = format_execution_package(_artifact())
    assert pkg.mode == "normal"


# ---------------------------------------------------------------------------
# Checkpoint 2 — constrained plan still produces valid package
# ---------------------------------------------------------------------------

def test_skip_auth_constraint_removes_auth_files():
    artifact = _artifact()
    artifact.files_changed = ["demo-app/main.py", "auth_handler.py"]
    pkg = format_execution_package(artifact, constraints={"skip_auth": True})
    assert "auth_handler.py" not in pkg.files_changed


def test_hotfix_only_constraint_trims_steps():
    pkg = format_execution_package(_artifact(), constraints={"hotfix_only": True})
    assert len(pkg.execution_steps) == 2


def test_constraints_applied_is_populated():
    pkg = format_execution_package(_artifact(), constraints={"skip_auth": True})
    assert "skip_auth" in pkg.constraints_applied


def test_constrained_package_still_valid():
    pkg = format_execution_package(_artifact(), constraints={"skip_auth": True, "hotfix_only": True})
    for f in ("execution_steps", "fix_spec", "diff_preview", "files_changed",
              "test_plan", "deployment_inputs", "narration_summary"):
        assert hasattr(pkg, f), f"missing field: {f}"


# ---------------------------------------------------------------------------
# Checkpoint 3 — hotfix path
# ---------------------------------------------------------------------------

def test_hotfix_package_has_3_step_plan():
    pkg = package_hotfix(_incident(), _fix_result())
    assert isinstance(pkg, HotfixPackage)
    assert len(pkg.hotfix_plan) == 3


def test_hotfix_files_limited_to_primary():
    pkg = package_hotfix(_incident(), _fix_result())
    assert len(pkg.fix_artifact.files_changed) <= 1


def test_hotfix_test_plan_trimmed():
    pkg = package_hotfix(_incident(), _fix_result())
    assert len(pkg.fix_artifact.test_plan) <= 2


def test_hotfix_verification_checklist_has_3_items():
    pkg = package_hotfix(_incident(), _fix_result())
    assert len(pkg.verification_checklist) == 3


def test_hotfix_excluded_files_respected():
    pkg = package_hotfix(_incident(), _fix_result(), excluded_files=["demo-app/main.py"])
    assert pkg.fix_artifact.files_changed == []


def test_hotfix_scope_note_present():
    pkg = package_hotfix(_incident(), _fix_result())
    assert isinstance(pkg.scope_note, str) and len(pkg.scope_note) > 0


# ---------------------------------------------------------------------------
# Checkpoint 4 — narration summary
# ---------------------------------------------------------------------------

def test_narration_summary_is_string():
    summary = build_narration_summary(_artifact())
    assert isinstance(summary, str) and len(summary) > 0


def test_narration_mentions_source_path():
    summary = build_narration_summary(_artifact())
    assert "demo-app/main.py" in summary


def test_narration_with_constraints_mentions_them():
    summary = build_narration_summary(_artifact(), constraints_applied=["skip_auth"])
    assert "skip_auth" in summary
