"""
kiro_client.py - Thin wrapper around the Kiro CLI for fix generation.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from agent.tracing import call_tool as _traced_call_tool


# ---------------------------------------------------------------------------
# Output parsing helpers
# ---------------------------------------------------------------------------

_DIFF_RE = re.compile(r"(@@.*?(?=\n@@|\Z))", re.DOTALL)
_FILE_RE = re.compile(r"^\+\+\+\s+(?:b/)?(.+)$", re.MULTILINE)


def _extract_diff(text: str) -> str | None:
    """Return the first unified-diff block found in text, or None."""
    match = re.search(r"(---\s+.+\n\+\+\+\s+.+\n@@.+)", text, re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_files_changed(diff: str | None) -> list[str]:
    """Parse +++ lines from a diff to get changed file paths."""
    if not diff:
        return []
    return [m.group(1).strip() for m in _FILE_RE.finditer(diff)]


# ---------------------------------------------------------------------------
# KiroClient
# ---------------------------------------------------------------------------

class KiroClient:
    """
    Wraps the `kiro fix` CLI command.

    Usage::

        client = KiroClient()
        result = client.run(spec_markdown, repo_path="/path/to/repo")

    The returned dict always contains:
        success (bool), exit_code (int), stdout (str), stderr (str),
        diff_preview (str | None), files_changed (list[str])
    """

    CLI_BINARY = "kiro"

    def run(
        self,
        spec_markdown: str,
        repo_path: str,
        timeout: int = 30,
    ) -> dict:
        """
        Write spec to a temp file and invoke `kiro fix --spec <file> --repo <repo>`.

        Returns a result dict regardless of outcome.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix="deepops_spec_",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(spec_markdown)
            spec_file = tmp.name

        try:
            return _traced_call_tool("kiro_fix", self._invoke, spec_file, repo_path, timeout)
        finally:
            # Clean up temp file
            try:
                Path(spec_file).unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _invoke(self, spec_file: str, repo_path: str, timeout: int) -> dict:
        cmd = [self.CLI_BINARY, "fix", "--spec", spec_file, "--repo", repo_path]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return self._error_result(
                exit_code=-1,
                stderr=f"Kiro CLI not found. Install it and ensure '{self.CLI_BINARY}' is on PATH.",
            )
        except subprocess.TimeoutExpired as exc:
            partial_stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            partial_stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return self._error_result(
                exit_code=-2,
                stdout=partial_stdout,
                stderr=f"Kiro CLI timed out after {timeout}s.\n{partial_stderr}",
            )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        diff = _extract_diff(stdout) if stdout.strip() else None
        files_changed = _extract_files_changed(diff)

        if proc.returncode == 0 and diff is None and not stdout.strip():
            success = False
            stderr = (stderr + "\nKiro exited 0 but produced no usable diff output.").lstrip()
        elif proc.returncode == 0 and diff is not None and not files_changed:
            success = False
            stderr = (stderr + "\nKiro produced a diff but no file paths could be extracted.").lstrip()
        else:
            success = proc.returncode == 0

        return {
            "success": success,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "diff_preview": diff,
            "files_changed": files_changed,
        }

    @staticmethod
    def _error_result(
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
    ) -> dict:
        return {
            "success": False,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "diff_preview": None,
            "files_changed": [],
        }
