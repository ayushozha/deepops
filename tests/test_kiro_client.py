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
