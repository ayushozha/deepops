"""
Tests for agent/kiro_client.py — thin Kiro CLI wrapper.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent.kiro_client import KiroClient, _extract_diff, _extract_files_changed

# ---------------------------------------------------------------------------
# Sample diff used across multiple tests
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
--- a/demo-app/main.py
+++ b/demo-app/main.py
@@ -9,5 +9,8 @@
 async def calculate(value: int):
     logging.info(f"Calculating for {value}")
+    if value == 0:
+        raise HTTPException(status_code=400, detail="Cannot divide by zero")
     result = 100 / value
     return {"result": result}
"""


# ---------------------------------------------------------------------------
# CLI availability
# ---------------------------------------------------------------------------

def test_kiro_not_installed():
    client = KiroClient()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = client.run("# spec", repo_path=".")
    assert result["success"] is False
    assert result["exit_code"] == -1


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------

def test_kiro_timeout():
    client = KiroClient()
    exc = subprocess.TimeoutExpired(cmd=["kiro"], timeout=30)
    exc.stdout = b""
    exc.stderr = b""
    with patch("subprocess.run", side_effect=exc):
        result = client.run("# spec", repo_path=".")
    assert result["success"] is False
    assert result["exit_code"] == -2


# ---------------------------------------------------------------------------
# Output parsing helpers
# ---------------------------------------------------------------------------

def test_extract_diff_from_output():
    diff = _extract_diff(SAMPLE_DIFF)
    assert diff is not None
    assert "@@" in diff
    assert "+    if value == 0:" in diff


def test_extract_diff_returns_none_when_no_diff():
    assert _extract_diff("No diff here, just plain text.") is None


def test_extract_files_changed():
    diff = _extract_diff(SAMPLE_DIFF)
    files = _extract_files_changed(diff)
    assert len(files) == 1
    assert "demo-app/main.py" in files[0]


def test_extract_files_changed_empty_on_none():
    assert _extract_files_changed(None) == []


# ---------------------------------------------------------------------------
# Zero exit with empty output
# ---------------------------------------------------------------------------

def test_kiro_zero_exit_empty_output():
    client = KiroClient()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = ""
    with patch("subprocess.run", return_value=mock_proc):
        result = client.run("# spec", repo_path=".")
    assert result["success"] is False
    assert result["exit_code"] == 0
    assert "no usable diff output" in result["stderr"]


# ---------------------------------------------------------------------------
# call_tool import verification
# ---------------------------------------------------------------------------

def test_call_tool_import_from_tracing():
    import agent.kiro_client as kc
    import agent.tracing as tracing
    # local shim must be gone
    assert not hasattr(kc, 'call_tool') or kc.call_tool is tracing.call_tool


# ---------------------------------------------------------------------------
# Diff without extractable file paths
# ---------------------------------------------------------------------------

def test_kiro_diff_without_files_is_rejected():
    client = KiroClient()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "--- a/foo.py\n+++ b/foo.py\n@@ -1,2 +1,3 @@\n line\n+added\n"
    mock_proc.stderr = ""
    # Simulate a diff being parsed but no file paths extracted
    with patch("subprocess.run", return_value=mock_proc), \
         patch("agent.kiro_client._extract_files_changed", return_value=[]):
        result = client.run("# spec", repo_path=".")
    assert result["success"] is False
    assert "no file paths could be extracted" in result["stderr"]
